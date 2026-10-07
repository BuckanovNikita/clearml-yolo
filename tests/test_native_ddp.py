"""Owner-only replay of native ClearML events produced by DDP rank zero."""

import os
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import matplotlib.pyplot as plt
import pytest

from clearml_yolo.native_ddp import native_ddp_relay
from clearml_yolo.native_runtime import OWNER_PID_ENV, OWNER_TASK_ENV, native_runtime


class _Logger:
    def __init__(self) -> None:
        self.scalars: list[tuple[str, str, float, int]] = []
        self.values: dict[str, float] = {}
        self.images: list[tuple[str, bytes]] = []
        self.figures: list[str] = []

    def report_scalar(self, title: str, series: str, value: float, iteration: int) -> None:
        self.scalars.append((title, series, value, iteration))

    def report_single_value(self, name: str, value: float) -> None:
        self.values[name] = value

    def report_image(self, **kwargs: Any) -> None:
        path = Path(kwargs["local_path"])
        self.images.append((path.name, path.read_bytes()))

    def report_matplotlib_figure(self, **kwargs: Any) -> None:
        self.figures.append(kwargs["title"])
        plt.close(kwargs["figure"])


class _Task:
    current: "_Task | None" = None

    def __init__(self) -> None:
        self.id = "owner-task"
        self.logger = _Logger()
        self.parameters: dict[str, Any] = {}
        self.output_models: list[tuple[str, str, bool]] = []

    @classmethod
    def current_task(cls) -> "_Task | None":
        return cls.current

    def connect(
        self,
        values: dict[str, Any],
        name: str,
        ignore_remote_overrides: bool,
    ) -> dict[str, Any]:
        assert name == "General"
        assert ignore_remote_overrides is True
        self.parameters.update({f"General/{key}": value for key, value in values.items()})
        return values

    def get_logger(self) -> _Logger:
        return self.logger

    def get_parameters(self) -> dict[str, Any]:
        return self.parameters.copy()

    def update_output_model(self, model_path: str, model_name: str, auto_delete_file: bool) -> None:
        self.output_models.append((model_path, model_name, auto_delete_file))


class _Model:
    def __init__(self) -> None:
        from ultralytics.utils.callbacks import base

        self.callbacks = {
            event: callbacks.copy() for event, callbacks in base.default_callbacks.items()
        }
        self.trainer: Any = None

    def add_callback(self, event: str, callback: Any) -> None:
        self.callbacks[event].append(callback)


def _capture_events(
    model: _Model,
    output: Path,
    before_finish: Callable[[], None] | None = None,
    *,
    plots: bool = False,
) -> Path:
    output.mkdir(parents=True)
    trainer = SimpleNamespace(
        args=SimpleNamespace(
            project="runs", name="ddp-run", profile=False, secret=output.name, imgsz=98
        ),
        save_dir=output,
        epoch=0,
        tloss=object(),
        lr={"lr/pg0": 0.01},
        epoch_time=2.5,
        metrics={"metrics/mAP50(B)": 0.75},
        label_loss_items=lambda _loss, prefix: {f"{prefix}/box_loss": 1.25},
    )
    _invoke(model, "on_pretrain_routine_start", trainer)
    trainer.args.imgsz = 128
    _invoke(model, "on_train_epoch_end", trainer)
    validator = SimpleNamespace(save_dir=output / "validation")
    validator.save_dir.mkdir()
    preview = validator.save_dir / "val_batch0_labels.jpg"
    preview.write_bytes(b"original-preview")
    _invoke(model, "on_val_end", validator)
    preview.write_bytes(b"overwritten-preview")
    _invoke(model, "on_fit_epoch_end", trainer)
    if before_finish is not None:
        before_finish()

    best = output / "weights" / "best.pt"
    best.parent.mkdir()
    best.write_bytes(b"checkpoint")
    trainer.best = best
    trainer.plots = {}
    trainer.validator = SimpleNamespace(
        plots={}, metrics=SimpleNamespace(results_dict={"metrics/mAP50(B)": 0.8})
    )
    if plots:
        figure = plt.figure()
        for owner, name in (
            (trainer, "results.png"),
            (trainer, "BoxPR_curve.png"),
            (trainer.validator, "confusion_matrix.png"),
            (trainer.validator, "MaskPR_curve.png"),
        ):
            path = output / name
            figure.savefig(path)
            owner.plots[path] = {}
        plt.close(figure)
    _invoke(model, "on_train_end", trainer)
    return best


