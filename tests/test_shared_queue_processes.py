"""Real-process queue lease protection survives worker and guardian death."""

import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.usefixtures("queue_memory")


def test_stale_reservation_does_not_block_another_root_after_owner_exits(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.locks import LocalGPULocks
    from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    pool = LocalGPULocks(identity, tmp_path / "local")
    claim = GuardianClaim(
        job_id="job",
        owner_uid=os.geteuid(),
        host_id="host",
        boot_id="boot",
        queue_root="/queue-one",
        devices=("GPU-test",),
        marker="marker",
        guardian_pid=os.getpid(),
        guardian_born=1,
    )
    first = pool.acquire(claim)
    assert first is not None
    first.close()
    # Process evidence survives, but an unlocked historical claim is not capacity.
    assert pool.reserved() == set()
    second = LocalGPULocks(identity, tmp_path / "local").acquire(
        claim.model_copy(update={"job_id": "other", "queue_root": "/queue-two"})
    )
    assert second is not None
    try:
        recovered = pool.acquire_recovery(claim)
        try:
            recovered.release_verified()
        finally:
            recovered.close()
        assert pool.reserved() == {"GPU-test"}
        assert pool.claim_for("other") == second.claim
        second.release_verified()
    finally:
        second.close()
    assert pool.reserved() == set()


def test_reservation_allocation_is_all_or_nothing(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.locks import LocalGPULocks
    from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    pool = LocalGPULocks(identity, tmp_path / "local")
    claim = GuardianClaim(
        job_id="job",
        owner_uid=os.geteuid(),
        host_id="host",
        boot_id="boot",
        queue_root="/queue",
        devices=("GPU-a",),
        marker="marker",
        guardian_pid=os.getpid(),
        guardian_born=1,
    )
    lease = pool.acquire(claim)
    assert lease is not None
    try:
        other = claim.model_copy(update={"job_id": "other", "devices": ("GPU-b", "GPU-a")})
        assert pool.acquire(other) is None
        assert pool.reserved() == {"GPU-a"}
    finally:
        lease.release_verified()
        lease.close()


def test_failed_atomic_claim_update_preserves_old_recovery_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue.locks import LocalGPULocks
    from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    pool = LocalGPULocks(identity, tmp_path / "local")
    claim = GuardianClaim(
        job_id="job",
        owner_uid=os.geteuid(),
        host_id="host",
        boot_id="boot",
        queue_root="/queue",
        devices=("GPU-a",),
        marker="marker",
        guardian_pid=os.getpid(),
        guardian_born=1,
    )
    lease = pool.acquire(claim)
    assert lease is not None
    original = Path.replace

    def interrupted(path: Path, target: Path) -> Path:
        if str(target).endswith(".claim.json"):
            raise OSError("injected atomic publication interruption")
        return original(path, target)

    try:
        monkeypatch.setattr(Path, "replace", interrupted)
        with pytest.raises(OSError, match="interruption"):
            lease.persist(claim.model_copy(update={"child_pid": 123, "child_born": 456}))
        assert pool.claim_for("job") == claim
    finally:
        monkeypatch.setattr(Path, "replace", original)
        lease.release_verified()
        lease.close()


def test_interrupted_whole_allocation_preserves_evidence_without_blocking_capacity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue.locks import LocalGPULocks
    from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    pool = LocalGPULocks(identity, tmp_path / "local")
    claim = GuardianClaim(
        job_id="job",
        owner_uid=os.geteuid(),
        host_id="host",
        boot_id="boot",
        queue_root="/queue",
        devices=("GPU-a", "GPU-b"),
        marker="marker",
        guardian_pid=os.getpid(),
        guardian_born=1,
    )
    original = Path.replace

    def interrupted(path: Path, target: Path) -> Path:
        if target == pool.claim_path("GPU-b"):
            raise OSError("injected partial allocation interruption")
        return original(path, target)

    monkeypatch.setattr(Path, "replace", interrupted)
    with pytest.raises(OSError, match="interruption"):
        pool.acquire(claim)
    monkeypatch.setattr(Path, "replace", original)
    assert pool.reserved() == set()
    other = pool.acquire(claim.model_copy(update={"job_id": "other"}))
    assert other is not None
    try:
        assert pool.reserved() == {"GPU-a", "GPU-b"}
        other.release_verified()
    finally:
        other.close()
    lease = pool.acquire_recovery(claim)
    lease.release_verified()
    lease.close()
    assert pool.reserved() == set()


def test_recovery_reuses_persisted_birth_and_never_signals_replacement_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime.process_tree import LinuxProcessTree, _read_process

    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True
    )
    try:
        current = _read_process(child.pid)
        assert current is not None
        persisted_born = current.born - 1
        original_iterdir = Path.iterdir

        def owned_processes(path: Path) -> Iterator[Path]:
            if path == Path("/proc"):
                return iter((path / str(child.pid),))
            return original_iterdir(path)

        # The assertion concerns this replacement PID. Unrelated /proc churn can
        # correctly make recovery report uncertain global discovery as running.
        # Keep real stat/birth reads and the pidfd signal path for the tested child.
        monkeypatch.setattr(Path, "iterdir", owned_processes)
        tree = LinuxProcessTree(
            child.pid, born=persisted_born, identities={child.pid: persisted_born},
        )
        tree.signal(signal.SIGKILL)
        assert child.poll() is None
        assert tree.identities == ((child.pid, persisted_born),)
        assert not tree.running()
    finally:
        child.kill()
        child.wait(timeout=5)


def _wait_for(path: Path, timeout: float = 10) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file() and path.read_text(encoding="utf-8"):
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    pytest.fail(f"Task-owned subprocess did not become ready: {path}")


def test_guardian_death_preserves_process_recovery_without_reserving_capacity(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.queue.identity import process_birth
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot, WorkerIdentity

    ready = tmp_path / "rank.pid"
    rank = (
        "import os,signal,sys,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )
    script = (
        "import subprocess,sys,time; "
        "subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]],"
        "start_new_session=True); time.sleep(60)"
    )
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    processes = QueueProcesses(
        store,
        identity,
        local_root=tmp_path / "local",
        command_builder=lambda snapshot, path, devices: [
            snapshot.interpreter,
            "-c",
            script,
            rank,
            str(ready),
        ],
    )
    guardian_pid: int | None = None
    rank_pid: int | None = None
    try:
        assert processes.start(job, ("GPU-test",))
        rank_pid = int(_wait_for(ready))
        claim = json.loads(
            (store.snapshot_path(job.id).parent / "claim.json").read_text(encoding="utf-8")
        )
        guardian_pid = claim["guardian_pid"]
        os.kill(guardian_pid, signal.SIGKILL)
        deadline = time.monotonic() + 5
        while process_birth(guardian_pid) is not None and time.monotonic() < deadline:
            time.sleep(0.02)
        processes.refresh()
        assert store.view().jobs[0].state == "recovery_required"
        assert processes.reserved() == set()
        assert process_birth(rank_pid) is not None
        result = processes.recover(job.id)
        assert result.state == "cancelled"
        assert process_birth(rank_pid) is None
        assert processes.reserved() == set()
    finally:
        for pid in (guardian_pid, rank_pid):
            if pid is not None and process_birth(pid) is not None:
                os.kill(pid, signal.SIGKILL)
        processes.refresh()


def test_guardian_cancellation_reaps_subreaper_children(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.identity import process_birth
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot, WorkerIdentity

    ready = tmp_path / "rank.pid"
    rank = (
        "import os,signal,sys,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )
    # Let the rank install its signal handler before owner exit triggers cleanup.
    script = """
import subprocess,sys,time
from pathlib import Path

child = subprocess.Popen(
    [sys.executable, '-c', sys.argv[1], sys.argv[2]], start_new_session=True
)
ready = Path(sys.argv[2])
deadline = time.monotonic() + 10
while not ready.is_file() or not ready.read_text():
    if child.poll() is not None:
        raise RuntimeError('Detached rank exited before readiness')
    if time.monotonic() >= deadline:
        raise TimeoutError('Detached rank did not become ready')
    time.sleep(0.01)
"""
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    processes = QueueProcesses(
        store,
        identity,
        local_root=tmp_path / "local",
        command_builder=lambda snapshot, path, devices: [
            snapshot.interpreter,
            "-c",
            script,
            rank,
            str(ready),
        ],
    )
    rank_pid: int | None = None
    try:
        assert processes.start(job, ("GPU-test",))
        rank_pid = int(_wait_for(ready))
        deadline = time.monotonic() + 10
        while store.view().jobs[0].state not in {"completed", "failed", "recovery_required"}:
            assert time.monotonic() < deadline
            processes.refresh()
            time.sleep(0.05)
        completed = store.view().jobs[0]
        assert completed.state == "completed", completed.error
        assert process_birth(rank_pid) is None
        assert processes.reserved() == set()
    finally:
        if rank_pid is not None and process_birth(rank_pid) is not None:
            os.kill(rank_pid, signal.SIGKILL)


def test_worker_death_leaves_independent_guardian_and_allocation_alive(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.identity import process_birth
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    ready = tmp_path / "native.pid"
    worker_ready = tmp_path / "worker.ready"
    worker_script = """
import os,sys,time
from pathlib import Path
from clearml_yolo.adapters.queue.runtime import QueueProcesses
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.core.queue import WorkerIdentity
identity=WorkerIdentity(owner_uid=os.geteuid(),host_id="host",boot_id="boot")
store=NFSQueueStore(Path(sys.argv[1]),identity)
script=("import os,sys,time; from pathlib import Path; "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)")
processes=QueueProcesses(store,identity,local_root=Path(sys.argv[2]),
    command_builder=lambda snapshot,path,devices:[sys.executable,"-c",script,sys.argv[3]])
with processes.worker_registration():
    assert processes.start(store.view().jobs[0],("GPU-test",))
    Path(sys.argv[4]).write_text("ready")
    time.sleep(60)
"""
    worker = subprocess.Popen(  # noqa: S603 - fixed task-owned worker script
        [
            sys.executable,
            "-c",
            worker_script,
            str(store.root),
            str(tmp_path / "local"),
            str(ready),
            str(worker_ready),
        ],
        start_new_session=True,
    )
    processes = QueueProcesses(store, identity, local_root=tmp_path / "local")
    native_pid: int | None = None
    try:
        native_pid = int(_wait_for(ready))
        _wait_for(worker_ready)
        worker.kill()
        worker.wait(timeout=5)
        processes.refresh()
        assert store.view().jobs[0].state == "running"
        assert process_birth(native_pid) is not None
        assert processes.reserved() == {"GPU-test"}
        store.cancel(job.id)
        deadline = time.monotonic() + 10
        while store.view().jobs[0].state != "cancelled":
            assert time.monotonic() < deadline
            processes.refresh()
            time.sleep(0.05)
        assert process_birth(native_pid) is None
        assert processes.reserved() == set()
    finally:
        if worker.poll() is None:
            worker.kill()
        worker.wait(timeout=5)
        if native_pid is not None and process_birth(native_pid) is not None:
            os.kill(native_pid, signal.SIGKILL)


def test_repeated_guardian_signals_hold_capacity_until_ignoring_child_is_reaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.queue.identity import process_birth
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot, WorkerIdentity

    original = subprocess.Popen

    def launch(argv: list[str], **options: Any) -> subprocess.Popen[bytes]:
        if argv[1:3] == ["-m", "clearml_yolo.adapters.queue.guardian"]:
            argv = [
                argv[0],
                "-c",
                (
                    "from clearml_yolo.adapters.queue import guardian; "
                    "guardian._OWNER_SHUTDOWN_GRACE_SECONDS=0.6; guardian.main()"
                ),
                argv[3],
            ]
        return original(argv, **options)

    monkeypatch.setattr(subprocess, "Popen", launch)

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    ready = tmp_path / "native.pid"
    script = (
        "import os,signal,sys,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )
    processes = QueueProcesses(
        store,
        identity,
        local_root=tmp_path / "local",
        command_builder=lambda snapshot, path, devices: [
            snapshot.interpreter,
            "-c",
            script,
            str(ready),
        ],
    )
    native_pid: int | None = None
    try:
        assert processes.start(job, ("GPU-test",))
        native_pid = int(_wait_for(ready))
        claim = processes.pool.claim_for(job.id)
        assert claim is not None
        os.kill(claim.guardian_pid, signal.SIGTERM)
        time.sleep(0.2)
        os.kill(claim.guardian_pid, signal.SIGINT)
        os.kill(claim.guardian_pid, signal.SIGTERM)
        assert process_birth(native_pid) is not None
        assert processes.reserved() == {"GPU-test"}
        deadline = time.monotonic() + 10
        while store.view().jobs[0].state != "cancelled":
            assert time.monotonic() < deadline
            processes.refresh()
            time.sleep(0.05)
        assert process_birth(native_pid) is None
        assert processes.reserved() == set()
    finally:
        if native_pid is not None and process_birth(native_pid) is not None:
            os.kill(native_pid, signal.SIGKILL)
        processes.refresh()


def test_owner_can_recover_startup_failure_before_guardian_claim(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.identity import process_ticks
    from clearml_yolo.adapters.queue.records import GuardianPayload
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    payload = GuardianPayload(
        job_id=job.id,
        identity=identity,
        queue_root=str(store.root),
        local_root=str(tmp_path / "local"),
        devices=("GPU-test",),
        marker="never-launched-token",
        ownership_since=process_ticks(),
        argv=(sys.executable, "-c", "raise SystemExit(0)"),
        snapshot_path=str(store.snapshot_path(job.id)),
        cwd=str(tmp_path),
        project_root=str(tmp_path),
        start_gate=str(tmp_path / "closed-gate"),
    )
    assert store.prepare_start(job.id, ("GPU-test",), payload.model_dump_json())
    store.update(job.id, "recovery_required")
    processes = QueueProcesses(store, identity, local_root=tmp_path / "local")
    assert processes.recover(job.id).state == "cancelled"
    assert processes.reserved() == set()


def test_incompatible_active_guardian_stops_admission_but_owner_can_recover(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.locks import LocalGPULocks
    from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    pool = LocalGPULocks(identity, tmp_path / "local")
    claim = GuardianClaim(
        job_id="job",
        owner_uid=os.geteuid(),
        host_id="host",
        boot_id="boot",
        queue_root="/queue",
        devices=("GPU-a",),
        marker="marker",
        guardian_pid=os.getpid(),
        guardian_born=1,
    )
    lease = pool.acquire(claim)
    assert lease is not None
    incompatible = claim.model_copy(update={"compatibility": "unknown-guardian-v2"})
    lease.persist(incompatible)
    try:
        with pytest.raises(RuntimeError, match="incompatible"):
            pool.reserved()
    finally:
        lease.close()
    assert pool.reserved() == set()
    recovered = pool.acquire_recovery(incompatible)
    recovered.release_verified()
    recovered.close()


def test_same_host_pid_namespace_mismatch_fails_before_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.queue.locks import LocalGPULocks
    from clearml_yolo.core.queue import WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    LocalGPULocks(identity, tmp_path / "local")
    monkeypatch.setattr(os, "readlink", lambda path: "pid:[incompatible-namespace]")
    with pytest.raises(RuntimeError, match="PID namespace"):
        LocalGPULocks(identity, tmp_path / "local")


def test_existing_foreign_lock_opens_without_create_in_sticky_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.queue.coordination import shared_descriptor

    path = tmp_path / "foreign.lock"
    path.write_text("", encoding="utf-8")
    original = os.open

    def protected_regular(file: Path, flags: int, mode: int = 0o777) -> int:
        if file == path and flags & os.O_CREAT:
            raise PermissionError("simulated fs.protected_regular")
        return original(file, flags, mode)

    monkeypatch.setattr(os, "open", protected_regular)
    descriptor = shared_descriptor(path)
    os.close(descriptor)


def test_direct_scope_reaps_detached_rank_after_repeated_interrupt_and_preserves_existing_child(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.queue.identity import process_birth

    supervisor_script = """
import os,subprocess,sys,time
from pathlib import Path
from clearml_yolo.adapters.runtime.process_tree import native_descendant_scope,OWNER_ENV
os.environ[OWNER_ENV]="inherited-guardian-marker"
existing=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"],
    start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
Path(sys.argv[1],"existing.pid").write_text(str(existing.pid))
rank=("import os,signal,sys,time; from pathlib import Path; "
      "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
      "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)")
worker=("import subprocess,sys,time; "
        "subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]],"
        "start_new_session=True); time.sleep(60)")
try:
    with native_descendant_scope():
        assert os.environ[OWNER_ENV]=="inherited-guardian-marker"
        subprocess.Popen([sys.executable,"-c",worker,rank,str(Path(sys.argv[1],"rank.pid"))],start_new_session=True)
        time.sleep(60)
except KeyboardInterrupt:
    Path(sys.argv[1],"cleanup.finished").write_text("finished")
    raise SystemExit(130)
"""
    supervisor = subprocess.Popen(  # noqa: S603 - task-owned cancellation regression
        [sys.executable, "-c", supervisor_script, str(tmp_path)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    existing_pid: int | None = None
    rank_pid: int | None = None
    try:
        existing_pid = int(_wait_for(tmp_path / "existing.pid"))
        rank_pid = int(_wait_for(tmp_path / "rank.pid"))
        os.kill(supervisor.pid, signal.SIGINT)
        time.sleep(0.2)
        os.kill(supervisor.pid, signal.SIGINT)
        os.kill(supervisor.pid, signal.SIGTERM)
        _, errors = supervisor.communicate(timeout=15)
        assert supervisor.returncode == 130, errors
        assert (tmp_path / "cleanup.finished").is_file()
        assert process_birth(rank_pid) is None
        assert process_birth(existing_pid) is not None
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait(timeout=5)
        if supervisor.stderr is not None:
            supervisor.stderr.close()
        for pid in (existing_pid, rank_pid):
            if pid is not None and process_birth(pid) is not None:
                os.kill(pid, signal.SIGKILL)


def test_cleanup_waits_for_fresh_verification_after_transient_unreadable_candidate(
    tmp_path: Path,
) -> None:
    from uuid import uuid4

    from clearml_yolo.adapters.queue.guardian import cleanup_tree
    from clearml_yolo.adapters.runtime.process_tree import OWNER_ENV, LinuxProcessTree

    token = uuid4().hex
    root = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
        env={**os.environ, OWNER_ENV: token},
    )
    opaque_script = """
import ctypes,sys,time
from pathlib import Path
libc=ctypes.CDLL(None)
assert libc.prctl(4,0,0,0,0)==0
Path(sys.argv[1]).write_text("ready")
time.sleep(0.5)
assert libc.prctl(4,1,0,0,0)==0
time.sleep(60)
"""
    opaque = subprocess.Popen(  # noqa: S603 - fixed task-owned process access fixture
        [sys.executable, "-c", opaque_script, str(tmp_path / "opaque.ready")],
        start_new_session=True,
    )
    try:
        tree = LinuxProcessTree(root.pid, token)
        _wait_for(tmp_path / "opaque.ready")
        try:
            Path(f"/proc/{opaque.pid}/environ").read_bytes()
        except PermissionError:
            pass
        else:
            pytest.skip("Runner can inspect nondumpable process environments")
        cleanup_tree(tree)
        root.wait(timeout=5)
        assert opaque.poll() is None, "Unknown candidate was wrongly signalled as job-owned"
    finally:
        if root.poll() is None:
            root.kill()
        root.wait(timeout=5)
        opaque.kill()
        opaque.wait(timeout=5)
