"""Independent case processes overlap and clean only their own descendants."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from clearml_yolo.adapters.runtime.process_tree import LinuxProcessTree
from clearml_yolo.adapters.runtime.worker_pool import IndependentWorkerPool, WorkerCompletion
from clearml_yolo.adapters.runtime.workers import WorkerCommand


def _command(source: str, output: Path, **environment: str) -> WorkerCommand:
    return WorkerCommand(
        argv=(sys.executable, "-c", source), environment=environment, log_path=output
    )


def _until(predicate: Callable[[], bool], *, seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() >= deadline:
            pytest.fail("Timed out waiting for the owned test process")
        time.sleep(0.01)


def _collect(pool: IndependentWorkerPool, count: int) -> tuple[WorkerCompletion, ...]:
    results: list[WorkerCompletion] = []

    def completed() -> bool:
        results.extend(pool.poll())
        return len(results) == count

    _until(completed)
    return tuple(results)


def _gone(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def test_independent_workers_overlap_and_keep_distinct_markers(tmp_path: Path) -> None:
    ready = tuple(tmp_path / f"ready-{index}" for index in range(2))
    with IndependentWorkerPool() as pool:
        for index in range(2):
            source = (
                "import os,time\nfrom pathlib import Path\n"
                f"Path({str(ready[index])!r}).touch()\n"
                f"while not Path({str(ready[1 - index])!r}).exists(): time.sleep(.01)\n"
                "print(os.environ['CY_BATCH_CASE_OWNER'])\n"
            )
            pool.start(
                str(index),
                _command(source, tmp_path / f"{index}.log", CY_BATCH_CASE_OWNER="caller"),
            )
        outcomes = _collect(pool, 2)
        assert pool.poll() == ()
    assert {item.key for item in outcomes} == {"0", "1"}
    assert all(item.exit_code == 0 and item.cleanup_complete for item in outcomes)
    markers = {(tmp_path / f"{index}.log").read_text().strip() for index in range(2)}
    assert len(markers) == 2
    assert "caller" not in markers
    assert all(markers)


def test_failed_case_does_not_terminate_running_peer(tmp_path: Path) -> None:
    pid_file, finish = tmp_path / "peer.pid", tmp_path / "finish"
    peer = (
        "import os,time\nfrom pathlib import Path\n"
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        f"while not Path({str(finish)!r}).exists(): time.sleep(.01)\n"
        "print('peer completed')\n"
    )
    failing = (
        "import time\nfrom pathlib import Path\n"
        f"while not Path({str(pid_file)!r}).exists(): time.sleep(.01)\n"
        "raise SystemExit(7)\n"
    )
    with IndependentWorkerPool() as pool:
        pool.start("peer", _command(peer, tmp_path / "peer.log"))
        pool.start("failed", _command(failing, tmp_path / "failed.log"))
        (failed,) = _collect(pool, 1)
        assert failed.key == "failed"
        assert failed.exit_code == 7
        assert failed.cleanup_complete
        assert not _gone(int(pid_file.read_text()))
        finish.touch()
        (successful,) = _collect(pool, 1)
        assert successful.key == "peer"
        assert successful.exit_code == 0
    assert (tmp_path / "peer.log").read_text().strip() == "peer completed"


@pytest.mark.parametrize("exit_code", [0, 7])
def test_completion_cleans_detached_grandchild_with_changed_trial_marker(
    tmp_path: Path, exit_code: int
) -> None:
    pid_file = tmp_path / "grandchild.pid"
    grandchild = (
        "import os,time\nfrom pathlib import Path\n"
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(60)\n"
    )
    intermediate = (
        "import os,subprocess,sys,time\nfrom pathlib import Path\n"
        f"subprocess.Popen([sys.executable,'-c',{grandchild!r}],start_new_session=True,"
        "env=dict(os.environ)|{'CY_TRAINING_WORKER_OWNER':'new-trial'})\n"
        f"while not Path({str(pid_file)!r}).exists(): time.sleep(.01)\n"
    )
    source = (
        "import subprocess,sys\n"
        f"subprocess.run([sys.executable,'-c',{intermediate!r}],check=True)\n"
        f"raise SystemExit({exit_code})\n"
    )
    helper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        with IndependentWorkerPool() as pool:
            pool.start("case", _command(source, tmp_path / "case.log"))
            (completed,) = _collect(pool, 1)
            assert completed.exit_code == exit_code
            assert completed.cleanup_complete
            assert _gone(int(pid_file.read_text()))
            assert helper.poll() is None
            pool.start("next", _command("print('next')", tmp_path / "next.log"))
            assert _collect(pool, 1)[0].cleanup_complete
        assert helper.poll() is None
    finally:
        helper.terminate()
        helper.wait(timeout=5)


def test_startup_failure_keeps_existing_case_running(tmp_path: Path) -> None:
    pid_file = tmp_path / "peer.pid"
    source = (
        f"import os,time;open({str(pid_file)!r},'w').write(str(os.getpid()));time.sleep(60)"
    )
    with IndependentWorkerPool() as pool:
        pool.start("peer", _command(source, tmp_path / "peer.log"))
        _until(lambda: pid_file.is_file() and bool(pid_file.read_text()))
        with pytest.raises(FileNotFoundError):
            pool.start(
                "missing",
                WorkerCommand(
                    argv=(str(tmp_path / "missing-executable"),),
                    environment={},
                    log_path=tmp_path / "missing.log",
                ),
            )
        assert not _gone(int(pid_file.read_text()))
        pool.start("next", _command("pass", tmp_path / "next.log"))
        assert _collect(pool, 1)[0].key == "next"
    assert _gone(int(pid_file.read_text()))


def test_pool_context_and_job_identity_are_single_use(tmp_path: Path) -> None:
    pool = IndependentWorkerPool()
    with pytest.raises(RuntimeError, match="context"):
        pool.start("outside", _command("pass", tmp_path / "outside.log"))
    with pool:
        with pytest.raises(ValueError, match="nonempty"):
            pool.start("", _command("pass", tmp_path / "empty.log"))
        with pytest.raises(ValueError, match="nonempty"):
            pool.start("empty", WorkerCommand((), {}, tmp_path / "empty.log"))
        pool.start("case", _command("pass", tmp_path / "case.log"))
        _collect(pool, 1)
        with pytest.raises(ValueError, match="already"):
            pool.start("case", _command("pass", tmp_path / "duplicate.log"))
    with pytest.raises(RuntimeError, match="context"):
        pool.poll()
    with pytest.raises(RuntimeError, match="reused"), pool:
        pytest.fail("A pool cannot acquire a second ownership scope")


def test_unverified_cleanup_is_reported_once_and_retried_on_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = LinuxProcessTree.terminate
    failed_roots: set[int] = set()
    attempts: list[int] = []

    def fail_once(tree: LinuxProcessTree, *, adopted_parent: int | None = None) -> None:
        if tree.root != os.getpid():
            attempts.append(tree.root)
            if tree.root not in failed_roots:
                failed_roots.add(tree.root)
                raise RuntimeError("cleanup evidence unavailable")
        original(tree, adopted_parent=adopted_parent)

    monkeypatch.setattr(LinuxProcessTree, "terminate", fail_once)
    with IndependentWorkerPool() as pool:
        pool.start("case", _command("pass", tmp_path / "case.log"))
        (completed,) = _collect(pool, 1)
        assert not completed.cleanup_complete
        assert "cleanup evidence unavailable" in completed.diagnostic
        assert pool.poll() == ()
        with pytest.raises(ValueError, match="already"):
            pool.start("case", _command("pass", tmp_path / "duplicate.log"))
    assert len(attempts) == 2


def test_exception_cleans_all_cases_and_preserves_original_error(tmp_path: Path) -> None:
    pids = [tmp_path / f"case-{index}.pid" for index in range(2)]

    def cancel() -> None:
        with IndependentWorkerPool() as pool:
            for index, path in enumerate(pids):
                source = (
                    f"import os,time;open({str(path)!r},'w').write(str(os.getpid()));time.sleep(60)"
                )
                pool.start(str(index), _command(source, tmp_path / f"{index}.log"))
            _until(lambda: all(path.is_file() and path.read_text() for path in pids))
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        cancel()
    assert all(_gone(int(path.read_text())) for path in pids)


def test_persistent_cleanup_failure_remains_visible_after_peer_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = LinuxProcessTree.terminate
    selected: list[int] = []
    observed: list[WorkerCompletion] = []

    def fail_selected(tree: LinuxProcessTree, *, adopted_parent: int | None = None) -> None:
        if tree.root != os.getpid() and not selected:
            selected.append(tree.root)
        if selected and tree.root == selected[0]:
            raise RuntimeError("unverifiable descendants")
        original(tree, adopted_parent=adopted_parent)

    def run() -> None:
        with IndependentWorkerPool() as pool:
            pool.start("uncertain", _command("pass", tmp_path / "uncertain.log"))
            observed.extend(_collect(pool, 1))
            pool.start("peer", _command("pass", tmp_path / "peer.log"))
            observed.extend(_collect(pool, 1))
            raise ValueError("original caller failure")

    monkeypatch.setattr(LinuxProcessTree, "terminate", fail_selected)
    with pytest.raises(ExceptionGroup, match="Independent worker cleanup failed") as failed:
        run()
    assert observed[0].cleanup_complete is False
    assert observed[1].cleanup_complete is True
    assert any(isinstance(error, ValueError) for error in failed.value.exceptions)
    assert any("unverifiable descendants" in str(error) for error in failed.value.exceptions)
    assert _gone(selected[0])


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_real_repeated_signals_finish_owned_cleanup(tmp_path: Path, signum: signal.Signals) -> None:
    ready, pids = tmp_path / "ready", [tmp_path / f"worker-{index}.pid" for index in range(2)]
    worker_sources = [
        "import os,signal,time\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        f"Path({str(path)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(60)\n"
        for path in pids
    ]
    supervisor = (
        "import sys,time\nfrom pathlib import Path\n"
        "from clearml_yolo.adapters.runtime.bootstrap import runtime_environment\n"
        "from clearml_yolo.adapters.runtime.worker_pool import IndependentWorkerPool\n"
        "from clearml_yolo.adapters.runtime.workers import WorkerCommand\n"
        "with runtime_environment(), IndependentWorkerPool() as pool:\n"
        f" for index,source in enumerate({worker_sources!r}):\n"
        f"  pool.start(str(index),WorkerCommand((sys.executable,'-c',source),{{}},"
        f"Path({str(tmp_path)!r})/f'worker-{{index}}.log'))\n"
        f" while not all(Path(p).exists() for p in {[str(path) for path in pids]!r}):"
        " time.sleep(.01)\n"
        f" Path({str(ready)!r}).touch()\n"
        " while True: time.sleep(.05)\n"
    )
    process = subprocess.Popen(  # noqa: S603 - fixed test harness and current interpreter
        [sys.executable, "-c", supervisor], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        _until(lambda: ready.exists() or process.poll() is not None)
        assert process.poll() is None, process.communicate(timeout=1)
        process.send_signal(signum)
        time.sleep(0.15)
        process.send_signal(signum)
        _stdout, stderr = process.communicate(timeout=20)
        assert process.returncode != 0
        assert b"cleanup failed" not in stderr.lower()
        assert all(_gone(int(path.read_text())) for path in pids)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for path in pids:
            if path.is_file() and not _gone(int(path.read_text())):
                os.kill(int(path.read_text()), signal.SIGKILL)
