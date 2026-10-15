"""Public queue output uses physical GPU numbers without leaking internal identities."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import cast

import pytest

from clearml_yolo.core.queue import (
    GPUControlStatus,
    GPUHold,
    GuardianClaim,
    PublicJob,
    QueueView,
    ResourceRequest,
)

GPU_A = "GPU-12345678-1234-1234-1234-123456789abc"
GPU_B = "GPU-abcdef01-1234-1234-1234-123456789abc"


def _job() -> PublicJob:
    return PublicJob(
        id="job",
        owner_uid=7,
        host_id="local",
        boot_id="boot",
        command="train",
        request=ResourceRequest(devices=(GPU_B, GPU_A)),
        devices=(GPU_B,),
        submitted_at=0,
        waiting_reason=f"Waiting for {GPU_A}",
        error=f"Unable to reserve {GPU_B}; claim-token={'a' * 64}",
    )


def test_queue_json_and_text_use_physical_order_and_sanitize_nested_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from clearml_yolo.entrypoints.queue import _show
    from clearml_yolo.entrypoints.queue_presentation import QueuePresentation

    presentation = QueuePresentation({GPU_A: 0, GPU_B: 2}, host_id="local")
    view = QueueView(host_id="local", revision=4, jobs=(_job(),))
    _show(view, as_json=True, presentation=presentation)
    rendered = capsys.readouterr().out
    result = json.loads(rendered)
    assert result["jobs"][0]["request"]["devices"] == ["2", "0"]
    assert result["jobs"][0]["devices"] == ["2"]
    assert result["jobs"][0]["waiting_reason"] == "Waiting for 0"
    assert GPU_A not in rendered
    assert GPU_B not in rendered
    assert "a" * 64 not in rendered
    _show(view, presentation=presentation)
    rendered = capsys.readouterr().out
    assert "request=2,0" in rendered
    assert "allocation=2" in rendered
    assert GPU_A not in rendered
    assert GPU_B not in rendered
    assert view.jobs[0].request.devices == (GPU_B, GPU_A)


def test_missing_and_remote_gpu_labels_are_stable_and_distinct() -> None:
    from clearml_yolo.entrypoints.queue_presentation import QueuePresentation

    presentation = QueuePresentation({GPU_A: 0}, host_id="local")
    remote = _job().model_copy(update={"host_id": "remote"})
    local_result = presentation.job(_job())
    remote_result = presentation.job(remote)
    local_devices = local_result["devices"]
    remote_devices = remote_result["devices"]
    remote_request = remote_result["request"]
    assert isinstance(local_devices, list)
    assert isinstance(remote_devices, list)
    assert isinstance(remote_request, dict)
    requested_devices = remote_request["devices"]
    assert isinstance(requested_devices, list)
    missing = local_devices[0]
    assert isinstance(missing, str)
    assert missing.startswith("gpu-")
    assert GPU_B not in missing
    assert requested_devices[1] != "0"
    assert requested_devices[1] != missing
    assert remote_devices[0] == missing


def _card() -> GPUControlStatus:
    claim = GuardianClaim(
        job_id="job",
        owner_uid=7,
        host_id="local",
        boot_id="boot",
        queue_root="/unavailable",
        devices=(GPU_B, GPU_A),
        marker="private-marker",
        guardian_pid=123,
        guardian_born=3,
    )
    hold = GPUHold(
        uuid=GPU_B,
        owner_uid=7,
        host_id="local",
        reason=f"Hold {GPU_B}; previous reservation {'e' * 64}",
        created_at=0,
    )
    return GPUControlStatus(
        uuid=GPU_B,
        physical_index=2,
        holds=(hold,),
        claim=claim,
    )


def test_gpu_list_public_view_omits_nested_claim_tokens_and_raw_devices() -> None:
    from clearml_yolo.entrypoints.queue_presentation import QueuePresentation

    card = _card()
    assert card.claim is not None
    result = QueuePresentation({GPU_A: 0, GPU_B: 2}).gpu(card)
    rendered = json.dumps(result)
    assert result["gpu"] == "2"
    claim_view = result["claim"]
    assert isinstance(claim_view, dict)
    assert claim_view["devices"] == ["2", "0"]
    assert all(value not in rendered for value in (GPU_A, GPU_B, "e" * 64))
    assert "claim_token" not in rendered
    assert "private-marker" not in rendered


@pytest.mark.parametrize("as_json", [False, True])
def test_gpu_list_cli_projects_internal_control_records(
    capsys: pytest.CaptureFixture[str], *, as_json: bool
) -> None:
    from clearml_yolo.application.queue import QueueGPUControlPort
    from clearml_yolo.entrypoints.queue import _gpu_operation, _parser

    card = _card()

    class Controls:
        def list(self) -> tuple[GPUControlStatus, ...]:
            return card, GPUControlStatus(uuid=GPU_A, physical_index=0)

    arguments = ["gpu", "list", *(["--json"] if as_json else [])]
    _gpu_operation(cast(QueueGPUControlPort, Controls()), _parser().parse_args(arguments))
    rendered = capsys.readouterr().out
    assert GPU_A not in rendered
    assert GPU_B not in rendered
    assert "e" * 64 not in rendered
    assert "claim-token" not in rendered
    if as_json:
        result = json.loads(rendered)
        assert result[0]["gpu"] == "2"
        assert result[0]["claim"]["devices"] == ["2", "0"]
    else:
        assert "2\tholds=uid=7\tjob=job" in rendered


@pytest.mark.parametrize("operation", ["free", "release", "disable", "enable"])
def test_gpu_controls_accept_only_a_physical_selector(operation: str) -> None:
    from clearml_yolo.entrypoints.queue import _parser

    parsed = _parser().parse_args(["gpu", operation, "2"])
    assert parsed.selector == "2"
    assert not any(hasattr(parsed, value) for value in ("claim_token", "reason", "force"))


def test_argparse_errors_do_not_echo_full_gpu_ids(capsys: pytest.CaptureFixture[str]) -> None:
    from clearml_yolo.entrypoints.queue import _parser

    with pytest.raises(SystemExit):
        _parser().parse_args(["gpu", "free", "0", "--bad-option", GPU_A])
    assert GPU_A not in capsys.readouterr().err


def test_queue_worker_has_no_memory_threshold_override() -> None:
    from clearml_yolo.entrypoints.queue import _parser

    with pytest.raises(SystemExit) as failure:
        _parser().parse_args(["worker", "--max-used-memory-gib", "5"])
    assert failure.value.code == 2


def test_cli_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from clearml_yolo.entrypoints import queue

    def fail(arguments: argparse.Namespace) -> None:
        raise RuntimeError(f"Reservation failed for {GPU_B}; claim-token={'b' * 64}")

    monkeypatch.setattr(queue, "_execute", fail)
    monkeypatch.setattr("sys.argv", ["cy-queue", "gpu", "list"])
    with pytest.raises(SystemExit):
        queue.main()
    rendered = capsys.readouterr().err
    assert "Reservation failed" in rendered
    assert GPU_B not in rendered
    assert "b" * 64 not in rendered


@pytest.mark.parametrize("arguments", [["gpu", "list"], ["gpu", "free", "0"]])
def test_driver_discovery_failure_is_a_sanitized_cli_error(
    arguments: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from types import SimpleNamespace

    from clearml_yolo.adapters.queue import locks
    from clearml_yolo.adapters.queue.identity import current_identity
    from clearml_yolo.adapters.runtime import gpu_resources
    from clearml_yolo.entrypoints import queue

    class DriverError(Exception):
        pass

    def unavailable() -> None:
        raise DriverError(f"Cannot initialize {GPU_A}")

    pool = locks.LocalGPULocks(current_identity(), root=tmp_path / "locks")
    monkeypatch.setattr(locks, "LocalGPULocks", lambda identity: pool)
    monkeypatch.setattr(gpu_resources, "_nvml", lambda: SimpleNamespace(nvmlInit=unavailable))
    monkeypatch.setattr("sys.argv", ["cy-queue", *arguments])
    with pytest.raises(SystemExit) as failure:
        queue.main()
    assert failure.value.code == 1
    rendered = capsys.readouterr().err
    assert "Cannot initialize" in rendered
    assert GPU_A not in rendered
    assert "Traceback" not in rendered


@pytest.mark.parametrize("operation", ["free", "release", "disable", "enable"])
def test_gpu_control_does_not_initialize_runtime_or_queue_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    operation: str,
) -> None:
    from clearml_yolo.adapters.queue import locks
    from clearml_yolo.adapters.queue.identity import current_identity
    from clearml_yolo.adapters.runtime import bootstrap, gpu_resources
    from clearml_yolo.entrypoints import queue

    def forbidden() -> Path:
        pytest.fail("GPU controls must not initialize runtime or queue directories")

    inventory_calls: list[bool] = []

    def physical(self: gpu_resources.GPUInventory) -> tuple[str, ...]:
        inventory_calls.append(True)
        return GPU_A, GPU_B

    pool = locks.LocalGPULocks(current_identity(), root=tmp_path / "locks")
    monkeypatch.setattr(locks, "LocalGPULocks", lambda identity: pool)
    monkeypatch.setattr(gpu_resources.GPUInventory, "physical_uuids", physical)
    monkeypatch.setattr(bootstrap, "initialize_runtime_environment", forbidden)
    arguments = queue._parser().parse_args(["--root", "/proc/denied", "gpu", operation, "1"])
    queue._execute(arguments)
    rendered = capsys.readouterr().out
    if operation != "enable":
        assert json.loads(rendered)["gpu"] == "1"
    assert GPU_B not in rendered
    assert len(inventory_calls) == 1


def test_submission_keeps_cuda_logical_order_but_display_uses_physical_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory
    from clearml_yolo.entrypoints.queue import _parser, _presentation, _resource_request

    monkeypatch.setattr(GPUInventory, "visible", lambda self: (GPU_B, GPU_A))
    monkeypatch.setattr(GPUInventory, "physical_uuids", lambda self: (GPU_A, GPU_B))
    parsed = _parser().parse_args(["submit", "--devices", "0,1", "--", "ground_truth=input.csv"])
    request = _resource_request(parsed)
    assert request.devices == (GPU_B, GPU_A)
    assert _presentation("local").request(request, "local") == "1,0"


@pytest.mark.parametrize("action", ["cancel", "recover", "move"])
def test_job_mutation_output_never_serializes_gpu_ids(
    action: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import MoveDirection, WorkerIdentity
    from clearml_yolo.entrypoints import queue
    from clearml_yolo.entrypoints.queue_presentation import QueuePresentation

    class Service:
        identity = WorkerIdentity(owner_uid=7, host_id="local", boot_id="boot")

        def cancel(self, identifier: str) -> PublicJob:
            return _job()

        def recover(self, identifier: str) -> PublicJob:
            return _job()

        def move(
            self,
            identifier: str,
            direction: MoveDirection,
            revision: int,
            *,
            relative_job_id: str | None = None,
        ) -> QueueView:
            return QueueView(host_id="local", revision=1, jobs=(_job(),))

    monkeypatch.setattr(
        queue, "_presentation", lambda host: QueuePresentation({GPU_A: 0, GPU_B: 2})
    )
    arguments = [action, "job"]
    if action == "move":
        arguments.extend(["top", "--revision", "0"])
    queue._queue_operation(
        cast(QueueService, Service()), queue._parser().parse_args(arguments), tmp_path
    )
    rendered = capsys.readouterr().out
    assert GPU_A not in rendered
    assert GPU_B not in rendered
    assert "a" * 64 not in rendered
    if action != "move":
        assert json.loads(rendered)["request"]["devices"] == ["2", "0"]


def test_tui_cells_and_error_notifications_use_safe_gpu_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("textual")
    from textual.widgets import DataTable, Static

    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import WorkerIdentity
    from clearml_yolo.entrypoints.queue_presentation import QueuePresentation
    from clearml_yolo.entrypoints.queue_tui import QueueApp

    class Service:
        identity = WorkerIdentity(owner_uid=7, host_id="local", boot_id="boot")
        failed = False

        def list(self) -> QueueView:
            if self.failed:
                raise RuntimeError(f"GPU unavailable {GPU_A}; claim-token={'c' * 64}")
            return QueueView(host_id="local", revision=1, jobs=(_job(),))

        def cancel(self, identifier: str) -> PublicJob:
            raise RuntimeError(f"Cancel error for {GPU_B}; claim-token={'d' * 64}")

    service = Service()

    async def exercise() -> None:
        application = QueueApp(
            cast(QueueService, service),
            presentation=QueuePresentation({GPU_A: 0, GPU_B: 2}, host_id="local"),
        )
        notifications: list[str] = []

        def notify(message: str, *, severity: str = "information") -> None:
            assert severity == "error"
            notifications.append(message)

        monkeypatch.setattr(application, "notify", notify)
        async with application.run_test() as pilot:
            row = application.query_one("#jobs", DataTable).get_row_at(0)
            assert row[4:6] == ["2,0", "2"]
            assert GPU_A not in str(row)
            assert GPU_B not in str(row)
            await pilot.press("c")
            assert "Cancel error for 2" in notifications[0]
            assert GPU_B not in notifications[0]
            assert "d" * 64 not in notifications[0]
            service.failed = True
            application.refresh_queue()
            status = str(application.query_one("#status", Static).render())
            assert "GPU unavailable 0" in status
            assert GPU_A not in status
            assert "c" * 64 not in status
            await pilot.press("q")

    asyncio.run(exercise())
