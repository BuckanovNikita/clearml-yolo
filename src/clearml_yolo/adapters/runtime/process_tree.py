"""Linux invocation ownership across native children that start new sessions."""

import ctypes
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import override
from uuid import uuid4

OWNER_ENV = "CY_MODEL_PROCESS_OWNER"
DIRECT_OWNER_ENV = "CY_DIRECT_MODEL_PROCESS_OWNER"
_SUPERVISION_PROBE_TIMEOUT_SECONDS = 10.0
_SUPERVISION_PROBE_SUCCESS = "cy-process-supervision-ok-v1"


@dataclass(frozen=True)
class _Process:
    pid: int
    parent: int
    session: int
    born: int
    state: str


class UnverifiableProcessTreeError(RuntimeError):
    """A fresh scan cannot currently rule out owned living processes."""


def _read_process(pid: int) -> _Process | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return _Process(pid, int(fields[1]), int(fields[3]), int(fields[19]), fields[0])


def _probe_pidfd() -> None:
    """Signal zero checks kernel support without delivering a signal or reaping a child."""
    operation = "os.pidfd_open"
    try:
        descriptor = os.pidfd_open(os.getpid())
        try:
            operation = "signal.pidfd_send_signal"
            signal.pidfd_send_signal(descriptor, 0)
            operation = "os.waitid(P_PIDFD)"
            # Our own pidfd is not a child. ECHILD proves this idtype was accepted.
            with suppress(ChildProcessError):
                os.waitid(os.P_PIDFD, descriptor, os.WEXITED | os.WNOHANG)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise RuntimeError(
            f"Process supervision unavailable in {sys.executable}: {operation} "
            f"failed ({error}); native work has not started"
        ) from error


def require_process_supervision() -> None:
    """Reject unsupported Python/kernel capabilities before expensive native execution."""
    if sys.platform != "linux":
        raise RuntimeError(f"Process supervision requires Linux: {sys.executable}")
    # These stdlib APIs are optional build/platform capabilities, not Python-version guarantees.
    required = {
        os: ("pidfd_open", "waitid", "P_PIDFD", "pipe2", "register_at_fork"),
        signal: ("pidfd_send_signal",),
    }
    missing = [
        f"{module.__name__}.{name}"
        for module, names in required.items()
        for name in names
        if not hasattr(module, name)
    ]
    if missing:
        raise RuntimeError(
            f"Process supervision unavailable in {sys.executable}: missing {', '.join(missing)}. "
            "Use a Linux Python build exposing pidfd APIs before starting native work"
        )
    _probe_pidfd()
    try:
        _subreaper()
        current = _read_process(os.getpid())
    except OSError as error:
        raise RuntimeError(
            f"Process supervision unavailable in {sys.executable}: "
            f"Linux subreaper/proc capability probe failed ({error})"
        ) from error
    if current is None:
        raise RuntimeError(f"Process supervision cannot read /proc identity in {sys.executable}")


