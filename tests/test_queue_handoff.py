"""Real local leases and supervisor packets exercise the training handoff."""

import os
import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from clearml_yolo.adapters.queue import locks
from clearml_yolo.adapters.queue.locks import GPULease, LocalGPULocks
from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity, claim_token

if TYPE_CHECKING:
    from clearml_yolo.adapters.queue.guardian import _Guardian
    from clearml_yolo.adapters.queue.runtime import QueueProcesses


def _lease(
    directory: Path,
    devices: tuple[str, ...] = ("GPU-b", "GPU-a", "GPU-c"),
    *,
    job_id: str = "training",
) -> GPULease:
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    pool = LocalGPULocks(identity, directory)
    claim = GuardianClaim(
        job_id=job_id,
        owner_uid=os.geteuid(),
        host_id="host",
        boot_id="boot",
        queue_root="/queue",
        devices=devices,
        marker="training",
        guardian_pid=os.getpid(),
        guardian_born=1,
    )
    lease = pool.acquire(claim)
    assert lease is not None
    return lease


def test_handoff_retains_first_ordered_gpu_and_releases_others_idempotently(tmp_path: Path) -> None:
    lease = _lease(tmp_path)
    try:
        original_token = claim_token(lease.claim)
        reduced = lease.retain_first()
        assert reduced.devices == ("GPU-b",)
        assert claim_token(reduced) != original_token
        assert lease.pool.claim_for("training") == reduced
        assert lease.pool.reserved() == {"GPU-b"}
        assert tuple(lease.descriptors) == ("GPU-b",)
        other = lease.pool.acquire(
            reduced.model_copy(update={"job_id": "other", "devices": ("GPU-a", "GPU-c")})
        )
        assert other is not None
        try:
            assert lease.retain_first() == reduced
            assert lease.pool.claim_for("other") == other.claim
        finally:
            other.release_verified()
            other.close()
        with pytest.raises(ValueError, match="identity or devices"):
            lease.persist(reduced.model_copy(update={"devices": ("GPU-a", "GPU-b")}))
    finally:
        lease.release_verified()
        lease.close()


@pytest.mark.parametrize("failure_at", ["delete", "sync", "replace"])
def test_interrupted_handoff_retains_full_recoverable_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_at: str,
) -> None:
    lease = _lease(tmp_path)
    original = lease.claim
    original_write = locks._write_claim
    original_sync = locks._sync_directory

    def write(path: Path, claim: GuardianClaim | None) -> None:
        if (failure_at == "delete" and path == lease.pool.claim_path("GPU-c")) or (
            failure_at == "replace" and claim is not None
        ):
            raise OSError("handoff interrupted")
        original_write(path, claim)

    def sync(path: Path) -> None:
        if failure_at == "sync":
            raise OSError("handoff interrupted")
        original_sync(path)

    monkeypatch.setattr(locks, "_write_claim", write)
    monkeypatch.setattr(locks, "_sync_directory", sync)
    try:
        with pytest.raises(OSError, match="handoff interrupted"):
            lease.retain_first()
        assert lease.claim == original
        assert set(lease.descriptors) == set(original.devices)
        assert lease.pool.claim_for("training") == original
        assert lease.pool.reserved() == set(original.devices)
    finally:
        lease.close()
    monkeypatch.undo()
    recovered = lease.pool.acquire_recovery(original)
    try:
        recovered.release_verified()
    finally:
        recovered.close()
    assert lease.pool.reserved() == set()


def test_single_gpu_handoff_has_no_durable_rewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lease = _lease(tmp_path, ("GPU-a",))
    original = locks._write_claim
    try:

        def reject_write(_path: Path, _claim: GuardianClaim | None) -> None:
            raise AssertionError("unchanged allocation must not be rewritten")

        monkeypatch.setattr(locks, "_write_claim", reject_write)
        assert lease.retain_first() == lease.claim
    finally:
        monkeypatch.setattr(locks, "_write_claim", original)
        lease.release_verified()
        lease.close()