def _invoke(model: _Model, event: str, source: Any) -> None:
    callback = cast(Callable[[Any], None], model.callbacks[event][-1])
    callback(source)


def test_ddp_rank_zero_events_replay_installed_callbacks_in_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import clearml
    from ultralytics.utils import torch_utils

    task = _Task()
    _Task.current = task
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setattr(
        torch_utils,
        "model_info_for_loggers",
        lambda _trainer: {
            "model/parameters": 123,
            "model/GFLOPs": 4.5,
            "model/speed_PyTorch(ms)": 6.75,
        },
    )
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    original = {event: callbacks.copy() for event, callbacks in model.callbacks.items()}

    with native_runtime(), native_ddp_relay(task, model) as relay:
        monkeypatch.setenv(OWNER_PID_ENV, "worker-owner-pid")
        monkeypatch.setattr("ultralytics.utils.RANK", 0)
        best = _capture_events(model, tmp_path / "train", plots=True)
        monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
        parent = SimpleNamespace(ddp=True, args=SimpleNamespace())
        model.trainer = parent
        relay.replay(parent)

    assert task.parameters["General/name"] == "ddp-run"
    assert task.parameters["General/secret"] == "<redacted>"
    assert parent.args.imgsz == 128
    assert ("train", "train/box_loss", 1.25, 0) in task.logger.scalars
    assert ("lr", "lr/pg0", 0.01, 0) in task.logger.scalars
    assert ("Epoch Time", "Epoch Time", 2.5, 0) in task.logger.scalars
    assert ("metrics", "metrics/mAP50(B)", 0.75, 0) in task.logger.scalars
    assert task.logger.values == {
        "model/parameters": 123,
        "model/GFLOPs": 4.5,
        "model/speed_PyTorch(ms)": 6.75,
        "metrics/mAP50(B)": 0.8,
    }
    assert task.output_models == [(str(best), "ddp-run", False)]
    assert task.logger.images == [("val_batch0_labels.jpg", b"original-preview")]
    assert task.logger.figures == ["results", "confusion_matrix"]
    assert model.callbacks == original


def test_ddp_replay_refuses_incomplete_events_before_best_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    task = _Task()
    _Task.current = task
    import clearml

    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()

    with native_runtime(), native_ddp_relay(task, model) as relay:
        monkeypatch.setenv(OWNER_PID_ENV, "worker-owner-pid")
        monkeypatch.setattr("ultralytics.utils.RANK", 0)
        trainer = SimpleNamespace(args=SimpleNamespace(project="runs", name="ddp-run"))
        _invoke(model, "on_pretrain_routine_start", trainer)
        monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
        parent = SimpleNamespace(ddp=True, args=SimpleNamespace())
        model.trainer = parent
        with pytest.raises(RuntimeError, match="incomplete"):
            relay.replay(parent)

    assert task.parameters["General/name"] == "ddp-run"
    assert task.logger.scalars == []
    assert task.output_models == []


def test_single_process_replay_is_noop_and_does_not_duplicate_native_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _Task()
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    parent = SimpleNamespace(ddp=False, args=SimpleNamespace())
    model.trainer = parent

    with native_ddp_relay(task, model) as relay:
        _invoke(
            model,
            "on_pretrain_routine_start",
            SimpleNamespace(args=SimpleNamespace(name="single-process")),
        )
        relay.replay(parent)

    assert task.parameters == {}
    assert task.logger.scalars == []
    assert task.output_models == []


