"""Application scheduling uses only explicit ports and durable job transitions."""

import os
import sys
from pathlib import Path


def test_service_submits_schedules_then_cancels_without_retry(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import GPUObservation, JobSnapshot, WorkerIdentity

    class Inventory:
        def snapshot(self) -> tuple[GPUObservation, ...]:
            return (GPUObservation(uuid="GPU-test", available=True),)

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    processes = QueueProcesses(
        store, identity, local_root=tmp_path / "locks", child_module="not_a_real_child"
    )
    service = QueueService(store, Inventory(), processes, identity)
    job = service.submit(
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
    assert service.list().jobs[0].id == job.id
    assert service.cancel(job.id).state == "cancelled"
    with processes.worker_registration():
        assert service.tick() == 0
    assert service.list().jobs[0].state == "cancelled"


def test_generic_child_status_is_published_without_private_configuration(tmp_path: Path) -> None:
    import json

    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import JobSnapshot, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json='{"secret":"private"}',
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    directory = tmp_path / ".cy" / "queue-status"
    directory.mkdir(parents=True)
    status = directory / f"{job.id}.json"
    status.write_text(
        json.dumps(
            {
                "task_url": "https://clearml.example/tasks/one",
                "progress": "Training step 5",
                "iteration": 5,
            }
        ),
        encoding="utf-8",
    )
    status.chmod(0o600)
    processes = QueueProcesses(store, identity, local_root=tmp_path / "local")
    processes.refresh()
    public = store.view().jobs[0]
    assert public.progress == "Training step 5"
    assert public.clearml_url == "https://clearml.example/tasks/one"
    assert "private" not in public.model_dump_json()


def test_rejected_second_worker_preserves_first_registration(tmp_path: Path) -> None:
    import pytest

    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    first = QueueProcesses(store, identity, local_root=tmp_path / "local")
    second = QueueProcesses(store, identity, local_root=tmp_path / "local")
    with first.worker_registration():
        with pytest.raises(RuntimeError, match="already registered"), second.worker_registration():
            raise AssertionError("Second worker unexpectedly acquired registration")
        assert first.live_owners() == {os.geteuid()}


def test_one_owner_worker_runs_disjoint_guardians_concurrently(tmp_path: Path) -> None:
    import time

    from clearml_yolo.adapters.queue.identity import process_birth
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import GPUObservation, JobSnapshot, WorkerIdentity

    class Inventory:
        def snapshot(self) -> tuple[GPUObservation, ...]:
            return (
                GPUObservation(uuid="GPU-a", available=True),
                GPUObservation(uuid="GPU-b", available=True),
            )

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    snapshots = tuple(
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
    script = (
        "import os,sys,time; from pathlib import Path; "
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
            str(tmp_path / f"{snapshot.label}.pid"),
        ],
    )
    service = QueueService(store, Inventory(), processes, identity)
    jobs = service.submit(snapshots)
    pids: list[int] = []
    try:
        with processes.worker_registration():
            assert service.tick() == 1
            assert service.tick() == 1
            deadline = time.monotonic() + 10
            while not all((tmp_path / f"{label}.pid").exists() for label in ("first", "second")):
                assert time.monotonic() < deadline
                time.sleep(0.02)
            pids = [
                int((tmp_path / f"{label}.pid").read_text(encoding="utf-8"))
                for label in ("first", "second")
            ]
            assert processes.reserved() == {"GPU-a", "GPU-b"}
            assert all(process_birth(pid) is not None for pid in pids)
            service.cancel(jobs[0].id)
            while store.view().jobs[0].state != "cancelled":
                assert time.monotonic() < deadline
                processes.refresh()
                time.sleep(0.02)
            assert process_birth(pids[0]) is None
            assert process_birth(pids[1]) is not None
            assert processes.reserved() == {"GPU-b"}
            service.cancel(jobs[1].id)
            while store.view().jobs[1].state != "cancelled":
                assert time.monotonic() < deadline
                processes.refresh()
                time.sleep(0.02)
            assert processes.reserved() == set()
    finally:
        for job in jobs:
            store.cancel(job.id)
        for pid in pids:
            if process_birth(pid) is not None:
                os.kill(pid, 9)


def test_pending_reason_uses_same_sampled_whole_allocation(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import GPUObservation, JobSnapshot, ResourceRequest, WorkerIdentity

    class Inventory:
        def snapshot(self) -> tuple[GPUObservation, ...]:
            return (GPUObservation(uuid="GPU-a", available=True),)

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    processes = QueueProcesses(store, identity, local_root=tmp_path / "local")
    service = QueueService(store, Inventory(), processes, identity)
    job = service.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
                request=ResourceRequest(gpus=2),
            ),
        )
    )[0]
    with processes.worker_registration():
        assert service.tick() == 0
        public = service.list().jobs[0]
        assert public.id == job.id
        assert public.waiting_reason == "Waiting for GPU capacity: 2 requested, 1 available"


def test_list_explains_absent_worker_before_first_worker_tick(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import GPUObservation, JobSnapshot, WorkerIdentity

    class Inventory:
        def snapshot(self) -> tuple[GPUObservation, ...]:
            raise AssertionError("Listing must not perform GPU discovery")

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    processes = QueueProcesses(store, identity, local_root=tmp_path / "local")
    service = QueueService(store, Inventory(), processes, identity)
    job = service.submit(
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
    revision = store.view().revision
    assert service.list().jobs[0].waiting_reason == "Owner worker unavailable"
    assert store.view().revision == revision
    assert store.view().jobs[0].id == job.id
