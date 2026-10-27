"""Real worker failures terminate peers and leave the supervisor reusable."""

import os
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

import pytest

from clearml_yolo.adapters.runtime import gpu_inventory as gpu
from clearml_yolo.adapters.runtime.workers import WorkerCommand, run_workers


def _command(source: str, output: Path) -> WorkerCommand:
    return WorkerCommand(argv=(sys.executable, "-c", source), environment={}, log_path=output)


def test_success_requires_every_worker_exit(tmp_path: Path) -> None:
    result = run_workers(
        [
            _command("print('rank zero')", tmp_path / "zero.log"),
            _command("print('rank one')", tmp_path / "one.log"),
        ],
        timeout_seconds=10,
    )
    assert result.status == "success"
    assert result.exit_codes == (0, 0)
    assert (tmp_path / "one.log").read_text().strip() == "rank one"


@pytest.mark.parametrize("failure", ["crash", "timeout"])
def test_failure_kills_peer_and_next_trial_succeeds(tmp_path: Path, failure: str) -> None:
    pid_file = tmp_path / "peer.pid"
    peer = f"import os,time;open({str(pid_file)!r},'w').write(str(os.getpid()));time.sleep(60)"
    failed = "import time;time.sleep(.3);raise SystemExit(7)" if failure == "crash" else peer
    start = time.monotonic()
    result = run_workers(
        [_command(failed, tmp_path / "zero.log"), _command(peer, tmp_path / "one.log")],
        timeout_seconds=0.7 if failure == "timeout" else 10,
    )
    assert result.status == failure
    assert time.monotonic() - start < 15
    assert all(code is not None for code in result.exit_codes)
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    assert (
        run_workers([_command("pass", tmp_path / "next.log")], timeout_seconds=10).status
        == "success"
    )


def test_invalid_timeout_never_starts_worker(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        run_workers([_command("pass", tmp_path / "unused.log")], timeout_seconds=float("nan"))
    assert not (tmp_path / "unused.log").exists()


def test_cancellation_terminates_owned_worker(tmp_path: Path) -> None:
    observed: list[int] = []

    def cancel(owned_pids: Callable[[], tuple[int, ...]]) -> None:
        observed.extend(owned_pids())
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_workers(
            [_command("import time;time.sleep(60)", tmp_path / "cancel.log")],
            timeout_seconds=10,
            monitor=cancel,
        )
    assert len(observed) == 1
    with pytest.raises(ProcessLookupError):
        os.kill(observed[0], 0)


def test_successful_leader_cannot_leave_detached_child(tmp_path: Path) -> None:
    pid_file = tmp_path / "descendant.pid"
    child = f"import os,time;open({str(pid_file)!r},'w').write(str(os.getpid()));time.sleep(60)"
    parent = (
        f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}],"
        "start_new_session=True);time.sleep(.3)"
    )
    result = run_workers([_command(parent, tmp_path / "parent.log")], timeout_seconds=10)
    assert result.status == "success"
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)


def test_monitor_recognizes_live_detached_descendant(tmp_path: Path) -> None:
    pid_file = tmp_path / "compiler.pid"
    child = f"import os,time;open({str(pid_file)!r},'w').write(str(os.getpid()));time.sleep(1)"
    parent = (
        f"import subprocess,sys;subprocess.Popen([sys.executable,'-c',{child!r}],"
        "start_new_session=True).wait()"
    )
    seen: set[int] = set()

    def observe(owned_pids: Callable[[], tuple[int, ...]]) -> None:
        seen.update(owned_pids())

    result = run_workers(
        [_command(parent, tmp_path / "parent.log")], timeout_seconds=10, monitor=observe
    )
    assert result.status == "success"
    assert int(pid_file.read_text()) in seen
    assert os.getpid() not in seen


def test_detached_child_is_reaped_without_touching_preexisting_helper(tmp_path: Path) -> None:
    pid_file = tmp_path / "descendant.pid"
    child = f"import os,time;open({str(pid_file)!r},'w').write(str(os.getpid()));time.sleep(60)"
    parent = (
        f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}],"
        "start_new_session=True);time.sleep(.3)"
    )
    helper = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(60)"],
    )
    try:
        result = run_workers([_command(parent, tmp_path / "parent.log")], timeout_seconds=10)
        assert result.status == "success"
        assert helper.poll() is None
        with pytest.raises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
    finally:
        helper.terminate()
        helper.wait(timeout=5)
        # A failed regression must still reap its own adopted zombie.
        if pid_file.is_file():
            with suppress(ChildProcessError):
                os.waitpid(int(pid_file.read_text()), os.WNOHANG)


def test_gpu_telemetry_accepts_owned_child_spawned_during_its_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trigger, finished, pid_file = (tmp_path / name for name in ("spawn", "finish", "child.pid"))
    child = (
        "import os,time\nfrom pathlib import Path\n"
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        f"while not Path({str(finished)!r}).exists(): time.sleep(.01)\n"
    )
    worker = (
        "import subprocess,sys,time\nfrom pathlib import Path\n"
        f"while not Path({str(trigger)!r}).exists(): time.sleep(.01)\n"
        f"subprocess.Popen([sys.executable,'-c',{child!r}],start_new_session=True).wait()\n"
    )
    device = gpu.GPUDevice(
        index=0, uuid="GPU-test", name="test", total_memory_bytes=100,
        used_memory_bytes=10, utilization=0,
    )
    observed: list[int] = []

    def telemetry() -> dict[str, gpu.GPUState]:
        # The child cannot exist when _await_workers calls the monitor. Its birth
        # occurs inside the telemetry query, after the formerly eager PID scan.
        trigger.touch()
        deadline = time.monotonic() + 5
        while not pid_file.is_file() or not pid_file.read_text():
            if time.monotonic() >= deadline:
                pytest.fail("Worker did not spawn its child during telemetry")
            time.sleep(.01)
        pid = int(pid_file.read_text())
        assert b"CY_TRAINING_WORKER_OWNER=" in Path(f"/proc/{pid}/environ").read_bytes()
        observed.append(pid)
        return {device.uuid: gpu.GPUState(50, 75, frozenset({pid}))}

    def monitor(owned_pids: Callable[[], tuple[int, ...]]) -> None:
        if not observed:
            assert gpu.monitor_devices((device,), owned_pids) == (50,)
            finished.touch()

    monkeypatch.setattr(gpu, "gpu_states", telemetry)
    outcome = run_workers(
        [_command(worker, tmp_path / "worker.log")], timeout_seconds=10, monitor=monitor
    )
    assert outcome.status == "success"
    assert len(observed) == 1
    with pytest.raises(ProcessLookupError):
        os.kill(observed[0], 0)
