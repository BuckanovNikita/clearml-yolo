"""TRACE spans retain owner identity through terminal status and local cleanup."""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from loguru import logger

from clearml_yolo.adapters.clearml.session import (
    ArtifactUploadError,
    ClearMLConfig,
    connect_config_file,
    invocation,
    register_finalizer,
    register_model_barrier,
    upload_artifact,
)
from test_clearml_session import FakeTask
from test_clearml_session import fake_clearml as fake_clearml  # noqa: PLC0414


@pytest.fixture
def trace_messages(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(message.record["message"]), level="TRACE")
    try:
        yield messages
    finally:
        logger.remove(sink)


def test_owner_identity_survives_finalizers_and_cleanup(
    fake_clearml: tuple[type[Any], FakeTask], trace_messages: list[str]
) -> None:
    _, task = fake_clearml
    with invocation(ClearMLConfig(), "pipeline"):
        register_finalizer(task, lambda: upload_artifact(task, "final-table", {"value": 1}))
        register_model_barrier(task, lambda: None)
    starts = [message for message in trace_messages if message.startswith("START ")]
    operations = [message.split()[1] for message in starts]
    assert operations == [
        "clearml.task.create",
        "clearml.publication.finalizer",
        "clearml.artifact.upload",
        "clearml.model.wait_uploads",
        "clearml.task.flush",
        "clearml.task.reload",
        "clearml.model.verify",
        "clearml.task.terminal",
        "clearml.task.close",
        "clearml.task.readback",
        "clearml.task.mark_completed",
        "clearml.temporary.cleanup",
    ]
    assert "task=- " in starts[0]
    assert all("task=task-id " in message for message in starts[1:])
    assert "artifact=final-table" in starts[2]
    assert task.events == ["close", "completed"]


def test_finalizer_failure_traces_failed_terminal_path_without_exception_text(
    fake_clearml: tuple[type[Any], FakeTask], trace_messages: list[str]
) -> None:
    _, task = fake_clearml
    original = ValueError("token=private-finalizer-token")

    def fail() -> None:
        raise original

    with (
        pytest.raises(ValueError, match="private-finalizer-token") as caught,
        invocation(ClearMLConfig(), "pipeline"),
    ):
        register_finalizer(task, fail)
    assert caught.value is original
    assert any(
        message.startswith("FAILED clearml.publication.finalizer ") for message in trace_messages
    )
    assert any(message.startswith("DONE clearml.task.mark_failed ") for message in trace_messages)
    assert any(
        message.startswith("DONE clearml.temporary.cleanup ") and "task=task-id " in message
        for message in trace_messages
    )
    assert all("private-finalizer-token" not in message for message in trace_messages)
    assert task.events == ["close", "failed"]


def test_flush_rejection_is_failed_span_and_preserves_error(
    fake_clearml: tuple[type[Any], FakeTask], trace_messages: list[str]
) -> None:
    _, task = fake_clearml
    task.flush_result = False
    with pytest.raises(ArtifactUploadError, match="flush"), invocation(ClearMLConfig(), "validate"):
        pass
    assert any(message.startswith("FAILED clearml.task.flush ") for message in trace_messages)
    assert task.events == ["close", "failed"]


def test_successful_invocation_is_silent_without_trace_opt_in(
    fake_clearml: tuple[type[Any], FakeTask],
    trace_messages: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "DEBUG")
    with invocation(ClearMLConfig(), "pipeline"):
        pass
    assert not any("clearml.task." in message for message in trace_messages)


