"""Scope Ultralytics' native ClearML callbacks to the invocation owner."""

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

OWNER_PID_ENV = "CY_CLEARML_OWNER_PID"
OWNER_TASK_ENV = "CY_CLEARML_OWNER_TASK_ID"


def _is_worker() -> bool:
    owner_pid = os.environ.get(OWNER_PID_ENV)
    if owner_pid and owner_pid != str(os.getpid()):
        return True
    local_rank = os.environ.get("LOCAL_RANK")
    return local_rank is not None and local_rank != "-1"


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
        from clearml_yolo.clearml_session import active_task, sanitize_configuration

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
        original_connect = current.connect
        integration.LOGGER = captured

        def connect(values: Any, *args: Any, **kwargs: Any) -> Any:
            # Native General is provenance only (remote overrides are disabled by
            # the installed callback); redact storage without altering trainer args.
            return original_connect(sanitize_configuration(values), *args, **kwargs)

        current.connect = connect
        try:
            callback(trainer)
        finally:
            current.connect = original_connect
            integration.LOGGER = original_logger
        if captured.messages:
            raise RuntimeError("Native ClearML pretrain callback reported a registration failure")
        parameters = current.get_parameters()
        if not isinstance(parameters, dict) or not any(
            str(name).startswith("General/") for name in parameters
        ):
            raise RuntimeError("Native ClearML callback did not register General parameters")

    return checked


def _write_inherited_settings(settings: Any, get_user_config_dir: Any) -> None:
    inherited = dict(settings)
    inherited.update(clearml=False, sync=False, api_key="", openai_api_key="")
    settings_path = Path(get_user_config_dir()) / "settings.json"
    settings_path.write_text(json.dumps(inherited), encoding="utf-8")


def _enable_owner(integration: Any, settings: Any) -> None:
    import clearml
    from clearml import Task

    dict.__setitem__(settings, "clearml", True)
    integration.clearml = clearml
    integration.Task = Task
    callbacks = _installed_callbacks(integration)
    callbacks["on_pretrain_routine_start"] = _checked_pretrain(
        integration, callbacks["on_pretrain_routine_start"]
    )
    integration.callbacks = callbacks


def _restore_attribute(target: Any, name: str, existed: bool, value: Any) -> None:
    if existed:
        setattr(target, name, value)
    elif hasattr(target, name):
        delattr(target, name)


@contextmanager
def native_runtime() -> Iterator[None]:
    """Enable native callbacks only for the owner and restore every modified global."""
    previous = os.environ.get("YOLO_CONFIG_DIR")
    from ultralytics.utils import SETTINGS, get_user_config_dir
    from ultralytics.utils.callbacks import clearml as integration

    original_setting = SETTINGS["clearml"]
    original_callbacks = integration.callbacks
    had_task = hasattr(integration, "Task")
    original_task = getattr(integration, "Task", None)
    had_clearml = hasattr(integration, "clearml")
    original_clearml = getattr(integration, "clearml", None)
    with TemporaryDirectory(prefix="cy-native-") as directory:
        os.environ["YOLO_CONFIG_DIR"] = directory
        try:
            _write_inherited_settings(SETTINGS, get_user_config_dir)
            if _is_worker():
                dict.__setitem__(SETTINGS, "clearml", False)
                integration.callbacks = {}
            else:
                _enable_owner(integration, SETTINGS)
            yield
        finally:
            # Bypass SettingsManager persistence: only process memory is restored.
            dict.__setitem__(SETTINGS, "clearml", original_setting)
            integration.callbacks = original_callbacks
            _restore_attribute(integration, "Task", had_task, original_task)
            _restore_attribute(integration, "clearml", had_clearml, original_clearml)
            if previous is None:
                os.environ.pop("YOLO_CONFIG_DIR", None)
            else:
                os.environ["YOLO_CONFIG_DIR"] = previous
