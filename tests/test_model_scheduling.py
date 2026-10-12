"""New detector configuration follows existing admission and replay invariants."""

import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from omegaconf import OmegaConf

from clearml_yolo.adapters.runtime.gpu_resources import job_request
from clearml_yolo.adapters.runtime.gpu_scheduling import exact_request
from clearml_yolo.entrypoints.hydra.execution import (
    effective_configuration,
    exact_effective_configuration,
)


def _config(backend: str = "fasterrcnn") -> dict[str, Any]:
    return {
        "model": {
            "backend": backend,
            "preset": {"fasterrcnn": "resnet50_fpn", "rfdetr": "small", "deimv2": "s"}[backend],
            "train": {"device": [2, 0]},
            "predict": {"device": 1},
        },
        "ultralytics": {"device": "cpu"},
        "ultralytics_predict": {"device": "cpu"},
    }


@pytest.mark.parametrize("backend", ["deimv2", "rfdetr", "fasterrcnn"])
@pytest.mark.parametrize(
    ("command", "expected"),
    [("train", 2), ("predict", 1), ("val", 1), ("compare", 1), ("pipeline", 2)],
)
def test_new_backend_demand_uses_model_groups(backend: str, command: str, expected: int) -> None:
    assert job_request(command, _config(backend)) == expected


@pytest.mark.parametrize(
    ("skip_train", "skip_predict", "skip_compare", "expected"),
    [(True, False, True, 1), (True, True, False, 1), (True, True, True, 0)],
)
def test_new_backend_demand_ignores_disabled_phases(
    *, skip_train: bool, skip_predict: bool, skip_compare: bool, expected: int
) -> None:
    config = {
        **_config(),
        "skip_train": skip_train,
        "skip_predict": skip_predict,
        "skip_compare": skip_compare,
    }
    assert job_request("pipeline", config) == expected


def test_new_backend_cpu_demand_does_not_use_default_yolo_gpu() -> None:
    config = {"model": {"backend": "rfdetr", "train": {"device": "cpu"}}}
    assert job_request("train", config) == 0


def test_automatic_remapping_preserves_requests_and_unselected_yolo_groups() -> None:
    requested = OmegaConf.create(_config())
    original = deepcopy(requested)
    effective = effective_configuration(requested, ("GPU-b", "GPU-c"))
    assert list(effective.model.train.device) == [0, 1]
    assert list(effective.model.predict.device) == [0]
    assert effective.ultralytics.device == "cpu"
    assert requested == original


def test_direct_automatic_remapping_uses_selected_visible_ordinals() -> None:
    requested = OmegaConf.create(_config())
    effective = effective_configuration(requested, (3, 7))
    assert list(effective.model.train.device) == [3, 7]
    assert list(effective.model.predict.device) == [3]


def test_minimal_model_replay_materializes_before_automatic_remapping() -> None:
    from clearml_yolo.core.models import ModelConfig

    requested = OmegaConf.create({"model": {"backend": "rfdetr", "preset": "small"}})
    effective = effective_configuration(requested, (3,))
    selected = ModelConfig.model_validate(OmegaConf.to_container(effective.model))
    assert selected.train.device == [3]
    assert selected.predict.device == [3]
    assert selected.train.imgsz == 512
    assert OmegaConf.to_container(requested) == {"model": {"backend": "rfdetr", "preset": "small"}}


def test_cpu_prediction_is_preserved_during_gpu_training_remap() -> None:
    config = _config()
    config["model"]["predict"]["device"] = "cpu"
    effective = effective_configuration(OmegaConf.create(config), ("GPU-b", "GPU-c"))
    assert list(effective.model.train.device) == [0, 1]
    assert effective.model.predict.device == "cpu"


def test_exact_model_union_remaps_and_contracts_without_changing_cuda_order() -> None:
    config = _config()
    selection = exact_request("pipeline", config, ("GPU-a", "GPU-b", "GPU-c"))
    assert selection.devices == ("GPU-b", "GPU-c", "GPU-a")
    effective = exact_effective_configuration(
        "pipeline", OmegaConf.create(config), selection, selection.devices
    )
    assert list(effective.model.train.device) == [1, 2]
    assert list(effective.model.predict.device) == [0]
    replay = OmegaConf.create({**config, "skip_train": True})
    contracted = exact_effective_configuration("pipeline", replay, selection, ("GPU-b",))
    assert list(contracted.model.predict.device) == [0]


