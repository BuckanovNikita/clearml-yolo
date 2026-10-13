"""Scope Ultralytics' native ClearML callbacks to the invocation owner."""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import Any, cast

from clearml_yolo.adapters.observability.capture import append_scalar
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
from clearml_yolo.adapters.storage.filesystem import initialize_filesystem

OWNER_PID_ENV = "CY_CLEARML_OWNER_PID"
OWNER_TASK_ENV = "CY_CLEARML_OWNER_TASK_ID"
_SCALAR_CALLBACK: ContextVar[bool] = ContextVar("native_scalar_callback", default=False)
_REPLAYED_SCALARS: ContextVar[bool] = ContextVar("native_replayed_scalars", default=False)
_SANITIZED_CALLBACK: ContextVar[bool] = ContextVar("native_sanitized_callback", default=False)


@trace_operation("gpu.memory.release", cleanup=True)
def release_training_memory() -> None:
    """Drop unreachable trainers and unused allocations before releasing their devices."""
    import gc

    with trace_operation("native.import.torch", cleanup=True):
        import torch

    with trace_operation("gpu.memory.collect", cleanup=True):
        gc.collect()
    # Torch exposes this runtime predicate without a typed signature.
    initialized = cast(Callable[[], bool], torch.cuda.is_initialized)
    if initialized():
        with trace_operation("gpu.memory.synchronize", cleanup=True):
            torch.cuda.synchronize()
        with trace_operation("gpu.memory.empty_cache", cleanup=True):
            torch.cuda.empty_cache()


def _is_worker() -> bool:
    owner_pid = os.environ.get(OWNER_PID_ENV)
    if owner_pid and os.environ.get(OWNER_TASK_ENV) and owner_pid != str(os.getpid()):
        return True
    local_rank = os.environ.get("LOCAL_RANK")
    if (
        local_rank is not None
        and local_rank != "-1"
        and not (owner_pid and os.environ.get(OWNER_TASK_ENV))
    ):
        raise ValueError(
            "Top-level LOCAL_RANK launches are unsupported; invoke the cy command directly"
        )
    return False


def validate_owner_environment() -> None:
    """Reject rank-bearing external launches before GPU waiting or native startup."""
    _is_worker()


def _installed_callbacks(integration: Any) -> dict[str, Any]:
    callbacks = {
        name: callback
        for name, callback in vars(integration).items()
        if name.startswith("on_") and callable(callback)
    }
    if not callbacks or "on_pretrain_routine_start" not in callbacks:
        raise RuntimeError("Ultralytics ClearML integration has no usable callback set")
    return callbacks


class _WarningCapture:
    def __init__(self, logger: Any) -> None:
        self.logger = logger
        self.messages: list[str] = []

    def warning(self, message: Any, *args: Any, **kwargs: Any) -> Any:
        self.messages.append(str(message))
        return self.logger.warning(message, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.logger, name)


def _checked_pretrain(integration: Any, callback: Any) -> Any:
    def checked(trainer: Any) -> None:
        from clearml_yolo.adapters.clearml.session import active_task

        task = cast(Any, integration.Task.current_task())
        owner_task_id = os.environ.get(OWNER_TASK_ENV)
        if task is None:
            raise RuntimeError("Native ClearML callback did not reuse the invocation-owned task")
        if task is not active_task():
            raise RuntimeError("Native ClearML callback did not reuse the invocation-owned task")
        current = cast(Any, task)
        if not owner_task_id or str(current.id) != owner_task_id:
            raise RuntimeError("Native ClearML callback task identity changed")
        # Ultralytics catches every exception and reports it as this callback's sole
        # warning. Capture that signal while still executing the installed callback.
        original_logger = integration.LOGGER
        captured = _WarningCapture(original_logger)
        integration.LOGGER = captured
        try:
            with _sanitized_callback_scope():
                callback(trainer)
        finally:
            if integration.LOGGER is captured:
                integration.LOGGER = original_logger
        if captured.messages:
            raise RuntimeError("Native ClearML pretrain callback reported a registration failure")
        parameters = current.get_parameters()
        if not isinstance(parameters, dict) or not any(
            str(name).startswith("General/") for name in parameters
        ):
            raise RuntimeError("Native ClearML callback did not register General parameters")

    return checked


def _without_training_pr(callback: Callable[[Any], None]) -> Callable[[Any], None]:
    def publish(trainer: Any) -> None:
        # Native training PR comes from validation. Test PR is published by the
        # project evaluation adapter; retain all other installed callback behavior.
        trainer_plots = trainer.plots
        validator_plots = trainer.validator.plots
        try:
            trainer.plots = {
                path: value
                for path, value in trainer_plots.items()
                if not Path(path).stem.endswith("PR_curve")
            }
            trainer.validator.plots = {
                path: value
                for path, value in validator_plots.items()
                if not Path(path).stem.endswith("PR_curve")
            }
            callback(trainer)
        finally:
            trainer.plots = trainer_plots
            trainer.validator.plots = validator_plots

    return publish


