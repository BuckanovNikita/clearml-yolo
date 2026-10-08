"""Explicit ClearML configuration, artifact storage, and invocation lifecycle."""

import json
import os
import signal
import subprocess
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
import pytest
from ruamel.yaml import YAML

from clearml_yolo.adapters.clearml.session import (
    DEFAULT_PROJECT_NAME,
    ArtifactUploadError,
    ClearMLConfig,
    connect_config_file,
    expect_artifacts,
    init_task,
    invocation,
    publish_table,
    record_run_configuration,
    register_model_barrier,
    replay_configuration,
    upload_artifact,
)
from clearml_yolo.application.ports import WorkflowDependencies
from workflow_dependencies import patch_workflow
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414


def test_harness_environment_does_not_rewrite_tracking_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CY_RUN_TAG", "external-harness-tag")
    monkeypatch.setenv("INFRA_RUN_TAG", "another-harness-tag")

    defaults = ClearMLConfig()
    explicit = ClearMLConfig(project_name="detection", tags=["prod"])

    assert defaults.project_name == DEFAULT_PROJECT_NAME
    assert defaults.tags == []
    assert explicit.project_name == "detection"
    assert explicit.tags == ["prod"]


class FakeTask:
    def __init__(self) -> None:
        self.id = "task-id"
        self.name = "tracked-run"
        self.uploads: list[dict[str, Any]] = []
        self.configurations: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []
        self.completed: list[dict[str, Any]] = []
        self.events: list[str] = []
        self.flush_result = True
        self.upload_result = True
        self.configuration_result: Path | None = None
        self.run_configuration_result: dict[str, Any] | None = None
        self.closed = False
        self.local = True
        self.reload_count = 0

    def upload_artifact(self, **kwargs: Any) -> bool:
        self.uploads.append(kwargs)
        return self.upload_result

    def connect_configuration(self, **kwargs: Any) -> Any:
        self.configurations.append(kwargs)
        if kwargs.get("ignore_remote_overrides"):
            return kwargs["configuration"]
        if kwargs.get("name") == "run":
            return self.run_configuration_result or kwargs["configuration"]
        return self.configuration_result or kwargs["configuration"]

    def flush(self, *, wait_for_uploads: bool) -> bool:
        assert wait_for_uploads is True
        return self.flush_result

    def running_locally(self) -> bool:
        return self.local

    def close(self) -> None:
        self.events.append("close")
        self.closed = True

    def reload(self) -> None:
        self.reload_count += 1

    def mark_failed(self, **kwargs: Any) -> object:
        self.events.append("failed")
        self.failed.append(kwargs)
        return object()

    def mark_completed(self, **kwargs: Any) -> object:
        self.events.append("completed")
        self.completed.append(kwargs)
        return object()


@pytest.fixture
def fake_clearml(monkeypatch: pytest.MonkeyPatch) -> tuple[type[Any], FakeTask]:
    task = FakeTask()

    class Task:
        init_calls: ClassVar[list[dict[str, Any]]] = []
        on_init: ClassVar[Callable[[], None] | None] = None

        @classmethod
        def init(cls, **kwargs: Any) -> FakeTask:
            cls.init_calls.append(kwargs)
            if cls.on_init is not None:
                cls.on_init()
            return task

        @classmethod
        def get_task(cls, *, task_id: str) -> FakeTask:
            assert task_id == task.id
            return task

    module = types.ModuleType("clearml")
    module.Task = Task  # type: ignore[attr-defined]

    class OutputModel:
        wait_calls: ClassVar[int] = 0

        @classmethod
        def wait_for_uploads(cls) -> None:
            cls.wait_calls += 1

    module.OutputModel = OutputModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", module)
    return Task, task


def test_tracking_is_required_and_old_task_reuse_controls_are_gone() -> None:
    config = ClearMLConfig()

    assert not hasattr(config, "enabled")
    assert not hasattr(config, "continue_task_id")
    assert not hasattr(config, "reuse_last_task_id")


@pytest.mark.parametrize("output_uri", [None, False])
def test_required_remote_artifacts_reject_disabled_output_storage(
    output_uri: bool | None,
) -> None:
    with pytest.raises(ValueError, match="output_uri"):
        ClearMLConfig(output_uri=output_uri)


def test_invocation_owns_one_task_and_nested_stages_reuse_it(
    fake_clearml: tuple[type[Any], FakeTask], monkeypatch: pytest.MonkeyPatch
) -> None:
    task_type, task = fake_clearml
    monkeypatch.delenv("CY_CLEARML_OWNER_PID", raising=False)

    with invocation(ClearMLConfig(), "pipeline", {"run_dir": "runs/example"}) as owner:
        assert owner is task
        assert init_task(ClearMLConfig(), "train") is owner
        upload_artifact(owner, "train_best", {"ok": True})

    assert len(task_type.init_calls) == 1
    assert task_type.init_calls[0]["reuse_last_task_id"] is False
    assert task_type.init_calls[0]["auto_connect_streams"] is True
    integrations = task_type.init_calls[0]["auto_connect_frameworks"]
    assert integrations["detect_repository"] is False
    assert integrations["pytorch"] is False
    assert not any(integrations.values())
    assert task.closed is True
    assert task.events[-2:] == ["close", "completed"]
    assert task.completed == [{"ignore_errors": False, "force": True}]
    assert task.failed == []
    assert "CY_CLEARML_OWNER_PID" not in os.environ
    assert [item["name"] for item in task.uploads] == ["train_best"]
    assert task.configurations == [
        {
            "configuration": {"run_dir": "runs/example"},
            "name": "run",
            "ignore_remote_overrides": False,
        },
        {
            "configuration": {"run_dir": "runs/example"},
            "name": "run",
            "ignore_remote_overrides": True,
        },
    ]


