"""Independent same-user Linux subreaper owns GPUs through descendant cleanup."""

import ctypes
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import FrameType

from clearml_yolo.adapters.queue.identity import process_birth
from clearml_yolo.adapters.queue.locks import GPULease, LocalGPULocks
from clearml_yolo.adapters.queue.records import GuardianPayload
from clearml_yolo.adapters.queue.storage import NFSQueueStore, atomic_write
from clearml_yolo.adapters.runtime.process_tree import (
    OWNER_ENV,
    LinuxProcessTree,
    defer_interruptions,
)
from clearml_yolo.core.queue import GuardianClaim, JobState

# Owner shutdown includes bounded SDK publication, console drain and native cleanup.
# Keep this independent of those adapters so queue admission stays SDK-free.
_OWNER_SHUTDOWN_GRACE_SECONDS = 90.0


def _signal_owner(pid: int, born: int) -> bool:
    """Signal only the recorded owner, pinned against PID replacement by a pidfd."""
    try:
        descriptor = os.pidfd_open(pid)
    except ProcessLookupError:
        return False
    try:
        if process_birth(pid) != born:
            return False
        try:
            signal.pidfd_send_signal(descriptor, signal.SIGTERM)
        except ProcessLookupError:
            return False
        return True
    finally:
        os.close(descriptor)


def establish_subreaper() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "Cannot establish Linux guardian subreaper")


def _reap_adopted() -> None:
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


@defer_interruptions()
def cleanup_tree(tree: LinuxProcessTree, *, adopted_parent: int | None = None) -> None:
    """Verified cleanup, including detached/adopted children; uncertainty raises."""
    tree.terminate(adopted_parent=adopted_parent)


