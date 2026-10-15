"""A queued workload cannot start using an earlier, now stale memory observation."""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from clearml_yolo.adapters.queue.runtime import QueueProcesses
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.core.queue import JobSnapshot, WorkerIdentity


@pytest.mark.parametrize("used", [2 * 1024**3, 2 * 1024**3 + 1, None])
def test_guardian_rechecks_memory_before_workload_exec(
    tmp_path: Path, queue_memory: Path, used: int | None
) -> None:
    queue_memory.write_text(json.dumps({"GPU-test": used}), encoding="utf-8")
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    started = tmp_path / "workload.started"
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
        command_builder=lambda snapshot, _path, _devices: [
            snapshot.interpreter,
            "-c",
            "from pathlib import Path; import sys; Path(sys.argv[1]).touch()",
            str(started),
        ],
    )
    try:
        assert not processes.start(job, ("GPU-test",))
        assert store.view().jobs[0].state == "pending"
        assert not started.exists()
        assert not processes.reserved()
        # A later attempt uses a fresh measurement, with the strict boundary.
        queue_memory.write_text(json.dumps({"GPU-test": 2 * 1024**3 - 1}), encoding="utf-8")
        assert processes.start(store.view().jobs[0], ("GPU-test",))
        deadline = time.monotonic() + 10
        while store.view().jobs[0].state not in {"completed", "failed", "recovery_required"}:
            assert time.monotonic() < deadline
            processes.refresh()
            time.sleep(0.02)
        assert started.exists()
        assert store.view().jobs[0].state == "completed"
        assert not processes.reserved()
    finally:
        for process in processes._guardians.values():
            process.wait(timeout=10)


def test_free_during_startup_memory_read_prevents_old_generation_launch(
    tmp_path: Path,
    queue_memory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue.gpu_controls import GPUControls

    queue_memory.write_text(json.dumps({"GPU-test": 0}), encoding="utf-8")
    barrier = tmp_path / "memory-gate"
    monkeypatch.setenv("CY_TEST_QUEUE_MEMORY_BARRIER", str(barrier))
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    started = tmp_path / "workload.started"
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
        command_builder=lambda snapshot, _path, _devices: [
            snapshot.interpreter,
            "-c",
            "from pathlib import Path; import sys; Path(sys.argv[1]).touch()",
            str(started),
        ],
    )
    controls = GPUControls(processes.pool, physical_uuids=lambda: ("GPU-test",))
    with ThreadPoolExecutor(max_workers=1) as executor:
        attempt = executor.submit(processes.start, job, ("GPU-test",))
        try:
            deadline = time.monotonic() + 10
            while not barrier.with_suffix(".ready").exists():
                assert time.monotonic() < deadline
                time.sleep(0.01)
            controls.release("0")
            barrier.with_suffix(".continue").touch()
            assert not attempt.result(timeout=10)
            assert store.view().jobs[0].state == "pending"
            assert not started.exists()
            assert not processes.reserved()
        finally:
            barrier.with_suffix(".continue").touch()
            attempt.result(timeout=10)
            for process in processes._guardians.values():
                process.wait(timeout=10)


def test_free_keeps_running_job_and_sibling_lease_then_rechecks_next_job(
    tmp_path: Path,
    queue_memory: Path,
) -> None:
    from clearml_yolo.adapters.queue.gpu_controls import GPUControls

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    jobs = store.submit(
        tuple(
            JobSnapshot(
                command="train",
                label=label,
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            )
            for label in ("first", "second")
        )
    )
    script = (
        "from pathlib import Path; import sys,time; p=Path(sys.argv[1]); "
        "p.with_suffix('.started').touch(); "
        "exec('while not p.with_suffix(\".finish\").exists(): time.sleep(0.02)')"
    )
    processes = QueueProcesses(
        store,
        identity,
        local_root=tmp_path / "local",
        command_builder=lambda snapshot, _path, _devices: [
            snapshot.interpreter,
            "-c",
            script,
            str(tmp_path / snapshot.label),
        ],
    )
    controls = GPUControls(processes.pool, physical_uuids=lambda: ("GPU-a", "GPU-b"))

    def wait_for_state(job_id: str, state: str) -> None:
        deadline = time.monotonic() + 10
        while next(job for job in store.view().jobs if job.id == job_id).state != state:
            assert time.monotonic() < deadline
            processes.refresh()
            time.sleep(0.02)

    try:
        assert processes.start(jobs[0], ("GPU-a", "GPU-b"))
        controls.release("0")
        assert processes.reserved() == {"GPU-b"}
        assert store.view().jobs[0].state == "running"
        queue_memory.write_text(json.dumps({"GPU-a": 2 * 1024**3, "GPU-b": 0}), encoding="utf-8")
        assert not processes.start(jobs[1], ("GPU-a",))
        assert not (tmp_path / "second.started").exists()
        queue_memory.write_text(json.dumps({"GPU-a": 0, "GPU-b": 0}), encoding="utf-8")
        assert processes.start(jobs[1], ("GPU-a",))
        assert processes.reserved() == {"GPU-a", "GPU-b"}
        (tmp_path / "first.finish").touch()
        wait_for_state(jobs[0].id, "completed")
        assert processes.reserved() == {"GPU-a"}
        (tmp_path / "second.finish").touch()
        wait_for_state(jobs[1].id, "completed")
        assert not processes.reserved()
    finally:
        for label in ("first", "second"):
            (tmp_path / f"{label}.finish").touch()
        for process in processes._guardians.values():
            process.wait(timeout=10)
