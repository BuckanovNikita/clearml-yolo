"""Watchdog isolation against logging/SDK stalls and fresh-process command checks."""

import os
import subprocess
import sys
import textwrap

import pytest


def _run(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - isolated current-interpreter test source
        [sys.executable, "-c", textwrap.dedent(source)],
        env=os.environ | {"LOGURU_LEVEL": "TRACE"},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_watchdog_bypasses_intercepted_stderr_and_blocked_loguru_sink() -> None:
    result = _run("""
        import io
        import sys
        import threading
        from loguru import logger
        from clearml_yolo.adapters.observability import tracing
        tracing.HEARTBEAT_SECONDS = 0.02
        tracing.STACK_SECONDS = 0.04
        logger.remove()
        intercepted = io.StringIO()
        with tracing.trace_operation("command"):
            sys.stderr = intercepted
            def blocked(message):
                threading.Event().wait(0.12)
            logger.add(blocked, level="TRACE")
            with tracing.trace_operation("sdk.close"):
                pass
        assert "TRACE ACTIVE" not in intercepted.getvalue()
        assert tracing._state.monitor is None
    """)
    assert result.returncode == 0, result.stderr
    assert "TRACE ACTIVE sdk.close" in result.stderr
    assert "in blocked" in result.stderr


@pytest.mark.parametrize("event", ["START command.signal", "DONE command.signal", "command.return"])
@pytest.mark.parametrize("signal_name", ["SIGINT", "SIGTERM"])
def test_real_signal_during_sink_emission_still_interrupts(event: str, signal_name: str) -> None:
    result = _run(f"""
        import os
        import signal
        from loguru import logger
        from clearml_yolo.adapters.observability import tracing
        from clearml_yolo.adapters.clearml.session import _exit_on_signal
        signal.signal(signal.SIGTERM, _exit_on_signal)
        before = signal.getsignal(signal.SIGTERM)
        entered = []
        def interrupt(message):
            if {event!r} in str(message):
                os.kill(os.getpid(), signal.{signal_name})
        sink = logger.add(interrupt, level="TRACE", catch=False)
        @tracing.trace_command("signal")
        def command():
            entered.append(True)
        try:
            command()
        except (KeyboardInterrupt, SystemExit):
            pass
        else:
            raise AssertionError("real signal swallowed by diagnostics")
        finally:
            logger.remove(sink)
        assert bool(entered) == {event != 'START command.signal'!r}
        assert signal.getsignal(signal.SIGTERM) is before
        assert tracing._state.active == {{}}
        assert tracing._state.monitor is None
    """)
    assert result.returncode == 0, result.stderr


def test_watchdog_covers_actual_invocation_closure_and_command_return() -> None:
    result = _run("""
        import sys
        import threading
        import types
        from unittest.mock import Mock
        from clearml_yolo.adapters.observability import tracing
        from clearml_yolo.adapters.clearml.session import invocation, ClearMLConfig
        tracing.HEARTBEAT_SECONDS = 0.02
        tracing.STACK_SECONDS = 0.04
        task = Mock(id="owned-task", name="example", artifacts={})
        task.flush.return_value = True
        task.close.side_effect = lambda: threading.Event().wait(0.14)
        sdk = types.ModuleType("clearml")
        sdk.Task = Mock()
        sdk.Task.init.return_value = task
        sdk.Task.get_task.return_value = task
        sdk.OutputModel = Mock()
        sys.modules["clearml"] = sdk
        @tracing.trace_command("closure")
        def run():
            with invocation(ClearMLConfig(), "test"):
                pass
        run()
        assert tracing._state.monitor is None
        assert tracing._state.active == {}
    """)
    assert result.returncode == 0, result.stderr
    assert "ACTIVE clearml.task.close" in result.stderr
    assert "task=owned-task" in result.stderr
    assert result.stderr.index("clearml.temporary.cleanup") < result.stderr.index("command.return")


def test_fork_resets_parent_operations_and_monitor() -> None:
    result = _run("""
        import os
        from clearml_yolo.adapters.observability import tracing
        with tracing.trace_task("parent-task"), tracing.trace_operation("parent", cleanup=True):
            pid = os.fork()
            if pid == 0:
                assert tracing._deferred_interruptions() is None
                with tracing.trace_operation("child"):
                    assert len(tracing._state.active) == 1
                    assert tracing._state.sequence == 1
                assert tracing._state.monitor is None
                with tracing.trace_task("child-task"), tracing.trace_operation("child.bound"):
                    pass
                os._exit(0)
            _, status = os.waitpid(pid, 0)
            assert status == 0
        assert tracing._state.monitor is None
    """)
    assert result.returncode == 0, result.stderr
    assert "START child op=1 parent=-" in result.stderr
    child = next(line for line in result.stderr.splitlines() if "START child op=" in line)
    assert "task=- " in child
    bound = next(line for line in result.stderr.splitlines() if "START child.bound " in line)
    assert "task=child-task " in bound


def test_import_and_sequential_commands_leave_threads_and_descriptors_unchanged() -> None:
    result = _run("""
        import threading
        from pathlib import Path
        # Establish dependency-owned resources (Loguru/Pydantic may open urandom).
        import loguru
        import clearml_yolo.core.redaction
        before_threads = {thread.ident for thread in threading.enumerate()}
        before_fds = len(list(Path("/proc/self/fd").iterdir()))
        from clearml_yolo.adapters.observability import tracing
        assert {thread.ident for thread in threading.enumerate()} == before_threads
        assert len(list(Path("/proc/self/fd").iterdir())) == before_fds
        for _ in range(20):
            with tracing.trace_operation("sequential"):
                pass
        assert {thread.ident for thread in threading.enumerate()} == before_threads
        assert len(list(Path("/proc/self/fd").iterdir())) == before_fds
    """)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "module",
    [
        "pipeline",
        "train",
        "predict",
        "metrics",
        "report",
        "compare",
        "ground_truth",
        "val",
        "config_tree",
        "dedup",
    ],
)
def test_all_command_helps_have_trace_lifecycle_without_native_imports(module: str) -> None:
    result = _run(f"""
        import runpy
        import sys
        sys.argv = ["command", "--help"]
        try:
            runpy.run_module("clearml_yolo.entrypoints.{module}", run_name="__main__")
        except SystemExit as error:
            assert not error.code
        assert "torch" not in sys.modules
        assert "clearml" not in sys.modules
        assert "ultralytics" not in sys.modules
        assert "fiftyone" not in sys.modules
    """)
    assert result.returncode == 0, result.stderr
    assert "START command." in result.stderr
    assert "command.return" in result.stderr