def test_console_streams_reach_offline_sdk_without_duplicates(tmp_path: Path) -> None:
    code = """
import json
import sys
from pathlib import Path

from loguru import logger
from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation

try:
    with invocation(ClearMLConfig(project_name='console-regression'), 'predict') as task:
        folder = Path(task.get_offline_mode_folder())
        print('console-stdout-marker')
        print('console-stderr-marker', file=sys.stderr)
        logger.info('console-loguru-marker')
        raise RuntimeError('controlled offline failure')
except RuntimeError as error:
    assert str(error) == 'controlled offline failure', error

events = [
    event
    for line in (folder / 'log.jsonl').read_text().splitlines()
    for event in json.loads(line)
]
for marker in ('console-stdout-marker', 'console-stderr-marker', 'console-loguru-marker'):
    assert sum(marker in event['msg'] for event in events) == 1, (marker, events)
"""
    environment = dict(os.environ)
    environment.update(
        CLEARML_OFFLINE_MODE="1",
        CLEARML_CACHE_DIR=str(tmp_path / "clearml"),
        CY_HOME=str(tmp_path),
    )
    environment.pop("LOCAL_RANK", None)
    environment.pop("CY_CLEARML_OWNER_PID", None)
    environment.pop("CY_CLEARML_OWNER_TASK_ID", None)
    result = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned source
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("console-stdout-marker") == 1
    assert result.stderr.count("console-stderr-marker") == 1
    assert result.stderr.count("console-loguru-marker") == 1


