"""Observable TRACE lifecycle, privacy and watchdog contracts."""

import threading
import time
from collections.abc import Iterator
from typing import override

import pytest
from loguru import logger

from clearml_yolo.adapters.observability import tracing


@pytest.fixture
def events(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    output: list[str] = []
    sink = logger.add(
        lambda message: output.append(str(message)), level="TRACE", format="{message}"
    )
    try:
        yield output
    finally:
        logger.remove(sink)


def test_nested_operations_correlate_and_preserve_exception(events: list[str]) -> None:
    error = ValueError("password=do-not-log")
    with (
        pytest.raises(ValueError, match="password") as caught,
        tracing.trace_operation("stage"),
        tracing.trace_task("task-123"),
        tracing.trace_operation("upload"),
    ):
        raise error
    assert caught.value is error
    assert len(events) == 4
    assert "START stage" in events[0]
    assert "START upload" in events[1]
    assert "task=task-123" in events[1]
    assert "FAILED upload" in events[2]
    assert "FAILED stage" in events[3]
    assert "elapsed=" in events[3]
    assert "do-not-log" not in "".join(events)
    assert tracing._state.active == {}
    assert tracing._state.monitor is None


def test_disabled_trace_is_inert(monkeypatch: pytest.MonkeyPatch, events: list[str]) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "DEBUG")
    with tracing.trace_operation("inactive"):
        assert tracing._state.monitor is None
    assert events == []


def test_context_does_not_render_opaque_objects(events: list[str]) -> None:
    class Opaque:
        @override
        def __str__(self) -> str:
            raise AssertionError("must not stringify")

    with tracing.trace_operation(
        "safe",
        context={
            "destination": "https://user:secret@example.test/upload?token=private",
            "rows": 42,
            "config": Opaque(),
            "password": "hide-me",
        },
    ):
        pass
    text = "".join(events)
    assert "rows=42" in text
    assert "secret" not in text
    assert "private" not in text
    assert "hide-me" not in text


def test_interruption_and_command_return_after_cleanup(events: list[str]) -> None:
    @tracing.trace_command("example")
    def command() -> None:
        with tracing.trace_operation("cleanup"):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        command()
    assert "INTERRUPTED cleanup" in events[-3]
    assert "INTERRUPTED command.example" in events[-2]
    assert "command.return" in events[-1]


def test_successful_system_exit_is_not_an_interruption(events: list[str]) -> None:
    with pytest.raises(SystemExit) as caught, tracing.trace_operation("help"):
        raise SystemExit(0)
    assert caught.value.code == 0
    assert "DONE help" in events[-1]


def test_watchdog_deepest_operation_and_stack_suppression(
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
) -> None:
    output: list[str] = []
    monkeypatch.setattr(tracing, "HEARTBEAT_SECONDS", 0.02)
    monkeypatch.setattr(tracing, "STACK_SECONDS", 0.04)
    monkeypatch.setattr(tracing, "_write_watchdog", lambda state, text: output.append(text))
    with tracing.trace_operation("stage"), tracing.trace_operation("blocked"):
        threading.Event().wait(0.16)
    text = "".join(output)
    assert "ACTIVE blocked" in text
    assert "stage=stage" in text
    assert "STACK" in text
    assert "test_watchdog_deepest_operation" in text
    assert text.count("STACK snapshot") >= 1


def test_changed_snapshots_emit_once_per_change(
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
) -> None:
    output: list[str] = []
    sampled = threading.Event()
    snapshots = iter(
        [((("first:1 in wait",), (101,), False),)] * 2
        + [((("second:2 in wait",), (101,), False),)] * 2
    )
    count = 0

    def sample(*args: object) -> tuple[tuple[tuple[str, ...], tuple[int, ...], bool], ...]:
        nonlocal count
        count += 1
        result = next(snapshots)
        if count == 4:
            tracing._state.stop.set()
            sampled.set()
        return result

    monkeypatch.setattr(tracing, "STACK_SECONDS", 0.01)
    monkeypatch.setattr(tracing, "_stack_snapshot", sample)
    monkeypatch.setattr(tracing, "_write_watchdog", lambda state, text: output.append(text))
    with tracing.trace_operation("changing"):
        assert sampled.wait(2)
    text = "".join(output)
    assert text.count("STACK snapshot") == 2
    assert text.count("first:1 in wait") == 1
    assert text.count("second:2 in wait") == 1


def test_production_intervals() -> None:
    assert tracing.HEARTBEAT_SECONDS == 30
    assert tracing.STACK_SECONDS == 60


def test_sink_failure_cannot_replace_application_failure(events: list[str]) -> None:
    def broken(message: object) -> None:
        raise RuntimeError("diagnostic sink")

    sink = logger.add(broken, level="TRACE", catch=False)
    original = LookupError("original")
    try:
        with pytest.raises(LookupError) as caught, tracing.trace_operation("failure"):
            raise original
        assert caught.value is original
    finally:
        logger.remove(sink)


