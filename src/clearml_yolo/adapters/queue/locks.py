"""Host-global generation locks separate reserved capacity from process evidence."""

import fcntl
import hashlib
import os
import re
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from clearml_yolo.adapters.queue.coordination import (
    host_directory,
    host_transaction,
    shared_descriptor,
)
from clearml_yolo.adapters.queue.generations import (
    advance_generation,
    current_generations,
    device_key,
    generation_events,
)
from clearml_yolo.adapters.queue.storage import atomic_write
from clearml_yolo.core.queue import (
    QUEUE_COMPATIBILITY,
    GPUFreeResult,
    GPUHold,
    GuardianClaim,
    WorkerIdentity,
    claim_token,
)

_MAX_RECORD_BYTES = 65536
_CONTROL_COMPATIBILITY = "shared-cy-queue-gpu-controls-v1"
_CONTROL_FENCE = "gpu-controls.claim.json"
_GENERATION_FENCE = "gpu-generations.claim.json"
_GENERATION_COMPATIBILITY = "shared-cy-queue-gpu-generations-v2"


def _read_claim(path: Path) -> GuardianClaim | None:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(status.st_mode) or status.st_size > _MAX_RECORD_BYTES:
        raise RuntimeError("Host-local GPU claim is not a bounded regular record")
    try:
        claim = GuardianClaim.model_validate_json(path.read_bytes())
    except ValidationError as error:
        raise RuntimeError("Host-local GPU claim protocol is corrupt; admission refused") from error
    if status.st_uid != claim.owner_uid or stat.S_IMODE(status.st_mode) & 0o022:
        raise PermissionError("GPU claim ownership does not match its filesystem record")
    return claim


def _write_claim(path: Path, claim: GuardianClaim | None) -> None:
    if claim is None:
        path.unlink(missing_ok=True)
        return
    payload = claim.model_dump_json()
    if len(payload.encode()) > _MAX_RECORD_BYTES:
        raise RuntimeError("Host-local GPU lock record exceeds its bounded size")
    atomic_write(path, payload)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class GPULease:
    """A process lease survives revocation while capacity writes remain fenced."""

    def __init__(
        self,
        pool: "LocalGPULocks",
        descriptors: dict[str, int],
        claim: GuardianClaim,
        *,
        recovering: bool = False,
    ) -> None:
        self.pool = pool
        self.descriptors = descriptors
        self.claim = claim
        self.recovering = recovering
        self._owned_generations = {
            uuid: dict(claim.generations).get(uuid, 0) for uuid in descriptors
        }

    def _generation(self, uuid: str) -> int:
        return dict(self.claim.generations).get(uuid, 0)

    def _current_devices(self) -> tuple[str, ...]:
        current = current_generations(self.pool.root)
        return tuple(
            uuid for uuid in self.descriptors if current.get(uuid, 0) == self._generation(uuid)
        )

    def is_current_in_transaction(self) -> bool:
        """Caller holds the pool transaction through the final launch gate."""
        return set(self.claim.devices) == set(self._current_devices())

    def is_current(self) -> bool:
        with self.pool.transaction():
            return self.is_current_in_transaction()

    def persist(self, claim: GuardianClaim) -> None:
        if claim.job_id != self.claim.job_id or claim.devices != self.claim.devices:
            raise ValueError("A guardian cannot replace the identity or devices of its lease")
        claim = claim.model_copy(update={"generations": self.claim.generations})
        with self.pool.transaction():
            for uuid in self._current_devices():
                _write_claim(self.pool.claim_path(uuid, self._generation(uuid)), claim)
            # Revocation never removes descendant evidence used by process recovery.
            _write_claim(self.pool.evidence_path(claim), claim)
        self.claim = claim

    def retain_first(self) -> GuardianClaim:
        """Keep the original first inference device, even when manually freed."""
        if not self.claim.devices or set(self.descriptors) != set(self.claim.devices):
            raise RuntimeError("GPU handoff requires the complete live allocation")
        if len(self.claim.devices) == 1:
            return self.claim
        retained, *released = self.claim.devices
        reduced = self.claim.model_copy(
            update={
                "devices": (retained,),
                "generations": tuple(
                    pair for pair in self.claim.generations if pair[0] == retained
                ),
            }
        )
        with self.pool.transaction():
            current_devices = self._current_devices()
            for uuid in current_devices:
                current = _read_claim(self.pool.claim_path(uuid, self._generation(uuid)))
                if current is None or claim_token(current) != claim_token(self.claim):
                    raise RuntimeError("GPU handoff record changed before partial release")
            for uuid in released:
                if uuid in current_devices:
                    _write_claim(self.pool.claim_path(uuid, self._generation(uuid)), None)
                else:
                    # Recovery reconstructs only the reduced allocation, so drop
                    # this lease's historical sibling before forgetting it.
                    self._remove_historical(uuid, self._generation(uuid))
            _sync_directory(self.pool.root)
            if retained in current_devices:
                _write_claim(self.pool.claim_path(retained, self._generation(retained)), reduced)
            _write_claim(self.pool.evidence_path(reduced), reduced)
            self.claim = reduced
            for uuid in released:
                descriptor = self.descriptors.pop(uuid)
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
        return reduced

    def release_verified(self) -> None:
        with self.pool.transaction():
            self.release_in_transaction()

    def release_in_transaction(self) -> None:
        """Only clear capacity still belonging to this lease's generation."""
        current_devices = self._current_devices()
        for uuid in current_devices:
            current = _read_claim(self.pool.claim_path(uuid, self._generation(uuid)))
            if current is None and self.recovering:
                continue
            if current is None or claim_token(current) != claim_token(self.claim):
                raise RuntimeError("GPU cleanup record changed before verified release")
        for uuid in current_devices:
            _write_claim(self.pool.claim_path(uuid, self._generation(uuid)), None)
        self.pool.evidence_path(self.claim).unlink(missing_ok=True)
        # Historical records can outlive a partial handoff after operator revocation.
        for uuid, generation in self._owned_generations.items():
            if uuid not in current_devices:
                self._remove_historical(uuid, generation)
        _sync_directory(self.pool.root)

    def _remove_historical(self, uuid: str, generation: int) -> None:
        path = self.pool.claim_path(uuid, generation)
        current = _read_claim(path)
        if current is not None and self.pool.same_process_owner(current, self.claim):
            path.unlink(missing_ok=True)

    def close(self) -> None:
        descriptors, self.descriptors = self.descriptors, {}
        for descriptor in descriptors.values():
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


