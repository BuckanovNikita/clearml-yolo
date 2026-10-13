"""Late DDP readers cannot execute SDK callbacks or overwrite owner state."""

import importlib
import json
import os
import subprocess
import time
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from clearml_yolo.adapters.integrations.native_ddp import NativeDDPRelay
from clearml_yolo.adapters.integrations.native_runtime import (
    OWNER_PID_ENV,
    OWNER_TASK_ENV,
    native_runtime,
)
from test_native_ddp import _Model, _Task


@pytest.mark.parametrize("original_failure", [False, True])
def test_stalled_reader_resume_after_timeout_never_dispatches_sdk_callbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    original_failure: bool,
) -> None:
    task = _Task()
    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.active_task", lambda: task)
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    monkeypatch.setattr(
        "clearml_yolo.adapters.integrations.native_ddp._JOIN_SECONDS", 0.03, raising=False
    )
    model = _Model()
    model.trainer = SimpleNamespace(ddp=True)
    relay = NativeDDPRelay(task, model, str(tmp_path))
    records = [
        {"event": "on_pretrain_routine_start", "args": {}},
        {
            "event": "on_train_epoch_end",
            "epoch": 0,
            "losses": {"train/loss": 1},
            "lr": {},
            "save_dir": str(tmp_path),
        },
    ]
    (tmp_path / "events.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records))
    entered, released = Event(), Event()
    late_effects: list[str] = []
    consume = relay._consume

    def stalled_read() -> None:
        entered.set()
        assert released.wait(5)
        consume()

    monkeypatch.setattr(relay, "_consume", stalled_read)
    monkeypatch.setattr(relay, "_dispatch", lambda record: late_effects.append(record["event"]))
    original = ValueError("original native failure")
    relay.__enter__()
    try:
        assert entered.wait(3)
        if original_failure:
            # Exceptional cleanup preserves the original failure despite join timeout.
            def raise_and_cleanup() -> None:
                try:
                    raise original
                finally:
                    relay.__exit__(ValueError, original, None)

            with pytest.raises(ValueError, match="original native failure") as caught:
                raise_and_cleanup()
            assert caught.value is original
        else:
            with pytest.raises(RuntimeError, match="deadline"):
                relay.__exit__(None, None, None)
        assert relay._thread is not None
        assert relay._thread.is_alive()
    finally:
        released.set()
        assert relay._thread is not None
        relay._thread.join(timeout=3)
    assert not relay._thread.is_alive()
    assert late_effects == []


def test_owner_callback_deadline_cannot_restore_logger_over_later_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import clearml

    from clearml_yolo.adapters.clearml.deadline import TaskFinalizationError

    task = _Task()
    _Task.current = task
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.active_task", lambda: task)
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    relay = NativeDDPRelay(task, _Model(), str(tmp_path))
    relay._args = SimpleNamespace()
    relay._callback_seconds = 0.03
    late_effects: list[str] = []

    def later_logger() -> object:
        return task.logger

    def blocking_scalar(*_args: object, **_kwargs: object) -> None:
        monkeypatch.setattr(task, "get_logger", later_logger)
        time.sleep(0.15)
        late_effects.append("report after deadline")

    monkeypatch.setattr(task.logger, "report_scalar", blocking_scalar)
    record = {
        "event": "on_train_epoch_end",
        "epoch": 0,
        "losses": {"train/loss": 1},
        "lr": {},
        "save_dir": str(tmp_path),
    }
    with pytest.raises(TaskFinalizationError, match="deadline"), native_runtime():
        relay._dispatch(record)
    assert late_effects == []
    assert task.get_logger is later_logger


def test_native_scalar_callbacks_remain_serializable_for_ddp() -> None:
    from ultralytics.utils.callbacks import clearml as integration

    # The installed serializer exposes no typing metadata.
    cloudpickle = importlib.import_module("cloudpickle")
    with native_runtime():
        restored = cloudpickle.loads(cloudpickle.dumps(integration.callbacks))
    assert set(restored) == {
        "on_pretrain_routine_start",
        "on_train_epoch_end",
        "on_fit_epoch_end",
        "on_val_end",
        "on_train_end",
    }


@pytest.mark.parametrize("fail_callback", [False, True])
def test_cpu_observer_reads_live_journal_and_preserves_publication_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_callback: bool
) -> None:
    from ddp_cpu_harness import _wait_workers
    from ddp_cpu_recording import RecordingTask

    task = RecordingTask(fail_callback=fail_callback)
    (tmp_path / "first-epoch-ready").touch()
    scalar_journal = tmp_path / "scalars.jsonl"
    scalar_journal.write_text(
        json.dumps(
            {"title": "metrics", "series": "metrics/mAP50(B)", "value": 0.75, "iteration": 0}
        )
        + "\n"
    )
    process = Mock(spec=subprocess.Popen)
    process.poll.side_effect = [None, 0]
    monkeypatch.setattr("ddp_cpu_harness.time.sleep", lambda _seconds: None)

    live, failure = _wait_workers(process, tmp_path, task, scalar_journal)

    assert (tmp_path / "release-first-epoch").is_file()
    if fail_callback:
        assert not live
        assert isinstance(failure, RuntimeError)
        assert str(failure) == "Injected owner callback failure"
        assert task.callback_failed
        assert task.scalars == []
    else:
        assert live
        assert failure is None
        assert len(task.scalars) == 1
        assert task.scalars[0]["value"] == 0.75
