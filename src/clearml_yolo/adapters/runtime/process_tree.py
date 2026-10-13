"""Linux invocation ownership across native children that start new sessions."""

import os
import signal
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

OWNER_ENV = "CY_MODEL_PROCESS_OWNER"


@dataclass(frozen=True)
class _Process:
    pid: int
    parent: int
    session: int
    born: int
    state: str


def _read_process(pid: int) -> _Process | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return _Process(pid, int(fields[1]), int(fields[3]), int(fields[19]), fields[0])


class LinuxProcessTree:
    """Retain identities and recover marked native ranks even after reparenting.

    The marker is private launch provenance, not an authorization boundary against
    malicious same-user processes. Environment bytes are never retained or logged.
    """

    def __init__(self, root: int, token: str | None = None) -> None:
        self.root = root
        self._marker = f"{OWNER_ENV}={token}".encode() if token is not None else None
        initial = _read_process(root)
        self._born = initial.born if initial is not None else None
        self._identities = {root: initial.born} if initial is not None else {}
        self._unreadable: set[int] = set()
        self._scan_changed = False
        self._snapshot: frozenset[tuple[int, int, bool]] = frozenset()

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
            # Exiting processes can deny environ access after the earlier stat read.
            # Only confirmed exit clears uncertainty; a live replacement is unknown.
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

    def _extend_unmarked_owners(self, owners: set[int], table: dict[int, _Process]) -> None:
        # Compatibility for private callers without launch provenance. Supervised
        # jobs always use a marker: numeric ancestry alone can race with PID reuse.
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
        self._unreadable.clear()
        self._scan_changed = False
        table = self._table()
        self._snapshot = frozenset(
            (process.pid, process.born, process.state == "Z")
            for process in table.values()
            if self._born is None or process.born >= self._born
        )
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
        owners.update(process.pid for process in table.values() if self._marked(process))
        if self._marker is None:
            self._extend_unmarked_owners(owners, table)
        for pid in owners:
            self._identities[pid] = table[pid].born
        return [table[pid] for pid in owners if table[pid].state != "Z"]

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
        """Require two stable empty scans so late forks cannot disappear between scans."""
        snapshots: list[frozenset[tuple[int, int, bool]]] = []
        for _ in range(2):
            alive = self._owned()
            if self._unreadable:
                raise RuntimeError(
                    "Cannot verify model process cleanup: /proc access denied for PIDs "
                    f"{sorted(self._unreadable)}; GPU lease remains owned"
                )
            if alive or self._scan_changed:
                return True
            snapshots.append(self._snapshot)
        return snapshots[0] != snapshots[1]


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