def test_failure_after_reduced_record_commit_keeps_locks_and_can_recover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lease = _lease(tmp_path)
    original_write = locks._write_claim

    def fail_after_commit(path: Path, claim: GuardianClaim | None) -> None:
        original_write(path, claim)
        if claim is not None:
            raise OSError("after reduced record commit")

    monkeypatch.setattr(locks, "_write_claim", fail_after_commit)
    try:
        with pytest.raises(OSError, match="after reduced"):
            lease.retain_first()
        assert len(lease.descriptors) == 3
        assert len(lease.claim.devices) == 3
        reduced = lease.pool.claim_for("training")
        assert reduced is not None
        assert reduced.devices == ("GPU-b",)
        with pytest.raises(RuntimeError, match="record changed"):
            lease.release_verified()
        assert (
            lease.pool.acquire(
                reduced.model_copy(update={"job_id": "other", "devices": ("GPU-a",)})
            )
            is None
        )
    finally:
        lease.close()
    monkeypatch.undo()
    recovered = lease.pool.acquire_recovery(reduced)
    try:
        recovered.release_verified()
    finally:
        recovered.close()
    other = lease.pool.acquire(
        reduced.model_copy(update={"job_id": "other", "devices": ("GPU-a", "GPU-c")})
    )
    assert other is not None
    other.release_verified()
    other.close()
    assert lease.pool.reserved() == set()


