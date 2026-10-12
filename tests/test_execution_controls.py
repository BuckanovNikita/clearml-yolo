"""Execution policy belongs to the wrapper, never the native workflow arguments."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf


def test_model_schemas_enable_independent_execution_controls() -> None:
    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        for name in ("pipeline", "train", "predict", "val", "compare", "export"):
            config = compose(config_name=name)
            assert config.queue.enabled is True
            assert config.autogpu.enabled is True
            assert config.autogpu.max_used_memory_gib == 2.0
            custom = compose(config_name=name, overrides=["autogpu.max_used_memory_gib=0.5"])
            assert custom.autogpu.max_used_memory_gib == 0.5
            disabled = compose(
                config_name=name, overrides=["queue.enabled=false", "autogpu.enabled=false"]
            )
            assert disabled.queue.enabled is False
            assert disabled.autogpu.enabled is False


def test_disabled_controls_preserve_native_device_without_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.clearml import session
    from clearml_yolo.entrypoints.hydra import common

    received: list[object] = []
    policies: list[dict[str, Any]] = []

    @contextmanager
    def runtime() -> Iterator[None]:
        yield

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(running_locally=lambda: True)

    def workflow(ultralytics_predict: dict[str, Any], clearml: dict[str, Any]) -> None:
        received.append((os.getpid(), ultralytics_predict["device"]))

    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(common, "wait_for_available_gpus", lambda _: pytest.fail("GPU probe used"))
    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", lambda task, values: values)
    monkeypatch.setattr(common, "initialize_naming", lambda _: None)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    monkeypatch.setattr(
        session, "record_run_configuration", lambda task, values: policies.append(values)
    )
    config = OmegaConf.create(
        {
            "ultralytics_predict": {"device": -1},
            "clearml": {},
            "queue": {"enabled": False},
            "autogpu": {"enabled": False},
        }
    )
    common.execute_owned("predict", config, workflow)
    assert received == [(os.getpid(), -1)]
    assert policies == [
        {"execution_policy": {"queue": False, "autogpu": False, "max_used_memory_gib": 2.0}}
    ]


@pytest.mark.parametrize("setting", ["queue", "autogpu"])
def test_execution_controls_reject_unknown_options(setting: str) -> None:
    from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys

    config = OmegaConf.create(
        {"ultralytics": {"device": "cpu"}, setting: {"enabled": True, "typo": 1}}
    )
    with pytest.raises((ValueError, TypeError), match="typo"):
        validate_wrapper_keys(config, lambda ultralytics: None)


@pytest.mark.parametrize("limit", [0, -1, float("nan"), float("inf"), True, "2", None])
def test_memory_limit_rejects_invalid_configuration(limit: object) -> None:
    from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys

    config = OmegaConf.create(
        {
            "ultralytics": {"device": "cpu"},
            "autogpu": {"enabled": True, "max_used_memory_gib": limit},
        }
    )
    with pytest.raises((ValueError, TypeError), match="max_used_memory_gib"):
        validate_wrapper_keys(config, lambda ultralytics: None)


@pytest.mark.parametrize("limit", [0.5, 2, 4.0])
def test_memory_limit_is_accepted_by_execution_controls(limit: float) -> None:
    from clearml_yolo.adapters.runtime.gpu_scheduling import execution_controls
    from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys

    config = OmegaConf.create(
        {
            "ultralytics": {"device": "cpu"},
            "autogpu": {"enabled": True, "max_used_memory_gib": limit},
        }
    )
    validate_wrapper_keys(config, lambda ultralytics: None)
    assert execution_controls(config) == (True, True)
