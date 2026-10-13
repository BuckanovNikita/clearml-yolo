"""User-wide FIFO reservations for whole NVIDIA GPUs."""

# Ticket and worker handles intentionally delegate to their owning queue in this module.
# ruff: noqa: SLF001

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Literal, Protocol, Self

from filelock import BaseFileLock, FileLock, Timeout

from clearml_yolo.adapters.runtime.gpu_resources import GPUDevice, GPUInventory
from clearml_yolo.core.execution import DEFAULT_MAX_USED_MEMORY_GIB

_SCHEMA_VERSION = 1
_State = Literal["pending", "active"]


class SnapshotProvider(Protocol):
    """Provide current devices and availability under the invoking job's policy."""

    def snapshot(self) -> tuple[GPUDevice, ...]: ...


@dataclass(frozen=True)
class DeviceAdmission:
    """One sampled card with exclusions from the same registry transaction."""

    device: GPUDevice
    logical_index: int | None
    in_selection: bool
    reserved_by: str | None = None

    @property
    def eligible(self) -> bool:
        return (
            self.logical_index is not None
            and self.in_selection
            and not self.device.busy
            and self.reserved_by is None
        )


@dataclass(frozen=True)
class AdmissionDiagnostics:
    """Detached admission evidence; UUID identities remain internal to scheduling."""

    requested_count: int
    visible_count: int
    max_used_memory_gib: float
    cards: tuple[DeviceAdmission, ...]
    ticket_id: str | None = None
    queue_position: int | None = None
    fifo_blocked_by: str | None = None
    admitted: tuple[str, ...] = ()

    @property
    def eligible_count(self) -> int:
        return sum(card.eligible for card in self.cards)

    @property
    def insufficient_capacity(self) -> bool:
        return self.eligible_count < self.requested_count


def admission_cards(
    snapshot: tuple[GPUDevice, ...],
    visible: tuple[str, ...],
    selection: tuple[str, ...],
    reservations: dict[str, str],
) -> tuple[DeviceAdmission, ...]:
    """Join sampled physical cards to CUDA order and the caller's exact selection."""
    ordinals = {uuid: index for index, uuid in enumerate(visible)}
    return tuple(
        DeviceAdmission(
            device,
            ordinals.get(device.uuid),
            device.uuid in selection,
            reservations.get(device.uuid),
        )
        for device in snapshot
    )


def queue_root() -> Path:
    """Return the per-user, same-operating-system queue state directory."""
    captured = os.environ.get("CY_GPU_QUEUE_ROOT")
    if captured:
        return Path(captured).expanduser()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        state = Path(base).expanduser() if base else Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_STATE_HOME")
        state = Path(base).expanduser() if base else Path.home() / ".local" / "state"
    return state / "clearml-yolo" / "queue"