def test_close_failure_preserves_primary_error_and_traces_cleanup(
    fake_clearml: tuple[type[Any], FakeTask],
    trace_messages: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task = fake_clearml
    original = KeyboardInterrupt()

    def fail() -> None:
        raise OSError("token=private-close-token")

    monkeypatch.setattr(task, "close", fail)
    with pytest.raises(KeyboardInterrupt) as caught, invocation(ClearMLConfig(), "pipeline"):
        raise original
    assert caught.value is original
    assert any(message.startswith("FAILED clearml.task.close ") for message in trace_messages)
    assert any(message.startswith("DONE clearml.temporary.cleanup ") for message in trace_messages)
    assert all("private-close-token" not in message for message in trace_messages)


def test_rejected_upload_is_failed_span_and_fails_owner(
    fake_clearml: tuple[type[Any], FakeTask], trace_messages: list[str]
) -> None:
    _, task = fake_clearml
    task.upload_result = False
    with (
        pytest.raises(ArtifactUploadError, match="rejected required artifact"),
        invocation(ClearMLConfig(), "predict"),
    ):
        upload_artifact(task, "predictions", {"value": 1})
    assert any(message.startswith("FAILED clearml.artifact.upload ") for message in trace_messages)
    assert task.events == ["close", "failed"]


def test_task_creation_failure_is_visible_before_owner_identity_exists(
    fake_clearml: tuple[type[Any], FakeTask], trace_messages: list[str]
) -> None:
    sdk, task = fake_clearml
    original = ConnectionError("creation unavailable")

    def fail() -> None:
        raise original

    sdk.on_init = fail
    with (
        pytest.raises(ConnectionError, match="creation unavailable") as caught,
        invocation(ClearMLConfig(), "pipeline"),
    ):
        pytest.fail("Task creation must fail before invocation body")
    assert caught.value is original
    assert any(
        message.startswith("FAILED clearml.task.create ") and "task=- " in message
        for message in trace_messages
    )
    assert task.events == []


@pytest.fixture
def interrupt_sink() -> Iterator[Callable[[str, BaseException], None]]:
    sinks: list[int] = []

    def install(prefix: str, error: BaseException) -> None:
        def emit(message: Any) -> None:
            if message.record["message"].startswith(prefix):
                raise error

        sinks.append(logger.add(emit, level="TRACE", catch=False))

    try:
        yield install
    finally:
        for sink in sinks:
            logger.remove(sink)


def test_creation_terminal_sink_interrupt_closes_and_fails_created_task(
    fake_clearml: tuple[type[Any], FakeTask],
    trace_messages: list[str],
    interrupt_sink: Callable[[str, BaseException], None],
) -> None:
    _, task = fake_clearml
    original = KeyboardInterrupt()
    interrupt_sink("DONE clearml.task.create ", original)
    with pytest.raises(KeyboardInterrupt) as caught, invocation(ClearMLConfig(), "pipeline"):
        pytest.fail("Creation terminal interruption must precede invocation body")
    assert caught.value is original
    assert task.closed
    assert task.events == ["close", "failed"]
    assert any(message.startswith("DONE clearml.temporary.cleanup ") for message in trace_messages)


def test_failure_close_sink_exit_preserves_primary_error_and_marks_failed(
    fake_clearml: tuple[type[Any], FakeTask],
    trace_messages: list[str],
    interrupt_sink: Callable[[str, BaseException], None],
) -> None:
    _, task = fake_clearml
    original = LookupError("original body failure")
    interrupt_sink("DONE clearml.task.close ", SystemExit(19))
    with (
        pytest.raises(LookupError, match="original body failure") as caught,
        invocation(ClearMLConfig(), "pipeline"),
    ):
        raise original
    assert caught.value is original
    assert task.events == ["close", "failed"]
    assert any(message.startswith("DONE clearml.temporary.cleanup ") for message in trace_messages)


def test_cleanup_start_sink_exit_still_removes_owned_configuration(
    fake_clearml: tuple[type[Any], FakeTask],
    trace_messages: list[str],
    interrupt_sink: Callable[[str, BaseException], None],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "home"))
    _, task = fake_clearml
    source = tmp_path / "config.yaml"
    source.write_text("name: original\n", encoding="utf-8")
    original = SystemExit(23)
    interrupt_sink("START clearml.temporary.cleanup ", original)

    def attach() -> Path:
        assert connect_config_file(task, "dataset", source) == source
        owned = Path(task.configurations[0]["configuration"])
        assert owned.is_file()
        assert owned != source
        return owned

    with pytest.raises(SystemExit) as caught, invocation(ClearMLConfig(), "pipeline"):
        owned = attach()
    assert caught.value is original
    assert not owned.exists()
    assert source.is_file()
    assert task.events == ["close", "completed"]
