"""Replay keeps initialized runtime ownership and native device settings."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
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
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    monkeypatch.setattr(common, "initialize_naming", lambda task: events.append("naming"))
    monkeypatch.setattr(session, "record_run_configuration", lambda task, values: None)
    monkeypatch.setattr(common, "publish_run_configuration", lambda task, values, defaults: None)
    return events


def _configuration(backend: str, preset: str) -> DictConfig:
    return OmegaConf.create(
        {
            "model": {"backend": backend, "preset": preset},
            "ultralytics_predict": {"device": [-1]},
            "clearml": {},
        }
    )


@pytest.mark.parametrize(
    "selector",
    [
        {"dataset_id": "fixed-id"},
        {"project_name": "annotations", "name": "truth"},
        {"project_name": "annotations", "name": "truth", "version": "1.0.0"},
    ],
)
def test_remote_replay_preserves_dataset_selector_and_separates_provenance(
    monkeypatch: pytest.MonkeyPatch, isolated_owner: list[str], selector: dict[str, str]
) -> None:
    observed: list[Any] = []
    published: list[dict[str, Any]] = []
    provenance = {"dataset_id": "resolved-id", "csv_sha256": "digest"}

    def workflow(ground_truth: Any, clearml: Any) -> None:
        observed.append(ground_truth)

    monkeypatch.setattr(
        common, "replay_configuration",
        lambda task, values, **kwargs: values | {
            "ground_truth": selector, "ground_truth_source": provenance
        },
    )
    monkeypatch.setattr(
        common, "publish_run_configuration",
        lambda task, values, defaults: published.append(values),
    )
    common.execute_owned(
        "train", OmegaConf.create({"clearml": {}, "ground_truth": "old-local.csv"}), workflow
    )
    assert observed == [selector]
    assert published[0]["ground_truth"] == selector
    assert "ground_truth_source" not in published[0]


@pytest.mark.parametrize("command", ["train", "pipeline"])
def test_training_replay_keeps_full_native_values_and_only_general_scientific_overrides(
    monkeypatch: pytest.MonkeyPatch,
    isolated_owner: list[str],
    command: str,
) -> None:
    replay_inputs: list[dict[str, Any]] = []
    connected: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    current = {"device": [0, 1], "epochs": 1, "name": "current", "classes": []}
    canonical = {
        "device": [2, 3],
        "epochs": 3,
        "name": "previous",
        "project": "/previous/run",
        "save_dir": "/previous/run/previous",
        "data": "cache/original/data.yaml",
        "classes": [],
        "exist_ok": False,
    }

    def replay(task: Any, values: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        replay_inputs.append(deepcopy(values))
        return values | {"ultralytics": deepcopy(canonical)}

    def get_parameters(*, cast: bool) -> dict[str, Any]:
        assert cast is True
        connected.append({"read": True})
        return {
            "General/epochs": 17,
            "General/device": [8, 9],
            "General/name": "inherited",
            "General/data": "old.yaml",
        }

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        task = SimpleNamespace(running_locally=lambda: False, get_parameters=get_parameters)
        state = session._InvocationState(task=task, stages=[command], current_stage=command)
        token = session._ACTIVE_INVOCATION.set(state)
        try:
            yield task
        finally:
            session._ACTIVE_INVOCATION.reset(token)

    def workflow(ultralytics: dict[str, Any], clearml: Any) -> None:
        observed.append(ultralytics)

    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", replay)
    config = OmegaConf.create({"clearml": {}, "ultralytics": current})
    common.execute_owned(command, config, workflow)

    assert replay_inputs == [{"clearml": {}, "ultralytics": current}]
    assert connected == [{"read": True}]
    assert observed == [
        {
            "device": [2, 3],
            "epochs": 17,
            "name": "current",
            "data": "cache/original/data.yaml",
            "classes": [],
            "exist_ok": False,
        }
    ]
    assert current == {"device": [0, 1], "epochs": 1, "name": "current", "classes": []}


def test_local_replay_records_complete_native_group_without_mutating_it(
    monkeypatch: pytest.MonkeyPatch, isolated_owner: list[str]
) -> None:
    captured: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    native = {"device": [2, 3], "epochs": 1, "name": "current", "classes": [], "project": None}

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(running_locally=lambda: True)

    def replay(task: Any, values: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        captured.append(deepcopy(values))
        return values

    def workflow(ultralytics: dict[str, Any], clearml: Any) -> None:
        observed.append(ultralytics)

    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", replay)
    common.execute_owned(
        "train", OmegaConf.create({"clearml": {}, "ultralytics": native}), workflow
    )
    assert captured == [{"clearml": {}, "ultralytics": native}]
    assert observed == [native]


@pytest.mark.parametrize("command", ["train", "pipeline"])
@pytest.mark.parametrize("stored_device", ["cpu", [2, 3]])
@pytest.mark.parametrize("canonical", [None, {"clearml": {}}])
def test_legacy_training_replay_restores_general_execution_fields_without_old_routing(
    monkeypatch: pytest.MonkeyPatch,
    isolated_owner: list[str],
    command: str,
    stored_device: str | list[int],
    canonical: dict[str, Any] | None,
) -> None:
    connected: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    recorded: list[dict[str, Any]] = []
    inherited = {
        "General/device": stored_device,
        "General/data": "cache/legacy/data.yaml",
        "General/exist_ok": True,
        "General/project": "/previous/run",
        "General/name": "previous",
        "General/save_dir": "/previous/run/previous",
        "General/epochs": 17,
    }

    def get_parameters(*, cast: bool) -> dict[str, Any]:
        assert cast is True
        return deepcopy(inherited)

    def connect(values: dict[str, Any], *, name: str, **kwargs: Any) -> dict[str, Any]:
        assert name == "General"
        assert kwargs == {"ignore_remote_overrides": False}
        connected.append(deepcopy(values))
        return values | {"epochs": 17}

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        task = SimpleNamespace(
            running_locally=lambda: False,
            connect=connect,
            get_parameters=get_parameters,
            get_configuration_object_as_dict=lambda name: deepcopy(canonical),
            get_configuration_object=lambda name: (
                None if canonical is None else json.dumps(canonical)
            ),
            set_configuration_object=lambda **values: recorded.append(
                json.loads(values["config_text"])
            ),
        )
        state = session._InvocationState(task=task, stages=[command], current_stage=command)
        token = session._ACTIVE_INVOCATION.set(state)
        try:
            yield task
        finally:
            session._ACTIVE_INVOCATION.reset(token)

    def workflow(ultralytics: dict[str, Any], clearml: Any) -> None:
        observed.append(ultralytics)

    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "publish_run_configuration", session.publish_run_configuration)
    # Exercise the real session boundary: legacy tasks either omitted the native
    # group from run or had no run Configuration Object at all.
    native = {"device": [0, 1], "epochs": 1, "name": "current", "data": None, "exist_ok": False}
    common.execute_owned(
        command, OmegaConf.create({"clearml": {}, "ultralytics": native}), workflow
    )

    assert observed == [
        {
            "device": stored_device,
            "epochs": 17,
            "name": "current",
            "data": "cache/legacy/data.yaml",
            "exist_ok": True,
        }
    ]
    assert connected == []
    assert inherited["General/name"] == "previous"
    assert recorded[0]["ultralytics"] == native | {
        "device": stored_device,
        "data": "cache/legacy/data.yaml",
        "exist_ok": True,
        "epochs": 17,
    }


@pytest.mark.parametrize(
    "canonical", [{}, {"device": [], "data": "", "exist_ok": False}, {"device": None}]
)
def test_explicit_canonical_native_values_never_fall_back_to_legacy_general(
    monkeypatch: pytest.MonkeyPatch,
    isolated_owner: list[str],
    canonical: dict[str, Any],
) -> None:
    observed: list[dict[str, Any]] = []

    def connect(values: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return values | {"device": [8, 9], "data": "old.yaml", "exist_ok": True}

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        # A canonical native group must never read legacy General execution values.
        task = SimpleNamespace(
            running_locally=lambda: False,
            connect=connect,
            get_parameters=lambda **kwargs: {
                "General/device": [8, 9],
                "General/data": "old.yaml",
                "General/exist_ok": True,
            },
            get_configuration_object_as_dict=lambda name: {
                "clearml": {},
                "ultralytics": deepcopy(canonical),
            },
            set_configuration_object=lambda **values: None,
        )
        state = session._InvocationState(task=task, stages=["train"], current_stage="train")
        token = session._ACTIVE_INVOCATION.set(state)
        try:
            yield task
        finally:
            session._ACTIVE_INVOCATION.reset(token)

    def workflow(ultralytics: dict[str, Any], clearml: Any) -> None:
        observed.append(ultralytics)

    monkeypatch.setattr(common, "invocation", invocation)
    common.execute_owned(
        "train",
        OmegaConf.create({"clearml": {}, "ultralytics": {"device": "cpu", "epochs": 1}}),
        workflow,
    )
    assert observed == [canonical]


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
        lambda task, values, **kwargs: (
            values | {"model": {"backend": replayed[0], "preset": replayed[1]}}
        ),
    )
    with pytest.raises(ValueError, match=r"runtime.*[Rr]elaunch.*model="):
        common.execute_owned("predict", _configuration(*initial), workflow)
    assert "workflow" not in isolated_owner
    assert "naming" not in isolated_owner


def test_native_replay_materializes_defaults_and_preserves_replayed_device(
    monkeypatch: pytest.MonkeyPatch, isolated_owner: list[str]
) -> None:
    observed: list[dict[str, Any]] = []

    def workflow(model: dict[str, Any], ultralytics_predict: dict[str, Any], clearml: Any) -> None:
        observed.append(model)

    monkeypatch.setattr(
        common,
        "replay_configuration",
        lambda task, values, **kwargs: (
            values
            | {"model": {"backend": "rfdetr", "preset": "small", "predict": {"device": "cuda:3"}}}
        ),
    )
    config = _configuration("deimv2", "s")
    common.execute_owned("predict", config, workflow)
    assert observed[0]["backend"] == "rfdetr"
    assert observed[0]["predict"]["device"] == "cuda:3"
    assert observed[0]["train"]["imgsz"] == 512
    assert config.model.predict.device == "cuda:3"
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
    monkeypatch.setattr(common, "replay_configuration", lambda task, values, **kwargs: values)
    config = _configuration(backend, preset)
    config.model["train"] = {"device": "cuda:3"}
    config.ultralytics = stage_settings(native_defaults(), "train")
    common.execute_owned(command, config, workflow)
    assert connected == []
    assert observed[0]["backend"] == backend
    assert observed[0]["train"]["device"] == "cuda:3"
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
        lambda task, values, **kwargs: (
            values | {"export_result": {"operation": "onnx", "graph_sha256": "a" * 64}}
        ),
    )
    config = OmegaConf.create(
        {
            "model": {"backend": "fasterrcnn", "preset": "resnet50_fpn"},
            "export": settings,
            "clearml": {},
        }
    )
    common.execute_owned("export", config, workflow)
    assert observed == [settings]
    assert isolated_owner == ["detector", "naming"]
