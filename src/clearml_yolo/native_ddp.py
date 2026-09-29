"""Relay native ClearML events from DDP rank zero to the invocation owner."""

import json
import os
import shutil
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace, TracebackType
from typing import Any, Self, cast
from uuid import uuid4

from clearml_yolo.native_runtime import OWNER_PID_ENV, OWNER_TASK_ENV

_EVENTS = (
    "on_pretrain_routine_start",
    "on_train_epoch_end",
    "on_fit_epoch_end",
    "on_val_end",
    "on_train_end",
)


def _plain(value: Any) -> Any:  # noqa: PLR0911 - explicit recursive JSON boundary
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    item = getattr(value, "item", None)
    if callable(item):
        scalar = item()
        if scalar is not value:
            return _plain(scalar)
    enum_value = getattr(value, "value", value)
    if enum_value is not value:
        return _plain(enum_value)
    return str(value)


def _worker_rank_zero() -> bool:
    owner_pid = os.environ.get(OWNER_PID_ENV)
    if not owner_pid or owner_pid == str(os.getpid()):
        return False
    from ultralytics import utils

    return int(utils.RANK) == 0


def _copy_matches(source: Path, target: Path, pattern: str) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob(pattern)):
        if path.is_file():
            shutil.copy2(path, target / path.name)


def _copy_plots(paths: list[Path], target: Path) -> list[str]:
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Native DDP plot is missing: {path}")
        destination = target / path.name
        shutil.copy2(path, destination)
        copied.append(str(destination))
    return copied


def _event_record(event: str, source: Any, directory: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"event": event}
    if event == "on_pretrain_routine_start":
        record["args"] = _plain(vars(source.args))
    elif event == "on_train_epoch_end":
        record.update(
            epoch=int(source.epoch),
            losses=_plain(source.label_loss_items(source.tloss, prefix="train")),
            lr=_plain(source.lr),
        )
        samples = directory / "train_samples"
        if source.epoch == 1:
            _copy_matches(Path(source.save_dir), samples, "train_batch*.jpg")
        record["save_dir"] = str(samples)
    elif event == "on_fit_epoch_end":
        record.update(
            epoch=int(source.epoch),
            epoch_time=_plain(source.epoch_time),
            metrics=_plain(source.metrics),
        )
        if source.epoch == 0:
            from ultralytics.utils.torch_utils import model_info_for_loggers

            get_model_info = cast(Callable[[Any], dict[str, Any]], model_info_for_loggers)
            record["model_info"] = _plain(get_model_info(source))
    elif event == "on_val_end":
        validation = directory / "validation"
        _copy_matches(Path(source.save_dir), validation, "val*.jpg")
        record["save_dir"] = str(validation)
    elif event == "on_train_end":
        trainer_plots = [Path(path) for path in source.plots]
        validator_plots = [Path(path) for path in source.validator.plots]
        record.update(
            args=_plain(vars(source.args)),
            save_dir=str(source.save_dir),
            best=str(source.best),
            trainer_plots=_copy_plots(trainer_plots, directory / "trainer_plots"),
            validator_plots=_copy_plots(validator_plots, directory / "validator_plots"),
            results=_plain(source.validator.metrics.results_dict),
        )
    else:
        raise RuntimeError(f"Unsupported native DDP event {event!r}")
    return record


