"""The ClearML identity of a run: where a tagged run's experiments go."""

from __future__ import annotations

import os
import signal
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd
import pytest

from clearml_yolo.clearml_session import (
    ARTIFACT_MANIFEST,
    DEFAULT_PROJECT_NAME,
    RUN_TAG_ENV_VARS,
    ArtifactUploadError,
    ClearMLConfig,
    connect_config_file,
    expect_artifacts,
    init_task,
    invocation,
    run_tag,
    tagged_project_name,
    upload_artifact,
    upload_dataframe,
)

TAG = "clearml-yolo-claude-20260905-deadline-a1b2"


def test_a_run_without_a_tag_keeps_the_default_project() -> None:
    config = ClearMLConfig()

    assert run_tag() is None
    assert config.project_name == DEFAULT_PROJECT_NAME
    assert config.tags == []


@pytest.mark.parametrize("variable", RUN_TAG_ENV_VARS)
def test_a_tagged_run_lands_in_the_tags_project_and_carries_the_tag(
    monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    """An agent's experiments belong in a project named after its tag, where the janitor
    finds them, and never among the user's own runs under the default name."""
    monkeypatch.setenv(variable, TAG)

    config = ClearMLConfig()

    assert config.project_name == tagged_project_name(TAG) == f"{TAG} {DEFAULT_PROJECT_NAME}"
    assert config.tags == [TAG]


def test_a_project_named_outright_is_kept_and_still_tagged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Naming the project is the override; the tag goes on regardless so the run is
    findable by tag wherever it landed."""
    monkeypatch.setenv("CY_RUN_TAG", TAG)

    config = ClearMLConfig(project_name="detection", tags=["prod"])

    assert config.project_name == "detection"
    assert config.tags == ["prod", TAG]


def test_the_projects_own_spelling_of_the_tag_wins_over_the_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INFRA_RUN_TAG", "clearml-yolo-ci-20260905-other-ffff")
    monkeypatch.setenv("CY_RUN_TAG", TAG)

    assert run_tag() == TAG
    assert ClearMLConfig().project_name == tagged_project_name(TAG)


def test_a_blank_tag_is_no_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CY_RUN_TAG", "  ")
    monkeypatch.setenv("INFRA_RUN_TAG", "")

    assert run_tag() is None
    assert ClearMLConfig().project_name == DEFAULT_PROJECT_NAME


def test_a_tag_already_on_the_run_is_not_added_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CY_RUN_TAG", TAG)

    assert ClearMLConfig(tags=[TAG]).tags == [TAG]


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
        self.closed = False

    def upload_artifact(self, **kwargs: Any) -> bool:
        self.uploads.append(kwargs)
        return self.upload_result

    def connect_configuration(self, **kwargs: Any) -> Any:
        self.configurations.append(kwargs)
        if kwargs.get("ignore_remote_overrides"):
            return kwargs["configuration"]
        return self.configuration_result or kwargs["configuration"]

    def flush(self, *, wait_for_uploads: bool) -> bool:
        assert wait_for_uploads is True
        return self.flush_result

    def running_locally(self) -> bool:
        return True

    def close(self) -> None:
        self.events.append("close")
        self.closed = True

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
    manifest_call = task.uploads[-1]
    assert manifest_call["name"] == ARTIFACT_MANIFEST
    assert manifest_call["wait_on_upload"] is True
    assert manifest_call["artifact_object"]["stages"] == ["pipeline", "train"]
    assert manifest_call["artifact_object"]["artifacts"] == [
        {
            "stage": "pipeline",
            "name": "resolved_configuration",
            "local_path": None,
            "required": True,
            "uploaded": True,
        },
        {
            "stage": "train",
            "name": "train_best",
            "local_path": None,
            "required": True,
            "uploaded": True,
        },
    ]


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
    assert task.events[-2:] == ["failed", "close"]


def test_upload_fulfils_a_predeclared_stage_artifact(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml

    with invocation(ClearMLConfig(), "pipeline") as owner:
        with invocation(ClearMLConfig(), "metrics"):
            expect_artifacts(owner, ["metrics_table"])
        upload_artifact(owner, "metrics_table", {"value": 1})

    manifest = task.uploads[-1]["artifact_object"]
    assert manifest["artifacts"] == [
        {
            "stage": "metrics",
            "name": "metrics_table",
            "local_path": None,
            "required": True,
            "uploaded": True,
        }
    ]


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

    stored = task.configurations[0]["configuration"]
    assert stored == {
        "clearml": {"access_key": "<redacted>", "secret_key": "<redacted>"},
        "endpoint": ("https://<redacted>@example.test/path?token=%3Credacted%3E&safe=yes&empty="),
        "nested": [{"password": "<redacted>", "epochs": 3}],
    }
    resolved_upload = task.uploads[0]
    assert resolved_upload["name"] == "resolved_configuration"
    assert resolved_upload["artifact_object"] == stored


def test_source_yaml_is_sanitized_in_configuration_and_downloadable_artifact(
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
        expect_artifacts(owner, ["dataset_configuration"])
        stored = connect_config_file(owner, "dataset_configuration", source)
        assert stored == source
        stored_text = task.configurations[-1]["configuration"].read_text(encoding="utf-8")
        artifact_path = task.uploads[0]["artifact_object"]
        artifact_text = artifact_path.read_text(encoding="utf-8")

    assert "hidden" not in stored_text
    assert "pass" not in stored_text
    assert "abc" not in stored_text
    assert "<redacted>" in stored_text
    assert "/datasets/cats" in stored_text
    assert "auth: <redacted>" in stored_text
    assert artifact_text == stored_text
    assert task.configurations[-1]["configuration"] == artifact_path
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
        uploaded_text = task.uploads[0]["artifact_object"].read_text(encoding="utf-8")

    assert "epochs: 2" in effective_text
    assert effective == override
    assert "remote-secret" in effective_text
    assert "remote-secret" not in uploaded_text
    assert "epochs: 2" in uploaded_text
    assert task.configurations[-1]["ignore_remote_overrides"] is True


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
    assert task.events[-2:] == ["failed", "close"]


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
        stored_text = task.uploads[0]["artifact_object"].read_text(encoding="utf-8")

    assert stored_text == (
        '{\n  "model": "yolo11n.pt",\n  "api_token": "<redacted>",\n  "epochs": 3\n}\n'
    )
    assert task.uploads[0]["artifact_object"].suffix == ".json"


def test_upload_dataframe_uses_the_required_synchronous_path(
    fake_clearml: tuple[type[Any], FakeTask],
) -> None:
    _, task = fake_clearml
    frame = pd.DataFrame({"value": [1]})

    with invocation(ClearMLConfig(), "metrics") as owner:
        upload_dataframe(owner, "metrics_table", frame)

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
    from clearml_yolo.clearml_session import sanitize_configuration

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