class _Guardian:
    """Keep execution state and its cleanup barrier together in one process."""

    def __init__(self, payload_path: Path) -> None:
        self.payload_path = payload_path
        self.directory = payload_path.parent
        self.payload = GuardianPayload.model_validate_json(payload_path.read_text(encoding="utf-8"))
        if self.payload.identity.owner_uid != os.geteuid():
            raise PermissionError("Guardian effective UID does not own this snapshot")
        self.store = NFSQueueStore(Path(self.payload.queue_root), self.payload.identity)
        self.cancelled = False
        self.child: subprocess.Popen[bytes] | None = None
        self.tree: LinuxProcessTree | None = None
        self.write_gate: int | None = None
        self.failure: BaseException | None = None
        self.exit_code = 1
        self.lease: GPULease | None = None
        self.claim: GuardianClaim | None = None

    def _cancel(self, _signum: int, _frame: FrameType | None) -> None:
        self.cancelled = True

    def _prepare(self) -> bool:
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, self._cancel)
        deadline = time.monotonic() + 30
        while not Path(self.payload.start_gate).is_file():
            if self.cancelled or time.monotonic() >= deadline:
                return False
            time.sleep(0.02)
        if self.store.cancelled(self.payload.job_id):
            self.store.update(self.payload.job_id, "cancelled")
            return False
        establish_subreaper()
        born = process_birth(os.getpid())
        if born is None:
            raise RuntimeError("Guardian process identity is unavailable")
        self.claim = GuardianClaim(
            job_id=self.payload.job_id,
            owner_uid=self.payload.identity.owner_uid,
            host_id=self.payload.identity.host_id,
            boot_id=self.payload.identity.boot_id,
            queue_root=self.payload.queue_root,
            devices=self.payload.devices,
            marker=self.payload.marker,
            guardian_pid=os.getpid(),
            guardian_born=born,
            ownership_since=self.payload.ownership_since,
        )
        pool = LocalGPULocks(
            self.payload.identity,
            Path(self.payload.local_root) if self.payload.local_root else None,
        )
        self.lease = pool.acquire(self.claim)
        if self.lease is None:
            state: JobState = (
                "cancelled" if self.store.cancelled(self.payload.job_id) else "pending"
            )
            self.store.update(self.payload.job_id, state, devices=())
            return False
        return True

    def _persist(self) -> None:
        if self.lease is None or self.claim is None:
            raise RuntimeError("Guardian capacity claim has not been established")
        self.lease.persist(self.claim)
        atomic_write(self.directory / "claim.json", self.claim.model_dump_json(), 0o600)

    def _log_path(self) -> Path:
        project = Path(self.payload.project_root).resolve()
        log_root = project / ".cy" / "queue-logs"
        path = log_root / f"{self.payload.job_id}.log"
        if not path.resolve().is_relative_to(project):
            raise ValueError("Guardian log destination escapes its project root")
        log_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        return path

    def _launch(self) -> None:
        self._persist()
        self.store.load_snapshot(self.payload.job_id)
        read_gate, self.write_gate = os.pipe()
        environment = dict(os.environ)
        environment.update(
            {
                OWNER_ENV: self.payload.marker,
                "CUDA_VISIBLE_DEVICES": ",".join(self.payload.devices),
                "PYTHONUNBUFFERED": "1",
                "CY_QUEUE_EXEC_GATE": str(read_gate),
                "CY_PROGRESS_FILE": str(
                    Path(self.payload.project_root)
                    / ".cy"
                    / "queue-status"
                    / f"{self.payload.job_id}.json"
                ),
            }
        )
        try:
            descriptor = os.open(
                self._log_path(), os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "ab", buffering=0) as output:
                self.child = subprocess.Popen(  # noqa: S603 - explicit argv behind owned exec gate
                    [
                        sys.executable,
                        "-m",
                        "clearml_yolo.adapters.queue.exec_child",
                        str(self.payload_path),
                    ],
                    cwd=self.payload.cwd,
                    env=environment,
                    pass_fds=(read_gate,),
                    start_new_session=True,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
        finally:
            os.close(read_gate)
        child_born = process_birth(self.child.pid)
        if child_born is None:
            raise RuntimeError("Gated child identity disappeared before launch")
        self.tree = LinuxProcessTree(self.child.pid, self.payload.marker, born=child_born)
        if self.claim is None:
            raise RuntimeError("Guardian launch is missing its lease")
        self.claim = self.claim.model_copy(
            update={
                "child_pid": self.child.pid,
                "child_born": child_born,
                "identities": self.tree.identities,
            }
        )
        self._persist()
        if self.store.cancelled(self.payload.job_id) or self.cancelled:
            raise InterruptedError("Queue job cancelled before native execution")
        self.store.update(
            self.payload.job_id, "running", devices=self.payload.devices, expected_state="starting"
        )
        os.write(self.write_gate, b"1")
        os.close(self.write_gate)
        self.write_gate = None

    def _monitor(self) -> None:
        if self.child is None or self.tree is None or self.claim is None:
            raise RuntimeError("Guardian monitor is missing a child claim")
        while self.child.poll() is None:
            self._record_descendants()
            if self.store.cancelled(self.payload.job_id):
                self.cancelled = True
            if self.cancelled:
                return
            time.sleep(0.1)
        self.exit_code = int(self.child.returncode or 0)

    def _record_descendants(self) -> None:
        if self.tree is None or self.claim is None:
            raise RuntimeError("Guardian descendant recording is missing a child claim")
        self.tree.adopt_children(os.getpid())
        identities = self.tree.identities
        if identities != self.claim.identities:
            self.claim = self.claim.model_copy(update={"identities": identities})
            self._persist()

    def _graceful_cancel(self) -> None:
        """Let the owner finalize its task while retaining every capacity reservation."""
        if self.child is None or self.claim is None:
            raise RuntimeError("Guardian cancellation is missing a child claim")
        pid, born = self.claim.child_pid, self.claim.child_born
        if pid is None or born is None:
            raise RuntimeError("Guardian cancellation is missing its owner identity")
        deadline = time.monotonic() + _OWNER_SHUTDOWN_GRACE_SECONDS
        if not _signal_owner(pid, born):
            return
        while self.child.poll() is None and time.monotonic() < deadline:
            # Children can be launched or adopted while owner shutdown is in progress.
            # Repeated guardian signals only set cancelled; they never reset this deadline.
            self._record_descendants()
            time.sleep(0.1)

    def _finish(self) -> None:
        if self.write_gate is not None:
            os.close(self.write_gate)
            self.write_gate = None
        if self.tree is not None:
            if self.cancelled and self.failure is None:
                self._graceful_cancel()
            cleanup_tree(self.tree, adopted_parent=os.getpid())
        if self.child is not None:
            self.child.wait(timeout=5)
        _reap_adopted()
        state: JobState = (
            "cancelled"
            if self.cancelled or self.store.cancelled(self.payload.job_id)
            else ("completed" if self.failure is None and self.exit_code == 0 else "failed")
        )
        error = (
            f"Guardian operation failed: {type(self.failure).__name__}"
            if self.failure is not None
            else f"Native process exited with status {self.exit_code}"
            if self.exit_code
            else None
        )
        self.store.update(self.payload.job_id, state, error=error)
        if self.lease is None:
            raise RuntimeError("Guardian cleanup is missing its capacity lease")
        self.lease.release_verified()

    def run(self) -> None:
        if not self._prepare():
            return
        try:
            self._launch()
            self._monitor()
        except BaseException as error:  # noqa: BLE001 - native cleanup owns all descendants
            self.failure = error
        try:
            self._finish()
        except BaseException as cleanup_error:
            self.store.update(
                self.payload.job_id,
                "recovery_required",
                error=(
                    f"Cleanup verification failed: {type(cleanup_error).__name__}; "
                    "owner recovery required"
                ),
            )
            raise
        finally:
            if self.lease is not None:
                self.lease.close()


def supervise(payload_path: Path) -> None:
    _Guardian(payload_path).run()


def main() -> None:
    supervise(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