def test_exact_model_replay_rejects_gpu_outside_admission() -> None:
    config = _config()
    selection = exact_request("predict", config, ("GPU-a", "GPU-b", "GPU-c"))
    replay = deepcopy(config)
    replay["model"]["predict"]["device"] = 2
    with pytest.raises(ValueError, match="admitted"):
        exact_effective_configuration(
            "predict", OmegaConf.create(replay), selection, selection.devices
        )


def test_exact_inference_rejects_multiple_model_devices() -> None:
    config = _config()
    config["model"]["predict"]["device"] = [0, 1]
    with pytest.raises(ValueError, match="one exact GPU"):
        exact_request("compare", config, ("GPU-a", "GPU-b"))


@pytest.mark.parametrize("export", [{}, {"operation": "onnx"}, {"device": "cpu"}])
def test_cpu_onnx_export_has_no_gpu_demand(export: dict[str, object]) -> None:
    assert job_request("export", {"export": export}) == 0


@pytest.mark.parametrize("operation", ["build", "verify"])
@pytest.mark.parametrize("device", [0, -1, "cuda:1", [2]])
def test_engine_work_demands_one_explicit_gpu(operation: str, device: object) -> None:
    assert job_request("export", {"export": {"operation": operation, "device": device}}) == 1


@pytest.mark.parametrize("operation", ["build", "verify"])
@pytest.mark.parametrize("device", [None, "", "  ", "cpu", "mps", [0, 1]])
def test_engine_work_rejects_non_gpu_or_multiple_devices(operation: str, device: object) -> None:
    with pytest.raises(ValueError, match=r"export.*one.*GPU"):
        job_request("export", {"export": {"operation": operation, "device": device}})


def test_export_exact_mapping_preserves_source_request_and_replay_identity() -> None:
    config = {"export": {"operation": "build", "device": 2}}
    selection = exact_request("export", config, ("GPU-a", "GPU-b", "GPU-c"))
    assert selection.devices == ("GPU-c",)
    effective = exact_effective_configuration(
        "export", OmegaConf.create(config), selection, selection.devices
    )
    assert list(effective.export.device) == [0]
    assert config["export"]["device"] == 2
    replay = OmegaConf.create({"export": {"operation": "build", "device": 1}})
    with pytest.raises(ValueError, match="admitted"):
        exact_effective_configuration("export", replay, selection, selection.devices)


def test_export_automatic_mapping_uses_one_selected_gpu() -> None:
    config = OmegaConf.create({"export": {"operation": "verify", "device": -1}})
    effective = effective_configuration(config, ("GPU-c",))
    assert list(effective.export.device) == [0]
    assert config.export.device == -1


def test_new_model_demand_does_not_import_native_sdks(tmp_path: Path) -> None:
    script = """
import sys
from clearml_yolo.adapters.runtime.gpu_resources import job_request
from clearml_yolo.adapters.runtime.gpu_scheduling import exact_request
from clearml_yolo.entrypoints.hydra.execution import effective_configuration
from omegaconf import OmegaConf
config = {'model': {'backend': 'rfdetr', 'train': {'device': [0, 1]}}}
assert job_request('train', config) == 2
assert exact_request('train', config, ('GPU-a', 'GPU-b')).devices == ('GPU-a', 'GPU-b')
minimal = OmegaConf.create({'model': {'backend': 'rfdetr', 'preset': 'small'}})
assert list(effective_configuration(minimal, (3,)).model.predict.device) == [3]
native = {'torch', 'torchvision', 'ultralytics', 'rfdetr', 'timm', 'tensorrt', 'clearml'}
assert not native & sys.modules.keys()
"""
    result = subprocess.run(  # noqa: S603 - fixed script in the current interpreter
        [sys.executable, "-B", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