def test_ddp_reports_epoch_before_replay_with_invocation_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Waiting until replay or losing the owner ContextVar hides live epoch progress."""
    from contextvars import ContextVar
    from threading import Event

    import clearml
    from ultralytics.utils import torch_utils

    task = _Task()
    _Task.current = task
    owner: ContextVar[Any] = ContextVar("test_ddp_owner", default=None)
    token = owner.set(task)
    reported = Event()
    original_report = task.logger.report_scalar

    def report(title: str, series: str, value: float, iteration: int) -> None:
        assert owner.get() is task
        original_report(title, series, value, iteration)
        reported.set()

    monkeypatch.setattr(task.logger, "report_scalar", report)
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", owner.get)
    monkeypatch.setattr("clearml_yolo.native_ddp._worker_rank_zero", lambda: True)
    monkeypatch.setattr(torch_utils, "model_info_for_loggers", lambda _trainer: {})
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    parent = SimpleNamespace(ddp=True, args=SimpleNamespace())
    model.trainer = parent

    def check_live_progress() -> None:
        assert reported.wait(3), "Epoch scalars were withheld until training finished"
        assert task.output_models == []

    try:
        with native_runtime(), native_ddp_relay(task, model) as relay:
            best = _capture_events(model, tmp_path / "train", before_finish=check_live_progress)
            relay.replay(parent)
        assert parent.best == best
        assert task.logger.scalars.count(("train", "train/box_loss", 1.25, 0)) == 1
        assert len(task.output_models) == 1
    finally:
        owner.reset(token)


def test_ddp_final_replay_cannot_publish_best_twice(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import clearml
    from ultralytics.utils import torch_utils

    task = _Task()
    _Task.current = task
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setattr("clearml_yolo.native_ddp._worker_rank_zero", lambda: True)
    monkeypatch.setattr(torch_utils, "model_info_for_loggers", lambda _trainer: {})
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    parent = SimpleNamespace(ddp=True, args=SimpleNamespace())
    model.trainer = parent
    with native_runtime(), native_ddp_relay(task, model) as relay:
        _capture_events(model, tmp_path / "train")
        relay.replay(parent)
        with pytest.raises(RuntimeError, match="already"):
            relay.replay(parent)
    assert len(task.output_models) == 1


def test_ddp_partial_record_waits_for_newline_and_interruption_stops_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json
    from threading import Event
    from threading import enumerate as enumerate_threads

    import clearml

    task = _Task()
    _Task.current = task
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    reported = Event()
    original_report = task.logger.report_scalar

    def report(title: str, series: str, value: float, iteration: int) -> None:
        original_report(title, series, value, iteration)
        reported.set()

    monkeypatch.setattr(task.logger, "report_scalar", report)
    model = _Model()
    model.trainer = SimpleNamespace(ddp=True)
    before = set(enumerate_threads())
    with (  # noqa: PT012 - test interruption and context cleanup together
        pytest.raises(KeyboardInterrupt),
        native_runtime(),
        native_ddp_relay(task, model) as relay,
    ):
        directory = relay._directory
        journal = directory / "events.jsonl"
        pretrain = {"event": "on_pretrain_routine_start", "args": {"name": "partial"}}
        epoch = {
            "event": "on_train_epoch_end",
            "epoch": 2,
            "losses": {"train/box_loss": 0.5},
            "lr": {},
            "save_dir": str(directory),
        }
        journal.write_bytes((json.dumps(pretrain) + "\n" + json.dumps(epoch)).encode())
        assert not reported.wait(0.6), "An unterminated record was consumed"
        with journal.open("ab") as stream:
            stream.write(b"\n")
        assert reported.wait(3), "Completed record was not consumed live"
        raise KeyboardInterrupt
    assert task.logger.scalars == [("train", "train/box_loss", 0.5, 2)]
    assert task.output_models == []
    assert not directory.exists()
    assert not any(
        thread.name == "cy-native-ddp-relay" for thread in set(enumerate_threads()) - before
    )


def test_ddp_live_callback_failure_reaches_caller_and_stops_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from threading import Event

    import clearml
    from ultralytics.utils import torch_utils

    task = _Task()
    _Task.current = task
    failed = Event()

    def fail_scalar(title: str, series: str, value: float, iteration: int) -> None:
        failed.set()
        raise OSError("scalar upload failed")

    monkeypatch.setattr(task.logger, "report_scalar", fail_scalar)
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setattr("clearml_yolo.native_ddp._worker_rank_zero", lambda: True)
    monkeypatch.setattr(torch_utils, "model_info_for_loggers", lambda _trainer: {})
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    model.trainer = SimpleNamespace(ddp=True, args=SimpleNamespace())
    with (  # noqa: PT012 - expected failure includes relay context cleanup
        pytest.raises(OSError, match="scalar upload failed"),
        native_runtime(),
        native_ddp_relay(task, model) as relay,
    ):
        directory = relay._directory
        _capture_events(model, tmp_path / "train")
        assert failed.wait(3)
        relay.replay(model.trainer)
    assert not directory.exists()
    assert task.output_models == []


@pytest.mark.parametrize("tail", [b'{"event":broken}\n', b'{"event":"on_train_end"}'])
def test_ddp_corrupt_or_unterminated_journal_never_publishes_best(
    monkeypatch: pytest.MonkeyPatch, tail: bytes
) -> None:
    import clearml

    task = _Task()
    _Task.current = task
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    model.trainer = SimpleNamespace(ddp=True, args=SimpleNamespace())
    with (  # noqa: PT012 - expected failure includes relay context cleanup
        pytest.raises(RuntimeError, match=r"incomplete|corrupt"),
        native_runtime(),
        native_ddp_relay(task, model) as relay,
    ):
        journal = relay._directory / "events.jsonl"
        journal.write_bytes(b'{"event":"on_pretrain_routine_start","args":{"name":"bad"}}\n' + tail)
        relay.replay(model.trainer)
    assert task.output_models == []


@pytest.mark.parametrize(
    "missing", ["args", "save_dir", "trainer_plots", "validator_plots", "results"]
)
def test_ddp_incomplete_final_state_fails_before_best_upload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing: str
) -> None:
    import json

    import clearml
    from ultralytics.utils import torch_utils

    task = _Task()
    _Task.current = task
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setattr("clearml_yolo.native_ddp._worker_rank_zero", lambda: True)
    monkeypatch.setattr(torch_utils, "model_info_for_loggers", lambda _trainer: {})
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    with (  # noqa: PT012 - expected failure includes relay context cleanup
        pytest.raises((RuntimeError, TypeError), match="incomplete"),
        native_runtime(),
        native_ddp_relay(task, model) as relay,
    ):
        _capture_events(model, tmp_path / "train")
        journal = relay._directory / "events.jsonl"
        records = [json.loads(line) for line in journal.read_text().splitlines()]
        del records[-1][missing]
        journal.write_text("".join(json.dumps(record) + "\n" for record in records))
        model.trainer = SimpleNamespace(ddp=True, args=SimpleNamespace())
        relay.replay(model.trainer)
    assert task.output_models == []


@pytest.mark.parametrize(
    ("event", "field", "replacement"),
    [
        ("on_train_epoch_end", "losses", None),
        ("on_train_epoch_end", "epoch", "wrong"),
        ("on_train_epoch_end", "lr", []),
        ("on_train_epoch_end", "save_dir", None),
        ("on_fit_epoch_end", "metrics", []),
        ("on_fit_epoch_end", "epoch_time", "wrong"),
        ("on_fit_epoch_end", "model_info", None),
        ("on_val_end", "save_dir", None),
    ],
)
def test_ddp_malformed_epoch_state_fails_before_best_upload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, event: str, field: str, replacement: Any
) -> None:
    import json

    import clearml
    from ultralytics.utils import torch_utils

    task = _Task()
    _Task.current = task
    monkeypatch.setattr(clearml, "Task", _Task)
    monkeypatch.setattr("clearml_yolo.clearml_session.active_task", lambda: task)
    monkeypatch.setattr("clearml_yolo.native_ddp._worker_rank_zero", lambda: True)
    monkeypatch.setattr(torch_utils, "model_info_for_loggers", lambda _trainer: {})
    monkeypatch.setenv(OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setenv(OWNER_TASK_ENV, task.id)
    model = _Model()
    with (  # noqa: PT012 - expected failure includes relay context cleanup
        pytest.raises((RuntimeError, TypeError), match=r"incomplete|invalid"),
        native_runtime(),
        native_ddp_relay(task, model) as relay,
    ):
        _capture_events(model, tmp_path / "train")
        journal = relay._directory / "events.jsonl"
        records = [json.loads(line) for line in journal.read_text().splitlines()]
        record = next(record for record in records if record["event"] == event)
        if replacement is None:
            del record[field]
        else:
            record[field] = replacement
        journal.write_text("".join(json.dumps(record) + "\n" for record in records))
        model.trainer = SimpleNamespace(ddp=True, args=SimpleNamespace())
        relay.replay(model.trainer)
    assert task.output_models == []
