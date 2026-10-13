"""Owner-thread deadlines cannot complete task state later in a detached thread."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from test_clearml_session import FakeTask
from test_clearml_session import fake_clearml as fake_clearml  # noqa: PLC0414


def test_sdk_deadline_interrupts_blocked_owner_and_restores_alarm() -> None:
    from clearml_yolo.adapters.clearml.deadline import TaskFinalizationError, sdk_deadline

    original = signal.getsignal(signal.SIGALRM)
    began = time.monotonic()
    with pytest.raises(TaskFinalizationError, match="deadline"), sdk_deadline(0.05):
        time.sleep(10)
    assert time.monotonic() - began < 1
    assert signal.getsignal(signal.SIGALRM) is original
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)


def test_sdk_deadline_rejects_existing_alarm_without_changing_it() -> None:
    from clearml_yolo.adapters.clearml.deadline import TaskFinalizationError, sdk_deadline

    signal.setitimer(signal.ITIMER_REAL, 30)
    try:
        with pytest.raises(TaskFinalizationError, match="existing"), sdk_deadline(0.05):
            raise AssertionError("Must fail before entering SDK")
        assert signal.getitimer(signal.ITIMER_REAL)[0] > 25
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def test_blocked_failure_finalization_preserves_original_exception(
    fake_clearml: tuple[type[object], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation

    _, task = fake_clearml
    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.FINALIZATION_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(task, "close", lambda: time.sleep(10))
    detached: list[object] = []

    def callback() -> None:
        pass

    monkeypatch.setattr(task, "_at_exit", callback, raising=False)
    monkeypatch.setattr("clearml_yolo.adapters.clearml.deadline.atexit.unregister", detached.append)
    original = ValueError("training failed")
    began = time.monotonic()
    with (
        pytest.raises(ValueError, match="training failed") as caught,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert caught.value is original
    assert time.monotonic() - began < 1
    # Nested failure boundaries may idempotently detach the same callback again.
    assert detached
    assert all(item is callback for item in detached)


def test_blocked_success_finalization_fails_without_marking_completed(
    fake_clearml: tuple[type[object], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.deadline import TaskFinalizationError
    from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation

    _, task = fake_clearml
    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.FINALIZATION_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(task, "close", lambda: time.sleep(10))
    with (
        pytest.raises(TaskFinalizationError, match="deadline"),
        invocation(ClearMLConfig(), "train"),
    ):
        pass
    assert task.completed == []


def test_publisher_drains_sdk_close_status_and_cleanup_output_before_final_receipt(
    fake_clearml: tuple[type[object], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation
    from clearml_yolo.adapters.observability.capture import OutputCapture

    _, task = fake_clearml
    captured: list[OutputCapture] = []
    acknowledged: list[dict[str, int]] = []
    close = task.close
    completed = task.mark_completed

    def close_with_output() -> None:
        os.write(1, b"native-sdk-close-output\n")
        close()

    def completed_with_output(**kwargs: Any) -> object:
        os.write(1, b"native-sdk-completed-output\n")
        return completed(**kwargs)

    class Publisher:
        def barrier(self) -> None:
            task.events.append("publisher-barrier")

        def finish(self) -> None:
            task.events.append("publisher-finish")
            acknowledged.append(captured[0].offsets())

    def start(_task: object, capture: OutputCapture) -> Publisher:
        captured.append(capture)
        return Publisher()

    monkeypatch.setattr(task, "close", close_with_output)
    monkeypatch.setattr(task, "mark_completed", completed_with_output)
    monkeypatch.setattr("clearml_yolo.adapters.clearml.session._start_console_publisher", start)
    with invocation(ClearMLConfig(), "train"):
        os.write(1, b"training-output\n")
    assert task.events == ["publisher-barrier", "close", "completed", "publisher-finish"]
    assert acknowledged == [captured[0].offsets()]


def test_required_final_publication_failure_corrects_completed_task_to_failed(
    fake_clearml: tuple[type[object], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublicationError
    from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation

    _, task = fake_clearml

    class Publisher:
        def barrier(self) -> None:
            pass

        def finish(self) -> None:
            raise ConsolePublicationError("required final drain failed")

    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.session._start_console_publisher", lambda *_args: Publisher()
    )
    with (
        pytest.raises(ConsolePublicationError, match="required final drain"),
        invocation(ClearMLConfig(), "train"),
    ):
        pass
    assert task.events == ["close", "completed", "failed"]
    assert task.failed[-1]["status_reason"] == "ConsolePublicationError"


def test_unacknowledged_workload_never_closes_or_completes_sdk_task(
    fake_clearml: tuple[type[object], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublicationError
    from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation

    _, task = fake_clearml

    class Publisher:
        def barrier(self) -> None:
            raise ConsolePublicationError("workload barrier not acknowledged")

        def finish(self) -> None:
            pass

    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.session._start_console_publisher", lambda *_args: Publisher()
    )
    with (
        pytest.raises(ConsolePublicationError, match="barrier"),
        invocation(ClearMLConfig(), "train"),
    ):
        pass
    assert task.events == ["failed"]
    assert task.completed == []


def test_failed_failure_path_barrier_preserves_original_error_without_sdk_close(
    fake_clearml: tuple[type[object], FakeTask],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml.console import ConsolePublicationError
    from clearml_yolo.adapters.clearml.session import ClearMLConfig, invocation

    _, task = fake_clearml

    class Publisher:
        def barrier(self) -> None:
            raise ConsolePublicationError("failure-path workload unacknowledged")

        def finish(self) -> None:
            pass

    monkeypatch.setattr(
        "clearml_yolo.adapters.clearml.session._start_console_publisher", lambda *_args: Publisher()
    )
    original = ValueError("original native failure")
    with (
        pytest.raises(ValueError, match="original native failure") as caught,
        invocation(ClearMLConfig(), "train"),
    ):
        raise original
    assert caught.value is original
    assert task.events == ["failed"]
    assert task.failed[-1]["status_reason"] == "ValueError"


def test_detaching_installed_sdk_callback_prevents_interpreter_exit_reentry(tmp_path: Path) -> None:
    code = """
import sys
from clearml import Task
from clearml.utilities.process.exit_hooks import ExitHooks
from clearml_yolo.adapters.clearml.deadline import detach_sdk_exit_callback
task = object.__new__(Task)
task._at_exit_called = False
task._Task__is_subprocess = lambda: False
task._Task__shutdown = lambda: print('unexpected-sdk-exit-retry')
# The installed ExitHooks registers precisely task._at_exit, as Task.init does.
hooks = ExitHooks(task._at_exit)
hooks.hook()
import atexit
atexit.register(lambda: print('unrelated-exit-callback'))
detach_sdk_exit_callback(task)
print('clean-interpreter-exit')
"""
    result = subprocess.run(  # noqa: S603 - real installed SDK hook, no task/network initialization
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "clean-interpreter-exit" in result.stdout
    assert "unexpected-sdk-exit-retry" not in result.stdout
    assert "unrelated-exit-callback" in result.stdout
