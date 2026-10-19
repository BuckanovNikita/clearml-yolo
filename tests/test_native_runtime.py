"""Native ClearML callbacks are scoped to the owner process."""

import os
from inspect import unwrap
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.adapters.integrations.native_runtime import OWNER_TASK_ENV, native_runtime


def test_owner_enables_every_installed_callback_and_restores_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.callbacks import clearml as integration

    installed = {
        "on_pretrain_routine_start": lambda _trainer: None,
        "on_train_epoch_end": lambda _trainer: None,
        "on_fit_epoch_end": lambda _trainer: None,
        "on_val_end": lambda _validator: None,
        "on_train_end": lambda _trainer: None,
    }
    original_callbacks = {"sentinel": lambda _trainer: None}
    original_setting = SETTINGS["clearml"]
    monkeypatch.setattr(integration, "callbacks", original_callbacks)
    for name, callback in installed.items():
        monkeypatch.setattr(integration, name, callback)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    previous = os.environ.get("YOLO_CONFIG_DIR")
    settings_bytes = Path(SETTINGS.file).read_bytes()

    with native_runtime():
        assert SETTINGS["clearml"] is True
        assert set(integration.callbacks) == set(installed)
        assert os.environ.get("YOLO_CONFIG_DIR") == previous
        assert Path(SETTINGS.file).read_bytes() == settings_bytes
        assert (
            unwrap(integration.callbacks["on_train_epoch_end"]) is installed["on_train_epoch_end"]
        )
        assert (
            integration.callbacks["on_pretrain_routine_start"]
            is not installed["on_pretrain_routine_start"]
        )

    assert SETTINGS["clearml"] is original_setting
    assert integration.callbacks is original_callbacks
    assert os.environ.get("YOLO_CONFIG_DIR") == previous
    assert Path(SETTINGS.file).read_bytes() == settings_bytes