def _capture_event(source: Any, *, event: str, journal: str) -> None:
    if not _worker_rank_zero():
        return
    root = Path(journal)
    event_directory = root / "files" / uuid4().hex
    record = _event_record(event, source, event_directory)
    payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with (root / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(payload + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class _ReplayTrainer:
    def __init__(self, record: dict[str, Any], args: SimpleNamespace) -> None:
        self.args = args
        self.epoch = int(record.get("epoch", 0))
        self.epoch_time = record.get("epoch_time")
        self.metrics = record.get("metrics", {})
        self.lr = record.get("lr", {})
        self.tloss = record.get("losses", {})
        self.save_dir = Path(record.get("save_dir", "."))
        self.best = Path(record.get("best", ""))
        self.plots = {Path(path): None for path in record.get("trainer_plots", [])}
        results = record.get("results", {})
        self.validator = SimpleNamespace(
            plots={Path(path): None for path in record.get("validator_plots", [])},
            metrics=SimpleNamespace(results_dict=results),
        )

    def label_loss_items(self, _losses: Any, prefix: str = "train") -> dict[str, Any]:
        if prefix != "train":
            raise RuntimeError(f"Native DDP replay received unexpected loss prefix {prefix!r}")
        return dict(self.tloss)


@contextmanager
def _recorded_model_info(values: dict[str, Any] | None) -> Iterator[None]:
    if values is None:
        yield
        return
    from ultralytics.utils import torch_utils

    original = torch_utils.model_info_for_loggers
    torch_utils.model_info_for_loggers = lambda _trainer: dict(values)
    try:
        yield
    finally:
        torch_utils.model_info_for_loggers = original


class NativeDDPRelay:
    """Capture worker callback state and replay it through installed callbacks in the owner."""

    def __init__(self, task: Any, model: Any, directory: str) -> None:
        self._task = task
        self._model = model
        self._directory = Path(directory)
        self._registered: list[tuple[str, Any]] = []
        self._attempted = False

    def __enter__(self) -> Self:
        for event in _EVENTS:
            callback = partial(_capture_event, event=event, journal=str(self._directory))
            self._model.add_callback(event, callback)
            self._registered.append((event, callback))
        return self

    def _remove_callbacks(self) -> None:
        for event, callback in self._registered:
            callbacks = self._model.callbacks.get(event, [])
            self._model.callbacks[event] = [item for item in callbacks if item is not callback]
        self._registered.clear()

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        _error: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self._remove_callbacks()
        trainer = getattr(self._model, "trainer", None)
        if error_type is None and getattr(trainer, "ddp", False) and not self._attempted:
            raise RuntimeError("Native DDP events were not replayed in the invocation owner")

    def _records(self) -> list[dict[str, Any]]:
        journal = self._directory / "events.jsonl"
        if not journal.is_file() or journal.stat().st_size == 0:
            raise RuntimeError("Native DDP event output is incomplete: no rank-zero journal")
        try:
            lines = journal.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines]
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("Native DDP event output is incomplete or corrupt") from error
        counts = {
            event: sum(record.get("event") == event for record in records) for event in _EVENTS
        }
        if (
            counts["on_pretrain_routine_start"] != 1
            or counts["on_train_epoch_end"] < 1
            or counts["on_fit_epoch_end"] < 1
            or counts["on_val_end"] < 1
            or counts["on_train_end"] != 1
            or records[0].get("event") != "on_pretrain_routine_start"
            or records[-1].get("event") != "on_train_end"
        ):
            raise RuntimeError(f"Native DDP event output is incomplete: {counts}")
        final = records[-1]
        best = Path(str(final.get("best", "")))
        if not best.is_file() or best.stat().st_size == 0:
            raise RuntimeError("Native DDP event output is incomplete: best checkpoint is missing")
        return records

    def _validate_owner(self) -> None:
        from clearml_yolo.clearml_session import active_task

        if os.environ.get(OWNER_PID_ENV) != str(os.getpid()):
            raise RuntimeError("Native DDP callbacks may only be replayed by the invocation owner")
        if self._task is not active_task():
            raise RuntimeError("Native DDP callbacks require the invocation-owned task")
        task = self._task
        if task is None:
            raise RuntimeError("Native DDP callbacks require the invocation-owned task")
        if os.environ.get(OWNER_TASK_ENV) != str(task.id):
            raise RuntimeError("Native DDP callback task identity changed")

    def replay(self, trainer: Any) -> None:
        """Replay complete DDP rank-zero events and apply effective worker state to the parent."""
        self._attempted = True
        if not getattr(trainer, "ddp", False):
            return
        self._validate_owner()
        records = self._records()
        from ultralytics.utils.callbacks import clearml as integration

        callbacks = integration.callbacks
        complete = set(callbacks) == set(_EVENTS) and all(
            callable(callbacks[event]) for event in _EVENTS
        )
        if not complete:
            raise RuntimeError("Installed native ClearML callback set changed before DDP replay")
        pretrain_args = records[0].get("args")
        final_args = records[-1].get("args")
        if not isinstance(pretrain_args, dict) or not isinstance(final_args, dict):
            raise TypeError(
                "Native DDP event output is incomplete: effective arguments are missing"
            )
        args = SimpleNamespace(**pretrain_args)
        for record in records:
            event = str(record["event"])
            view = _ReplayTrainer(record, args)
            with _recorded_model_info(record.get("model_info")):
                callbacks[event](view)
        for name, value in final_args.items():
            setattr(trainer.args, name, value)
        trainer.best = Path(str(records[-1]["best"]))
        trainer.save_dir = Path(str(records[-1]["save_dir"]))


@contextmanager
def native_ddp_relay(task: Any, model: Any) -> Iterator[NativeDDPRelay]:
    """Yield replay storage that callers keep through native model finalization and flush."""
    with (
        TemporaryDirectory(prefix="cy-native-ddp-") as directory,
        NativeDDPRelay(task, model, directory) as relay,
    ):
        yield relay
