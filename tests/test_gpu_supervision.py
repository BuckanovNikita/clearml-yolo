"""Failure-safe queued child supervision."""

import json
import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast, override

import pytest
from hydra.core.utils import JobReturn, JobStatus
from omegaconf import OmegaConf


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
        if timeout is not None:
            raise subprocess.TimeoutExpired("worker", timeout)
        self.returncode = 0
        return 0


def _config() -> Any:
    return OmegaConf.create({"hydra": {"job": {"env_set": {}}, "overrides": {"task": []}}})


def _sweep_job(tmp_path: Path, receipt: object | None) -> Any:
    from clearml_yolo.entrypoints.hydra.execution import ModelJob

    temporary = TemporaryDirectory(prefix="receipt-", dir=tmp_path)
    if receipt is not None:
        Path(temporary.name, "result.json").write_text(json.dumps(receipt), encoding="utf-8")
    return ModelJob(
        "train",
        lambda: None,
        _config(),
        sweep=True,
        process=cast(subprocess.Popen[Any], FinishedProcess()),
        temporary=temporary,
        launch_cwd=str(tmp_path / "launcher"),
    )


def test_sweep_receipt_controls_status_and_working_directory(tmp_path: Path) -> None:
    job = _sweep_job(
        tmp_path,
        {"status": "COMPLETED", "working_dir": str(tmp_path / "sweep" / "3")},
    )

    job.poll()

    assert job.result is not None
    assert job.result.status is JobStatus.COMPLETED
    assert job.result.working_dir == str(tmp_path / "sweep" / "3")


@pytest.mark.parametrize(
    "receipt",
    [
        None,
        {"status": "UNKNOWN", "working_dir": "/tmp/job"},
        {"status": ["COMPLETED"], "working_dir": "/tmp/job"},
        {"status": "COMPLETED"},
    ],
)
def test_missing_or_invalid_sweep_receipt_is_failed(tmp_path: Path, receipt: object | None) -> None:
    job = _sweep_job(tmp_path, receipt)

    job.poll()

    assert job.result is not None
    assert job.result.status is JobStatus.FAILED
    with pytest.raises(RuntimeError, match="receipt"):
        _ = job.result.return_value


def test_model_job_close_attempts_every_owned_cleanup() -> None:
    from clearml_yolo.entrypoints.hydra import execution

    events: list[str] = []

    class Ticket:
        def close(self) -> None:
            events.append("ticket")
            raise OSError("ticket close failed")

    class Temporary:
        def cleanup(self) -> None:
            events.append("temporary")

    job = execution.ModelJob(
        "train",
        lambda: None,
        _config(),
        process=cast(subprocess.Popen[Any], FinishedProcess()),
        ticket=cast(Any, Ticket()),
        temporary=cast(Any, Temporary()),
    )

    with pytest.raises(BaseExceptionGroup, match="cleanup"):
        job.close()

    assert events == ["ticket", "temporary"]


def test_failed_process_cancellation_preserves_ticket_and_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.entrypoints.hydra import execution

    process = FinishedProcess(None)

    def fail_cancel(_process: subprocess.Popen[Any]) -> None:
        raise OSError("cancel failed")

    monkeypatch.setattr(execution, "cancel_process", fail_cancel)
    ticket = cast(Any, object())
    temporary = cast(Any, object())
    job = execution.ModelJob(
        "train",
        lambda: None,
        _config(),
        process=cast(subprocess.Popen[Any], process),
        ticket=ticket,
        temporary=temporary,
    )

    with pytest.raises(OSError, match="cancel failed"):
        job.close()

    assert job.process is cast(Any, process)
    assert job.ticket is ticket
    assert job.temporary is temporary


def test_run_jobs_closes_all_jobs_when_one_cleanup_fails() -> None:
    from clearml_yolo.entrypoints.hydra.execution import run_jobs

    events: list[str] = []

    class Job:
        result = JobReturn()

        def __init__(self, name: str, fail: bool = False) -> None:
            self.name = name
            self.fail = fail

        def prepare(self) -> None:
            events.append(f"prepare-{self.name}")

        def start(self) -> None:
            raise AssertionError("completed jobs must not start")

        def poll(self) -> None:
            raise AssertionError("completed jobs must not poll")

        def close(self) -> None:
            events.append(f"close-{self.name}")
            if self.fail:
                raise OSError(f"close-{self.name}")

    first = Job("first", fail=True)
    second = Job("second")
    with pytest.raises(BaseExceptionGroup, match="cleanup"):
        run_jobs(cast(Any, [first, second]))

    assert events == ["prepare-first", "prepare-second", "close-first", "close-second"]


def test_posix_timeout_tolerates_process_exit_before_group_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.entrypoints.hydra import execution

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
    from clearml_yolo.entrypoints.hydra import execution

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


def test_process_tree_is_attached_before_start_gate_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.entrypoints.hydra import execution

    process = FinishedProcess()
    typed_process = cast(subprocess.Popen[Any], process)
    attached: list[object] = []

    def attach(candidate: object) -> None:
        attached.append(candidate)

    def fake_popen(*args: object, **kwargs: object) -> subprocess.Popen[Any]:
        return typed_process

    monkeypatch.setattr(execution, "temporary_root", lambda: tmp_path)
    monkeypatch.setattr(
        subprocess,
        "Popen",
        fake_popen,
    )
    monkeypatch.setattr(
        execution,
        "_attach_process_tree",
        attach,
    )
    job = execution.ModelJob("train", lambda: None, _config(), launch_cwd=str(tmp_path))

    job.start()

    assert attached == [process]
    assert job.temporary is not None
    directory = Path(job.temporary.name)
    payload = OmegaConf.load(directory / "job.yaml")
    assert Path(payload.start_gate) == directory / "start.ready"
    assert Path(payload.start_gate).is_file()
    job.close()


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
    from clearml_yolo.entrypoints.hydra import execution

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


def test_restore_hydra_config_accepts_composed_environment_group() -> None:
    from hydra.conf import HydraConf

    from clearml_yolo.entrypoints.hydra.execution import restore_hydra_config

    config = OmegaConf.create(
        {
            "hydra": {
                "env": {"selected": "default"},
                "run": {"dir": "outputs"},
                "sweep": {"dir": "multirun", "subdir": "0"},
            }
        }
    )

    restored = restore_hydra_config(config)

    assert OmegaConf.get_type(restored.hydra) is HydraConf
    assert restored.hydra.env.selected == "default"


def test_effective_configuration_does_not_expand_smaller_replay_request() -> None:
    from clearml_yolo.entrypoints.hydra.execution import effective_configuration

    requested = OmegaConf.create(
        {"ultralytics": {"device": 7}, "ultralytics_predict": {"device": "cuda"}}
    )

    effective = effective_configuration(requested, ("GPU-a", "GPU-b"))

    assert list(effective.ultralytics.device) == [0]
    assert list(effective.ultralytics_predict.device) == [0]