@pytest.mark.parametrize("sink_error", [SystemExit(23), KeyboardInterrupt()])
@pytest.mark.parametrize(
    "original", [LookupError("original"), KeyboardInterrupt(), SystemExit(7), SystemExit(0)]
)
def test_sink_base_exception_preserves_application_exception(
    events: list[str], sink_error: BaseException, original: BaseException,
) -> None:
    def broken(message: object) -> None:
        if "START" not in str(message):
            raise sink_error

    @tracing.trace_command("failure")
    def command() -> None:
        with tracing.trace_operation("failure"):
            raise original

    sink = logger.add(broken, level="TRACE", catch=False)
    try:
        with pytest.raises(type(original)) as caught:
            command()
        assert caught.value is original
    finally:
        logger.remove(sink)


def test_sink_failure_preserves_command_result(events: list[str]) -> None:
    def broken(message: object) -> None:
        raise RuntimeError("sink failed")

    @tracing.trace_command("success")
    def command() -> int:
        return 42

    sink = logger.add(broken, level="TRACE", catch=False)
    try:
        assert command() == 42
        assert tracing._state.active == {}
        assert tracing._state.monitor is None
    finally:
        logger.remove(sink)


@pytest.mark.parametrize("event", ["START cleanup", "DONE cleanup", "START nested"])
def test_cleanup_runs_before_sink_interruption_propagates(events: list[str], event: str) -> None:
    cleaned: list[str] = []
    original = KeyboardInterrupt()

    def interrupt(message: object) -> None:
        if event in str(message):
            raise original

    def clean() -> None:
        with tracing.trace_operation("cleanup", cleanup=True):
            with tracing.trace_operation("nested", cleanup=True):
                cleaned.append("nested")
            cleaned.append("outer")

    sink = logger.add(interrupt, level="TRACE", catch=False)
    try:
        with pytest.raises(KeyboardInterrupt) as failure:
            clean()
        assert failure.value is original
        assert cleaned == ["nested", "outer"]
        assert tracing._state.active == {}
        assert tracing._cleanup_interruptions.get() is None
    finally:
        logger.remove(sink)


def test_nested_finalization_logging_preserves_active_exception(events: list[str]) -> None:
    original = LookupError("application")
    finalized: list[str] = []

    def interrupt(message: object) -> None:
        if "finalization" in str(message):
            raise SystemExit(23)

    def run() -> None:
        try:
            raise original
        finally:
            with tracing.trace_operation("finalization"):
                finalized.append("closed")

    sink = logger.add(interrupt, level="TRACE", catch=False)
    try:
        with pytest.raises(LookupError) as failure:
            run()
        assert failure.value is original
        assert finalized == ["closed"]
    finally:
        logger.remove(sink)


def test_task_bindings_are_independent_between_threads(events: list[str]) -> None:
    entered = threading.Event()
    finish = threading.Event()

    def worker() -> None:
        with tracing.trace_task("worker-task"), tracing.trace_operation("worker"):
            entered.set()
            assert finish.wait(2)

    with tracing.trace_task("parent-task"):
        thread = threading.Thread(target=worker)
        thread.start()
        try:
            assert entered.wait(2)
            with tracing.trace_operation("parent"):
                pass
        finally:
            finish.set()
            thread.join(2)
    assert any("START parent" in item and "task=parent-task" in item for item in events)
    assert any("START worker" in item and "task=worker-task" in item for item in events)


def test_sequential_invocations_leave_no_monitor(events: list[str]) -> None:
    before = {thread.ident for thread in threading.enumerate()}
    for _ in range(3):
        with tracing.trace_operation("short"):
            time.sleep(0.001)
    assert {thread.ident for thread in threading.enumerate()} == before


def test_monitor_start_failure_does_not_leak_state(
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
) -> None:
    def unavailable(self: threading.Thread) -> None:
        raise RuntimeError("no threads available")

    monkeypatch.setattr(threading.Thread, "start", unavailable)
    with tracing.trace_operation("still_runs"):
        pass
    assert tracing._state.active == {}
    assert tracing._state.monitor is None
    assert tracing._state.fd is None


def test_stack_frames_and_groups_are_bounded() -> None:
    import sys

    def recurse(depth: int) -> tuple[tuple[str, ...], bool]:
        if depth:
            return recurse(depth - 1)
        return tracing._frames(sys._getframe())

    frames, truncated = recurse(25)
    assert len(frames) == 12
    assert truncated is True
    snapshot = tuple((frames, (index,), truncated) for index in range(10))
    text = tracing._render_snapshot(snapshot)
    assert text.count("threads=") == 8
    assert "groups truncated: omitted=2" in text
    assert text.count("frames truncated at 12") == 8


def test_unchanged_stacks_group_threads_and_prioritize_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    frame = sys._getframe()
    monkeypatch.setattr(sys, "_current_frames", lambda: {101: frame, 102: frame, 103: frame})
    snapshot = tracing._stack_snapshot({102: ()}, 103)
    assert len(snapshot) == 1
    assert snapshot[0][1] == (102, 101)
