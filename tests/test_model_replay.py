"""Replay keeps initialized runtime ownership and admitted device assignment."""

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from omegaconf import DictConfig, OmegaConf

from clearml_yolo.adapters.clearml import session
from clearml_yolo.adapters.yolo.config import native_defaults, stage_settings
from clearml_yolo.entrypoints.hydra import common
from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys


@pytest.fixture
def isolated_owner(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    events: list[str] = []

    @contextmanager
    def runtime(family: str) -> Iterator[None]:
        events.append(family)
        yield

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(running_locally=lambda: False)

    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(common, "native_runtime", lambda: runtime("ultralytics"))
    monkeypatch.setattr(common, "detector_runtime", lambda: runtime("detector"))
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "wait_for_available_gpus", lambda count: (3,))
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    monkeypatch.setattr(common, "initialize_naming", lambda task: events.append("naming"))
    monkeypatch.setattr(session, "record_run_configuration", lambda task, values: None)
    return events


def _configuration(backend: str, preset: str) -> DictConfig:
    return OmegaConf.create(
        {
            "model": {"backend": backend, "preset": preset},
            "ultralytics_predict": {"device": [-1]},
            "clearml": {},
            "queue": {"enabled": False},
            "autogpu": {"enabled": True},
        }
    )


@pytest.mark.parametrize(
    ("initial", "replayed"),
    [
        (("rfdetr", "small"), ("ultralytics", "default")),
        (("ultralytics", "default"), ("rfdetr", "small")),
    ],
)
def test_replay_cannot_cross_initialized_runtime_family(
    monkeypatch: pytest.MonkeyPatch,
    isolated_owner: list[str],
    initial: tuple[str, str],
    replayed: tuple[str, str],
) -> None:
    def workflow(model: dict[str, Any], ultralytics_predict: dict[str, Any], clearml: Any) -> None:
        isolated_owner.append("workflow")

    monkeypatch.setattr(
        common,
        "replay_configuration",
        lambda task, values: values | {"model": {"backend": replayed[0], "preset": replayed[1]}},
    )
    with pytest.raises(ValueError, match=r"runtime.*[Rr]elaunch.*model="):
        common.execute_owned("predict", _configuration(*initial), workflow)
    assert "workflow" not in isolated_owner
    assert "naming" not in isolated_owner


def test_native_replay_materializes_defaults_and_keeps_selected_gpu(
    monkeypatch: pytest.MonkeyPatch, isolated_owner: list[str]
) -> None:
    observed: list[dict[str, Any]] = []

    def workflow(model: dict[str, Any], ultralytics_predict: dict[str, Any], clearml: Any) -> None:
        observed.append(model)

    monkeypatch.setattr(
        common,
        "replay_configuration",
        lambda task, values: values | {"model": {"backend": "rfdetr", "preset": "small"}},
    )
    config = _configuration("deimv2", "s")
    common.execute_owned("predict", config, workflow)
    assert observed[0]["backend"] == "rfdetr"
    assert observed[0]["predict"]["device"] == [3]
    assert observed[0]["train"]["imgsz"] == 512
    assert config.model.predict.device is None
    assert isolated_owner == ["detector", "naming"]


@pytest.mark.parametrize("command", ["train", "pipeline"])
@pytest.mark.parametrize(
    ("backend", "preset"), [("deimv2", "s"), ("rfdetr", "nano"), ("fasterrcnn", "resnet50_fpn")]
)
def test_detector_training_replay_uses_model_group_without_importing_general_into_yolo(
    monkeypatch: pytest.MonkeyPatch,
    isolated_owner: list[str],
    command: str,
    backend: str,
    preset: str,
) -> None:
    connected: list[str] = []
    observed: list[dict[str, Any]] = []

    def connect(values: dict[str, Any], *, name: str, **kwargs: Any) -> dict[str, Any]:
        connected.append(name)
        return values | {"grad_accum_steps": 2, "device": "cuda:0"}

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(running_locally=lambda: False, connect=connect)

    def workflow(
        model: dict[str, Any],
        ultralytics: dict[str, Any],
        ultralytics_predict: dict[str, Any],
        clearml: Any,
    ) -> None:
        observed.append(model)

    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", lambda task, values: values)
    config = _configuration(backend, preset)
    config.ultralytics = stage_settings(native_defaults(), "train")
    common.execute_owned(command, config, workflow)
    assert connected == []
    assert observed[0]["backend"] == backend
    assert observed[0]["train"]["device"] == [3]
    assert observed[0]["train"]["grad_accum_steps"] == 1


def test_validation_materializes_native_groups_without_rewriting_yolo_settings() -> None:
    def workflow(ultralytics_predict: dict[str, Any], clearml: Any) -> None:
        pass

    config = _configuration("rfdetr", "small")
    validate_wrapper_keys(config, workflow)
    assert config.model.train.epochs == 100
    assert config.model.predict.device is None
    assert config.ultralytics_predict.device == [-1]
    legacy = _configuration("ultralytics", "default")
    validate_wrapper_keys(legacy, workflow)
    assert OmegaConf.to_container(legacy.model) == {"backend": "ultralytics", "preset": "default"}


def test_export_replay_retains_inputs_and_ignores_result_evidence(
    monkeypatch: pytest.MonkeyPatch, isolated_owner: list[str]
) -> None:
    observed: list[dict[str, Any]] = []

    def workflow(export: dict[str, Any], model: dict[str, Any], clearml: Any) -> None:
        observed.append(export)

    settings = {"operation": "onnx", "device": "cpu", "precision": "fp32"}
    monkeypatch.setattr(
        common,
        "replay_configuration",
        lambda task, values: (
            values | {"export_result": {"operation": "onnx", "graph_sha256": "a" * 64}}
        ),
    )
    config = OmegaConf.create(
        {
            "model": {"backend": "fasterrcnn", "preset": "resnet50_fpn"},
            "export": settings,
            "clearml": {},
            "queue": {"enabled": False},
            "autogpu": {"enabled": True},
        }
    )
    common.execute_owned("export", config, workflow)
    assert observed == [settings]
    assert isolated_owner == ["detector", "naming"]
