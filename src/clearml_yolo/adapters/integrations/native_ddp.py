"""Relay native ClearML events from DDP rank zero to the invocation owner."""

import json
import os
import shutil
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import copy_context
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
from types import SimpleNamespace, TracebackType
from typing import Any, Self, cast
from uuid import uuid4

from clearml_yolo.adapters.integrations.native_runtime import OWNER_PID_ENV, OWNER_TASK_ENV
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import temporary_root

_EVENTS = (
    "on_pretrain_routine_start",
    "on_train_epoch_end",
    "on_fit_epoch_end",
    "on_val_end",
    "on_train_end",
)


_RECORD_FIELDS: dict[str, dict[str, type[Any] | tuple[type[Any], ...]]] = {
    "on_pretrain_routine_start": {"args": dict},
    "on_train_epoch_end": {"epoch": int, "losses": dict, "lr": dict, "save_dir": str},
    "on_fit_epoch_end": {"epoch": int, "epoch_time": (int, float), "metrics": dict},
    "on_val_end": {"save_dir": str},
    "on_train_end": {
        "args": dict,
        "save_dir": str,
        "best": str,
        "trainer_plots": list,
        "validator_plots": list,
        "results": dict,
    },
}


def _validate_record(record: dict[str, Any]) -> None:
    event = str(record["event"])
    fields = _RECORD_FIELDS[event]
    if event == "on_fit_epoch_end" and record.get("epoch") == 0:
        fields = fields | {"model_info": dict}
    for name, expected in fields.items():
        if not isinstance(record.get(name), expected):
            raise TypeError(f"Native DDP event output is incomplete: invalid {event} {name}")


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
        self._stop = Event()
        self._thread: Thread | None = None
        self._failure: BaseException | None = None
        self._offset = 0
        self._pending = b""
        self._consumed: list[dict[str, Any]] = []
        self._args: SimpleNamespace | None = None

    def __enter__(self) -> Self:
        try:
            with trace_operation("ddp.relay.start"):
                for event in _EVENTS:
                    callback = partial(_capture_event, event=event, journal=str(self._directory))
                    self._model.add_callback(event, callback)
                    self._registered.append((event, callback))
                # Bind the invocation context when creating the thread, including its trace task ID.
                context = copy_context()
                self._thread = Thread(
                    target=context.run,
                    args=(self._consume_live,),
                    name="cy-native-ddp-relay",
                    daemon=True,
                )
                self._thread.start()
        except BaseException:
            # Roll back resources even if the startup trace terminal sink interrupts.
            try:
                self._stop_consumer()
            finally:
                self._remove_callbacks()
            raise
        else:
            return self

    def _consume_live(self) -> None:
        # Callback exceptions belong to the invocation boundary, never to a detached
        # thread's stderr. Training may finish, but cannot finalize successfully.
        try:
            with trace_operation("ddp.consumer", context={"stage": "train"}):
                while not self._stop.wait(0.25):
                    trainer = getattr(self._model, "trainer", None)
                    if getattr(trainer, "ddp", False):
                        self._consume()
        except BaseException as error:  # noqa: BLE001 - relay all failures to the owner boundary
            self._failure = error

    @trace_operation("ddp.relay.join", cleanup=True)
    def _stop_consumer(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.ident is not None:
            self._thread.join()

    def _callbacks(self) -> dict[str, Any]:
        from ultralytics.utils.callbacks import clearml as integration

        callbacks: dict[str, Any] = integration.callbacks
        if set(callbacks) != set(_EVENTS) or not all(
            callable(callbacks[event]) for event in _EVENTS
        ):
            raise RuntimeError("Installed native ClearML callback set changed before DDP replay")
        return callbacks

    def _consume(self) -> None:
        journal = self._directory / "events.jsonl"
        if not journal.is_file():
            return
        self._validate_owner()
        with journal.open("rb") as stream:
            stream.seek(self._offset)
            payload = stream.read()
            self._offset = stream.tell()
        lines = (self._pending + payload).split(b"\n")
        self._pending = lines.pop()
        for line in lines:
            try:
                record = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError("Native DDP event output is incomplete or corrupt") from error
            if not isinstance(record, dict) or record.get("event") not in _EVENTS:
                raise RuntimeError("Native DDP event output contains an invalid event")
            _validate_record(record)
            if self._consumed and self._consumed[-1]["event"] == "on_train_end":
                raise RuntimeError("Native DDP event output continues after training ended")
            if not self._consumed:
                arguments = record.get("args")
                if record["event"] != "on_pretrain_routine_start" or not isinstance(
                    arguments, dict
                ):
                    raise RuntimeError(
                        "Native DDP event output is incomplete: effective arguments are missing"
                    )
                self._args = SimpleNamespace(**arguments)
            elif record["event"] == "on_pretrain_routine_start":
                raise RuntimeError("Native DDP event output contains duplicate pretrain events")
            self._consumed.append(record)
            # Keep native best publication behind full-journal/checkpoint validation.
            if record["event"] != "on_train_end":
                self._dispatch(record)

    def _dispatch(self, record: dict[str, Any]) -> None:
        if self._args is None:
            raise RuntimeError(
                "Native DDP event output is incomplete: effective arguments are missing"
            )
        view = _ReplayTrainer(record, self._args)
        with (
            trace_operation(
                "ddp.callback", context={"event": str(record["event"]), "stage": "train"}
            ),
            _recorded_model_info(record.get("model_info")),
        ):
            self._callbacks()[str(record["event"])](view)

    def _remove_callbacks(self) -> None:
        for event, callback in self._registered:
            callbacks = self._model.callbacks.get(event, [])
            self._model.callbacks[event] = [item for item in callbacks if item is not callback]
        self._registered.clear()

    @trace_operation("ddp.relay.cleanup", cleanup=True)
    def __exit__(
        self,
        error_type: type[BaseException] | None,
        _error: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        try:
            self._stop_consumer()
        finally:
            self._remove_callbacks()
        if error_type is None and self._failure is not None:
            raise self._failure
        trainer = getattr(self._model, "trainer", None)
        if error_type is None and getattr(trainer, "ddp", False) and not self._attempted:
            raise RuntimeError("Native DDP events were not replayed in the invocation owner")

    def _records(self) -> list[dict[str, Any]]:
        records = self._consumed
        if not records or self._pending:
            raise RuntimeError("Native DDP event output is incomplete: rank-zero journal")
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
        for name in ("trainer_plots", "validator_plots"):
            for path in final[name]:
                if not isinstance(path, str) or not Path(path).is_file():
                    raise RuntimeError(
                        "Native DDP event output is incomplete: final plot is missing"
                    )
        best = Path(str(final.get("best", "")))
        if not best.is_file() or best.stat().st_size == 0:
            raise RuntimeError("Native DDP event output is incomplete: best checkpoint is missing")
        return records

    def _validate_owner(self) -> None:
        from clearml_yolo.adapters.clearml.session import active_task

        if os.environ.get(OWNER_PID_ENV) != str(os.getpid()):
            raise RuntimeError("Native DDP callbacks may only be replayed by the invocation owner")
        if self._task is not active_task():
            raise RuntimeError("Native DDP callbacks require the invocation-owned task")
        task = self._task
        if task is None:
            raise RuntimeError("Native DDP callbacks require the invocation-owned task")
        if os.environ.get(OWNER_TASK_ENV) != str(task.id):
            raise RuntimeError("Native DDP callback task identity changed")

    @trace_operation("ddp.relay.replay")
    def replay(self, trainer: Any) -> None:
        """Replay complete DDP rank-zero events and apply effective worker state to the parent."""
        if self._attempted:
            raise RuntimeError("Native DDP final replay was already attempted")
        self._attempted = True
        self._stop_consumer()
        if not getattr(trainer, "ddp", False):
            return
        if self._failure is not None:
            raise self._failure
        self._validate_owner()
        self._consume()
        records = self._records()
        final_args = records[-1].get("args")
        if not isinstance(final_args, dict):
            raise TypeError(
                "Native DDP event output is incomplete: effective arguments are missing"
            )
        self._args = SimpleNamespace(**final_args)
        self._dispatch(records[-1])
        for name, value in final_args.items():
            setattr(trainer.args, name, value)
        trainer.best = Path(str(records[-1]["best"]))
        trainer.save_dir = Path(str(records[-1]["save_dir"]))


@contextmanager
def native_ddp_relay(task: Any, model: Any) -> Iterator[NativeDDPRelay]:
    """Yield replay storage that callers keep through native model finalization and flush."""
    with (
        TemporaryDirectory(prefix="cy-native-ddp-", dir=temporary_root()) as directory,
        NativeDDPRelay(task, model, directory) as relay,
    ):
        yield relay