def check_interpreter_supervision(interpreter: str) -> None:
    """Probe the actual snapshot interpreter before mutating admission or GPU claims."""
    script = (
        "import sys\n"
        "from clearml_yolo.adapters.runtime.process_tree import require_process_supervision\n"
        "try:\n"
        "    require_process_supervision()\n"
        "except RuntimeError as error:\n"
        "    sys.stderr.write(str(error))\n"
        "    sys.exit(1)\n"
        f"print({_SUPERVISION_PROBE_SUCCESS!r})\n"
    )
    try:
        result = subprocess.run(  # noqa: S603 - frozen interpreter and fixed capability probe
            [interpreter, "-c", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=_SUPERVISION_PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Process supervision probe timed out for {interpreter}") from error
    except OSError as error:
        raise RuntimeError(f"Cannot probe process supervision in {interpreter}: {error}") from error
    if result.returncode or result.stdout.strip() != _SUPERVISION_PROBE_SUCCESS:
        detail = result.stderr.strip()[-2048:] or "capability acknowledgement missing"
        raise RuntimeError(f"Process supervision probe failed for {interpreter}: {detail}")


class LinuxProcessTree:
    """Retain identities and recover marked native ranks even after reparenting.

    The marker is private launch provenance, not an authorization boundary against
    malicious same-user processes. Environment bytes are never retained or logged.
    """

    def __init__(
        self,
        root: int,
        token: str | None = None,
        *,
        born: int | None = None,
        identities: Mapping[int, int] | None = None,
        owner_env: str = OWNER_ENV,
        excluded: Mapping[int, int] | None = None,
    ) -> None:
        self.root = root
        self._marker = f"{owner_env}={token}".encode() if token is not None else None
        self._excluded = dict(excluded or {})
        initial = _read_process(root)
        self._born = born if born is not None else initial.born if initial is not None else None
        self._identities = dict(identities) if identities is not None else {}
        if self._born is not None:
            self._identities[root] = self._born
        self._unreadable: set[int] = set()
        self._scan_changed = False
        self._snapshot: frozenset[tuple[int, int, bool]] = frozenset()

    @property
    def identities(self) -> tuple[tuple[int, int], ...]:
        """Persist known births so recovery never adopts replacement processes."""
        self._owned()
        return tuple(sorted(self._identities.items()))

    def adopt_children(self, parent: int) -> None:
        """A subreaper may retain descendants adopted after their parent exits."""
        for process in self._table().values():
            if process.parent == parent:
                self._identities[process.pid] = process.born

    def _table(self) -> dict[int, _Process]:
        table: dict[int, _Process] = {}
        for path in Path("/proc").iterdir():
            if not path.name.isdecimal():
                continue
            pid = int(path.name)
            try:
                if path.stat().st_uid != os.getuid() and pid not in self._identities:
                    continue
                process = _read_process(pid)
            except (FileNotFoundError, ProcessLookupError):
                self._scan_changed = True
                continue
            except PermissionError:
                self._unreadable.add(pid)
                continue
            if process is not None:
                table[pid] = process
            else:
                self._scan_changed = True
        return table

    def _marked(self, process: _Process) -> bool:
        if (
            self._marker is None
            or process.state == "Z"
            or self._excluded.get(process.pid) == process.born
            or (self._born is not None and process.born < self._born)
        ):
            return False
        try:
            environment = Path(f"/proc/{process.pid}/environ").read_bytes()
            current = _read_process(process.pid)
        except (FileNotFoundError, ProcessLookupError):
            self._scan_changed = True
            return False
        except PermissionError:
            # Exit can deny environ after stat. A live replacement is still unknown.
            try:
                current = _read_process(process.pid)
            except PermissionError:
                pass
            else:
                if current is None or current.state == "Z":
                    self._scan_changed = True
                    return False
            self._unreadable.add(process.pid)
            return False
        if current is None or current.born != process.born or current.state == "Z":
            self._scan_changed = True
            return False
        return self._marker in environment.split(b"\0")

    def _begin_scan(self) -> dict[int, _Process]:
        """Share discovery churn and snapshots with native ownership overrides."""
        self._unreadable.clear()
        self._scan_changed = False
        table = self._table()
        self._snapshot = frozenset(
            (process.pid, process.born, process.state == "Z")
            for process in table.values()
            if self._born is None or process.born >= self._born
        )
        return table

    def _known_owners(self, table: Mapping[int, _Process]) -> set[int]:
        """Revalidate recorded births before using an earlier discovery snapshot."""
        owners: set[int] = set()
        for pid, born in self._identities.items():
            if pid not in table or table[pid].born != born:
                continue
            try:
                current = _read_process(pid)
            except PermissionError:
                self._unreadable.add(pid)
            else:
                if current is not None and current.born == born and current.state != "Z":
                    owners.add(pid)
                elif current != table[pid]:
                    self._scan_changed = True
        return owners

    def _extend_unmarked_owners(self, owners: set[int], table: Mapping[int, _Process]) -> None:
        # Only private callers without launch provenance use numeric ancestry.
        # Marker jobs must not adopt children of a root replaced after discovery.
        # A session ID remains reserved while its children survive the leader.
        # Reject a replacement leader instead of adopting a reused root PID.
        leader = table.get(self.root)
        root_matches = self._born is not None and (leader is None or leader.born == self._born)
        changed = True
        while changed:
            changed = False
            for process in table.values():
                if process.pid not in owners and (
                    process.parent in owners or (root_matches and process.session == self.root)
                ):
                    owners.add(process.pid)
                    changed = True

    def _owned(self) -> list[_Process]:
        table = self._begin_scan()
        owners = self._known_owners(table)
        owners.update(process.pid for process in table.values() if self._marked(process))
        if self._marker is None:
            self._extend_unmarked_owners(owners, table)
        for pid in owners:
            self._identities[pid] = table[pid].born
        return [
            table[pid]
            for pid in owners
            if table[pid].state != "Z" and self._excluded.get(pid) != table[pid].born
        ]

    def signal(self, signum: signal.Signals) -> None:
        """Signal confirmed identities, descendants before their direct worker."""
        for process in sorted(self._owned(), key=lambda item: item.pid == self.root):
            try:
                descriptor = os.pidfd_open(process.pid)
            except ProcessLookupError:
                continue
            try:
                current = _read_process(process.pid)
                if current is not None and current.born == process.born:
                    with suppress(ProcessLookupError):
                        signal.pidfd_send_signal(descriptor, signum)
            finally:
                os.close(descriptor)

    def running(self) -> bool:
        """Require two stable empty scans so late forks cannot vanish between scans."""
        snapshots: list[frozenset[tuple[int, int, bool]]] = []
        for _ in range(2):
            alive = self._owned()
            if self._unreadable:
                raise UnverifiableProcessTreeError(
                    "Cannot verify model process cleanup: /proc access denied for PIDs "
                    f"{sorted(self._unreadable)}; GPU lease remains owned"
                )
            if alive or self._scan_changed:
                return True
            snapshots.append(self._snapshot)
        return snapshots[0] != snapshots[1]

    def terminate(self, *, adopted_parent: int | None = None) -> None:
        """Allow transient /proc denial within a bounded complete-verification barrier."""
        with defer_interruptions():
            if adopted_parent is not None:
                self.adopt_children(adopted_parent)
            self.signal(signal.SIGTERM)
            graceful = time.monotonic() + 2
            deadline = graceful + 8
            while True:
                if adopted_parent is not None:
                    self.adopt_children(adopted_parent)
                verification_error: UnverifiableProcessTreeError | None = None
                try:
                    if not self.running():
                        return
                except UnverifiableProcessTreeError as error:
                    verification_error = error
                if time.monotonic() >= deadline:
                    if verification_error is not None:
                        raise verification_error
                    raise RuntimeError("Owned descendants survived bounded cleanup")
                if time.monotonic() >= graceful:
                    self.signal(signal.SIGKILL)
                time.sleep(0.05)


class SubreaperProcessTree(LinuxProcessTree):
    """Own a live supervisor's descendants without global marker discovery.

    The supervisor must be dedicated to this invocation and remain its subreaper.
    Every child branch is consequently owned, including orphans adopted after a
    native fork. Historical recovery still uses ``LinuxProcessTree`` and markers.
    """

    def __init__(
        self, root: int, token: str, *, subreaper: int, born: int | None = None,
    ) -> None:
        super().__init__(root, token, born=born)
        supervisor = _read_process(subreaper)
        if supervisor is None:
            raise RuntimeError("Live supervisor process identity is unavailable")
        self._supervisor = supervisor
        self._threaded_zombies: set[int] = set()

    def _identity(self, pid: int) -> _Process | None:
        try:
            return _read_process(pid)
        except PermissionError:
            self._unreadable.add(pid)
            return None

    def _children(self, process: _Process) -> set[int]:
        """Read every thread's children, rejecting a replaced parent snapshot."""
        children: set[int] = set()
        try:
            tasks = tuple(Path(f"/proc/{process.pid}/task").iterdir())
        except (FileNotFoundError, ProcessLookupError):
            self._scan_changed = True
            return children
        except PermissionError:
            self._unreadable.add(process.pid)
            return children
        if not tasks:
            self._scan_changed = True
        if process.state == "Z" and any(task.name != str(process.pid) for task in tasks):
            # A dead main thread does not imply that its native thread group exited.
            self._threaded_zombies.add(process.pid)
        for task in tasks:
            try:
                children.update(map(int, (task / "children").read_text(encoding="ascii").split()))
            except (FileNotFoundError, ProcessLookupError):
                # An exiting thread can reparent a child after its earlier slot was read.
                self._scan_changed = True
            except PermissionError:
                self._unreadable.add(process.pid)
        current = self._identity(process.pid)
        if current is None or current.born != process.born:
            self._scan_changed = True
            return set()
        return children

    def _matches_parent(self, process: _Process, parent: _Process) -> bool:
        current = self._identity(parent.pid)
        if (
            current is None
            or current.born != parent.born
            or process.parent != parent.pid
            or process.born < parent.born
        ):
            self._scan_changed = True
            return False
        return True

    def _candidate(
        self, pid: int, born: int | None, parent: _Process | None,
    ) -> _Process | None:
        process = self._identity(pid)
        if process is None or (born is not None and process.born != born):
            if process is None and parent is not None:
                self._scan_changed = True
            if pid == self._supervisor.pid:
                self._unreadable.add(pid)
            # A recorded PID may now belong to an entirely unrelated process.
            return None
        if parent is not None and not self._matches_parent(process, parent):
            return None
        return process

    @override
    def _table(self) -> dict[int, _Process]:
        self._threaded_zombies.clear()
        table: dict[int, _Process] = {}
        pending: list[tuple[int, int | None, _Process | None]] = [
            (pid, born, None) for pid, born in self._identities.items()
        ]
        pending.append((self._supervisor.pid, self._supervisor.born, None))
        visited: set[tuple[int, int]] = set()
        while pending:
            pid, born, parent = pending.pop()
            process = self._candidate(pid, born, parent)
            if process is None:
                continue
            identity = (process.pid, process.born)
            if identity in visited:
                continue
            visited.add(identity)
            if process.pid != self._supervisor.pid:
                table[pid] = process
            pending.extend((child, None, process) for child in self._children(process))
        return table

    @override
    def _owned(self) -> list[_Process]:
        table = self._begin_scan()
        for process in table.values():
            self._identities[process.pid] = process.born
        owners = self._known_owners(table)
        for pid in self._threaded_zombies:
            current = self._identity(pid)
            if current is not None and current.born == table[pid].born:
                owners.add(pid)
            else:
                self._scan_changed = True
        return [table[pid] for pid in owners]


@contextmanager
def defer_interruptions() -> Iterator[None]:
    """Finish bounded cleanup before delivering SIGINT/SIGTERM to prior handlers."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    pending: list[int] = []
    primary = sys.exception()
    previous = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}

    def defer(signum: int, _frame: FrameType | None) -> None:
        if not pending and previous[signal.Signals(signum)] != signal.SIG_IGN:
            pending.append(signum)

    try:
        for signum in previous:
            signal.signal(signum, defer)
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    if pending and primary is None:
        signum = signal.Signals(pending[0])
        handler = previous[signum]
        if callable(handler):
            handler(signum, None)
        elif handler == signal.SIG_DFL:
            raise SystemExit(128 + signum)


def process_ticks() -> int:
    """Earliest possible Linux birth tick for descendants launched after this point."""
    uptime = float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
    return int(uptime * os.sysconf("SC_CLK_TCK"))


_fork_writers: list[int] = []
_fork_callback_registered: list[bool] = []


def _record_native_fork() -> None:
    """Python fork callbacks run before child code, including a second fork."""
    if not _fork_writers:
        return
    process = _read_process(os.getpid())
    if process is not None:
        record = f"{process.pid} {process.born}\n".encode("ascii")
        for descriptor in _fork_writers:
            # Overflow or a closed parent's pipe leaves ancestry unverified;
            # cleanup must then use its conservative unknown-child rule.
            with suppress(OSError):
                os.write(descriptor, record)


def _subreaper(enabled: bool | None = None) -> bool:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, *([ctypes.c_ulong] * 4)]
    libc.prctl.restype = ctypes.c_int
    flag = ctypes.c_int()
    if libc.prctl(37, ctypes.addressof(flag), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Cannot inspect Linux child subreaper")
    if enabled is not None and libc.prctl(36, int(enabled), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Cannot configure Linux child subreaper")
    return bool(flag.value)


class _NativeProcessTree(LinuxProcessTree):
    """An unsignallable caller anchor with protected preexisting branches."""

    def __init__(self, current: _Process, token: str, reader: int) -> None:
        super().__init__(
            current.pid,
            token,
            owner_env=DIRECT_OWNER_ENV,
            excluded={current.pid: current.born},
        )
        self._reader = reader
        self._records = b""
        self._ambiguous: set[int] = set()
        table = self._table()
        protected = {current.pid}
        changed = True
        while changed:
            changed = False
            for process in table.values():
                if process.parent in protected and process.pid not in protected:
                    protected.add(process.pid)
                    self._excluded[process.pid] = process.born
                    changed = True
        self._has_helpers = len(protected) > 1

    def _fork_identities(self) -> None:
        while True:
            try:
                data = os.read(self._reader, 65536)
            except BlockingIOError:
                break
            if not data:
                break
            self._records += data
        records = self._records.split(b"\n")
        self._records = records.pop()
        for record in records:
            pid, born = map(int, record.split())
            if self._identities.get(pid) != born:
                self._scan_changed = True
            self._identities[pid] = born

    def _protected(self, table: Mapping[int, _Process]) -> set[int]:
        protected = {
            pid
            for pid, born in self._excluded.items()
            if pid != self.root and pid in table and table[pid].born == born
        }
        # Never propagate from the caller: only its preexisting helper branches.
        changed = True
        while changed:
            changed = False
            for process in table.values():
                if process.parent in protected and process.pid not in protected:
                    protected.add(process.pid)
                    self._excluded[process.pid] = process.born
                    changed = True
        return protected

    @override
    def _owned(self) -> list[_Process]:
        self._ambiguous.clear()
        table = self._begin_scan()
        self._fork_identities()
        protected = self._protected(table)
        owners = {
            pid for pid in self._known_owners(table) if pid != self.root and pid not in protected
        }
        owners.update(process.pid for process in table.values() if self._marked(process))
        changed = True
        while changed:
            changed = False
            for process in table.values():
                if process.pid in owners or process.pid in protected or process.pid == self.root:
                    continue
                if process.parent in owners or (
                    process.parent == self.root and not self._has_helpers
                ):
                    owners.add(process.pid)
                    changed = True
        for process in table.values():
            if (
                process.parent == self.root
                and process.pid not in owners | protected
                and process.state != "Z"
            ):
                self._ambiguous.add(process.pid)
        if self._ambiguous:
            self._scan_changed = True
        for pid in owners:
            self._identities[pid] = table[pid].born
        self._reap_owned(table, protected)
        return [table[pid] for pid in owners if table[pid].state != "Z"]

    def _reap_owned(self, table: Mapping[int, _Process], protected: set[int]) -> None:
        """Keep dead recorded children available for reaping after live revalidation."""
        for pid, born in self._identities.items():
            process = table.get(pid)
            if (
                process is not None
                and process.born == born
                and process.state == "Z"
                and process.parent == self.root
                and pid != self.root
                and pid not in protected
            ):
                self._reap(process)

    @staticmethod
    def _reap(process: _Process) -> None:
        """Reap only a recorded own child; never consume a publisher's status."""
        try:
            descriptor = os.pidfd_open(process.pid)
        except ProcessLookupError:
            return
        try:
            current = _read_process(process.pid)
            if current is not None and current.born == process.born:
                with suppress(ChildProcessError, ProcessLookupError):
                    os.waitid(os.P_PIDFD, descriptor, os.WEXITED | os.WNOHANG)
        finally:
            os.close(descriptor)

    @override
    def running(self) -> bool:
        alive = super().running()
        if self._ambiguous:
            raise UnverifiableProcessTreeError(
                "Cannot prove native ownership of adopted children with preexisting "
                f"helper branches: {sorted(self._ambiguous)}; children remain untouched"
            )
        return alive


@contextmanager
def _collect_scope_failure(failures: list[BaseException]) -> Iterator[None]:
    """At the cleanup boundary, retain failures while attempting every release."""
    try:
        yield
    except BaseException as error:  # noqa: BLE001 - preserve interruptions at cleanup boundary
        failures.append(error)


def _restore_native_scope(
    reader: int, writer: int, previous: str | None, previous_subreaper: bool | None
) -> list[BaseException]:
    failures: list[BaseException] = []
    with _collect_scope_failure(failures):
        _fork_writers.remove(writer)
    for descriptor in (reader, writer):
        with _collect_scope_failure(failures):
            os.close(descriptor)
    if previous_subreaper is not None:
        with _collect_scope_failure(failures):
            _subreaper(previous_subreaper)
    with _collect_scope_failure(failures):
        if previous is None:
            os.environ.pop(DIRECT_OWNER_ENV, None)
        else:
            os.environ[DIRECT_OWNER_ENV] = previous
    return failures


@contextmanager
def native_descendant_scope() -> Iterator[None]:
    """Own new native descendants without signalling the caller or old helpers.

    Ancestry plus subreaper adoption covers fork-only children without relying on
    runtime environment bytes being visible in /proc. Python fork births provide
    positive provenance even before the first scan. Unmarked adopted children
    cannot be attributed safely when preexisting helper branches exist; preserve
    those children and report unverifiable cleanup. Queue guardian markers remain
    intact, and only recorded own child statuses are reaped.
    """
    if sys.platform != "linux":
        yield
        return
    require_process_supervision()
    current = _read_process(os.getpid())
    if current is None:
        raise RuntimeError("Native invocation process identity is unavailable")
    reader, writer = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
    previous = os.environ.get(DIRECT_OWNER_ENV)
    token = uuid4().hex
    try:
        tree = _NativeProcessTree(current, token, reader)
        previous_subreaper = _subreaper(True)
    except BaseException:
        os.close(reader)
        os.close(writer)
        raise
    if not _fork_callback_registered:
        os.register_at_fork(after_in_child=_record_native_fork)
        _fork_callback_registered.append(True)
    _fork_writers.append(writer)
    os.environ[DIRECT_OWNER_ENV] = token
    try:
        yield
    finally:
        primary = sys.exception()
        failures: list[BaseException] = []
        with defer_interruptions():
            # A Python fork may unwind the copied context in its child. Only the
            # original invocation owns cleanup and restoration of subreaper state.
            owner = os.getpid() == current.pid
            if owner:
                with _collect_scope_failure(failures):
                    tree.terminate()
            failures.extend(
                _restore_native_scope(
                    reader, writer, previous, previous_subreaper if owner else None
                )
            )
            if failures:
                errors = [primary, *failures] if primary is not None else failures
                if len(errors) == 1:
                    raise errors[0]
                raise BaseExceptionGroup(
                    "Native execution, descendant cleanup or restoration failed", errors
                ) from None
