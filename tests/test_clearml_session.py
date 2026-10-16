"""Explicit ClearML configuration, artifact storage, and invocation lifecycle."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
import types
from collections import UserDict
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
import pytest
from ruamel.yaml import YAML

from clearml_yolo.adapters.clearml.console import ConsolePublicationError
from clearml_yolo.adapters.clearml.deadline import TaskFinalizationError
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
        self.run_configuration_result: Any = None
        self.configuration_reads: list[str] = []
        self.run_configuration_text: str | None = None
        self.ignore_remote_run_overrides = False
        self.closed = False
        self.script_updates: list[dict[str, Any]] = []
        self.script: dict[str, Any] = {}
        self.data = types.SimpleNamespace(script=types.SimpleNamespace(to_dict=lambda: self.script))
        self.local = True
        self.reload_count = 0
        self._dev_worker: Any = None
        self._logger: Any = None

    def set_script(self, **kwargs: Any) -> None:
        self.script_updates.append(kwargs)
        self.script.update(kwargs)
        if "commit" in self.script:
            self.script["version_num"] = self.script.pop("commit")

    def upload_artifact(self, **kwargs: Any) -> bool:
        self.uploads.append(kwargs)
        return self.upload_result

    def connect_configuration(self, **kwargs: Any) -> Any:
        self.configurations.append(kwargs)
        if kwargs.get("ignore_remote_overrides"):
            return kwargs["configuration"]
        if kwargs.get("name") == "run":
            if self.ignore_remote_run_overrides:
                return kwargs["configuration"]
            return self.run_configuration_result or kwargs["configuration"]
        return self.configuration_result or kwargs["configuration"]

    def get_configuration_object_as_dict(self, name: str) -> Any:
        self.configuration_reads.append(name)
        return self.run_configuration_result

    def get_configuration_object(self, name: str) -> str | None:
        assert name == "run"
        return self.run_configuration_text

    def set_configuration_object(self, **kwargs: Any) -> None:
        self.configurations.append(kwargs)

    def flush(self, *, wait_for_uploads: bool) -> bool:
        assert wait_for_uploads is True
        return self.flush_result

    def running_locally(self) -> bool:
        return self.local

    def get_output_log_web_page(self) -> str:
        return "https://clearml.example/tasks/task-id"

    def close(self) -> None:
        self.events.append("close")
        self.closed = True

    def is_main_task(self) -> bool:
        return not self.closed

    def reload(self) -> None:
        self.reload_count += 1

    def _reload_field(self, field: str) -> Any:
        assert field == "script"
        self.reload()
        return self.data.script

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
    module.Logger = types.SimpleNamespace(report_text=lambda *_args, **_kwargs: None)  # type: ignore[attr-defined]

    class OutputModel:
        wait_calls: ClassVar[int] = 0

        @classmethod
        def wait_for_uploads(cls) -> None:
            cls.wait_calls += 1

    module.OutputModel = OutputModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clearml", module)
    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.session._start_console_publisher", lambda *_args: None
    )
    return Task, task


def test_tracking_is_required_and_old_task_reuse_controls_are_gone() -> None:
    config = ClearMLConfig()

    assert not hasattr(config, "enabled")
    assert not hasattr(config, "continue_task_id")
    assert not hasattr(config, "reuse_last_task_id")


@pytest.mark.parametrize("fail", [False, True])
def test_sdk_startup_capture_is_owner_scoped_and_restores_on_failure(
    capfd: pytest.CaptureFixture[str], fail: bool,
) -> None:
    from clearml_yolo.adapters.clearml.session import _capture_sdk_startup

    sent: list[str] = []

    class Reporter:
        def report_text(self, message: str, *_args: object, **_kwargs: object) -> None:
            sent.append(message)

    reporter = Reporter()
    original = Reporter.report_text
    startup = "ClearML Task: created new task id=" + "a" * 32
    with suppress(RuntimeError), _capture_sdk_startup(Reporter):
        reporter.report_text(startup)
        reporter.report_text("Ordinary application message")
        unrelated = threading.Thread(target=reporter.report_text, args=(startup,))
        unrelated.start()
        unrelated.join(timeout=1)
        assert not unrelated.is_alive()
        if fail:
            raise RuntimeError("Task initialization failed")
    assert Reporter.report_text is original
    assert sent == ["Ordinary application message", startup]
    assert capfd.readouterr().out == startup + "\n"


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
    assert task_type.init_calls[0]["auto_connect_streams"] is False
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
            "config_dict": {"run_dir": "runs/example"},
            "name": "run",
            "config_type": "dictionary",
        }
    ]


def test_invocation_publishes_source_identity_before_workflow(
    fake_clearml: tuple[type[Any], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task = fake_clearml
    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.script._source_identity",
        lambda: {
            "repository": "https://example.test/repo.git",
            "branch": "main",
            "commit": "a" * 40,
        },
    )
    with invocation(ClearMLConfig(), "ground_truth"):
        assert len(task.script_updates) == 1
        script = task.script_updates[0]
        assert script["repository"] == "https://example.test/repo.git"
        assert len(script["commit"]) == 40
        assert script["branch"]
        assert script["entry_point"] == "-m clearml_yolo.entrypoints.ground_truth"
        assert script["working_dir"] == "."
        assert script["diff"] == ""
        with invocation(ClearMLConfig(), "train"):
            assert len(task.script_updates) == 1


def test_remote_invocation_preserves_agent_script_metadata(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    task.local = False
    with invocation(ClearMLConfig(), "ground_truth"):
        assert task.script_updates == []


def test_rejected_source_metadata_fails_owner_before_workflow(
    fake_clearml: tuple[type[Any], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task = fake_clearml
    monkeypatch.setattr(task, "set_script", lambda **_kwargs: None)
    with (
        pytest.raises(RuntimeError, match="did not retain script metadata field"),
        invocation(ClearMLConfig(), "ground_truth"),
    ):
        pytest.fail("Workflow must not start after rejected script metadata")
    assert task.closed
    assert task.failed
    assert not task.completed


def test_console_streams_reach_offline_sdk_without_duplicates(tmp_path: Path) -> None:
    code = """