def _guardian(directory: Path) -> "_Guardian":
    from clearml_yolo.adapters.queue.guardian import _Guardian
    from clearml_yolo.adapters.queue.records import GuardianPayload
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(directory / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(directory),
                cwd=str(directory),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    store.update(job.id, "starting", devices=("GPU-b", "GPU-a", "GPU-c"))
    store.update(job.id, "running")
    path = store.snapshot_path(job.id).parent / "guardian.json"
    path.write_text(
        GuardianPayload(
            job_id=job.id,
            identity=identity,
            queue_root=str(store.root),
            devices=("GPU-b", "GPU-a", "GPU-c"),
            marker="marker",
            ownership_since=0,
            argv=(sys.executable,),
            snapshot_path=str(store.snapshot_path(job.id)),
            cwd=str(directory),
            project_root=str(directory),
            start_gate=str(directory / "gate"),
        ).model_dump_json()
    )
    guardian = _Guardian(path)
    guardian.lease = _lease(directory / "local", job_id=job.id)
    guardian.claim = guardian.lease.claim
    return guardian


def test_guardian_acknowledges_only_after_claim_and_public_devices_are_reduced(
    tmp_path: Path,
) -> None:
    guardian = _guardian(tmp_path)
    guardian.channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.channel.setblocking(False)
    child.settimeout(1)
    assert guardian.lease is not None
    try:
        for _ in range(2):
            child.sendall(b"training-finished-v1")
            guardian._consume_phase()
            assert child.recv(64) == b"ok-v1"
            assert guardian.lease.pool.reserved() == {"GPU-b"}
            assert guardian.store.view().jobs[0].devices == ("GPU-b",)
            persisted = GuardianClaim.model_validate_json(
                (guardian.directory / "claim.json").read_bytes()
            )
            assert persisted.devices == ("GPU-b",)
        child.close()
        guardian._consume_phase()
        _assert_channel_closed(guardian)
        assert not guardian.cancelled
    finally:
        child.close()
        if guardian.channel is not None:
            guardian.channel.close()
        guardian.lease.release_verified()
        guardian.lease.close()


@pytest.mark.parametrize(
    "packet", [b"unknown", b"training-finished-v1" + b"x" * 65536], ids=["unknown", "oversized"]
)
def test_guardian_rejects_unknown_or_oversized_packets_without_releasing_capacity(
    tmp_path: Path,
    packet: bytes,
) -> None:
    guardian = _guardian(tmp_path)
    guardian.channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.channel.setblocking(False)
    assert guardian.lease is not None
    try:
        child.sendall(packet)
        with pytest.raises(RuntimeError, match="phase"):
            guardian._consume_phase()
        assert guardian.lease.pool.reserved() == {"GPU-a", "GPU-b", "GPU-c"}
    finally:
        child.close()
        guardian.channel.close()
        guardian.lease.release_verified()
        guardian.lease.close()


def test_cancelled_guardian_does_not_accept_training_handoff(tmp_path: Path) -> None:
    guardian = _guardian(tmp_path)
    guardian.channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.channel.setblocking(False)
    guardian.cancelled = True
    child.settimeout(0.05)
    assert guardian.lease is not None
    try:
        child.sendall(b"training-finished-v1")
        guardian._consume_phase()
        with pytest.raises(TimeoutError):
            child.recv(64)
        assert len(guardian.lease.claim.devices) == 3
    finally:
        child.close()
        guardian.channel.close()
        guardian.lease.release_verified()
        guardian.lease.close()


def test_public_record_failure_sends_no_ack_and_verified_finish_clears_remaining_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guardian = _guardian(tmp_path)
    guardian.channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.channel.setblocking(False)
    child.settimeout(0.05)
    assert guardian.lease is not None

    def fail_update(*_args: object, **_kwargs: object) -> None:
        raise OSError("public record unavailable")

    try:
        monkeypatch.setattr(guardian.store, "update", fail_update)
        child.sendall(b"training-finished-v1")
        with pytest.raises(OSError, match="public record"):
            guardian._consume_phase()
        with pytest.raises(TimeoutError):
            child.recv(64)
        assert guardian.lease.claim.devices == ("GPU-b",)
        assert not guardian.handoff_done
        guardian.failure = OSError("public record unavailable")
        monkeypatch.undo()
        guardian._finish()
        _assert_channel_closed(guardian)
        assert guardian.store.view().jobs[0].state == "failed"
        assert guardian.lease.pool.reserved() == set()
    finally:
        child.close()
        if guardian.channel is not None:
            guardian.channel.close()
        guardian.lease.close()


def test_launch_failure_closes_channel_and_gate_at_finish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess

    guardian = _guardian(tmp_path)
    assert guardian.lease is not None

    def fail_launch(*_args: object, **_kwargs: object) -> None:
        raise OSError("launch unavailable")

    monkeypatch.setattr(subprocess, "Popen", fail_launch)
    try:
        with pytest.raises(OSError, match="launch unavailable"):
            guardian._launch()
        assert guardian.channel is not None
        channel_fd = guardian.channel.fileno()
        gate_fd = guardian.write_gate
        assert gate_fd is not None
        guardian.failure = OSError("launch unavailable")
        guardian._finish()
        for descriptor in (channel_fd, gate_fd):
            with pytest.raises(OSError, match="Bad file descriptor"):
                os.fstat(descriptor)
        assert guardian.lease.pool.reserved() == set()
    finally:
        if guardian.channel is not None:
            guardian.channel.close()
        guardian.lease.close()


@pytest.mark.parametrize("cancel", [False, True], ids=["complete", "cancel"])
def test_live_guardian_handoff_preserves_publisher_and_allocation_until_owner_finishes(
    tmp_path: Path,
    cancel: bool,
) -> None:
    import time

    from clearml_yolo.adapters.queue.identity import process_birth
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot

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
    script = """
import os,signal,subprocess,sys,time
from pathlib import Path
from clearml_yolo.adapters.runtime.execution_lifecycle import execution_lifecycle
from clearml_yolo.adapters.runtime.execution_lifecycle import notify_training_finished
p=Path(sys.argv[1])
stop=False
def cancel(signum,frame):
    global stop
    stop=True
signal.signal(signal.SIGTERM,cancel)
with execution_lifecycle() as supervised:
    assert supervised
    assert os.environ['CUDA_VISIBLE_DEVICES']=='GPU-b,GPU-a,GPU-c'
    publisher=subprocess.Popen(
        [sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
    (p/'publisher.pid').write_text(str(publisher.pid))
    (p/'training.started').write_text('started')
    while not (p/'training.finish').exists():
        time.sleep(0.01)
    notify_training_finished()
    notify_training_finished()
    assert publisher.poll() is None
    (p/'handoff.done').write_text('acknowledged')
    while not stop and not (p/'owner.finish').exists():
        assert publisher.poll() is None
        time.sleep(0.01)
    (p/'publication.done').write_text('published')
    publisher.terminate()
    publisher.wait(timeout=5)
"""
    processes = QueueProcesses(
        store,
        identity,
        local_root=tmp_path / "local",
        command_builder=lambda snapshot, _path, _devices: [
            snapshot.interpreter,
            "-c",
            script,
            str(tmp_path),
        ],
    )
    extra: GPULease | None = None

    def wait_for(path: Path) -> None:
        deadline = time.monotonic() + 10
        while not path.is_file():
            assert time.monotonic() < deadline, store.view().jobs[0]
            processes.refresh()
            time.sleep(0.02)

    try:
        assert processes.start(job, ("GPU-b", "GPU-a", "GPU-c"))
        wait_for(tmp_path / "training.started")
        assert processes.reserved() == {"GPU-a", "GPU-b", "GPU-c"}
        (tmp_path / "training.finish").touch()
        wait_for(tmp_path / "handoff.done")
        publisher_pid = int((tmp_path / "publisher.pid").read_text())
        assert process_birth(publisher_pid) is not None
        assert processes.reserved() == {"GPU-b"}
        assert store.view().jobs[0].devices == ("GPU-b",)
        claim = processes.pool.claim_for(job.id)
        assert claim is not None
        extra = processes.pool.acquire(
            claim.model_copy(update={"job_id": "other", "devices": ("GPU-a", "GPU-c")})
        )
        assert extra is not None
        if cancel:
            store.cancel(job.id)
        else:
            (tmp_path / "owner.finish").touch()
        wait_for(tmp_path / "publication.done")
        deadline = time.monotonic() + 10
        while store.view().jobs[0].state not in {
            "completed",
            "cancelled",
            "failed",
            "recovery_required",
        }:
            assert time.monotonic() < deadline
            processes.refresh()
            time.sleep(0.02)
        assert store.view().jobs[0].state == ("cancelled" if cancel else "completed")
        assert processes.reserved() == {"GPU-a", "GPU-c"}
        assert process_birth(publisher_pid) is None
    finally:
        if extra is not None:
            extra.release_verified()
            extra.close()
        _stop_owned_guardians(processes, job.id)


def _stop_owned_guardians(processes: "QueueProcesses", job_id: str) -> None:
    """Do not leak task-owned processes after a failed integration assertion."""
    import signal
    from contextlib import suppress

    from clearml_yolo.adapters.queue.identity import process_birth

    claim = processes.pool.claim_for(job_id)
    if claim is not None:
        for pid, born in (*claim.identities, (claim.guardian_pid, claim.guardian_born)):
            with suppress(ProcessLookupError):
                descriptor = os.pidfd_open(pid)
                try:
                    if process_birth(pid) == born:
                        signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                finally:
                    os.close(descriptor)
    for process in processes._guardians.values():
        process.wait(timeout=5)


def _assert_channel_closed(guardian: "_Guardian") -> None:
    assert guardian.channel is None


def test_post_commit_handoff_failure_becomes_recoverable_and_closes_every_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guardian = _guardian(tmp_path)
    guardian.channel, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    guardian.channel.setblocking(False)
    child.settimeout(1)
    assert guardian.lease is not None
    original_write = locks._write_claim

    def fail_after_commit(path: Path, claim: GuardianClaim | None) -> None:
        original_write(path, claim)
        if claim is not None:
            raise OSError("reduced record directory sync interrupted")

    monkeypatch.setattr(locks, "_write_claim", fail_after_commit)
    monkeypatch.setattr(guardian, "_prepare", lambda: True)
    monkeypatch.setattr(guardian, "_launch", lambda: None)
    monkeypatch.setattr(guardian, "_monitor", guardian._consume_phase)
    try:
        child.sendall(b"training-finished-v1")
        with pytest.raises(RuntimeError, match="record changed"):
            guardian.run()
        assert child.recv(64) == b""
        assert guardian.store.view().jobs[0].state == "recovery_required"
        assert guardian.lease.descriptors == {}
        reduced = guardian.lease.pool.claim_for(guardian.payload.job_id)
        assert reduced is not None
        assert reduced.devices == ("GPU-b",)
    finally:
        child.close()
        guardian.lease.close()
    monkeypatch.undo()
    recovered = guardian.lease.pool.acquire_recovery(reduced)
    try:
        recovered.release_verified()
    finally:
        recovered.close()
    assert guardian.lease.pool.reserved() == set()
