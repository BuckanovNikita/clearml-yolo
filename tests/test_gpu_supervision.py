"""Failure-safe queued child supervision."""


import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, cast, override

import pytest


class FinishedProcess:
    def __init__(self, code: int | None = 0) -> None:
        self.pid = 12345
        self.returncode: int | None = code
        self.terminated = False

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        return cast(int, self.returncode)

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -1

    def kill(self) -> None:
        self.returncode = -9


class TimeoutRaceProcess(FinishedProcess):
    def __init__(self) -> None:
        super().__init__(None)
        self.waits = 0

    @override
    def wait(self, timeout: float | None = None) -> int:
        self.waits += 1
        if self.waits == 1:
            assert timeout is not None
            raise subprocess.TimeoutExpired("worker", timeout)
        self.returncode = 0
        return 0


def test_posix_timeout_tolerates_process_exit_before_group_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import supervision as execution

    process = TimeoutRaceProcess()

    def missing_group(_pid: int) -> int:
        raise ProcessLookupError

    monkeypatch.setattr(os, "getpgid", missing_group)

    execution.cancel_process(cast(subprocess.Popen[Any], process))

    assert process.waits == 2
    assert process.poll() == 0


def test_windows_cancellation_uses_owned_process_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import supervision as execution

    process = FinishedProcess(None)
    calls: list[object] = []

    def terminate_tree(candidate: object) -> None:
        calls.append(candidate)

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(
        execution,
        "_terminate_windows_process_tree",
        terminate_tree,
        raising=False,
    )

    execution.cancel_process(cast(subprocess.Popen[Any], process))

    assert calls == [process]
    assert not process.terminated


def _process_running(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()[2]
    except (FileNotFoundError, IndexError):
        return False
    return state != "Z"


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX process groups")
@pytest.mark.parametrize("root_exits_first", [False, True])
def test_posix_cancellation_kills_surviving_descendants(
    tmp_path: Path, root_exits_first: bool
) -> None:
    from clearml_yolo.adapters.runtime import supervision as execution

    child_pid_path = tmp_path / "child.pid"
    child_script = (
        "import os,signal,sys,time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "open(sys.argv[1], 'w', encoding='utf-8').write(str(os.getpid())); "
        "time.sleep(60)"
    )
    root_script = (
        "import subprocess,sys,time; "
        "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]], "
        "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
        + ("raise SystemExit(0)" if root_exits_first else "time.sleep(60)")
    )
    process = subprocess.Popen(  # noqa: S603 - fixed task-owned process tree
        [sys.executable, "-c", root_script, child_script, str(child_pid_path)],
        start_new_session=True,
    )
    child_pid: int | None = None
    try:
        execution._attach_process_tree(process)
        deadline = time.monotonic() + 5
        while not child_pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        child_pid = int(child_pid_path.read_text(encoding="utf-8"))
        if root_exits_first:
            process.wait(timeout=5)

        execution.cancel_process(process)

        deadline = time.monotonic() + 5
        while _process_running(child_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not _process_running(child_pid)
        assert process.poll() is not None
    finally:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