import json
import sys
from pathlib import Path

from loguru import logger
from clearml import Logger
from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation
from clearml_yolo.adapters.observability.capture import active_capture

original_report_text = Logger.report_text
try:
    with invocation(ClearMLConfig(project_name='console-regression'), 'predict') as task:
        folder = Path(task.get_offline_mode_folder())
        capture = active_capture()
        assert capture is not None
        print('console-stdout-marker')
        print('console-stderr-marker', file=sys.stderr)
        logger.info('console-loguru-marker')
        raise RuntimeError('controlled offline failure')
except RuntimeError as error:
    assert str(error) == 'controlled offline failure', error
assert Logger.report_text is original_report_text

events = [
    event
    for line in (folder / 'log.jsonl').read_text().splitlines()
    for event in json.loads(line)
]
for marker in ('console-stdout-marker', 'console-stderr-marker', 'console-loguru-marker'):
    assert sum(marker in event['msg'] for event in events) == 1, (marker, events)
assert sum('created new task' in event['msg'] for event in events) == 1
assert all(task.id not in event['msg'] for event in events)
assert task.id in capture.paths['stdout'].read_text()
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

    stored = task.configurations[-1]["config_dict"]
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
        lambda *a, **_kw: None,
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

    assert [upload["name"] for upload in task.uploads] == [
        "predictions", "predictions_2", "predictions_3",
    ]


