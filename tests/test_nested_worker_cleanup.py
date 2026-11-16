"""Real nested worker sessions are reaped without stopping unrelated siblings."""

import json
import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

import pytest

from clearml_yolo.adapters.runtime.worker_pool import IndependentWorkerPool
from clearml_yolo.adapters.runtime.workers import WorkerCommand

pytestmark = [
    pytest.mark.process_capabilities,
    pytest.mark.skipif(sys.platform != "linux", reason="Linux process ownership"),
]


@pytest.mark.parametrize("stop", ["reserve", "interrupt", "timeout"])
def test_nested_sessions_are_reaped_on_outer_cancellation(tmp_path: Path, stop: str) -> None:
    ready, outer_pid = tmp_path / "ready.json", tmp_path / "outer.pid"
    token = uuid4().hex
    leaf = "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"
    child = (
        "import json,os,signal,subprocess,sys,time\n"
        f"leaf=subprocess.Popen([sys.executable,'-c',{leaf!r}],start_new_session=True)\n"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        f"open({str(ready)!r},'w').write(json.dumps([os.getpid(),leaf.pid]))\n"
        "time.sleep(60)\n"
    )
    outer = (
        "import os,sys\nfrom pathlib import Path\n"
        "from clearml_yolo.adapters.runtime.workers import WorkerCommand,run_workers\n"
        f"Path({str(outer_pid)!r}).write_text(str(os.getpid()))\n"
        f"run_workers([WorkerCommand((sys.executable,'-c',{child!r}),{{}},"
        f"Path({str(tmp_path / 'inner.log')!r}))],timeout_seconds=45)\n"
    )
    environment = {"CY_TEST_NESTED_OWNER": token, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    command = WorkerCommand((sys.executable, "-c", outer), environment, tmp_path / "outer.log")
    sibling = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"])

    def execute() -> None:
        with IndependentWorkerPool() as pool:
            pool.start("case", command)
            deadline = time.monotonic() + 2
            while True:
                assert not pool.poll(), "Nested worker exited before cancellation"
                if ready.exists() and ready.read_text(encoding="utf-8"):
                    if stop == "reserve":
                        raise RuntimeError("GPU memory reserve breached")
                    if stop == "interrupt":
                        raise KeyboardInterrupt
                if time.monotonic() >= deadline:
                    raise TimeoutError("Scenario deadline exceeded")
                time.sleep(0.01)

    try:
        expected = {"reserve": RuntimeError, "interrupt": KeyboardInterrupt, "timeout": TimeoutError}[stop]
        with pytest.raises(expected):
            execute()
        assert sibling.poll() is None
        pids = [int(outer_pid.read_text()), *json.loads(ready.read_text(encoding="utf-8"))]
        for pid in pids:
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)
    finally:
        sibling.terminate()
        sibling.wait(timeout=5)
        _reap_test_descendants(ready, token)


def _reap_test_descendants(ready: Path, token: str) -> None:
    # Failed assertions must still clean only descendants bearing this test's
    # fresh marker; a reused numeric PID grants no cleanup authority.
    if ready.exists() and ready.read_text(encoding="utf-8"):
        for pid in json.loads(ready.read_text(encoding="utf-8")):
            with suppress(FileNotFoundError, ProcessLookupError):
                if f"CY_TEST_NESTED_OWNER={token}".encode() in Path(f"/proc/{pid}/environ").read_bytes():
                    os.kill(pid, signal.SIGKILL)
            with suppress(ChildProcessError):
                os.waitpid(pid, 0)