def test_pretrain_wrapper_rejects_missing_general_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import clearml
    from ultralytics.utils.callbacks import clearml as integration

    class Task:
        id = "task-id"

        current: Any = None

        @staticmethod
        def current_task() -> Any:
            return Task.current

        def get_parameters(self, **_kwargs: Any) -> dict[str, Any]:
            return {}

        def connect(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    owner = Task()
    Task.current = owner
    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.active_task", lambda: owner)
    monkeypatch.setattr(integration, "on_pretrain_routine_start", lambda _trainer: None)
    monkeypatch.setattr(clearml, "Task", Task)
    monkeypatch.setenv(OWNER_TASK_ENV, "task-id")
    monkeypatch.delenv("LOCAL_RANK", raising=False)

    trainer = type("Trainer", (), {"args": type("Args", (), {})()})()
    with native_runtime(), pytest.raises(RuntimeError, match="General"):
        integration.callbacks["on_pretrain_routine_start"](trainer)


def test_pretrain_wrapper_rejects_a_different_current_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import clearml
    from ultralytics.utils.callbacks import clearml as integration

    class Task:
        id = "different-task"

        current: Any = None

        @staticmethod
        def current_task() -> Any:
            return Task.current

        def get_parameters(self, **_kwargs: Any) -> dict[str, Any]:
            return {"General/epochs": 1}

        def connect(self, values: Any, **kwargs: Any) -> Any:
            return values

    current = Task()
    Task.current = current
    invoked: list[object] = []

    def foreign_task() -> object:
        return object()

    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.active_task", foreign_task)
    monkeypatch.setattr(integration, "on_pretrain_routine_start", invoked.append)
    monkeypatch.setattr(clearml, "Task", Task)
    monkeypatch.setenv(OWNER_TASK_ENV, "task-id")
    monkeypatch.delenv("LOCAL_RANK", raising=False)

    with native_runtime(), pytest.raises(RuntimeError, match="invocation-owned"):
        integration.callbacks["on_pretrain_routine_start"](object())
    assert invoked == []


def test_pretrain_wrapper_propagates_native_swallowed_failure_with_existing_general(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import clearml
    from ultralytics.utils.callbacks import clearml as integration

    class Task:
        id = "task-id"

        current: Any = None

        @staticmethod
        def current_task() -> Any:
            return Task.current

        def get_parameters(self, **_kwargs: Any) -> dict[str, Any]:
            return {"General/epochs": 1}

        def connect(self, values: Any, **kwargs: Any) -> Any:
            return values

    owner = Task()
    Task.current = owner
    original_logger = vars(integration)["LOGGER"]
    invoked: list[object] = []

    def swallowed_failure(trainer: object) -> None:
        invoked.append(trainer)
        vars(integration)["LOGGER"].warning("ClearML installed but not initialized correctly")

    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.active_task", lambda: owner)
    monkeypatch.setattr(integration, "on_pretrain_routine_start", swallowed_failure)
    monkeypatch.setattr(clearml, "Task", Task)
    monkeypatch.setenv(OWNER_TASK_ENV, "task-id")
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    trainer = object()

    with native_runtime(), pytest.raises(RuntimeError, match="registration failure"):
        integration.callbacks["on_pretrain_routine_start"](trainer)

    assert invoked == [trainer]
    assert vars(integration)["LOGGER"] is original_logger


def test_owner_restores_globals_when_callback_discovery_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.callbacks import clearml as integration

    original_callbacks = integration.callbacks
    original_setting = SETTINGS["clearml"]
    previous = os.environ.get("YOLO_CONFIG_DIR")
    settings_bytes = Path(SETTINGS.file).read_bytes()
    for name in tuple(vars(integration)):
        if name.startswith("on_"):
            monkeypatch.setattr(integration, name, None)
    monkeypatch.delenv("LOCAL_RANK", raising=False)

    with pytest.raises(RuntimeError, match="callback set"), native_runtime():
        pass

    assert SETTINGS["clearml"] is original_setting
    assert integration.callbacks is original_callbacks
    assert os.environ.get("YOLO_CONFIG_DIR") == previous
    assert Path(SETTINGS.file).read_bytes() == settings_bytes


def test_worker_disables_callbacks_without_persisting_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.callbacks import clearml as integration

    original_callbacks = integration.callbacks
    original_setting = SETTINGS["clearml"]
    previous = os.environ.get("YOLO_CONFIG_DIR")
    settings_bytes = Path(SETTINGS.file).read_bytes()
    monkeypatch.setenv("LOCAL_RANK", "0")
    monkeypatch.setenv("CY_CLEARML_OWNER_PID", str(os.getpid() + 1))
    monkeypatch.setenv("CY_CLEARML_OWNER_TASK_ID", "parent-task")

    with native_runtime():
        assert os.environ.get("YOLO_CONFIG_DIR") == previous
        assert Path(SETTINGS.file).read_bytes() == settings_bytes
        assert SETTINGS["clearml"] is False
        assert integration.callbacks == {}

    assert SETTINGS["clearml"] is original_setting
    assert integration.callbacks is original_callbacks
    assert os.environ.get("YOLO_CONFIG_DIR") == previous
    assert Path(SETTINGS.file).read_bytes() == settings_bytes
    assert Path(SETTINGS.file).read_bytes() == settings_bytes


def test_native_general_redacts_credentials_without_changing_training_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    import clearml
    from ultralytics.utils.callbacks import clearml as integration

    recorded: list[dict[str, Any]] = []

    class Task:
        id = "task-id"

        @staticmethod
        def current_task() -> Any:
            return owner

        def connect(self, values: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
            recorded.append(values)
            return values

        def get_parameters(self) -> dict[str, Any]:
            return {"General/epochs": 1}

    owner = Task()
    trainer = SimpleNamespace(
        args=SimpleNamespace(
            model="https://host/m.pt?token=secret",
            epochs=1,
            device=[2, 3],
            project="runs",
            name="native-run",
            save_dir="runs/native-run",
            exist_ok=True,
            data="cache/generated/data.yaml",
        )
    )
    original_connect = owner.connect
    monkeypatch.setattr("clearml_yolo.adapters.clearml.session.active_task", lambda: owner)
    monkeypatch.setattr(clearml, "Task", Task)
    monkeypatch.setattr(
        integration,
        "on_pretrain_routine_start",
        # This optional SDK export is populated dynamically by the integration module.
        lambda trainer: (
            integration.__dict__["Task"].current_task().connect(vars(trainer.args), name="General")
        ),
    )
    monkeypatch.setenv(OWNER_TASK_ENV, owner.id)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    with native_runtime():
        integration.callbacks["on_pretrain_routine_start"](trainer)
    assert "secret" not in recorded[0]["model"]
    assert set(recorded[0]) == {"model", "epochs"}
    assert trainer.args.model.endswith("token=secret")
    assert trainer.args.device == [2, 3]
    assert trainer.args.name == "native-run"
    assert trainer.args.data == "cache/generated/data.yaml"
    assert owner.connect == original_connect


def test_fresh_ddp_trainer_scopes_callbacks_without_changing_sdk_settings(tmp_path: Path) -> None:
    import subprocess
    import sys

    script = """
import os
from inspect import unwrap
from pathlib import Path
from unittest.mock import patch
from ultralytics.utils import SETTINGS
from ultralytics.utils.callbacks import clearml as integration
from ultralytics.models.yolo.detect import DetectionTrainer
from clearml_yolo.adapters.integrations.native_trainer import OwnedDetectionTrainer
# Simulate a user's enabled setting. The native trainer must suppress it in workers.
dict.__setitem__(SETTINGS, 'clearml', True)
integration.callbacks = {'sentinel': object()}
before = Path(SETTINGS.file).read_bytes()
old_callbacks = integration.callbacks
calls = []
def inspect(self, *args, **kwargs):
    assert SETTINGS['clearml'] is False
    assert integration.callbacks == {}
    assert Path(SETTINGS.file).read_bytes() == before
    self.save_dir = Path(os.environ['CY_HOME']) / 'native'
    calls.append('scoped')
with (
    patch.object(DetectionTrainer, '__init__', inspect),
    patch.object(DetectionTrainer, 'train', inspect),
):
    trainer = OwnedDetectionTrainer()
    assert SETTINGS['clearml'] is True
    assert integration.callbacks is old_callbacks
    trainer.train()
assert calls == ['scoped', 'scoped']
assert SETTINGS['clearml'] is True
assert integration.callbacks is old_callbacks
assert Path(SETTINGS.file).read_bytes() == before
"""
    result = subprocess.run(  # noqa: S603 - fresh test-owned DDP worker environment
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=dict(
            os.environ,
            CY_HOME=str(tmp_path / "project"),
            LOCAL_RANK="0",
            CY_CLEARML_OWNER_PID=str(os.getpid()),
            CY_CLEARML_OWNER_TASK_ID="owner",
            YOLO_CONFIG_DIR=str(tmp_path / "user-settings"),
        ),
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stderr