class LocalGPULocks:
    """Global per-host UUID coordination across queue roots and mount aliases."""

    def __init__(self, identity: WorkerIdentity, root: Path | None = None) -> None:
        self.identity = identity
        self.local_root = root
        self.root = host_directory(identity.host_id, root)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with host_transaction(
            self.identity.host_id, name="gpu-transaction.lock", root=self.local_root
        ):
            yield

    def ensure_control_fence(self) -> None:
        """Fence legacy admission, preserving normal completion of existing leases."""
        with self.transaction():
            self._ensure_control_fence()

    def _ensure_control_fence(self) -> None:
        # A second incompatible sentinel also fences deployed v1 control workers.
        for name, compatibility in (
            (_CONTROL_FENCE, _CONTROL_COMPATIBILITY),
            (_GENERATION_FENCE, _GENERATION_COMPATIBILITY),
        ):
            path = self.root / name
            existing = _read_claim(path)
            if existing is not None:
                self._validate_fence(existing, compatibility)
                continue
            _write_claim(path, self._fence(os.geteuid(), compatibility))

    def _fence(self, uid: int, compatibility: str) -> GuardianClaim:
        return GuardianClaim(
            compatibility=compatibility,
            job_id="gpu-controls-fence",
            owner_uid=uid,
            host_id=self.identity.host_id,
            boot_id="persistent-control",
            queue_root="",
            devices=(),
            marker="gpu-controls-fence",
            guardian_pid=0,
            guardian_born=0,
        )

    def _validate_fence(self, claim: GuardianClaim, compatibility: str) -> None:
        if claim != self._fence(claim.owner_uid, compatibility):
            raise RuntimeError("GPU control admission fence is corrupt")

    def _generation(self, uuid: str) -> int:
        return current_generations(self.root).get(uuid, 0)

    def hold_path(self, uuid: str, uid: int, generation: int | None = None) -> Path:
        selected = self._generation(uuid) if generation is None else generation
        suffix = f"-g{selected}" if selected else ""
        return self.root / f"hold-{device_key(uuid)}-{uid}{suffix}.json"

    def _holds(self) -> tuple[GPUHold, ...]:
        generations = {
            device_key(uuid): gen for uuid, gen in current_generations(self.root).items()
        }
        holds: list[GPUHold] = []
        for path in self.root.glob("hold-*.json"):
            match = re.fullmatch(r"hold-([0-9a-f]{64})-[0-9]+(?:-g([0-9]+))?\.json", path.name)
            if match is None:
                raise RuntimeError("GPU hold filename is corrupt")
            generation = int(match[2] or 0)
            if generation != generations.get(match[1], 0):
                continue
            status = path.lstat()
            if not stat.S_ISREG(status.st_mode) or status.st_size > _MAX_RECORD_BYTES:
                raise RuntimeError("GPU hold is not a bounded regular record")
            try:
                hold = GPUHold.model_validate_json(path.read_bytes())
            except ValidationError as error:
                raise RuntimeError("GPU hold protocol is corrupt; admission refused") from error
            if (
                status.st_uid != hold.owner_uid
                or stat.S_IMODE(status.st_mode) & 0o022
                or hold.host_id != self.identity.host_id
                or path != self.hold_path(hold.uuid, hold.owner_uid, hold.generation)
            ):
                raise PermissionError("GPU hold ownership or identity differs from its record")
            holds.append(hold)
        return tuple(holds)

    def holds(self) -> tuple[GPUHold, ...]:
        with self.transaction():
            return self._holds()

    def disable(self, uuid: str) -> GPUHold:
        with self.transaction():
            self._ensure_control_fence()
            hold = GPUHold(
                uuid=uuid,
                owner_uid=os.geteuid(),
                host_id=self.identity.host_id,
                created_at=time.time(),
                generation=self._generation(uuid),
            )
            atomic_write(self.hold_path(uuid, hold.owner_uid), hold.model_dump_json())
        return hold

    def enable(self, uuid: str) -> None:
        with self.transaction():
            self._ensure_control_fence()
            self.hold_path(uuid, os.geteuid()).unlink(missing_ok=True)
            _sync_directory(self.root)

    def free(self, uuid: str) -> GPUFreeResult:
        # Do not inspect claims, process liveness, holds, or queue storage here.
        with self.transaction():
            self._ensure_control_fence()
            return advance_generation(self.root, uuid)

    def _path(self, uuid: str, generation: int | None = None) -> Path:
        selected = self._generation(uuid) if generation is None else generation
        suffix = f"-g{selected}" if selected else ""
        return self.root / f"gpu-{device_key(uuid)}{suffix}.lock"

    def claim_path(self, uuid: str, generation: int | None = None) -> Path:
        return self._path(uuid, generation).with_suffix(".claim.json")

    def evidence_path(self, claim: GuardianClaim) -> Path:
        identity = (claim.owner_uid, claim.queue_root, claim.job_id, claim.marker)
        key = hashlib.sha256(repr(identity).encode()).hexdigest()
        return self.root / f"evidence-{key}.json"

    def acquire(self, claim: GuardianClaim) -> GPULease | None:
        return self._acquire(claim, recovery=False)

    def acquire_recovery(self, claim: GuardianClaim) -> GPULease:
        if claim.owner_uid != os.geteuid():
            raise PermissionError("Only the effective owner may recover GPU capacity")
        lease = self._acquire(claim, recovery=True)
        if lease is None:
            raise RuntimeError("GPU guardian still owns its locks; recovery refused")
        return lease

    def transaction_claims(self) -> tuple[GuardianClaim, ...]:
        """Return capacity projections; private evidence remains in claim_for()."""
        result: list[GuardianClaim] = []
        generations = current_generations(self.root)
        for claim in self._claims(live_only=True):
            owned = dict(claim.generations)
            devices = tuple(
                uuid
                for uuid in claim.devices
                if owned.get(uuid, 0) == generations.get(uuid, 0)
                and self._locked(uuid, generations.get(uuid, 0))
            )
            if devices:
                projected = claim.model_copy(update={"devices": devices})
                if projected not in result:
                    result.append(projected)
        return tuple(result)

    def transaction_recovery(self, claim: GuardianClaim) -> GPULease:
        """Pin old process ownership without claiming a newer capacity generation."""
        if claim.owner_uid != os.geteuid():
            raise PermissionError("Only the effective owner may recover GPU capacity")
        acquired: dict[str, int] = {}
        try:
            self._take_recovery_locks(claim, acquired)
        except BaseException:
            self._close_descriptors(acquired)
            raise
        return GPULease(self, acquired, claim, recovering=True)

    def _take_recovery_locks(self, claim: GuardianClaim, acquired: dict[str, int]) -> None:
        for uuid in sorted(claim.devices):
            generation = dict(claim.generations).get(uuid, 0)
            if not self._take_lock(uuid, generation, acquired):
                raise RuntimeError("GPU guardian still owns its locks; recovery refused")
            self._validate_recovery(uuid, generation, claim)

    def _prepare_claim(self, claim: GuardianClaim) -> GuardianClaim | None:
        if any(hold.uuid in claim.devices for hold in self._holds()):
            return None
        generations = current_generations(self.root)
        # Observe every selected lock before advancing any generation.
        if any(self._locked(uuid, generations.get(uuid, 0)) for uuid in claim.devices):
            return None
        for uuid in claim.devices:
            generation = generations.get(uuid, 0)
            # A handoff can delete a sibling record before committing its reduced
            # allocation. The old lock inode still identifies that recovery epoch,
            # so every reuse needs a new generation even without a claim file.
            if self._path(uuid, generation).exists() or self.claim_path(uuid, generation).exists():
                generations[uuid] = advance_generation(self.root, uuid).generation
        return claim.model_copy(
            update={
                "generations": tuple(
                    (uuid, generations[uuid]) for uuid in claim.devices if generations.get(uuid, 0)
                )
            }
        )

    @staticmethod
    def _close_descriptors(acquired: dict[str, int]) -> None:
        for descriptor in acquired.values():
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _acquire(self, claim: GuardianClaim, *, recovery: bool) -> GPULease | None:
        acquired: dict[str, int] = {}
        succeeded = False
        with self.transaction():
            self._ensure_control_fence()
            if not recovery:
                prepared = self._prepare_claim(claim)
                if prepared is None:
                    return None
                claim = prepared
            try:
                for uuid in sorted(claim.devices):
                    generation = dict(claim.generations).get(uuid, 0)
                    if not self._take_lock(uuid, generation, acquired):
                        return None
                    if recovery:
                        self._validate_recovery(uuid, generation, claim)
                if not recovery:
                    for uuid in acquired:
                        _write_claim(
                            self.claim_path(uuid, dict(claim.generations).get(uuid, 0)), claim
                        )
                    _write_claim(self.evidence_path(claim), claim)
                succeeded = True
                return GPULease(self, acquired, claim, recovering=recovery)
            finally:
                if not succeeded:
                    self._close_descriptors(acquired)

    def _take_lock(self, uuid: str, generation: int, acquired: dict[str, int]) -> bool:
        descriptor = shared_descriptor(self._path(uuid, generation))
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            return False
        acquired[uuid] = descriptor
        return True

    def _locked(self, uuid: str, generation: int) -> bool:
        path = self._path(uuid, generation)
        if not path.exists():
            return False
        descriptor = shared_descriptor(path)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            return False
        finally:
            os.close(descriptor)

    @staticmethod
    def same_process_owner(first: GuardianClaim, second: GuardianClaim) -> bool:
        return (first.job_id, first.owner_uid, first.host_id, first.marker, first.queue_root) == (
            second.job_id,
            second.owner_uid,
            second.host_id,
            second.marker,
            second.queue_root,
        )

    def _validate_recovery(self, uuid: str, generation: int, claim: GuardianClaim) -> None:
        current = _read_claim(self.claim_path(uuid, generation))
        # Reduced allocations can leave historical sibling records after handoff.
        if current is not None and not self.same_process_owner(current, claim):
            raise RuntimeError("GPU recovery claim does not own the historical device")

    def _claims(self, *, live_only: bool = False) -> tuple[GuardianClaim, ...]:
        claims: list[GuardianClaim] = []
        generations = {
            device_key(uuid): gen for uuid, gen in current_generations(self.root).items()
        }
        for path in self.root.glob("gpu-*.claim.json"):
            if path.name in {_CONTROL_FENCE, _GENERATION_FENCE}:
                continue
            if live_only:
                match = re.fullmatch(r"gpu-([0-9a-f]{64})(?:-g([0-9]+))?\.claim\.json", path.name)
                if match is None or int(match[2] or 0) != generations.get(match[1], 0):
                    continue
                lock_path = path.with_name(path.name.removesuffix(".claim.json") + ".lock")
                descriptor = shared_descriptor(lock_path)
                try:
                    try:
                        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        pass
                    else:
                        fcntl.flock(descriptor, fcntl.LOCK_UN)
                        continue
                finally:
                    os.close(descriptor)
            claim = _read_claim(path)
            if claim is not None:
                if claim.host_id != self.identity.host_id:
                    raise RuntimeError("GPU claim belongs to a different host namespace")
                if live_only and claim.compatibility != QUEUE_COMPATIBILITY:
                    raise RuntimeError("An incompatible active guardian stops GPU admission")
                claims.append(claim)
        return tuple(claims)

    def reserved(self) -> set[str]:
        with self.transaction():
            return {hold.uuid for hold in self._holds()} | {
                uuid for claim in self.transaction_claims() for uuid in claim.devices
            }

    def known_devices(self) -> tuple[str, ...]:
        with self.transaction():
            return tuple(
                dict.fromkeys(
                    (
                        *(uuid for claim in self._claims() for uuid in claim.devices),
                        *(hold.uuid for hold in self._holds()),
                        *(event.uuid for event in generation_events(self.root)),
                    )
                )
            )

    def allocated_devices(self, job_id: str) -> tuple[str, ...]:
        with self.transaction():
            return tuple(
                dict.fromkeys(
                    uuid
                    for claim in self.transaction_claims()
                    if claim.job_id == job_id
                    for uuid in claim.devices
                )
            )

    @staticmethod
    def _process_order(claim: GuardianClaim) -> tuple[int, int, int]:
        return (
            claim.ownership_since,
            claim.guardian_born,
            max(dict(claim.generations).values(), default=0),
        )

    def claim_for(self, job_id: str, *, marker: str | None = None) -> GuardianClaim | None:
        with self.transaction():
            evidence = [
                claim
                for path in self.root.glob("evidence-*.json")
                if (claim := _read_claim(path)) is not None
                and claim.job_id == job_id
                and (marker is None or claim.marker == marker)
            ]
            claims = [
                claim
                for claim in self._claims()
                if claim.job_id == job_id and (marker is None or claim.marker == marker)
            ]
        if not claims and not evidence:
            return None
        newest = max((*claims, *evidence), key=self._process_order)
        claims = [claim for claim in claims if self.same_process_owner(claim, newest)]
        evidence = [claim for claim in evidence if self.same_process_owner(claim, newest)]
        # Evidence is independent of current capacity. A committed reduced capacity
        # record takes precedence over the pre-handoff evidence after interruption.
        candidates = evidence or claims
        reduced = [claim for claim in claims if len(claim.devices) < len(candidates[0].devices)]
        if reduced:
            candidates = reduced
        first = candidates[0]
        stable = first.model_dump(exclude={"child_pid", "child_born", "identities"})
        if any(
            claim.model_dump(exclude={"child_pid", "child_born", "identities"}) != stable
            for claim in candidates
        ):
            raise RuntimeError("GPU recovery evidence has inconsistent ownership")
        latest = max(
            candidates, key=lambda claim: (claim.child_pid is not None, len(claim.identities))
        )
        identities: dict[int, int] = {}
        for claim in candidates:
            for pid, born in claim.identities:
                identities[pid] = max(identities.get(pid, 0), born)
        return latest.model_copy(update={"identities": tuple(sorted(identities.items()))})
