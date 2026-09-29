"""Owner-only replay of native ClearML events produced by DDP rank zero."""

import os
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from clearml_yolo.native_ddp import native_ddp_relay
from clearml_yolo.native_runtime import OWNER_PID_ENV, OWNER_TASK_ENV, native_runtime


class _Logger:
    def __init__(self) -> None:
        self.scalars: list[tuple[str, str, float, int]] = []
        self.values: dict[str, float] = {}
        self.images: list[tuple[str, bytes]] = []

    def report_scalar(self, title: str, series: str, value: float, iteration: int) -> None:
        self.scalars.append((title, series, value, iteration))

    def report_single_value(self, name: str, value: float) -> None:
        self.values[name] = value

    def report_image(self, **kwargs: Any) -> None:
        path = Path(kwargs["local_path"])
        self.images.append((path.name, path.read_bytes()))

    def report_matplotlib_figure(self, **_kwargs: Any) -> None:
        return None


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


def _capture_events(model: _Model, output: Path) -> Path:
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

    best = output / "weights" / "best.pt"
    best.parent.mkdir()
    best.write_bytes(b"checkpoint")
    trainer.best = best
    trainer.plots = {}
    trainer.validator = SimpleNamespace(
        plots={}, metrics=SimpleNamespace(results_dict={"metrics/mAP50(B)": 0.8})
    )
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
        best = _capture_events(model, tmp_path / "train")
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
    assert model.callbacks == original


def test_ddp_replay_refuses_incomplete_events_before_native_publication(
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

    assert task.parameters == {}
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