def test_expected_artifact_must_be_uploaded_before_completion(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    def run() -> None:
        with invocation(ClearMLConfig(), "predict") as owner:
            expect_artifacts(owner, ["predictions", "image_membership"])
            upload_artifact(owner, "predictions", {"row": 1})

    with pytest.raises(ArtifactUploadError, match="image_membership"):
        run()

    assert task.failed[0]["status_reason"] == "ArtifactUploadError"
    assert task.events[-2:] == ["close", "failed"]


def test_upload_fulfils_a_predeclared_stage_artifact(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    with invocation(ClearMLConfig(), "pipeline") as owner:
        with invocation(ClearMLConfig(), "metrics"):
            expect_artifacts(owner, ["metrics_table"])
        upload_artifact(owner, "metrics_table", {"value": 1})

    assert [upload["name"] for upload in task.uploads] == ["metrics_table"]


def test_upload_rejection_fails_the_invocation(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    def run() -> None:
        with invocation(ClearMLConfig(), "predict") as owner:
            task.upload_result = False
            upload_artifact(owner, "predictions", {"row": 1})

    with pytest.raises(ArtifactUploadError, match="predictions"):
        run()

    assert task.closed is True
    assert len(task.failed) == 1
    assert "ArtifactUploadError" in task.failed[0]["status_message"]


def test_failure_status_does_not_capture_arbitrary_credentials(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    detail = "GET https://user:password@host/data?token=secret failed Authorization: Bearer key"
    with (
        pytest.raises(RuntimeError, match="Authorization"),
        invocation(ClearMLConfig(), "predict"),
    ):
        raise RuntimeError(detail)

    assert task.failed[0]["status_reason"] == "RuntimeError"
    assert task.failed[0]["status_message"] == (
        "RuntimeError: invocation failed; see local diagnostics for details"
    )


def test_required_path_must_exist_before_upload(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    missing = tmp_path / "missing.csv"

    def run() -> None:
        with invocation(ClearMLConfig(), "predict") as owner:
            upload_artifact(owner, "predictions", missing)

    with pytest.raises(FileNotFoundError, match=r"missing\.csv"):
        run()

    assert task.uploads == []
    assert len(task.failed) == 1


def test_required_output_tree_is_a_valid_artifact(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    output_tree = tmp_path / "native-output"
    output_tree.mkdir()
    (output_tree / "args.yaml").write_text("epochs: 1\n", encoding="utf-8")

    with invocation(ClearMLConfig(), "train") as owner:
        upload_artifact(owner, "train_native_outputs", output_tree)

    assert task.uploads[0]["artifact_object"] == output_tree


class DeliberateBaseException(BaseException):
    pass


def test_base_exception_marks_the_task_failed(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    def run() -> None:
        with invocation(ClearMLConfig(), "metrics"):
            raise DeliberateBaseException("computation stopped")

    with pytest.raises(DeliberateBaseException):
        run()

    assert task.closed is True
    assert task.failed[0]["status_reason"] == "DeliberateBaseException"


def test_keyboard_interrupt_marks_the_task_failed(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    def run() -> None:
        with invocation(ClearMLConfig(), "metrics"):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run()

    assert task.closed is True
    assert task.failed[0]["status_reason"] == "KeyboardInterrupt"


def test_sigterm_marks_the_task_failed_and_keeps_a_nonzero_exit(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    def run() -> None:
        with invocation(ClearMLConfig(), "train"):
            handler = signal.getsignal(signal.SIGTERM)
            assert callable(handler)
            handler(signal.SIGTERM, None)

    with pytest.raises(SystemExit) as raised:
        run()

    assert raised.value.code == 128 + signal.SIGTERM
    assert task.closed is True
    assert task.failed[0]["status_reason"] == "SIGTERM"


def test_invocation_restores_the_handler_from_before_task_initialization(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    task_type, _ = fake_clearml
    original = signal.getsignal(signal.SIGTERM)

    def sdk_handler(_signum: int, _frame: Any) -> None:
        return None

    task_type.on_init = lambda: signal.signal(signal.SIGTERM, sdk_handler)

    with invocation(ClearMLConfig(), "train"):
        pass

    assert signal.getsignal(signal.SIGTERM) is original


def test_flush_rejection_prevents_completion(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    task.flush_result = False

    def run() -> None:
        with invocation(ClearMLConfig(), "report"):
            pass

    with pytest.raises(ArtifactUploadError, match="flush"):
        run()

    assert task.closed is True
    assert len(task.failed) == 1


def test_worker_never_creates_a_task_or_uploads(
    fake_clearml: tuple[type[Any], FakeTask], monkeypatch: pytest.MonkeyPatch
) -> None:
    task_type, task = fake_clearml
    monkeypatch.setenv("LOCAL_RANK", "0")
    monkeypatch.setenv("CY_CLEARML_OWNER_PID", str(os.getpid() + 1))
    monkeypatch.setenv("CY_CLEARML_OWNER_TASK_ID", "parent-task")

    with invocation(ClearMLConfig(), "train") as owner:
        assert owner is None
        assert init_task(ClearMLConfig(), "train") is None
        upload_artifact(owner, "worker-output", {"forbidden": True})

    assert task_type.init_calls == []
    assert task.uploads == []
    assert task.closed is False


def test_resolved_configuration_is_sanitized_recursively(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    resolved = {
        "clearml": {"access_key": "access", "secret_key": "secret"},
        "endpoint": "https://alice:hunter2@example.test/path?token=abc&safe=yes&empty=",
        "nested": [{"password": "also-secret", "epochs": 3}],
    }

    with invocation(ClearMLConfig(), "train", resolved):
        pass

    stored = task.configurations[-1]["configuration"]
    assert stored == {
        "clearml": {"access_key": "<redacted>", "secret_key": "<redacted>"},
        "endpoint": ("https://<redacted>@example.test/path?token=%3Credacted%3E&safe=yes&empty="),
        "nested": [{"password": "<redacted>", "epochs": 3}],
    }
    assert task.uploads == []
    assert task.configurations[-1]["name"] == "run"


def test_source_yaml_is_sanitized_in_configuration_without_an_artifact(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    source = tmp_path / "dataset.yaml"
    source.write_text(
        "path: /datasets/cats\nendpoint: https://user:pass@example.test/data?token=abc\n"
        "auth:\n  secret_key: hidden\n  region: eu\n",
        encoding="utf-8",
    )

    with invocation(ClearMLConfig(), "train") as owner:
        stored = connect_config_file(owner, "dataset_configuration", source)
        assert stored == source
        stored_text = task.configurations[-1]["configuration"].read_text(encoding="utf-8")

    assert "hidden" not in stored_text
    assert "pass" not in stored_text
    assert "abc" not in stored_text
    assert "<redacted>" in stored_text
    assert "/datasets/cats" in stored_text
    assert "auth: <redacted>" in stored_text
    assert task.uploads == []
    assert task.configurations[-1]["ignore_remote_overrides"] is True


def test_remote_source_override_is_resanitized_and_used_as_the_effective_file(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    source = tmp_path / "dataset.yaml"
    source.write_text("epochs: 1\n", encoding="utf-8")
    override = tmp_path / "clearml-override.yaml"
    override.write_text("epochs: 2\npassword: remote-secret\n", encoding="utf-8")
    task.configuration_result = override

    with invocation(ClearMLConfig(), "train") as owner:
        effective = connect_config_file(owner, "dataset_configuration", source)
        effective_text = effective.read_text(encoding="utf-8")
        stored_text = task.configurations[-1]["configuration"].read_text(encoding="utf-8")

    assert "epochs: 2" in effective_text
    assert effective == override
    assert "remote-secret" in effective_text
    assert "remote-secret" not in stored_text
    assert "epochs: 2" in stored_text
    assert task.configurations[-1]["ignore_remote_overrides"] is True


def test_source_yaml_preserves_comments_order_and_redacts_commented_credentials(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    source = tmp_path / "ultralytics.yaml"
    source.write_text(
        "# Ultralytics license and configuration\n"
        "# Training settings\n"
        "epochs: 3 # Number of epochs\n"
        "# source: null # Prediction only\n"
        "nested:\n  - batch: 4 # Batch size\n"
        "# password: comment-secret\n"
        "# Original credential was active-secret\n"
        "# Download: https://user:pass@example.test/model?token=url-secret\n"
        "token: active-secret # api_key=inline-secret\n",
        encoding="utf-8",
    )

    with invocation(ClearMLConfig(), "train") as owner:
        connect_config_file(owner, "ultralytics", source)
        stored = task.configurations[-1]["configuration"].read_text(encoding="utf-8")

    for comment in (
        "# Ultralytics license and configuration",
        "# Training settings",
        "# Number of epochs",
        "# source: null # Prediction only",
        "# Batch size",
    ):
        assert comment in stored
    assert stored.index("epochs:") < stored.index("nested:") < stored.index("token:")
    for secret in ("comment-secret", "user:pass", "url-secret", "active-secret", "inline-secret"):
        assert secret not in stored
    assert task.uploads == []


def test_invalid_source_yaml_fails_without_echoing_its_contents(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    source = tmp_path / "broken.yaml"
    source.write_text("secret_key: do-not-echo\ninvalid: [", encoding="utf-8")

    def run() -> None:
        with invocation(ClearMLConfig(), "train") as owner:
            connect_config_file(owner, "source", source)

    with pytest.raises(ValueError, match="Invalid YAML configuration file") as raised:
        run()

    assert "do-not-echo" not in str(raised.value)
    assert task.configurations == []
    assert task.events[-2:] == ["close", "failed"]


def test_source_json_is_sanitized_without_changing_non_secret_values(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    source = tmp_path / "native.json"
    source.write_text(
        '{"model": "yolo11n.pt", "api_token": "hidden", "epochs": 3}',
        encoding="utf-8",
    )

    with invocation(ClearMLConfig(), "train") as owner:
        stored = connect_config_file(owner, "native_configuration", source)
        assert stored == source
        stored_text = task.configurations[-1]["configuration"].read_text(encoding="utf-8")

    assert stored_text == (
        '{\n  "model": "yolo11n.pt",\n  "api_token": "<redacted>",\n  "epochs": 3\n}\n'
    )
    assert task.configurations[-1]["configuration"].suffix == ".json"
    assert task.uploads == []


def test_dataframe_artifact_uses_the_required_synchronous_path(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    frame = pd.DataFrame({"value": [1]})

    with invocation(ClearMLConfig(), "metrics") as owner:
        upload_artifact(owner, "metrics_table", frame)

    uploaded = task.uploads[0]
    assert uploaded["artifact_object"] is frame
    assert uploaded["wait_on_upload"] is True


def test_remote_configuration_can_replace_missing_original(
    fake_clearml: tuple[type[Any], FakeTask],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task = fake_clearml
    override = tmp_path / "remote.yaml"
    override.write_text("epochs: 2\n")
    task.configuration_result = override
    monkeypatch.setattr(task, "running_locally", lambda: False)
    with invocation(ClearMLConfig(), "train") as owner:
        effective = connect_config_file(owner, "source", tmp_path / "missing.yaml")
        assert effective == override


def test_common_authentication_shapes_are_redacted() -> None:
    from clearml_yolo.adapters.clearml.session import sanitize_configuration

    value = {
        "headers": {"Authorization": "Bearer credential", "Content-Type": "application/json"},
        "private_key": "private material",
        "auth": {"username": "operator", "password": "value"},
        "endpoint": "https://example.test?sig=credential&safe=yes",
    }
    assert sanitize_configuration(value) == {
        "headers": {"Authorization": "<redacted>", "Content-Type": "application/json"},
        "private_key": "<redacted>",
        "auth": "<redacted>",
        "endpoint": "https://example.test?sig=%3Credacted%3E&safe=yes",
    }


def test_metric_split_upload_rejection_fails_owner_and_retains_payload(
    fake_clearml: tuple[type[Any], FakeTask],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    from clearml_yolo.application.use_cases.metrics import EvaluationConfig, compute_metrics
    from clearml_yolo.core.publication import FiftyOneConfig
    from test_metrics import _write_inputs

    _, task = fake_clearml
    predictions, ground_truth = _write_inputs(tmp_path)
    original = task.upload_artifact

    def reject_evaluation(**kwargs: Any) -> bool:
        if kwargs["name"] == "metrics_dashboard_full_test":
            return False
        return original(**kwargs)

    monkeypatch.setattr(task, "upload_artifact", reject_evaluation)
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.report_table",
        lambda *a, **kw: None,
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.metrics.report_scalars",
        lambda *a: None,
    )
    with (
        pytest.raises(ArtifactUploadError, match="metrics_dashboard_full_test"),
        invocation(ClearMLConfig(), "metrics"),
    ):
        compute_metrics(
            predictions,
            ground_truth,
            tmp_path / "metrics",
            ClearMLConfig(),
            EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="test model",
            deps=workflow_dependencies,
        )
    assert task.failed
    assert not task.completed
    assert (tmp_path / "metrics/evaluation_test.json").is_file()
    assert (tmp_path / "metrics/full_dashboard_test.xlsx").is_file()


def test_publish_table_deduplicates_bytes_and_satisfies_aliases(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    first = tmp_path / "first.csv"
    alias = tmp_path / "alias.csv"
    first.write_bytes(b"name,value\ncat,1\n")
    alias.write_bytes(first.read_bytes())

    with invocation(ClearMLConfig(), "pipeline") as owner:
        expect_artifacts(owner, ["ground_truth", "metrics_ground_truth"])
        publish_table(owner, "ground_truth", first)
        publish_table(owner, "metrics_ground_truth", alias)
        publish_table(owner, "ground_truth", first)

    assert [upload["name"] for upload in task.uploads] == ["ground_truth"]


def test_publish_table_suffixes_different_content_under_the_same_name(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    third = tmp_path / "third.csv"
    first.write_bytes(b"name,value\ncat,1\n")
    second.write_bytes(b"name,value\ndog,2\n")
    third.write_bytes(b"name,value\nbird,3\n")

    with invocation(ClearMLConfig(), "metrics") as owner:
        publish_table(owner, "predictions", first)
        publish_table(owner, "predictions", second)
        publish_table(owner, "predictions", third)
        publish_table(owner, "predictions", second)

    assert task.uploads[0]["name"] == "predictions"
    assert task.uploads[1]["name"].startswith("predictions_")
    assert len(task.uploads[1]["name"]) == len("predictions_") + 12
    assert task.uploads[2]["name"].startswith("predictions_")
    assert len({upload["name"] for upload in task.uploads}) == 3


def test_record_run_configuration_merges_sanitized_meaningful_values(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    with invocation(ClearMLConfig(), "pipeline") as owner:
        first = record_run_configuration(
            owner,
            {
                "wrapper": {"output": "runs/example", "unused": {}},
                "token": "secret",
                "predict": {"save": False, "classes": None},
            },
        )
        merged = record_run_configuration(owner, {"evaluation": {"iou": 0.0}, "empty": []})

    assert first["predict"] == {"save": False, "classes": None}
    assert merged == {
        "wrapper": {"output": "runs/example"},
        "token": "<redacted>",
        "predict": {"save": False, "classes": None},
        "evaluation": {"iou": 0.0},
    }
    assert all(configuration["name"] == "run" for configuration in task.configurations)
    assert task.configurations[-1]["configuration"] == merged
    assert task.uploads == []


def test_empty_run_configuration_contribution_is_a_noop(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    with invocation(ClearMLConfig(), "train") as owner:
        assert record_run_configuration(owner, {"normalization": {}}) == {}

    assert task.configurations == []


def test_replay_configuration_returns_remote_canonical_mapping(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    task.local = False
    task.run_configuration_result = {
        "wrapper": {"output": "remote"},
        "predict": {"classes": None, "save": False},
    }

    with invocation(ClearMLConfig(), "predict") as owner:
        effective = replay_configuration(owner, {"wrapper": {"output": "local"}})

    assert effective == task.run_configuration_result
    assert task.configurations[0]["ignore_remote_overrides"] is False
    assert task.configurations[1] == {
        "configuration": task.run_configuration_result,
        "name": "run",
        "ignore_remote_overrides": True,
    }


def test_model_barrier_waits_flushes_reloads_and_verifies_before_completion(
    fake_clearml: tuple[type[Any], FakeTask], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, task = fake_clearml
    clearml_module = sys.modules["clearml"]
    output_model = clearml_module.OutputModel
    events: list[str] = []
    original_flush = task.flush

    def flush(*, wait_for_uploads: bool) -> bool:
        events.append("flush")
        return original_flush(wait_for_uploads=wait_for_uploads)

    monkeypatch.setattr(task, "flush", flush)
    original_reload = task.reload

    def reload() -> None:
        events.append("reload")
        original_reload()

    monkeypatch.setattr(task, "reload", reload)

    with invocation(ClearMLConfig(), "train") as owner:
        register_model_barrier(owner, lambda: events.append("verify"))

    assert output_model.wait_calls == 1
    assert events == ["flush", "reload", "verify"]
    assert task.events[-2:] == ["close", "completed"]


def test_model_barrier_failure_fails_task_and_command(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    def run() -> None:
        with invocation(ClearMLConfig(), "train") as owner:
            register_model_barrier(
                owner, lambda: (_ for _ in ()).throw(ArtifactUploadError("model missing"))
            )

    with pytest.raises(ArtifactUploadError, match="model missing"):
        run()

    assert task.failed
    assert not task.completed


def test_model_upload_wait_failure_fails_task_and_command(
    fake_clearml: tuple[type[Any], FakeTask], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, task = fake_clearml
    output_model = sys.modules["clearml"].OutputModel
    monkeypatch.setattr(
        output_model,
        "wait_for_uploads",
        classmethod(lambda cls: (_ for _ in ()).throw(ArtifactUploadError("upload wait"))),
    )

    with (
        pytest.raises(ArtifactUploadError, match="upload wait"),
        invocation(ClearMLConfig(), "train") as owner,
    ):
        register_model_barrier(owner, lambda: None)

    assert task.failed
    assert not task.completed


@pytest.mark.parametrize("remote", [False, True])
def test_run_replay_redacts_storage_without_rewriting_execution_credentials(
    fake_clearml: tuple[type[Any], FakeTask], remote: bool
) -> None:
    _, task = fake_clearml
    task.local = not remote
    local = {"weights": "https://host/model.pt?token=local-secret"}
    effective = {"weights": "https://host/model.pt?token=remote-secret"} if remote else local
    if remote:
        task.run_configuration_result = effective
    with invocation(ClearMLConfig(), "predict") as owner:
        replayed = replay_configuration(owner, local)
    assert replayed == effective
    stored = str(task.configurations[-1]["configuration"])
    assert "local-secret" not in stored
    assert "remote-secret" not in stored


def _resolve_attachment(document: Any) -> Any:
    from clearml_yolo.entrypoints.hydra.config_resolution import resolve_config_document

    return resolve_config_document(document, {"run_dir": "runs/effective", "batch": 8})


@pytest.mark.parametrize("suffix", [".yaml", ".yml", ".json"])
def test_configuration_file_resolves_active_typed_values_and_preserves_source(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path, suffix: str
) -> None:
    _, task = fake_clearml
    source = tmp_path / f"source{suffix}"
    document = {
        "size": 960,
        "copy": "${size}",
        "output": "${run_dir}",
        "nested": [{"value": "${batch}", "enabled": True, "empty": None}],
        "literal": r"\${kept}",
    }
    if suffix == ".json":
        source.write_text(json.dumps(document), encoding="utf-8")
    else:
        with source.open("w", encoding="utf-8") as stream:
            YAML().dump(document, stream)
        with source.open("a", encoding="utf-8") as stream:
            stream.write("# example: ${unknown} remains a comment\n")
    original = source.read_bytes()

    with invocation(ClearMLConfig(), "train", config_resolver=_resolve_attachment) as owner:
        effective = connect_config_file(owner, "source", source)
        initial_path = task.configurations[0]["configuration"]
        stored_path = task.configurations[-1]["configuration"]
        stored = YAML(typ="safe").load(stored_path)
        executed = YAML(typ="safe").load(effective)
        assert effective != source
        assert effective != stored_path
        assert (
            stored
            == executed
            == {
                "size": 960,
                "copy": 960,
                "output": "runs/effective",
                "nested": [{"value": 8, "enabled": True, "empty": None}],
                "literal": "${kept}",
            }
        )
        assert YAML(typ="safe").load(initial_path) == stored
        if suffix != ".json":
            assert "# example: ${unknown} remains a comment" in stored_path.read_text()

    assert source.read_bytes() == original
    assert task.uploads == []
    assert task.completed


@pytest.mark.parametrize("suffix", [".yaml", ".json"])
def test_configuration_file_redacts_resolved_secret_aliases_only_in_storage(
    fake_clearml: tuple[type[Any], FakeTask],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    _, task = fake_clearml
    monkeypatch.setenv("CY_ATTACHMENT_TEST_SECRET", "private-test-value")
    document = {
        "password": "${oc.env:CY_ATTACHMENT_TEST_SECRET}",
        "copy": "${password}",
        "message": "prefix-${password}",
    }
    source = tmp_path / f"private{suffix}"
    source.write_text(json.dumps(document), encoding="utf-8")
    original = source.read_bytes()
    with invocation(ClearMLConfig(), "train", config_resolver=_resolve_attachment) as owner:
        effective = connect_config_file(owner, "private", source)
        assert YAML(typ="safe").load(effective) == {
            "password": "private-test-value",
            "copy": "private-test-value",
            "message": "prefix-private-test-value",
        }
        for attachment in task.configurations:
            payload = attachment["configuration"].read_text()
            assert "private-test-value" not in payload
            assert "${" not in payload
            assert "<redacted>" in payload
        assert effective != task.configurations[-1]["configuration"]
    assert source.read_bytes() == original


@pytest.mark.parametrize("missing_source", [False, True])
def test_remote_configuration_resolution_preserves_private_execution_and_comments(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path, missing_source: bool
) -> None:
    _, task = fake_clearml
    task.local = False
    source = tmp_path / "source.yaml"
    if not missing_source:
        source.write_text("epochs: 1\n", encoding="utf-8")
    override = tmp_path / "override.yaml"
    override.write_text(
        "# example: ${unknown}\npassword: remote-private\n"
        "copy: ${password} # copy comment\nepochs: ${batch}\n",
        encoding="utf-8",
    )
    original = override.read_bytes()
    task.configuration_result = override
    with invocation(ClearMLConfig(), "train", config_resolver=_resolve_attachment) as owner:
        effective = connect_config_file(owner, "source", source)
        assert effective != override
        assert YAML(typ="safe").load(effective) == {
            "password": "remote-private",
            "copy": "remote-private",
            "epochs": 8,
        }
        stored = task.configurations[-1]["configuration"].read_text()
        assert "remote-private" not in stored
        assert "epochs: 8" in stored
        assert "# example: ${unknown}" in stored
        assert "# copy comment" in stored
        assert task.configurations[-1]["ignore_remote_overrides"] is True
    assert override.read_bytes() == original


@pytest.mark.parametrize("value", ["${absent}", "???", "${a}"])
def test_direct_file_attachment_requires_resolver_for_active_references(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path, value: str
) -> None:
    _, task = fake_clearml
    source = tmp_path / "source.yaml"
    source.write_text(f"a: {value}\n", encoding="utf-8")
    original = source.read_bytes()
    with (
        pytest.raises(ValueError, match="config_resolver"),
        invocation(ClearMLConfig(), "train") as owner,
    ):
        connect_config_file(owner, "source", source)
    assert task.configurations == []
    assert task.uploads == []
    assert task.failed
    assert not task.completed
    assert source.read_bytes() == original


@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize(
    "value",
    [
        "${missing}",
        "???",
        "${a}",
        "${unregistered:value}",
        "${oc.env:CY_ATTACHMENT_ABSENT_ENV}",
    ],
)
def test_invalid_file_resolution_fails_before_final_publication(
    fake_clearml: tuple[type[Any], FakeTask],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    remote: bool,
) -> None:
    _, task = fake_clearml
    monkeypatch.delenv("CY_ATTACHMENT_ABSENT_ENV", raising=False)
    source = tmp_path / "source.yaml"
    invalid = tmp_path / "invalid.yaml"
    source.write_text("a: 1\n", encoding="utf-8")
    invalid.write_text(f"password: never-publish\na: {value}\n", encoding="utf-8")
    original = invalid.read_bytes()
    if remote:
        task.configuration_result = invalid
    else:
        source = invalid
    with (
        pytest.raises(ValueError, match="could not be resolved") as raised,
        invocation(ClearMLConfig(), "train", config_resolver=_resolve_attachment) as owner,
    ):
        connect_config_file(owner, "source", source)
    assert "never-publish" not in str(raised.value)
    assert task.uploads == []
    assert task.failed
    assert not task.completed
    assert invalid.read_bytes() == original
    assert len(task.configurations) == (1 if remote else 0)


def test_attachment_resolver_exception_does_not_expose_credential_details(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    source = tmp_path / "source.yaml"
    source.write_text("password: ${hidden}\n", encoding="utf-8")

    def broken_resolver(document: Any) -> Any:
        raise RuntimeError("private exception credential")

    with (
        pytest.raises(ValueError, match="could not be resolved") as raised,
        invocation(ClearMLConfig(), "train", config_resolver=broken_resolver) as owner,
    ):
        connect_config_file(owner, "source", source)
    assert "private exception credential" not in str(raised.value)
    assert raised.value.__suppress_context__
    assert task.configurations == []
    assert "private exception credential" not in str(task.failed)


def test_configuration_copies_have_unique_paths_without_artifact_registration(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("epochs: 2\n", encoding="utf-8")
    second.write_text("epochs: 3\n", encoding="utf-8")
    with invocation(ClearMLConfig(), "train") as owner:
        assert connect_config_file(owner, "first", first) == first
        first_copy = task.configurations[-1]["configuration"]
        assert connect_config_file(owner, "second", second) == second
        second_copy = task.configurations[-1]["configuration"]
        assert first_copy != second_copy
        assert YAML(typ="safe").load(first_copy) == {"epochs": 2}
        assert YAML(typ="safe").load(second_copy) == {"epochs": 3}
    assert task.uploads == []


def test_resolved_configuration_preserves_fields_and_cleans_owned_copy(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, task = fake_clearml
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    source = dataset_dir / "dataset.yaml"
    source.write_text("train: images/train\nval: images/val\ninference_batch: ${batch}\n")
    neighbor = dataset_dir / ".preexisting-resolved.yaml"
    neighbor.write_text("untouched\n")
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("CY_HOME", str(workspace))
    with invocation(ClearMLConfig(), "train", config_resolver=_resolve_attachment) as owner:
        effective = connect_config_file(owner, "source", source)
        stored = task.configurations[-1]["configuration"]
        assert effective.is_relative_to(workspace / ".tmp")
        assert effective != source
        assert effective.is_file()
        assert YAML(typ="safe").load(effective)["train"] == "images/train"
        assert "path" not in YAML(typ="safe").load(effective)
    assert source.is_file()
    assert neighbor.read_text() == "untouched\n"
    assert not effective.exists()
    assert not stored.exists()


@pytest.mark.parametrize("use_resolver", [False, True])
def test_yaml_dataset_integer_label_keys_and_comments_survive_publication(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path, use_resolver: bool
) -> None:
    _, task = fake_clearml
    source = tmp_path / "dataset.yaml"
    source.write_text("names:\n  0: person # person label\n  1: car # car label\n")
    with invocation(
        ClearMLConfig(), "train", config_resolver=_resolve_attachment if use_resolver else None
    ) as owner:
        assert connect_config_file(owner, "source", source) == source
        stored = task.configurations[-1]["configuration"]
        assert YAML(typ="safe").load(stored) == {"names": {0: "person", 1: "car"}}
        assert "# person label" in stored.read_text()
        assert "# car label" in stored.read_text()


@pytest.mark.parametrize("secret", [172983, True, 1729.83])
@pytest.mark.parametrize("suffix", [".yaml", ".json"])
def test_configuration_file_redacts_typed_credential_aliases(
    fake_clearml: tuple[type[Any], FakeTask],
    tmp_path: Path,
    secret: bool | float,
    suffix: str,
) -> None:
    _, task = fake_clearml
    source = tmp_path / f"private{suffix}"
    source.write_text(json.dumps({"password": secret, "copy": "${password}"}))
    with invocation(ClearMLConfig(), "train", config_resolver=_resolve_attachment) as owner:
        effective = connect_config_file(owner, "source", source)
        assert YAML(typ="safe").load(effective) == {"password": secret, "copy": secret}
        stored = task.configurations[-1]["configuration"]
        assert YAML(typ="safe").load(stored) == {
            "password": "<redacted>",
            "copy": "<redacted>",
        }


@pytest.mark.parametrize("reference", ["${auth.password}", "${oc.env:CY_PROBE_API_SECRET}"])
def test_configuration_file_redacts_aliases_with_secret_provenance_from_context(
    fake_clearml: tuple[type[Any], FakeTask],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reference: str,
) -> None:
    _, task = fake_clearml
    monkeypatch.setenv("CY_PROBE_API_SECRET", "probe-private-value")
    source = tmp_path / "alias.yaml"
    source.write_text(f"copy: {reference}\n")
    original = source.read_bytes()

    def resolve_private(document: Any) -> Any:
        from clearml_yolo.entrypoints.hydra.config_resolution import resolve_config_file

        context = (
            {"auth": {"password": "probe-private-value"}} if reference == "${auth.password}" else {}
        )
        return resolve_config_file(document, context)

    with invocation(ClearMLConfig(), "train", config_resolver=resolve_private) as owner:
        effective = connect_config_file(owner, "source", source)
        assert YAML(typ="safe").load(effective) == {"copy": "probe-private-value"}
        for attachment in task.configurations:
            stored = attachment["configuration"].read_text()
            assert "probe-private-value" not in stored
            assert YAML(typ="safe").load(stored) == {"copy": "<redacted>"}
    assert source.read_bytes() == original


def test_replay_preserves_explicit_empty_executable_values(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    with invocation(ClearMLConfig(), "predict") as owner:
        values = {"ultralytics_predict": {"classes": [], "source": "", "nested": {}}, "splits": []}
        assert replay_configuration(owner, values) == values
        stored = record_run_configuration(owner, {"ultralytics_predict": {"classes": []}})
        assert stored["ultralytics_predict"]["classes"] == []


def test_cleanup_failure_retains_original_exception(
    fake_clearml: tuple[type[Any], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task = fake_clearml
    original = ValueError("original computation failure")

    def failed_close() -> None:
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(task, "close", failed_close)
    with (
        pytest.raises(ValueError, match="original computation failure") as captured,
        invocation(ClearMLConfig(), "report"),
    ):
        raise original
    assert captured.value is original
    assert task.failed == []


def test_local_cleanup_oserror_does_not_mask_original_failure(
    fake_clearml: tuple[type[Any], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.session import _InvocationState

    original = ValueError("computation failed")

    def cleanup(_self: _InvocationState) -> None:
        raise PermissionError("cleanup denied")

    monkeypatch.setattr(_InvocationState, "cleanup", cleanup)
    with (
        pytest.raises(ValueError, match="computation failed") as captured,
        invocation(ClearMLConfig(), "report"),
    ):
        raise original
    assert captured.value is original


def test_local_cleanup_oserror_propagates_after_otherwise_successful_call(
    fake_clearml: tuple[type[Any], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.session import _InvocationState

    def cleanup(_self: _InvocationState) -> None:
        raise PermissionError("cleanup denied")

    monkeypatch.setattr(_InvocationState, "cleanup", cleanup)
    with (
        pytest.raises(PermissionError, match="cleanup denied"),
        invocation(ClearMLConfig(), "report"),
    ):
        pass


@pytest.mark.parametrize("failure_stage", ["finalization", "local_cleanup"])
def test_secondary_failure_diagnostics_preserve_primary_and_redact_credentials(
    fake_clearml: tuple[type[Any], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
    failure_stage: str,
) -> None:
    from loguru import logger

    from clearml_yolo.adapters.clearml.session import _InvocationState

    _, task = fake_clearml
    original = ValueError("primary failure")

    def fail(*args: Any) -> None:
        raise PermissionError("filesystem denied access token=private-cleanup-token")

    if failure_stage == "finalization":
        monkeypatch.setattr(task, "close", fail)
    else:
        monkeypatch.setattr(_InvocationState, "cleanup", fail)
    messages: list[str] = []
    sink = logger.add(messages.append, level="DEBUG", format="{message}")
    try:
        with (
            pytest.raises(ValueError, match="primary failure") as caught,
            invocation(ClearMLConfig(), "report"),
        ):
            raise original
    finally:
        logger.remove(sink)
    assert caught.value is original
    output = "".join(messages)
    assert "PermissionError" in output
    assert "filesystem denied access" in output
    assert "private-cleanup-token" not in output