def _enable_owner(integration: Any, settings: Any) -> None:
    import clearml
    from clearml import Task

    dict.__setitem__(settings, "clearml", True)
    integration.clearml = clearml
    integration.Task = _CallbackTasks(Task)
    callbacks = _installed_callbacks(integration)
    callbacks["on_pretrain_routine_start"] = _checked_pretrain(
        integration, callbacks["on_pretrain_routine_start"]
    )
    callbacks["on_train_end"] = _without_training_pr(callbacks["on_train_end"])
    for event in ("on_train_epoch_end", "on_fit_epoch_end"):
        callbacks[event] = _journal_scalars(callbacks[event])
    integration.callbacks = callbacks


class _ScalarLogger:
    """Preserve installed callback images/single values; journal only epoch scalars."""

    def __init__(self, original: Any, *, suppress_scalars: bool = False) -> None:
        self.original = original
        self.suppress_scalars = suppress_scalars

    def report_scalar(self, title: str, series: str, value: float, iteration: int) -> None:
        if self.suppress_scalars:
            return
        if not append_scalar(title, series, float(value), iteration):
            self.original.report_scalar(title, series, value, iteration=iteration)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original, name)


class _CallbackTask:
    """A callback-local SDK view; never replace the real owner's get_logger."""

    def __init__(self, original: Any) -> None:
        self.original = original

    def get_logger(self) -> Any:
        original = self.original.get_logger()
        return (
            _ScalarLogger(original, suppress_scalars=_REPLAYED_SCALARS.get())
            if _SCALAR_CALLBACK.get()
            else original
        )

    def connect(self, values: Any, *args: Any, **kwargs: Any) -> Any:
        from clearml_yolo.adapters.clearml.session import sanitize_configuration

        prepared = sanitize_configuration(values) if _SANITIZED_CALLBACK.get() else values
        return self.original.connect(prepared, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original, name)


class _CallbackTasks:
    """Keep native Task access scoped by ContextVar without mutating SDK objects."""

    def __init__(self, original: Any) -> None:
        self.original = original

    def current_task(self) -> Any:
        task = self.original.current_task()
        scoped = _SCALAR_CALLBACK.get() or _SANITIZED_CALLBACK.get()
        return _CallbackTask(task) if task is not None and scoped else task

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original, name)


@contextmanager
def replayed_scalars(journaled: bool) -> Iterator[None]:
    """Native replay retains previews/single values without duplicating worker scalars."""
    token = _REPLAYED_SCALARS.set(journaled)
    try:
        yield
    finally:
        _REPLAYED_SCALARS.reset(token)


@contextmanager
def _scalar_callback_scope() -> Iterator[None]:
    token = _SCALAR_CALLBACK.set(True)
    try:
        yield
    finally:
        _SCALAR_CALLBACK.reset(token)


@contextmanager
def _sanitized_callback_scope() -> Iterator[None]:
    token = _SANITIZED_CALLBACK.set(True)
    try:
        yield
    finally:
        _SANITIZED_CALLBACK.reset(token)


def _journal_scalars(callback: Callable[[Any], None]) -> Callable[[Any], None]:
    @wraps(callback)
    def publish(trainer: Any) -> None:
        # Refer to an importable helper so native DDP serialization never tries
        # to pickle a ContextVar from this nested callback's globals.
        with _scalar_callback_scope():
            callback(trainer)

    return publish


def _restore_attribute(target: Any, name: str, existed: bool, value: Any) -> None:
    if existed:
        setattr(target, name, value)
    elif hasattr(target, name):
        delattr(target, name)


@contextmanager
def detector_runtime() -> Iterator[None]:
    """Initialize Torch before owner tracking starts package discovery."""
    with runtime_environment():
        initialize_filesystem()
        import torch  # noqa: F401 - finish native initialization before ClearML threads

        yield


@contextmanager
def native_runtime() -> Iterator[None]:
    """Scope in-memory callbacks without changing native storage or user settings."""
    with runtime_environment(), _configured_native_runtime():
        yield


@contextmanager
def _configured_native_runtime() -> Iterator[None]:
    """Enable native callbacks only for the owner and restore every modified global."""
    with trace_operation("native.runtime.import"):
        initialize_filesystem()
        from ultralytics.utils import SETTINGS
        from ultralytics.utils.callbacks import clearml as integration

    original_setting = SETTINGS["clearml"]
    original_callbacks = integration.callbacks
    had_task = hasattr(integration, "Task")
    original_task = getattr(integration, "Task", None)
    had_clearml = hasattr(integration, "clearml")
    original_clearml = getattr(integration, "clearml", None)
    try:
        with trace_operation("native.runtime.setup"):
            if _is_worker():
                dict.__setitem__(SETTINGS, "clearml", False)
                integration.callbacks = {}
            else:
                _enable_owner(integration, SETTINGS)
        yield
    finally:
        with trace_operation("native.runtime.restore", cleanup=True):
            # SettingsManager writes on mutation: bypass persistence for runtime switches.
            dict.__setitem__(SETTINGS, "clearml", original_setting)
            integration.callbacks = original_callbacks
            _restore_attribute(integration, "Task", had_task, original_task)
            _restore_attribute(integration, "clearml", had_clearml, original_clearml)