def _integer(value: object, name: str, *, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise RuntimeError(f"GPU queue registry has invalid {name}")
    return value


def _strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RuntimeError(f"GPU queue registry has invalid {name}")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise RuntimeError(f"GPU queue registry has duplicate {name}")
    return result


@dataclass
class _Request:
    ticket: int
    count: int
    visible: tuple[str, ...]
    devices: tuple[str, ...]
    state: _State

    @classmethod
    def parse(cls, value: object) -> Self:
        if not isinstance(value, dict) or set(value) != {
            "ticket",
            "count",
            "visible",
            "devices",
            "state",
        }:
            raise RuntimeError("GPU queue registry has an invalid request")
        ticket = _integer(value["ticket"], "ticket", minimum=1)
        count = _integer(value["count"], "count", minimum=1)
        visible = _strings(value["visible"], "visible devices")
        devices = _strings(value["devices"], "assigned devices")
        state_value = value["state"]
        if state_value not in ("pending", "active"):
            raise RuntimeError("GPU queue registry has an invalid request state")
        if count > len(visible) or any(device not in visible for device in devices):
            raise RuntimeError("GPU queue registry has an inconsistent request")
        if state_value == "pending" and devices:
            raise RuntimeError("GPU queue registry has devices on a pending request")
        if state_value == "active" and len(devices) not in (1, count):
            raise RuntimeError("GPU queue registry has an invalid reservation size")
        return cls(ticket, count, visible, devices, state_value)

    def serialized(self) -> dict[str, object]:
        return {
            "ticket": self.ticket,
            "count": self.count,
            "visible": list(self.visible),
            "devices": list(self.devices),
            "state": self.state,
        }


@dataclass
class _Registry:
    next_ticket: int
    requests: list[_Request]

    @classmethod
    def parse(cls, value: object) -> Self:
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "next_ticket",
            "requests",
        }:
            raise RuntimeError("GPU queue registry has an invalid layout")
        if type(value["schema_version"]) is not int or value["schema_version"] != _SCHEMA_VERSION:
            raise RuntimeError("GPU queue registry has an unsupported schema version")
        next_ticket = _integer(value["next_ticket"], "next ticket", minimum=1)
        request_values = value["requests"]
        if not isinstance(request_values, list):
            raise RuntimeError("GPU queue registry requests must be a list")  # noqa: TRY004
        requests = [_Request.parse(item) for item in request_values]
        tickets = [request.ticket for request in requests]
        if tickets != sorted(tickets) or len(set(tickets)) != len(tickets):
            raise RuntimeError("GPU queue registry tickets are not strictly ordered")
        if tickets and tickets[-1] >= next_ticket:
            raise RuntimeError("GPU queue registry next ticket is not monotonic")
        reserved = [device for request in requests for device in request.devices]
        if len(set(reserved)) != len(reserved):
            raise RuntimeError("GPU queue registry contains overlapping reservations")
        return cls(next_ticket, requests)

    def serialized(self) -> dict[str, object]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "next_ticket": self.next_ticket,
            "requests": [request.serialized() for request in self.requests],
        }


def _native_lock(path: Path) -> BaseFileLock:
    return FileLock(
        path,
        timeout=0,
        fallback_to_soft=False,
        preserve_lock_file=True,
    )


