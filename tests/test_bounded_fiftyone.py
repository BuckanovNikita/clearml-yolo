"""Real publication subprocess failures must be bounded without backend services."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clearml_yolo.core.publication import FiftyOneConfig, PublicationRequest


@pytest.mark.parametrize(
    "field", ["preflight_timeout_seconds", "publish_timeout_seconds", "lock_timeout_seconds"]
)
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_timeout_controls_reject_nonpositive_and_nonfinite(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        FiftyOneConfig.model_validate({field: value})


def _publisher(monkeypatch: pytest.MonkeyPatch, script: str, timeout: float = 0.4) -> Any:
    from clearml_yolo.adapters.fiftyone import bounded

    # A real fresh interpreter exercises the production supervisor and JSON boundary.
    monkeypatch.setattr(
        bounded, "_worker_command", lambda *args: [sys.executable, "-c", script, *map(str, args)]
    )
    return bounded.BoundedFiftyOnePublisher(
        FiftyOneConfig(preflight_timeout_seconds=timeout, publish_timeout_seconds=timeout)
    )


def test_worker_import_hang_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = _publisher(monkeypatch, "import time; time.sleep(30)")
    started = time.monotonic()
    with pytest.raises(RuntimeError, match=r"deadline.*startup"):
        publisher.preflight()
    assert time.monotonic() - started < 3


@pytest.mark.parametrize("phase", ["import", "database", "lock", "write", "shutdown"])
def test_worker_phase_hang_is_bounded(monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    script = (
        f"import sys,time,pathlib; pathlib.Path(sys.argv[3]).write_text('{phase}'); time.sleep(30)"
    )
    publisher = _publisher(monkeypatch, script)
    started = time.monotonic()
    with pytest.raises(RuntimeError, match=rf"deadline.*{phase}"):
        publisher.preflight()
    assert time.monotonic() - started < 3


@pytest.mark.parametrize(
    ("exit_code", "receipt"),
    [(1, {}), (0, {}), (0, {"operation": "publish", "operation_id": "wrong", "complete": True})],
)
def test_exit_and_matching_complete_receipt_are_required(
    monkeypatch: pytest.MonkeyPatch, exit_code: int, receipt: dict[str, Any]
) -> None:
    script = (
        "import sys,pathlib,json; "
        f"pathlib.Path(sys.argv[2]).write_text({json.dumps(json.dumps(receipt))}); "
        f"sys.exit({exit_code})"
    )
    publisher = _publisher(monkeypatch, script)
    with pytest.raises(RuntimeError):
        publisher.preflight()


def test_successful_preflight_uses_fresh_clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "CUDA_VISIBLE_DEVICES",
        "NVIDIA_VISIBLE_DEVICES",
        "CY_CLEARML_OWNER_ID",
        "CY_GPU_QUEUE_TICKET",
    ):
        monkeypatch.setenv(key, "inherited")
    script = """
import sys,pathlib,json,os
request=json.loads(pathlib.Path(sys.argv[1]).read_text())
assert os.environ['CUDA_VISIBLE_DEVICES'] == ''
assert os.environ['NVIDIA_VISIBLE_DEVICES'] == 'none'
assert not any(k.startswith(('CY_CLEARML_OWNER_', 'CY_GPU_QUEUE_')) for k in os.environ)
response=dict(operation=request['operation'], operation_id=request['operation_id'],
    task_id=None, complete=True, receipt=None)
pathlib.Path(sys.argv[2]).write_text(json.dumps(response))
"""
    _publisher(monkeypatch, script).preflight()


def test_large_worker_output_cannot_deadlock_and_diagnostic_is_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = "import sys; sys.stderr.write('x'*1000000 + '\\npassword=secret-value'); sys.exit(1)"
    with pytest.raises(RuntimeError) as failure:
        _publisher(monkeypatch, script).preflight()
    assert len(str(failure.value)) < 5000
    assert "secret-value" not in str(failure.value)


def test_shutdown_hang_after_receipt_is_still_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    script = """
import sys,pathlib,json,time
request=json.loads(pathlib.Path(sys.argv[1]).read_text())
response=dict(operation=request['operation'], operation_id=request['operation_id'],
    task_id=None, complete=True, receipt=None)
pathlib.Path(sys.argv[2]).write_text(json.dumps(response))
pathlib.Path(sys.argv[3]).write_text('shutdown')
time.sleep(30)
"""
    with pytest.raises(RuntimeError, match=r"deadline.*shutdown"):
        _publisher(monkeypatch, script).preflight()


def test_cancellation_propagates_and_worker_is_reaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pid_file = tmp_path / "pid"
    script = (
        f"import os,pathlib,time; pathlib.Path({str(pid_file)!r})"
        ".write_text(str(os.getpid())); time.sleep(30)"
    )
    publisher = _publisher(monkeypatch, script, timeout=10)
    original_wait = subprocess.Popen.wait

    def interrupted(process: subprocess.Popen[bytes], timeout: float | None = None) -> int:
        if not pid_file.exists():
            return original_wait(process, timeout=timeout)
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess.Popen, "wait", interrupted)
    with pytest.raises(KeyboardInterrupt):
        publisher.preflight()
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_timeout_defaults() -> None:
    config = FiftyOneConfig()
    assert config.preflight_timeout_seconds == 60
    assert config.publish_timeout_seconds == 900
    assert config.lock_timeout_seconds == 30


def test_owned_descendant_is_stopped_while_shared_service_survives(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shared = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    descendant_path = tmp_path / "descendant"
    script = f"""
