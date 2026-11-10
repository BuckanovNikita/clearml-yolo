"""Lookup changes execution copies while retaining explicit batches and replay intent."""

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.clearml import session
from clearml_yolo.adapters.integrations import batch_profiles
from clearml_yolo.adapters.integrations import batch_resolution as resolution
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice
from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
from clearml_yolo.core.models import ModelConfig
from clearml_yolo.core.transforms import TransformConfig
from test_batch_lookup import GIB, _dataset


def test_explicit_batches_do_not_discover_gpus(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def forbidden() -> Any:
        pytest.fail("Numeric batches must retain direct native device behavior")

    monkeypatch.setattr(resolution, "discover_gpus", forbidden)
    config = ModelConfig.model_validate({"backend": "fcos", "preset": "resnet50_fpn"})
    prepared = _dataset(tmp_path)
    assert resolution.resolve_native_batch(config, prepared, None) == (config, None)
    for values in ({}, {"batch": 16}, {"batch": -1}, {"batch": 0.8}):
        result, provenance = resolution.resolve_yolo_batch("yolo11n.pt", values, prepared, None)
        assert result is values
        assert provenance is None


@pytest.mark.parametrize("device", ["cpu", "mps"])
def test_native_null_on_non_cuda_device_fails_before_gpu_discovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, device: str
) -> None:
    def forbidden() -> Any:
        pytest.fail("Explicit non-CUDA selection must not query unavailable GPU telemetry")

    monkeypatch.setattr(resolution, "discover_gpus", forbidden)
    config = ModelConfig.model_validate(
        {"backend": "fcos", "preset": "resnet50_fpn", "train": {"batch": None, "device": device}}
    )
    with pytest.raises(ValueError, match="explicit batch for CPU/MPS"):
        resolution.resolve_native_batch(config, _dataset(tmp_path), None)


@pytest.mark.parametrize("classes", [2, 151, 300])
@pytest.mark.parametrize("backend", ["native", "yolo"])
def test_lookup_ignores_dataset_density_recipes_dependencies_and_custom_augmentation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, classes: int, backend: str
) -> None:
    import ultralytics.utils.torch_utils as native_torch

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Table lookup must not build a measurement compatibility profile")

    monkeypatch.setattr(batch_profiles, "training_profile", forbidden)
    monkeypatch.setattr(batch_profiles, "_versions", forbidden)
    monkeypatch.setattr(batch_profiles, "prepare_model_assets", forbidden)
    devices = tuple(
        GPUDevice(
            index=index,
            uuid=f"assigned-{index}",
            name="GPU",
            total_memory_bytes=24 * GIB,
            used_memory_bytes=0,
            utilization=0,
        )
        for index in range(3)
    )
    monkeypatch.setattr(resolution, "discover_gpus", lambda: devices)
    path = tmp_path / "batch-sizes.yaml"
    path.write_text('"GPU [24 GiB]":\n  960:\n    fcos/resnet50_fpn: 3\n    ultralytics/yolo11n: 3\n')
    monkeypatch.setattr(resolution, "BatchSizeStore", lambda: BatchSizeStore(path))
    prepared = _dataset(
        tmp_path, class_names={index: str(index) for index in range(classes)}, images=[{"split": "train", "boxes": 500}]
    )
    transforms = TransformConfig(mode="albumentations", pipeline_file=tmp_path / "custom.yaml")
    if backend == "native":
        config = ModelConfig.model_validate(
            {
                "backend": "fcos",
                "preset": "resnet50_fpn",
                "train": {"batch": None, "imgsz": 960, "device": [2, 0], "amp": False, "grad_accum_steps": 3},
            }
        )
        requested = config.model_dump(mode="json")
        result, provenance = resolution.resolve_native_batch(config, prepared, transforms)
        assert config.model_dump(mode="json") == requested
        assert result.train.amp is False
        assert result.train.grad_accum_steps == 3
        assert result is not config
        assert config.train.batch is None
        assert result.train.batch == 6
        assert result.train.device == [2, 0]
    else:
        monkeypatch.setattr(native_torch, "parse_device", lambda _: "2,0")
        settings = {"batch": None, "imgsz": 960, "device": "-1,-1", "amp": False, "optimizer": "SGD"}
        requested_settings = settings.copy()
        resolved, provenance = resolution.resolve_yolo_batch("yolo11n.pt", settings, prepared, transforms)
        assert settings == requested_settings
        assert resolved == requested_settings | {"batch": 6, "device": [2, 0]}
        assert settings["batch"] is None
        assert resolved["batch"] == 6
        assert resolved["device"] == [2, 0]
    assert provenance is not None
    assert provenance["origin"] == "batch_sizes_table"
    assert provenance["global_batch"] == 6
    assert provenance["per_gpu_batch"] == 3
    assert provenance["table_digest"] == hashlib.sha256(path.read_bytes()).hexdigest()
    expected_model = "fcos/resnet50_fpn" if backend == "native" else "ultralytics/yolo11n"
    assert provenance["model"] == expected_model
    assert provenance["image_size"] == 960
    for selected, index in zip(provenance["selected_entries"], (2, 0), strict=True):
        assert selected["target_gpu"] == {
            "name": "GPU",
            "total_memory_bytes": 24 * GIB,
            "uuid": f"assigned-{index}",
        }
        assert selected["resolved_per_gpu_batch"] == 3
        assert selected["entry"] == {
            "gpu_label": "GPU [24 GiB]",
            "gpu_name": "GPU",
            "total_memory_bytes": 24 * GIB,
            "image_size": 960,
            "model": expected_model,
            "per_gpu_batch": 3,
            "origin": "manual",
            "forced": False,
            "source_status": None,
            "source_diagnostic": "",
            "source_estimate_key": None,
        }
    assert "estimate_key" not in provenance
    assert "profile" not in provenance
    assert [entry["target_gpu"]["uuid"] for entry in provenance["selected_entries"]] == ["assigned-2", "assigned-0"]
    assert all(entry["fallback"] is False for entry in provenance["selected_entries"])


def test_non_square_and_custom_yolo_still_require_explicit_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import ultralytics.utils.torch_utils as native_torch

    prepared = _dataset(tmp_path)
    config = ModelConfig.model_validate(
        {"backend": "fcos", "preset": "resnet50_fpn", "train": {"batch": None, "imgsz": [960, 640]}}
    )
    with pytest.raises(TypeError, match="Non-square"):
        resolution.resolve_native_batch(config, prepared, None)
    with pytest.raises(TypeError, match="Non-square"):
        resolution.resolve_yolo_batch("yolo11n.pt", {"batch": None, "imgsz": [960, 640]}, prepared, None)
    device = GPUDevice(
        index=0, uuid="GPU-test", name="GPU", total_memory_bytes=24 * GIB, used_memory_bytes=0, utilization=0
    )
    monkeypatch.setattr(resolution, "discover_gpus", lambda: (device,))
    monkeypatch.setattr(native_torch, "parse_device", lambda _: "0")
    with pytest.raises(ValueError, match="Custom YOLO"):
        resolution.resolve_yolo_batch("custom.yaml", {"batch": None, "imgsz": 960}, prepared, None)


def test_replay_null_is_not_replaced_by_previous_effective_general_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session, "_is_worker", lambda: False)
    task = SimpleNamespace(get_parameters=lambda **_: {"General/batch": 32, "General/epochs": 9})
    state = session._InvocationState(task=task, stages=["train"], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        values = session.replay_training_parameters(task, {"batch": None, "epochs": 3})
    finally:
        session._ACTIVE_INVOCATION.reset(token)
    assert values == {"batch": None, "epochs": 9}