class GPUQueue:
    """Coordinate short registry transactions and durable GPU reservations."""

    def __init__(
        self,
        root: Path | None = None,
        inventory: SnapshotProvider | None = None,
    ) -> None:
        self.root = Path(root) if root is not None else queue_root()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._inventory = inventory if inventory is not None else GPUInventory()
        self._registry_path = self.root / "registry.json"
        self._registry_lock = _native_lock(self.root / "registry.lock")

    def register(
        self, count: int, visible: tuple[str, ...], *, cuda_visible: tuple[str, ...] | None = None
    ) -> "Ticket":
        """Publish a pending request after acquiring its supervisor liveness lock."""
        if type(count) is not int or count <= 0:
            raise ValueError("GPU count must be a positive integer")
        # Validate public callers at runtime even when static types are correct.
        if any(not isinstance(device, str) or not device for device in visible):  # type: ignore[redundant-expr]
            raise ValueError("visible GPU UUIDs must be non-empty strings")
        if len(set(visible)) != len(visible):
            raise ValueError("visible GPU UUIDs must be unique")
        if count > len(visible):
            raise ValueError("GPU count exceeds the visible GPU set")
        inherited = visible if cuda_visible is None else cuda_visible
        if len(set(inherited)) != len(inherited) or any(uuid not in inherited for uuid in visible):
            raise ValueError("Selection must be a subset of unique CUDA-visible GPUs")

        supervisor_lock: BaseFileLock | None = None
        with self._locked_registry():
            registry = self._read_registry()
            self._reap_stale(registry)
            ticket_number = registry.next_ticket
            supervisor_lock = _native_lock(self._supervisor_path(ticket_number))
            try:
                supervisor_lock.acquire(timeout=0)
            except Timeout:
                raise RuntimeError(
                    "GPU queue supervisor liveness lock is unexpectedly held"
                ) from None
            registry.next_ticket += 1
            registry.requests.append(_Request(ticket_number, count, visible, (), "pending"))
            try:
                self._write_registry(registry)
            except BaseException:
                supervisor_lock.release()
                raise
        return Ticket(self, str(ticket_number), supervisor_lock, inherited)

    def claim_worker(self, ticket_id: str) -> "WorkerClaim":
        """Return a context manager that validates and owns child liveness."""
        return WorkerClaim(self, ticket_id)

    def _position(self, ticket_id: str) -> int:
        ticket_number = self._ticket_number(ticket_id)
        with self._locked_registry():
            registry = self._read_registry()
            changed = self._reap_stale(registry)
            request = self._request(registry, ticket_number)
            if request is None:
                if changed:
                    self._write_registry(registry)
                raise ValueError("GPU queue ticket is closed or missing")
            if changed:
                self._write_registry(registry)
            if request.state == "active":
                return 0
            pending = [item for item in registry.requests if item.state == "pending"]
            return pending.index(request) + 1

    def _devices(self, ticket_id: str) -> tuple[str, ...]:
        ticket_number = self._ticket_number(ticket_id)
        with self._locked_registry():
            registry = self._read_registry()
            changed = self._reap_stale(registry)
            request = self._request(registry, ticket_number)
            if request is None:
                if changed:
                    self._write_registry(registry)
                raise ValueError("GPU queue ticket is closed or missing")
            if changed:
                self._write_registry(registry)
            return request.devices

    def _live_request(self, ticket_number: int) -> tuple[_Registry, _Request]:
        """Read and validate a live request while the caller holds the transaction."""
        registry = self._read_registry()
        if self._reap_stale(registry):
            self._write_registry(registry)
        request = self._request(registry, ticket_number)
        if request is None:
            raise ValueError("GPU queue ticket is closed or missing")
        return registry, request

    def _try_acquire(
        self, ticket_id: str, cuda_visible: tuple[str, ...]
    ) -> tuple[tuple[str, ...] | None, AdmissionDiagnostics | None]:
        ticket_number = self._ticket_number(ticket_id)
        with self._locked_registry():
            _, request = self._live_request(ticket_number)
            if request.state == "active":
                return request.devices, None

        # Driver calls may block. Never hold the shared transaction while probing.
        snapshot = self._inventory.snapshot()
        known, externally_busy = self._availability(snapshot)
        with self._locked_registry():
            registry, request = self._live_request(ticket_number)
            if request.state == "active":
                return request.devices, None
            missing = [device for device in request.visible if device not in known]
            if missing:
                raise RuntimeError(f"GPU visibility was lost for physical GPU UUIDs: {missing}")
            # Each supervisor owns its availability policy. Never admit another
            # project's ticket using this caller's memory threshold.
            pending = [item for item in registry.requests if item.state == "pending"]
            head = pending[0]
            reservations = {
                device: str(item.ticket)
                for item in registry.requests
                if item.state == "active"
                for device in item.devices
            }
            occupied = set(reservations) | externally_busy
            available = tuple(device for device in request.visible if device not in occupied)
            selected = (
                available[: request.count]
                if head is request and len(available) >= request.count
                else ()
            )
            diagnostics = AdmissionDiagnostics(
                requested_count=request.count,
                visible_count=len(cuda_visible),
                max_used_memory_gib=(
                    self._inventory.max_used_memory_gib
                    if isinstance(self._inventory, GPUInventory)
                    else DEFAULT_MAX_USED_MEMORY_GIB
                ),
                cards=admission_cards(snapshot, cuda_visible, request.visible, reservations),
                ticket_id=ticket_id,
                queue_position=pending.index(request) + 1,
                fifo_blocked_by=str(head.ticket) if head is not request else None,
                admitted=selected,
            )
            if selected:
                request.devices = selected
                request.state = "active"
                self._write_registry(registry)
            return selected or None, diagnostics

    def _close_ticket(self, ticket_id: str) -> None:
        ticket_number = self._ticket_number(ticket_id)
        with self._locked_registry():
            registry = self._read_registry()
            changed = self._reap_stale(registry)
            request = self._request(registry, ticket_number)
            if request is not None and not self._lock_is_held(self._worker_path(ticket_number)):
                registry.requests.remove(request)
                changed = True
            if changed:
                self._write_registry(registry)

    def _claim(self, ticket_id: str) -> tuple[BaseFileLock, tuple[str, ...]]:
        ticket_number = self._ticket_number(ticket_id)
        with self._locked_registry():
            registry = self._read_registry()
            changed = self._reap_stale(registry)
            worker_lock = _native_lock(self._worker_path(ticket_number))
            try:
                worker_lock.acquire(timeout=0)
            except Timeout:
                if changed:
                    self._write_registry(registry)
                raise RuntimeError("GPU queue ticket already has a live worker") from None
            request = self._request(registry, ticket_number)
            if request is None or request.state != "active":
                worker_lock.release()
                if changed:
                    self._write_registry(registry)
                raise ValueError("GPU queue ticket is missing or has not been admitted")
            if changed:
                self._write_registry(registry)
            return worker_lock, request.devices

    def _shrink(self, ticket_id: str) -> tuple[str, ...]:
        ticket_number = self._ticket_number(ticket_id)
        with self._locked_registry():
            _, request = self._live_request(ticket_number)
            if request.state != "active":
                raise ValueError("GPU queue ticket has not been admitted")
            if len(request.devices) <= 1:
                return request.devices

        if isinstance(self._inventory, GPUInventory):
            # A fresh worker inherits narrowed CUDA visibility. Only its lease's
            # telemetry can prevent safe contraction, never an unrelated hidden card.
            self._inventory.restrict_to(request.devices)
        known, externally_busy = self._availability(self._inventory.snapshot())
        with self._locked_registry():
            registry, request = self._live_request(ticket_number)
            if request.state != "active":
                raise ValueError("GPU queue ticket has not been admitted")
            surplus = request.devices[1:]
            if any(device not in known for device in surplus):
                raise RuntimeError("GPU queue cannot release a device with unknown telemetry")
            if any(device in externally_busy for device in surplus):
                raise RuntimeError("GPU queue cannot release a device at or above its memory limit")
            request.devices = request.devices[:1]
            self._write_registry(registry)
            return request.devices

    def _cleanup(self) -> None:
        with self._locked_registry():
            registry = self._read_registry()
            if self._reap_stale(registry):
                self._write_registry(registry)

    @contextmanager
    def _locked_registry(self) -> Iterator[None]:
        with self._registry_lock.acquire(timeout=10):
            yield

    def _read_registry(self) -> _Registry:
        if not self._registry_path.exists():
            return _Registry(next_ticket=1, requests=[])
        try:
            raw: object = json.loads(self._registry_path.read_text(encoding="utf-8"))
            return _Registry.parse(raw)
        except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as error:
            raise RuntimeError(f"GPU queue registry is corrupt: {error}") from None

    def _write_registry(self, registry: _Registry) -> None:
        payload = json.dumps(registry.serialized(), separators=(",", ":"), sort_keys=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.root,
                prefix=".registry-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
            temporary_path.replace(self._registry_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _reap_stale(self, registry: _Registry) -> bool:
        live: list[_Request] = []
        for request in registry.requests:
            supervisor_live = self._lock_is_held(self._supervisor_path(request.ticket))
            worker_live = self._lock_is_held(self._worker_path(request.ticket))
            if supervisor_live or worker_live:
                live.append(request)
        if len(live) == len(registry.requests):
            return False
        registry.requests = live
        return True

    @staticmethod
    def _availability(inventory: tuple[GPUDevice, ...]) -> tuple[set[str], set[str]]:
        known: set[str] = set()
        busy: set[str] = set()
        for device in inventory:
            if not device.uuid or device.uuid in known:
                raise RuntimeError("GPU inventory contains invalid or duplicate UUIDs")
            known.add(device.uuid)
            if device.busy:
                busy.add(device.uuid)
        return known, busy

    def _lock_is_held(self, path: Path) -> bool:
        probe = _native_lock(path)
        try:
            probe.acquire(timeout=0)
        except Timeout:
            return True
        probe.release()
        return False

    @staticmethod
    def _request(registry: _Registry, ticket: int) -> _Request | None:
        return next((request for request in registry.requests if request.ticket == ticket), None)

    @staticmethod
    def _ticket_number(ticket_id: str) -> int:
        if not ticket_id.isascii() or not ticket_id.isdecimal():
            raise ValueError("GPU queue ticket ID is invalid")
        ticket = int(ticket_id)
        if ticket <= 0 or str(ticket) != ticket_id:
            raise ValueError("GPU queue ticket ID is invalid")
        return ticket

    def _supervisor_path(self, ticket: int) -> Path:
        return self.root / f"supervisor-{ticket}.lock"

    def _worker_path(self, ticket: int) -> Path:
        return self.root / f"worker-{ticket}.lock"


class Ticket:
    """A supervisor-owned pending or active queue request."""

    def __init__(
        self,
        queue: GPUQueue,
        ticket_id: str,
        supervisor_lock: BaseFileLock,
        cuda_visible: tuple[str, ...],
    ) -> None:
        self.id = ticket_id
        self._queue = queue
        self._supervisor_lock = supervisor_lock
        self._closed = False
        self._cuda_visible = cuda_visible
        self._diagnostics: AdmissionDiagnostics | None = None

    @property
    def diagnostics(self) -> AdmissionDiagnostics | None:
        """Last acquisition's immutable decision, without a second probe or transaction."""
        return self._diagnostics

    @property
    def devices(self) -> tuple[str, ...]:
        self._ensure_open()
        return self._queue._devices(self.id)

    def position(self) -> int:
        self._ensure_open()
        return self._queue._position(self.id)

    def try_acquire(self) -> tuple[str, ...] | None:
        self._ensure_open()
        selected, diagnostics = self._queue._try_acquire(self.id, self._cuda_visible)
        if diagnostics is not None:
            self._diagnostics = diagnostics
        return selected

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._queue._close_ticket(self.id)
        finally:
            self._supervisor_lock.release()
            self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("GPU queue ticket is closed or missing")


class WorkerClaim:
    """A worker-owned liveness claim for one admitted ticket."""

    def __init__(self, queue: GPUQueue, ticket_id: str) -> None:
        self._queue = queue
        self._ticket_id = ticket_id
        self._worker_lock: BaseFileLock | None = None
        self._devices: tuple[str, ...] = ()

    def __enter__(self) -> Self:
        if self._worker_lock is not None:
            raise RuntimeError("GPU queue worker claim is already active")
        self._worker_lock, self._devices = self._queue._claim(self._ticket_id)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # Context-manager protocol; close never suppresses errors.
        del exc_type, exc_value, traceback
        self.close()

    @property
    def devices(self) -> tuple[str, ...]:
        self._ensure_active()
        self._devices = self._queue._devices(self._ticket_id)
        return self._devices

    def shrink(self) -> tuple[str, ...]:
        self._ensure_active()
        self._devices = self._queue._shrink(self._ticket_id)
        return self._devices

    def close(self) -> None:
        if self._worker_lock is None:
            return
        worker_lock = self._worker_lock
        self._worker_lock = None
        worker_lock.release()
        self._queue._cleanup()

    def _ensure_active(self) -> None:
        if self._worker_lock is None:
            raise RuntimeError("GPU queue worker claim is not active")