import sys,pathlib,subprocess,time
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'], start_new_session=True)
pathlib.Path({str(descendant_path)!r}).write_text(str(child.pid))
time.sleep(30)
"""
    try:
        with pytest.raises(RuntimeError, match=r"deadline"):
            _publisher(monkeypatch, script).preflight()
        assert shared.poll() is None
        pid = int(descendant_path.read_text())
        proc = Path("/proc") / str(pid) / "stat"
        assert not proc.exists() or proc.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    finally:
        shared.terminate()
        shared.wait(timeout=5)


def test_successful_publication_preserves_receipt_and_requires_task_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script = """
import sys,pathlib,json,datetime
request=json.loads(pathlib.Path(sys.argv[1]).read_text())
task=request['request']['task_id']
receipt=dict(dataset_name='persistent', task_id=task, run_key='run',
ground_truth_sha256='truth', source_ground_truth_sha256='source', dataset_reused=True,
sample_count=2, fields={'predictions':'pred'}, dataset_complete=True, run_complete=True,
payload_paths={'ground_truth':request['request']['ground_truth']},
published_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
result=dict(operation=request['operation'],operation_id=request['operation_id'],
task_id=task,complete=True,receipt=receipt)
pathlib.Path(sys.argv[2]).write_text(json.dumps(result))
"""
    result = _publisher(monkeypatch, script).publish(
        PublicationRequest(task_id="mine", ground_truth=tmp_path / "truth.csv")
    )
    assert result.task_id == "mine"
    assert result.dataset_name == "persistent"
    assert result.sample_count == 2


def test_relative_request_paths_resolve_before_worker_changes_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    script = """
import sys,pathlib,json
request=json.loads(pathlib.Path(sys.argv[1]).read_text())['request']
paths=[request['ground_truth'],request['source_ground_truth'],request['predictions'],
    *request['evaluations'].values()]
assert all(pathlib.Path(value).is_absolute() for value in paths)
assert pathlib.Path(request['ground_truth']).parent == pathlib.Path.cwd()
"""
    request = PublicationRequest(
        task_id="relative",
        ground_truth=Path("truth.csv"),
        source_ground_truth=Path("source.csv"),
        predictions=Path("pred.csv"),
        evaluations={"test": Path("evaluation.json")},
    )
    publisher = _publisher(monkeypatch, script)
    # The probe deliberately provides no receipt. It must fail only at receipt validation.
    with pytest.raises(RuntimeError, match="invalid receipt"):
        publisher.publish(request)
    assert request.ground_truth == Path("truth.csv")


def _deny_marker_updates(monkeypatch: pytest.MonkeyPatch, retained_reasons: list[str]) -> None:
    from clearml_yolo.adapters.runtime import bootstrap

    monkeypatch.setattr(bootstrap, "retain_current_arena", retained_reasons.append)
    original_write = Path.write_text

    def restricted_write(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if path.name == ".cy-unsafe-cleanup.json" and path.exists():
            raise PermissionError("marker update denied")
        return original_write(path, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", restricted_write)


@pytest.mark.parametrize("marker_update_denied", [False, True])
@pytest.mark.parametrize("interrupted", [False, True])
def test_unsafe_cleanup_preserves_operation_scratch_and_live_worker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    marker_update_denied: bool,
    interrupted: bool,
) -> None:
    from clearml_yolo.adapters.fiftyone import bounded

    arena_file = tmp_path / "arena"
    script = f"""
import pathlib,sys,time,os
pathlib.Path({str(arena_file)!r}).write_text(str(pathlib.Path(sys.argv[1]).parent)+'\\n'+str(os.getpid()))
time.sleep(30)
"""

    def denied(_owned: Any, _signal: Any) -> None:
        raise PermissionError("termination denied")

    monkeypatch.setattr(bounded._OwnedProcesses, "signal", denied)
    retained_reasons: list[str] = []
    launched: list[subprocess.Popen[bytes]] = []
    original_init = bounded._OwnedProcesses.__init__
    original_wait = subprocess.Popen.wait

    def recorded(owned: Any, process: subprocess.Popen[bytes]) -> None:
        original_init(owned, process)
        launched.append(process)

    monkeypatch.setattr(bounded._OwnedProcesses, "__init__", recorded)
    if marker_update_denied:
        _deny_marker_updates(monkeypatch, retained_reasons)
    if interrupted:

        def cancelled(process: subprocess.Popen[bytes], timeout: float | None = None) -> int:
            if arena_file.exists():
                raise KeyboardInterrupt
            return original_wait(process, timeout=timeout)

        monkeypatch.setattr(subprocess.Popen, "wait", cancelled)
    publisher = _publisher(monkeypatch, script)
    try:
        expected_error = KeyboardInterrupt if interrupted else RuntimeError
        with pytest.raises(expected_error, match=None if interrupted else "cleanup unsafe"):
            publisher.preflight()
    finally:
        if arena_file.exists():
            arena_text, pid_text = arena_file.read_text().splitlines()
            arena, pid = Path(arena_text), int(pid_text)
            try:
                assert arena.is_dir()
                marker = json.loads((arena / ".cy-unsafe-cleanup.json").read_text())
                assert marker["version"] == 1
                if marker_update_denied:
                    assert marker["owners"] == []
                    assert retained_reasons
                elif os.name == "posix":
                    assert pid in [owner["pid"] for owner in marker["owners"]]
                assert launched[0].poll() is None
            finally:
                launched[0].terminate()
                original_wait(launched[0], timeout=5)
                # Only this test-owned worker and operation directory are removed.
                import shutil

                shutil.rmtree(arena, ignore_errors=True)


def test_windows_cleanup_verifies_entire_job_after_direct_worker_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.fiftyone import bounded

    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait(timeout=5)
    active = [True]
    closed: list[int] = []
    monkeypatch.setattr(bounded, "_platform", lambda: "nt")
    monkeypatch.setattr(bounded, "_create_windows_job", lambda _process: 73)
    monkeypatch.setattr(bounded, "_windows_job_running", lambda _handle: active[0])
    monkeypatch.setattr(
        bounded, "_terminate_windows_job", lambda _handle: active.__setitem__(0, False)
    )
    monkeypatch.setattr(bounded, "_close_windows_job", closed.append)
    owned = bounded._OwnedProcesses(process)
    owned.attach()
    owned.cleanup()
    assert not active[0]
    assert closed == [73]


def test_unsupported_process_tracking_refuses_to_open_worker_start_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.fiftyone import bounded

    monkeypatch.setattr(bounded, "_platform", lambda: "unsupported")
    publisher = bounded.BoundedFiftyOnePublisher(FiftyOneConfig())
    with pytest.raises(RuntimeError, match="ownership is unsupported"):
        publisher.preflight()


def test_unproved_windows_accounting_retains_unknown_owner_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.fiftyone import bounded

    arena_file = tmp_path / "arena"
    script = f"""
import pathlib,sys,time
pathlib.Path({str(arena_file)!r}).write_text(str(pathlib.Path(sys.argv[1]).parent))
time.sleep(30)
"""
    monkeypatch.setattr(bounded, "_platform", lambda: "nt")
    monkeypatch.setattr(bounded, "_create_windows_job", lambda _process: 73)

    def inaccessible(_handle: int) -> bool:
        raise OSError("job accounting unavailable")

    monkeypatch.setattr(bounded, "_windows_job_running", inaccessible)
    publisher = _publisher(monkeypatch, script)
    with pytest.raises(RuntimeError, match="cleanup unsafe"):
        publisher.preflight()
    arena = Path(arena_file.read_text())
    try:
        marker = json.loads((arena / ".cy-unsafe-cleanup.json").read_text())
        assert marker["owners"] == []
        assert "accounting unavailable" in marker["reason"]
    finally:
        import shutil

        shutil.rmtree(arena)


def test_cannot_launch_without_durable_scratch_sentinel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.fiftyone import bounded

    directory = tmp_path / "operation"
    directory.mkdir()
    monkeypatch.setattr(bounded, "mkdtemp", lambda **_kwargs: str(directory))
    started: list[Any] = []
    monkeypatch.setattr(bounded, "_worker_command", lambda *args: started.append(args))
    original_write = Path.write_text

    def denied(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if path.name == ".cy-unsafe-cleanup.json":
            raise PermissionError("cannot persist ownership")
        return original_write(path, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", denied)
    with pytest.raises(RuntimeError, match="durable FiftyOne scratch ownership"):
        bounded.BoundedFiftyOnePublisher(FiftyOneConfig()).preflight()
    assert started == []
    assert not directory.exists()


def test_interruption_during_cleanup_keeps_conservative_scratch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.fiftyone import bounded

    arena_file = tmp_path / "arena"
    launched: list[subprocess.Popen[bytes]] = []
    original_init = bounded._OwnedProcesses.__init__

    def recorded(owned: Any, process: subprocess.Popen[bytes]) -> None:
        original_init(owned, process)
        launched.append(process)

    def interrupt(_owned: Any, _signal: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(bounded._OwnedProcesses, "__init__", recorded)
    monkeypatch.setattr(bounded._OwnedProcesses, "signal", interrupt)
    script = f"""
import pathlib,sys,time
pathlib.Path({str(arena_file)!r}).write_text(str(pathlib.Path(sys.argv[1]).parent))
time.sleep(30)
"""
    try:
        with pytest.raises(KeyboardInterrupt):
            _publisher(monkeypatch, script).preflight()
        arena = Path(arena_file.read_text())
        assert (arena / ".cy-unsafe-cleanup.json").is_file()
    finally:
        if launched:
            launched[0].terminate()
            launched[0].wait(timeout=5)
        if arena_file.exists():
            import shutil

            shutil.rmtree(Path(arena_file.read_text()), ignore_errors=True)
