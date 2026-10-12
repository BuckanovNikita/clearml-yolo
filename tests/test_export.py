"""Export request and command contracts, without model or accelerator execution."""

from pathlib import Path

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store

from clearml_yolo.core.export_requests import ExportRequest, ExportSettings
from clearml_yolo.entrypoints.hydra.config_tree import dump_config_tree


@pytest.mark.parametrize("device", ["cpu", None, "", [], [0, 1], "0,1", True])
def test_gpu_operations_require_one_explicit_device(device: object) -> None:
    with pytest.raises(ValueError, match=r"device|validation error"):
        ExportSettings.model_validate({"operation": "build", "device": device})


@pytest.mark.parametrize("operation", ["onnx", "build", "verify"])
def test_each_operation_requires_its_inputs(operation: str) -> None:
    with pytest.raises(ValueError, match="requires"):
        ExportRequest.model_validate(
            {"operation": operation, "device": "cpu" if operation == "onnx" else 0}
        )


@pytest.mark.parametrize("settings", [{"device": 0}, {"precision": "fp16"}])
def test_onnx_rejects_ignored_acceleration_settings(settings: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="device=cpu precision=fp32"):
        ExportSettings.model_validate(settings)


def test_cpu_onnx_request_and_gpu_build_request() -> None:
    assert ExportRequest(weights=Path("best.pth")).device == "cpu"
    request = ExportRequest(operation="build", device="cuda:1", onnx=Path("model.onnx"))
    assert request.operation == "build"


def test_export_config_defaults_and_selected_inventory(tmp_path: Path) -> None:
    paths = dump_config_tree(tmp_path, command="cy-export")
    assert {p.relative_to(tmp_path).as_posix() for p in paths} == {
        "cy-export.yaml",
        "model/fasterrcnn/resnet50_fpn.yaml",
    }
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="export")
    assert config.model.backend == "fasterrcnn"
    assert config.export.operation == "onnx"
    assert config.export.device == "cpu"
    assert "ultralytics" not in config


def test_export_rejects_non_fasterrcnn_presets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Faster R-CNN"):
        dump_config_tree(tmp_path, command="cy-export", model="rfdetr/small")
    assert not list(tmp_path.iterdir())
