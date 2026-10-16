"""Worker diagnostics stay useful without contaminating command stdout."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from loguru import logger

from clearml_yolo.core.queue import PublicJob, QueueView, ResourceRequest
from queue_cli_helpers import queue_command, queue_environment


@pytest.mark.parametrize("level", [None, "DEBUG", "WARNING"])
def test_real_idle_worker_logs_by_default_and_stops_cleanly(
    tmp_path: Path, level: str | None
) -> None:
    queue_root = tmp_path / "queue"
    command = [*queue_command(tmp_path), "worker"]
    if level:
        command.extend(["--log-level", level])
    with subprocess.Popen(  # noqa: S603 - fixed CLI with an isolated empty queue
        command,
        env=queue_environment(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        try:
            deadline = time.monotonic() + 15
            while not list(queue_root.rglob("worker.json")):
                if process.poll() is not None or time.monotonic() >= deadline:
                    pytest.fail("Worker exited or failed to register")
                time.sleep(0.02)
            process.terminate()
            stdout, stderr = process.communicate(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    assert process.returncode == 0, stderr
    assert stdout == ""
    assert not list(queue_root.rglob("worker.json"))
    if level == "WARNING":
        assert stderr == ""
    else:
        assert "Starting queue worker" in stderr
        assert str(queue_root) in stderr
        assert "idle" in stderr.lower()
        assert "Queue worker stopped" in stderr
        assert ("DEBUG" in stderr) == (level == "DEBUG")


def test_worker_logs_changes_and_heartbeat_without_timestamp_noise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.entrypoints import queue
    from clearml_yolo.entrypoints.queue_presentation import QueuePresentation

    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    messages: list[str] = []
    sink = logger.add(messages.append, format="{level}: {message}", level="INFO")
    try:
        observer = queue._WorkerLog(
            owner_uid=7, presentation=QueuePresentation({"GPU-one": 2}, host_id="host")
        )
        pending = PublicJob(
            id="own-job",
            submission_sequence=17,
            label="Training experiment",
            owner_uid=7,
            host_id="host",
            boot_id="boot",
            command="train",
            request=ResourceRequest(gpus=1),
            submitted_at=0,
            waiting_reason="Waiting for 1 available GPU",
        )
        foreign = pending.model_copy(update={"id": "foreign-job", "owner_uid": 8})
        view = QueueView(host_id="host", revision=1, jobs=(pending, foreign))
        observer(view)
        assert "Job 17 · Training experiment" in "".join(messages)
        assert "own-job" not in "".join(messages)
        assert "Waiting for 1 available GPU" in "".join(messages)
        assert "foreign-job" not in "".join(messages)
        messages.clear()
        observer(
            view.model_copy(
                update={
                    "revision": 2,
                    "jobs": (
                        pending.model_copy(update={"updated_at": 100, "revision": 2}),
                        foreign,
                    ),
                }
            )
        )
        assert not messages
        clock[0] = 61
        observer(view)
        assert "pending=1" in "".join(messages)
        running = pending.model_copy(
            update={
                "state": "running",
                "devices": ("GPU-one",),
                "waiting_reason": None,
                "progress": "Training step 5",
            }
        )
        messages.clear()
        observer(view.model_copy(update={"jobs": (running,)}))
        rendered = "".join(messages)
        assert "running" in rendered
        assert "allocation=2" in rendered
        assert "GPU-one" not in rendered
        assert "Training step 5" in rendered
        messages.clear()
        observer(
            view.model_copy(
                update={
                    "jobs": (
                        running.model_copy(
                            update={"state": "failed", "error": "Child exit code 2"}
                        ),
                    )
                }
            )
        )
        assert "ERROR" in "".join(messages)
        assert "Child exit code 2" in "".join(messages)
        messages.clear()
        observer(
            view.model_copy(
                update={
                    "jobs": (
                        running.model_copy(
                            update={
                                "state": "recovery_required",
                                "error": "token=private-value\nrecovery needed",
                            }
                        ),
                    )
                }
            )
        )
        assert "ERROR" in "".join(messages)
        assert "private-value" not in "".join(messages)
        assert "\\nrecovery needed" in "".join(messages)
    finally:
        logger.remove(sink)


def test_completed_history_is_counted_without_replaying_old_jobs() -> None:
    from clearml_yolo.entrypoints.queue import _WorkerLog

    completed = PublicJob(
        id="old-job",
        owner_uid=7,
        host_id="host",
        boot_id="boot",
        command="train",
        request=ResourceRequest(gpus=1),
        submitted_at=0,
        state="completed",
    )
    messages: list[str] = []
    sink = logger.add(messages.append, format="{message}", level="INFO")
    try:
        _WorkerLog(7)(QueueView(host_id="host", revision=1, jobs=(completed,)))
    finally:
        logger.remove(sink)
    assert "old-job" not in "".join(messages)
    assert "completed=1" in "".join(messages)
    assert "idle" in "".join(messages)


def test_worker_observer_reports_real_waiting_reason_and_releases_registration(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import GPUObservation, JobSnapshot, WorkerIdentity

    class BusyInventory:
        def snapshot(self) -> tuple[GPUObservation, ...]:
            return (GPUObservation(uuid="GPU-busy", available=False),)

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    processes = QueueProcesses(store, identity, local_root=tmp_path / "locks")
    service = QueueService(store, BusyInventory(), processes, identity)
    service.submit(
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
    )
    views: list[QueueView] = []
    service.worker(lambda: len(views) >= 2, poll_seconds=0, observe=views.append)
    assert views[0].jobs[0].waiting_reason is None
    assert views[1].jobs[0].state == "pending"
    assert views[1].jobs[0].waiting_reason
    assert not (store.actor_root / "worker.json").exists()


def test_failed_worker_does_not_claim_clean_shutdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import GPUObservation, WorkerIdentity
    from clearml_yolo.entrypoints.queue import _worker

    class Inventory:
        def snapshot(self) -> tuple[GPUObservation, ...]:
            return ()

    def fail() -> int:
        raise OSError("queue storage unavailable")

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(tmp_path / "queue", identity)
    processes = QueueProcesses(store, identity, local_root=tmp_path / "locks")
    service = QueueService(store, Inventory(), processes, identity)
    monkeypatch.setattr(service, "tick", fail)
    messages: list[str] = []
    sink = logger.add(messages.append, format="{message}")
    try:
        with pytest.raises(OSError, match="queue storage unavailable"):
            _worker(service)
    finally:
        logger.remove(sink)
    assert "Queue worker stopped" not in "".join(messages)
    assert not (store.actor_root / "worker.json").exists()