def test_publish_table_numbered_suffix_skips_existing_caller_names(
    fake_clearml: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = fake_clearml
    paths = [tmp_path / f"table-{number}.csv" for number in range(4)]
    for number, path in enumerate(paths):
        path.write_text(f"name,value\ncat,{number}\n")

    with invocation(ClearMLConfig(), "metrics") as owner:
        publish_table(owner, "predictions_2", paths[0])
        publish_table(owner, "predictions", paths[1])
        publish_table(owner, "predictions", paths[2])
        publish_table(owner, "predictions_3", paths[3])
        publish_table(owner, "predictions", paths[2])
        publish_table(owner, "alias", paths[2])

    assert [upload["name"] for upload in task.uploads] == [
        "predictions_2", "predictions", "predictions_3", "predictions_3_2",
    ]


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
    assert task.configurations[-1]["config_dict"] == merged
    assert task.uploads == []


def test_empty_run_configuration_contribution_is_a_noop(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    with invocation(ClearMLConfig(), "train") as owner:
        assert record_run_configuration(owner, {"normalization": {}}) == {}

    assert task.configurations == []


@pytest.mark.parametrize(
    "evidence",
    [
        {"operation": "onnx", "plugins": [], "engine_sha256": None},
        {"operation": "verify", "cases": [{"detections": []}], "rejections": {}},
    ],
)
def test_export_result_preserves_empty_evidence_fields(
    evidence: dict[str, Any], fake_clearml: tuple[type[Any], FakeTask]
) -> None:
    _, task = fake_clearml
    with invocation(ClearMLConfig(), "export") as owner:
        stored = record_run_configuration(owner, {"export_result": evidence})

    assert stored["export_result"] == evidence
    assert task.configurations[-1]["config_dict"]["export_result"] == evidence


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
    assert task.configuration_reads == ["run"]
    assert task.configurations == [
        {
            "config_dict": task.run_configuration_result,
            "name": "run",
            "config_type": "dictionary",
        }
    ]


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
        events.clear()  # Observe the model barrier after initial script metadata readback.
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
    stored = str(task.configurations[-1]["config_dict"])
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
    assert ("PermissionError" in output) is (failure_stage == "finalization")
    assert ("filesystem denied access" in output) is (failure_stage == "finalization")
    assert "private-cleanup-token" not in output


def test_remote_run_replay_bypasses_inherited_ignore_flag(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    task.local = False
    task.ignore_remote_run_overrides = True
    task.run_configuration_result = {"queue": {"enabled": True}, "model": {"backend": "deimv2"}}
    with invocation(ClearMLConfig(), "predict") as owner:
        replayed = replay_configuration(owner, {"queue": {"enabled": False}})
    assert replayed == task.run_configuration_result
    assert task.configuration_reads == ["run"]
    assert all("ignore_remote_overrides" not in item for item in task.configurations)


def test_run_replay_detaches_nested_proxies_before_storage_mutation(
    fake_clearml: tuple[type[Any], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task = fake_clearml
    task.local = False
    nested: UserDict[str, Any] = UserDict(
        {"sizes": (UserDict({"width": 64}),), "token": "private-token"}
    )
    task.run_configuration_result = UserDict({"model": nested})
    saved: list[dict[str, Any]] = []

    def mutate_snapshot(**kwargs: Any) -> None:
        snapshot = kwargs["config_dict"]
        saved.append(json.loads(json.dumps(snapshot)))
        snapshot["model"]["sizes"][0]["width"] = 999

    monkeypatch.setattr(task, "set_configuration_object", mutate_snapshot)
    with invocation(ClearMLConfig(), "predict") as owner:
        replayed = replay_configuration(owner, {"model": {"sizes": []}})
        merged = record_run_configuration(owner, {"prediction_result": {"rows": 1}})
    assert type(replayed) is dict
    assert type(replayed["model"]) is dict
    assert type(replayed["model"]["sizes"]) is list
    assert type(replayed["model"]["sizes"][0]) is dict
    assert replayed["model"]["sizes"][0]["width"] == 64
    assert replayed["model"]["token"] == nested["token"]
    assert nested["sizes"][0]["width"] == 64
    assert merged["model"]["sizes"][0]["width"] == 64
    assert saved[-1]["model"]["token"] != nested["token"]
    assert "private-token" not in json.dumps(saved)
    assert saved[-1]["prediction_result"] == {"rows": 1}


@pytest.mark.parametrize("remote", [False, True])
def test_missing_remote_run_falls_back_without_redacting_executable_defaults(
    fake_clearml: tuple[type[Any], FakeTask],
    remote: bool,
) -> None:
    _, task = fake_clearml
    task.local = not remote
    local = {"token": "local-secret", "model": {"classes": []}}
    with invocation(ClearMLConfig(), "predict") as owner:
        assert replay_configuration(owner, local) == local
    assert task.configuration_reads == (["run"] if remote else [])
    assert task.configurations[-1]["config_dict"]["token"] != local["token"]
    assert "local-secret" not in json.dumps(task.configurations)


@pytest.mark.parametrize("canonical", [{}, [], "invalid"])
def test_present_invalid_remote_run_never_falls_back(
    fake_clearml: tuple[type[Any], FakeTask],
    canonical: Any,
) -> None:
    _, task = fake_clearml
    task.local = False
    task.run_configuration_result = canonical
    with pytest.raises((TypeError, ValueError)), invocation(ClearMLConfig(), "predict") as owner:
        replay_configuration(owner, {"model": {"backend": "deimv2"}})
    assert task.failed
    assert task.configurations == []


@pytest.mark.parametrize("text", ["", "   ", "\n"])
def test_present_empty_remote_run_text_never_uses_defaults(
    fake_clearml: tuple[type[Any], FakeTask],
    text: str,
) -> None:
    _, task = fake_clearml
    task.local = False
    task.run_configuration_text = text
    with (
        pytest.raises(ValueError, match="must not be empty"),
        invocation(ClearMLConfig(), "predict") as owner,
    ):
        replay_configuration(owner, {"model": {"backend": "deimv2"}})
    assert task.failed
    assert task.configurations == []


def test_failed_finalization_retains_config_for_pending_consumers(
    fake_clearml: tuple[type[Any], FakeTask],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task = fake_clearml
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    source = tmp_path / "configuration.yaml"
    source.write_text("epochs: 2\n")
    monkeypatch.setattr(task, "flush", lambda **_kwargs: False)
    stored: list[Path] = []

    def run() -> None:
        with invocation(ClearMLConfig(), "train") as owner:
            connect_config_file(owner, "source", source)
            stored.append(Path(task.configurations[-1]["configuration"]))

    with pytest.raises(RuntimeError, match="flush"):
        run()
    assert stored[0].is_file()
    assert source.read_text() == "epochs: 2\n"


@pytest.fixture
def isolated_owner_session(
    fake_clearml: tuple[type[Any], FakeTask], monkeypatch: pytest.MonkeyPatch
) -> tuple[type[Any], FakeTask, list[str]]:
    """Exercise real session boundaries with inert external capture/SDK effects."""
    task_type, task = fake_clearml
    effects: list[str] = []

    def captured() -> object:
        effects.append("capture")
        return object()

    def unexpected_current_task() -> None:
        pytest.fail("An inert owner guard must not query SDK current_task")

    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.active_capture", captured)
    monkeypatch.setattr(task_type, "current_task", unexpected_current_task, raising=False)
    return task_type, task, effects


def _assert_later_owner_is_blocked(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
) -> None:
    task_type, task, effects = isolated_owner_session
    initial_effects = list(effects)
    initial_configurations = list(task.configurations)
    initial_calls = list(task_type.init_calls)
    with (
        pytest.raises(RuntimeError, match="fresh process"),
        invocation(ClearMLConfig(), "predict", {"second": True}),
    ):
        effects.append("workflow")
    assert effects == initial_effects
    assert task_type.init_calls == initial_calls
    assert task.configurations == initial_configurations


@pytest.mark.parametrize("failure_site", ["workflow", "barrier", "start"])
def test_owner_isolation_blocks_after_console_publication_failure(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    failure_site: str,
) -> None:
    _, task, _ = isolated_owner_session
    original = ConsolePublicationError("first required delivery failed")

    def fail(*_args: Any) -> Any:
        raise original

    if failure_site == "start":
        monkeypatch.setattr("clearml_yolo.adapters.clearml.session._start_console_publisher", fail)
    elif failure_site == "barrier":
        publisher = types.SimpleNamespace(barrier=fail, finish=lambda: None)
        monkeypatch.setattr(
            "clearml_yolo.adapters.clearml.session._start_console_publisher",
            lambda *_args: publisher,
        )

    def run() -> None:
        with invocation(ClearMLConfig(), "train"):
            if failure_site == "workflow":
                raise original

    with pytest.raises(ConsolePublicationError) as raised:
        run()
    assert raised.value is original
    assert not task.closed
    _assert_later_owner_is_blocked(isolated_owner_session)


def test_owner_isolation_preserves_workflow_error_when_failure_barrier_fails(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    original = ValueError("first computation failed")

    def fail() -> None:
        raise ConsolePublicationError("delivery failed during failure cleanup")

    publisher = types.SimpleNamespace(barrier=fail, finish=lambda: None)
    monkeypatch.setattr(session, "_start_console_publisher", lambda *_args: publisher)
    with (
        pytest.raises(ValueError, match="first computation failed") as raised,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert raised.value is original
    assert not task.closed
    assert task.failed
    _assert_later_owner_is_blocked(isolated_owner_session)


@pytest.mark.parametrize(
    "cleanup_error", [RuntimeError("close failed"), TaskFinalizationError("deadline")]
)
@pytest.mark.parametrize("workflow_fails", [False, True])
def test_owner_isolation_blocks_after_unconfirmed_close(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: Exception,
    workflow_fails: bool,
) -> None:
    _, task, _ = isolated_owner_session
    original = ValueError("first computation failed") if workflow_fails else cleanup_error

    def fail() -> None:
        raise cleanup_error

    monkeypatch.setattr(task, "close", fail)

    def run() -> None:
        with invocation(ClearMLConfig(), "train"):
            if workflow_fails:
                raise original

    with pytest.raises(type(original)) as raised:
        run()
    assert raised.value is original
    assert not task.closed
    _assert_later_owner_is_blocked(isolated_owner_session)


def test_owner_isolation_blocks_after_partial_task_initialization(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
) -> None:
    task_type, task, _ = isolated_owner_session
    original = RuntimeError("SDK retained an owner before init failed")

    def fail() -> None:
        raise original

    task_type.on_init = fail
    with pytest.raises(RuntimeError) as raised, invocation(ClearMLConfig(), "train"):
        pytest.fail("Initialization failure must prevent workflow execution")
    assert raised.value is original
    assert not task.closed
    task_type.on_init = None
    _assert_later_owner_is_blocked(isolated_owner_session)


@pytest.mark.parametrize("workflow_fails", [False, True])
def test_owner_isolation_allows_sequential_invocations_after_confirmed_close(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]], workflow_fails: bool
) -> None:
    task_type, task, effects = isolated_owner_session
    if workflow_fails:
        with (
            pytest.raises(ValueError, match="ordinary computation failure"),
            invocation(ClearMLConfig(), "train"),
        ):
            raise ValueError("ordinary computation failure")
    else:
        with invocation(ClearMLConfig(), "train"):
            effects.append("first")
    assert task.closed
    with invocation(ClearMLConfig(), "predict", {"second": True}):
        effects.append("second")
    assert len(task_type.init_calls) == 2
    assert effects[-1] == "second"
    assert task.configurations[-1]["config_dict"] == {"second": True}


@pytest.mark.parametrize("failure_site", ["readback", "completed", "failed", "finish"])
def test_owner_isolation_allows_later_owner_after_post_close_failure(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    failure_site: str,
) -> None:
    from clearml_yolo.adapters.clearml import session

    task_type, task, effects = isolated_owner_session
    original = RuntimeError("post-close operation failed")

    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise original

    with monkeypatch.context() as patch:
        if failure_site == "readback":
            patch.setattr(task_type, "get_task", fail)
        elif failure_site in {"completed", "failed"}:
            patch.setattr(task, f"mark_{failure_site}", fail)
        else:
            publisher = types.SimpleNamespace(barrier=lambda: None, finish=fail)
            patch.setattr(session, "_start_console_publisher", lambda *_args: publisher)

        def run() -> None:
            with invocation(ClearMLConfig(), "train"):
                if failure_site == "failed":
                    raise original

        with pytest.raises(RuntimeError) as raised:
            run()
        assert raised.value is original
    assert task.closed
    with invocation(ClearMLConfig(), "predict"):
        effects.append("second")
    assert len(task_type.init_calls) == 2
    assert effects[-1] == "second"


def test_owner_isolation_keeps_nested_stages_and_workers_inert(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_type, task, effects = isolated_owner_session
    with invocation(ClearMLConfig(), "pipeline") as owner:
        with invocation(ClearMLConfig(), "train", {"nested": True}) as nested:
            assert nested is owner
        assert init_task(ClearMLConfig(), "val") is owner
        with monkeypatch.context() as patch:
            patch.setenv("CY_CLEARML_OWNER_PID", str(os.getpid() + 1))
            with invocation(ClearMLConfig(), "predict") as worker:
                assert worker is None
    assert len(task_type.init_calls) == 1
    assert task.configurations == []
    assert effects == ["capture"]


def test_owner_isolation_blocks_after_real_close_deadline(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    monkeypatch.setattr(session, "FINALIZATION_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(task, "close", lambda: time.sleep(0.2))
    with (
        pytest.raises(TaskFinalizationError, match="deadline expired"),
        invocation(ClearMLConfig(), "train"),
    ):
        pass
    assert not task.closed
    _assert_later_owner_is_blocked(isolated_owner_session)


def test_owner_isolation_retains_inherited_guard_but_allows_worker_bypass(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_type, _, effects = isolated_owner_session
    owner_pid = os.getpid()
    with (
        pytest.raises(ConsolePublicationError, match="required delivery failed"),
        invocation(ClearMLConfig(), "train"),
    ):
        raise ConsolePublicationError("required delivery failed")
    # A fork inherits SDK state as well as our guard; PID mismatch is not proof of closure.
    monkeypatch.setattr(os, "getpid", lambda: owner_pid + 1)
    _assert_later_owner_is_blocked(isolated_owner_session)
    monkeypatch.setenv("CY_CLEARML_OWNER_PID", str(owner_pid))
    monkeypatch.setenv("CY_CLEARML_OWNER_TASK_ID", "task-id")
    with invocation(ClearMLConfig(), "predict", {"worker": True}) as worker:
        assert worker is None
    assert len(task_type.init_calls) == 1
    assert effects == ["capture"]


@pytest.mark.parametrize("workflow_fails", [False, True])
def test_owner_isolation_does_not_retry_interrupted_close_that_returns_noop(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    workflow_fails: bool,
) -> None:
    _, task, _ = isolated_owner_session
    close_error = TaskFinalizationError("first close interrupted after shutdown began")
    original = ValueError("first computation failed") if workflow_fails else close_error
    close_calls: list[str] = []

    def close() -> None:
        close_calls.append("close")
        if len(close_calls) == 1:
            raise close_error
        # The SDK records shutdown entry before flushing, so a retry returns immediately.

    monkeypatch.setattr(task, "close", close)

    def run() -> None:
        with invocation(ClearMLConfig(), "train"):
            if workflow_fails:
                raise original

    with pytest.raises(type(original)) as raised:
        run()
    assert raised.value is original
    assert close_calls == ["close"]
    assert not task.closed
    _assert_later_owner_is_blocked(isolated_owner_session)


@pytest.mark.parametrize("workflow_fails", [False, True])
def test_owner_isolation_rejects_close_returning_with_sdk_main_still_active(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    workflow_fails: bool,
) -> None:
    _, task, _ = isolated_owner_session
    original = ValueError("first computation failed")
    # ClearML shutdown catches ordinary exceptions before clearing its main task.
    monkeypatch.setattr(task, "close", lambda: None)

    def run() -> None:
        with invocation(ClearMLConfig(), "train"):
            if workflow_fails:
                raise original

    expected = ValueError if workflow_fails else TaskFinalizationError
    with pytest.raises(expected, match=r"computation failed|remained active") as raised:
        run()
    if workflow_fails:
        assert raised.value is original
    assert not task.closed
    assert not task.completed
    _assert_later_owner_is_blocked(isolated_owner_session)


def test_owner_isolation_detaches_exit_callback_when_failure_close_raises(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    original = ValueError("first computation failed")
    detached: list[FakeTask] = []

    def close() -> None:
        raise RuntimeError("ordinary close failure")

    monkeypatch.setattr(task, "close", close)
    monkeypatch.setattr(session, "detach_sdk_exit_callback", detached.append)
    with (
        pytest.raises(ValueError, match="first computation failed") as raised,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert raised.value is original
    assert detached
    assert all(candidate is task for candidate in detached)
    _assert_later_owner_is_blocked(isolated_owner_session)


@pytest.mark.parametrize("publication_fails", [False, True])
def test_owner_failure_releases_monitor_before_terminal_failure_status(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    publication_fails: bool,
) -> None:
    _, task, _ = isolated_owner_session
    original = (
        ConsolePublicationError("required delivery failed")
        if publication_fails
        else ValueError("first computation failed")
    )

    class Monitor:
        registered = True

        def unregister(self) -> bool:
            task.events.append("monitor-unregistered")
            self.registered = False
            return True

    monitor = Monitor()
    task._dev_worker = monitor
    mark_failed = task.mark_failed

    def terminal_failure(**kwargs: Any) -> object:
        if monitor.registered:
            # SDK monitoring interprets the owner's own failed status as external abort.
            task.events.append("monitor-stopped-owner")
            return object()
        return mark_failed(**kwargs)

    monkeypatch.setattr(task, "mark_failed", terminal_failure)
    with pytest.raises(type(original)) as raised, invocation(ClearMLConfig(), "train"):
        raise original
    assert raised.value is original
    assert task.events[0] == "monitor-unregistered"
    assert "monitor-stopped-owner" not in task.events
    assert task.failed
    assert task.closed is not publication_fails
    if publication_fails:
        _assert_later_owner_is_blocked(isolated_owner_session)
    else:
        with invocation(ClearMLConfig(), "predict"):
            pass


@pytest.mark.parametrize(
    "release_failure", ["missing-field", "missing-method", "rejected", "exception", "interrupt"]
)
def test_owner_failure_monitor_release_failure_preserves_original_and_skips_status(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    release_failure: str,
) -> None:
    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    original = ValueError("first computation failed")
    diagnostics: list[BaseException] = []
    detached: list[FakeTask] = []

    class Monitor:
        def unregister(self) -> bool:
            if release_failure == "exception":
                raise RuntimeError("monitor release failed")
            if release_failure == "interrupt":
                raise KeyboardInterrupt("monitor release interrupted")
            return False

    if release_failure == "missing-field":
        monkeypatch.delattr(task, "_dev_worker")
    elif release_failure == "missing-method":
        task._dev_worker = object()
    else:
        task._dev_worker = Monitor()
    monkeypatch.setattr(session, "detach_sdk_exit_callback", detached.append)
    monkeypatch.setattr(
        "clearml_yolo.adapters.observability.diagnostics.log_exception",
        lambda _message, error, **_kwargs: diagnostics.append(error),
    )
    with (
        pytest.raises(ValueError, match="first computation failed") as raised,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert raised.value is original
    assert diagnostics
    assert detached == [task]
    assert not task.closed
    assert not task.failed
    assert not task.completed
    _assert_later_owner_is_blocked(isolated_owner_session)


def test_incomplete_owner_detaches_exact_cached_reporter_without_exit_reentry(
    tmp_path: Path,
) -> None:
    code = """
import atexit
import time
from clearml_yolo.adapters.clearml.deadline import detach_sdk_exit_callback

class Reporter:
    def __init__(self, name, blocks):
        self.name = name
        self.blocks = blocks

    def _handle_program_exit(self):
        print(self.name, flush=True)
        if self.blocks:
            time.sleep(30)

class Owner:
    def __init__(self, reporter):
        self._Task__reporter = reporter

    @property
    def _reporter(self):
        raise AssertionError('Lazy SDK reporter getter must remain untouched')

    def _at_exit(self):
        print('unexpected-owner-exit-reentry', flush=True)
        time.sleep(30)

owner_reporter = Reporter('unexpected-owner-reporter-reentry', True)
unrelated_reporter = Reporter('unrelated-reporter-exit', False)
owner = Owner(owner_reporter)
atexit.register(owner._at_exit)
atexit.register(owner_reporter._handle_program_exit)
atexit.register(unrelated_reporter._handle_program_exit)
atexit.register(lambda: print('unrelated-exit-callback', flush=True))
detach_sdk_exit_callback(owner)
print('clean-interpreter-exit', flush=True)
"""
    result = subprocess.run(  # noqa: S603 - inert test-owned callbacks, no SDK/service initialization
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "clean-interpreter-exit" in result.stdout
    assert "unexpected-owner" not in result.stdout
    assert "unrelated-reporter-exit" in result.stdout
    assert "unrelated-exit-callback" in result.stdout


def test_owner_failure_diagnostic_precedes_console_barrier_and_finish(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    original = ValueError("original optimizer failure")
    events: list[str] = []
    logged: list[tuple[str, BaseException, dict[str, Any]]] = []

    def diagnostic(message: str, error: BaseException, **kwargs: Any) -> None:
        events.append("diagnostic")
        logged.append((message, error, kwargs))

    publisher = types.SimpleNamespace(
        barrier=lambda: events.append("barrier"), finish=lambda: events.append("finish")
    )
    monkeypatch.setattr("clearml_yolo.adapters.observability.diagnostics.log_exception", diagnostic)
    monkeypatch.setattr(session, "_start_console_publisher", lambda *_args: publisher)
    with (
        pytest.raises(ValueError, match="original optimizer failure") as raised,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert raised.value is original
    assert events == ["diagnostic", "barrier", "finish"]
    assert logged == [
        ("Invocation failed", original, {"level": "ERROR", "context": {"task": task.name}})
    ]


@pytest.mark.parametrize("diagnostic_error", [RuntimeError("broken sink"), KeyboardInterrupt()])
def test_owner_failure_diagnostic_error_preserves_original_and_terminal_cleanup(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    diagnostic_error: BaseException,
) -> None:
    _, task, _ = isolated_owner_session
    original = ValueError("original optimizer failure")

    def diagnostic(*_args: Any, **_kwargs: Any) -> None:
        raise diagnostic_error

    monkeypatch.setattr("clearml_yolo.adapters.observability.diagnostics.log_exception", diagnostic)
    with (
        pytest.raises(ValueError, match="original optimizer failure") as raised,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert raised.value is original
    assert task.closed
    assert task.failed


@pytest.mark.parametrize("failure_site", ["barrier", "finalization", "finish"])
def test_secondary_diagnostic_sink_failure_preserves_original_and_cleanup(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    failure_site: str,
) -> None:
    from loguru import logger

    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    original = ValueError("original computation failure")
    events: list[str] = []
    diagnostics: list[str] = []
    expected_message = {
        "barrier": "Console publication barrier failed",
        "finalization": "ClearML failure finalization failed",
        "finish": "Console publication failed",
    }[failure_site]

    def barrier() -> None:
        events.append("barrier")
        if failure_site == "barrier":
            raise ConsolePublicationError("secondary barrier failure")

    def finish() -> None:
        events.append("finish")
        if failure_site == "finish":
            raise ConsolePublicationError("secondary finish failure")

    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("secondary SDK failure")

    def broken_sink(message: Any) -> None:
        if expected_message in message.record["message"]:
            diagnostics.append(message.record["message"])
            raise RuntimeError("broken diagnostic sink")

    if failure_site == "finalization":
        monkeypatch.setattr(task, "close", fail)
    publisher = types.SimpleNamespace(barrier=barrier, finish=finish)
    monkeypatch.setattr(session, "_start_console_publisher", lambda *_args: publisher)
    previous_signal = signal.getsignal(signal.SIGTERM)
    previous_environment = os.environ.get(session.OWNER_PID_ENV)
    sink = logger.add(broken_sink, catch=False, format="{message}")
    try:
        with (
            pytest.raises(ValueError, match="original computation failure") as raised,
            invocation(ClearMLConfig(), "train"),
        ):
            raise original
    finally:
        logger.remove(sink)
    assert raised.value is original
    assert diagnostics
    assert events == ["barrier", "finish"]
    assert signal.getsignal(signal.SIGTERM) == previous_signal
    assert os.environ.get(session.OWNER_PID_ENV) == previous_environment
    assert session._ACTIVE_INVOCATION.get() is None
    assert bool(task.failed) is (failure_site != "finalization")
    assert task.closed is (failure_site == "finish")


def test_status_diagnostic_sink_failure_preserves_publication_error(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from loguru import logger

    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    original = ConsolePublicationError("required final delivery failed")
    diagnostics: list[str] = []

    def finish() -> None:
        raise original

    def fail(**_kwargs: Any) -> None:
        raise RuntimeError("secondary SDK status failure")

    def broken_sink(message: Any) -> None:
        if "ClearML publication failure status update failed" in message.record["message"]:
            diagnostics.append(message.record["message"])
            raise RuntimeError("broken diagnostic sink")

    monkeypatch.setattr(task, "mark_failed", fail)
    publisher = types.SimpleNamespace(barrier=lambda: None, finish=finish)
    monkeypatch.setattr(session, "_start_console_publisher", lambda *_args: publisher)
    sink = logger.add(broken_sink, catch=False, format="{message}")
    try:
        with pytest.raises(ConsolePublicationError) as raised, invocation(ClearMLConfig(), "train"):
            pass
    finally:
        logger.remove(sink)
    assert raised.value is original
    assert diagnostics
    assert task.closed
    assert session._ACTIVE_INVOCATION.get() is None


@pytest.mark.parametrize("handler_fails", [False, True])
def test_incomplete_owner_closes_exact_handler_after_status_with_separate_deadline(
    isolated_owner_session: tuple[type[Any], FakeTask, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    handler_fails: bool,
) -> None:
    from clearml_yolo.adapters.clearml import session

    _, task, _ = isolated_owner_session
    events: list[str] = []
    original = ConsolePublicationError("required delivery failed")

    class Handler:
        def close(self, *, wait: bool) -> None:
            assert wait is False
            assert task.failed
            events.append("handler")
            if handler_fails:
                raise RuntimeError("owner handler cleanup failed")
            # Installed BackgroundMonitor.stop can swallow the alarm interrupt at join.
            with suppress(BaseException):
                time.sleep(0.2)

    def finish() -> None:
        # Publication receives a new alarm after handler close consumed its own.
        assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
        events.append("finish")

    task._logger = types.SimpleNamespace(_task_handler=Handler())
    publisher = types.SimpleNamespace(barrier=lambda: None, finish=finish)
    monkeypatch.setattr(session, "_start_console_publisher", lambda *_args: publisher)
    monkeypatch.setattr(session, "FINALIZATION_TIMEOUT_SECONDS", 0.02)
    with (
        pytest.raises(ConsolePublicationError, match="required delivery failed") as raised,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert raised.value is original
    assert events == ["handler", "finish"]
    _assert_later_owner_is_blocked(isolated_owner_session)


def test_incomplete_owner_handler_join_cannot_reenter_during_logging_shutdown(
    tmp_path: Path,
) -> None:
    code = """
import logging
import sys
import threading
import types
from clearml_yolo.adapters.clearml import session
from clearml_yolo.adapters.clearml.console import ConsolePublicationError

class Handler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.background = threading.Thread(target=lambda: threading.Event().wait(30), daemon=True)
        self.background.start()

    def close(self, wait=False):
        background = self.background
        self.background = None
        if background is not None:
            try:
                background.join()
            except BaseException:
                pass

handler = Handler()
class Task:
    id = 'owned-task'
    _dev_worker = None
    _logger = types.SimpleNamespace(_task_handler=handler)
    failed = False

    @classmethod
    def init(cls, **kwargs):
        return task

    def get_output_log_web_page(self):
        return 'https://example.invalid/task'

    def mark_failed(self, **kwargs):
        self.failed = True

task = Task()
sdk = types.ModuleType('clearml')
sdk.Task = Task
sdk.Logger = types.SimpleNamespace(report_text=lambda *args, **kwargs: None)
sys.modules['clearml'] = sdk
session.active_capture = lambda: object()
session._start_console_publisher = lambda *args: None
session.publish_script = lambda *args: None
session.FINALIZATION_TIMEOUT_SECONDS = 0.02
original = ConsolePublicationError('required delivery failed')
try:
    with session.invocation(session.ClearMLConfig(), 'train'):
        raise original
except ConsolePublicationError as error:
    assert error is original
assert task.failed
assert handler.background is None
assert session._INCOMPLETE_OWNER.pid is not None
print('bounded-owner-exit', flush=True)
"""
    result = subprocess.run(  # noqa: S603 - inert fake SDK and test-owned logging thread
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "bounded-owner-exit" in result.stdout
