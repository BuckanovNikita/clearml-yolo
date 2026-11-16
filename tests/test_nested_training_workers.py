"""Nested training supervisors retain ownership of detached descendants."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

import pytest

from clearml_yolo.adapters.runtime.workers import WorkerCommand, run_workers

pytestmark = [
    pytest.mark.process_capabilities,
    pytest.mark.skipif(sys.platform != "linux", reason="Linux process ownership"),
]


def _wait_ready(ready: Path) -> None:
    deadline = time.monotonic() + 10
    while not ready.exists():
        if time.monotonic() >= deadline:
            pytest.fail("Nested workers did not finish starting")
        time.sleep(0.01)


def _cleanup_owned(pid_files: tuple[Path, ...], token: str) -> None:
    """Keep a failing regression from leaving its own subprocesses behind."""
    for path in reversed(pid_files):
        if not path.exists() or not path.read_text():
            continue
        pid = int(path.read_text())
        with suppress(FileNotFoundError, ProcessLookupError):
            descriptor = os.pidfd_open(pid)
            try:
                environment = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
                if f"CY_TEST_NESTED_OWNER={token}".encode() in environment:
                    signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                    with suppress(ChildProcessError):
                        os.waitid(os.P_PIDFD, descriptor, os.WEXITED)
            finally:
                os.close(descriptor)
        with suppress(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)


@pytest.mark.parametrize("stop", ["exception", "interrupt", "timeout"])
def test_nested_training_cancellation_reaps_detached_descendants(tmp_path: Path, stop: str) -> None:
    ready = tmp_path / "ready"
    pid_files = tuple(tmp_path / name for name in ("outer.pid", "inner.pid", "leaf.pid"))
    outer_pid, inner_pid, leaf_pid = pid_files
    token = uuid4().hex
    leaf = (
        "import os,signal,time\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        f"Path({str(leaf_pid)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(60)\n"
    )
    inner = (
        "import os,signal,subprocess,sys,time\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        f"Path({str(inner_pid)!r}).write_text(str(os.getpid()))\n"
        f"subprocess.Popen([sys.executable,'-c',{leaf!r}],start_new_session=True)\n"
        f"while not Path({str(leaf_pid)!r}).exists() or not Path({str(leaf_pid)!r}).read_text(): time.sleep(.01)\n"
        f"Path({str(ready)!r}).touch()\n"
        "time.sleep(60)\n"
    )
    outer = (
        "import os,sys\nfrom pathlib import Path\n"
        "from clearml_yolo.adapters.runtime.workers import WorkerCommand,run_workers\n"
        f"Path({str(outer_pid)!r}).write_text(str(os.getpid()))\n"
        f"run_workers([WorkerCommand((sys.executable,'-c',{inner!r}),{{}},"
        f"Path({str(tmp_path / 'inner.log')!r}))],timeout_seconds=45)\n"
    )
    command = WorkerCommand(
        (sys.executable, "-c", outer),
        {"CY_TEST_NESTED_OWNER": token, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        tmp_path / "outer.log",
    )
    sibling = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"])

    def cancel(_owned: Callable[[], tuple[int, ...]]) -> None:
        # The timeout cannot expire before the stubborn leaf's signal handler is installed.
        _wait_ready(ready)
        if stop == "exception":
            raise RuntimeError("Cancel native work")
        if stop == "interrupt":
            raise KeyboardInterrupt

    try:
        if stop == "timeout":
            result = run_workers([command], timeout_seconds=0.1, monitor=cancel)
            assert result.status == "timeout"
        else:
            expected = RuntimeError if stop == "exception" else KeyboardInterrupt
            with pytest.raises(expected):
                run_workers([command], timeout_seconds=15, monitor=cancel)
        assert sibling.poll() is None
        for path in pid_files:
            with pytest.raises(ProcessLookupError):
                os.kill(int(path.read_text()), 0)
    finally:
        _cleanup_owned(pid_files, token)
        sibling.terminate()
        sibling.wait(timeout=5)
