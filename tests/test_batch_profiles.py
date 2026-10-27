"""Recorded recipes match native effective shapes and prepared training settings."""

import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.integrations import batch_profiles as profiles
from clearml_yolo.adapters.integrations import batch_resolution as resolution
from clearml_yolo.adapters.runtime.gpu_inventory import GPUDevice
from clearml_yolo.application.use_cases.batch_estimate import estimate_batches
from clearml_yolo.core.batch_estimation import SearchSettings, SyntheticWorkload, select_models
from clearml_yolo.core.models import ModelConfig, model_preset
from clearml_yolo.core.transforms import TransformConfig
from test_batch_estimate_workflow import MemoryStore, RecordingProbe
from test_batch_lookup import _dataset


def sample_devices() -> tuple[GPUDevice, ...]:
    return tuple(
        GPUDevice(
            index=index,
            uuid=f"GPU-{index}",
            name=f"Device-{index}",
            total_memory_bytes=1000,
            used_memory_bytes=10,
            utilization=0,
        )
        for index in range(2)
    )


@pytest.fixture(autouse=True)
def stable_profile_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(profiles, "_versions", lambda backend: {backend: "test"})
    monkeypatch.setattr(profiles, "_implementation", lambda: "test-source")


def _prepared_default(config: ModelConfig, *, training: bool) -> tuple[ModelConfig, tuple[()]]:
    prepared = config.model_copy(deep=True)
    if config.backend == "rfdetr":
        prepared.train.weights = Path("/assets/default-detector.pth")
    else:
        prepared.train.backbone_weights = Path("/assets/default-backbone.pth")
    if config.backend == "deimv2":
        prepared.source_dir = Path("/assets/approved-source")
    return prepared, ()


@pytest.mark.parametrize(
    ("selection", "size", "effective"),
    [
        ("yolo11n", 641, 672),
        ("yolov5n6u", 641, 704),
        ("deimv2/s", 960, 1184),
        ("rfdetr/small", 960, 1120),
        ("fasterrcnn/resnet50_fpn", 801, 832),
        ("fcos/resnet50_fpn", 801, 832),
    ],
)
def test_default_profiles_are_metadata_only_and_cover_native_maximum_shapes(
    monkeypatch: pytest.MonkeyPatch, selection: str, size: int, effective: int
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Profile catalogue must not download or initialize model assets")

    monkeypatch.setattr(profiles, "prepare_model_assets", forbidden)
    profile = profiles.training_profile(select_models((selection,))[0], size, sample_devices())
    assert profile.nominal_size == (size, size)
    assert profile.effective_size == (effective, effective)
    assert [gpu.uuid for gpu in profile.gpus] == ["GPU-0", "GPU-1"]
    assert profile.optimizers == (
        ("AdamW", "MuSGD") if selection.startswith("yolo") else ("AdamW",)
    )


@pytest.mark.parametrize(
    ("selection", "size", "scale", "stride"),
    [("yolo11n", 640, 0.13, 32), ("yolov5n6u", 960, 0.1, 64), ("yolo11n", 640, 0.5, 32)],
)
def test_multiscale_profile_covers_actual_native_exclusive_upper_bound(
    monkeypatch: pytest.MonkeyPatch, selection: str, size: int, scale: float, stride: int
) -> None:
    import torch
    from ultralytics.models.yolo.detect import DetectionTrainer

    monkeypatch.setattr(random, "randrange", lambda start, stop: stop - 1)
    trainer: Any = SimpleNamespace(
        device=torch.device("cpu"),
        args=SimpleNamespace(imgsz=size, multi_scale=scale),
        stride=stride,
    )
    result = DetectionTrainer.preprocess_batch(trainer, {"img": torch.zeros(1, 3, 32, 32)})
    profile = profiles.training_profile(
        select_models((selection,))[0], size, sample_devices(), yolo={"multi_scale": scale}
    )
    assert profile.effective_size == tuple(result["img"].shape[-2:])


@pytest.mark.parametrize(
    "selection",
    ["deimv2/s", "rfdetr/small", "fasterrcnn/resnet50_fpn", "fcos/resnet50_fpn"],
)
def test_resolved_default_assets_and_execution_controls_preserve_compatibility(
    monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    monkeypatch.setattr(profiles, "prepare_model_assets", _prepared_default)
    model = select_models((selection,))[0]
    expected = profiles.training_profile(model, 960, sample_devices())
    prepared, _ = _prepared_default(model_preset(selection), training=True)
    prepared.train.batch = None
    prepared.train.imgsz = 960
    prepared.train.workers = 0
    prepared.train.device = [0, 1]
    prepared.train.epochs = 1
    prepared.train.seed = 19
    actual = profiles.training_profile(model, 960, sample_devices(), native=prepared)
    assert actual.compatibility_data() == expected.compatibility_data()


@pytest.mark.parametrize(
    "setting", ["weights", "backbone_weights", "amp", "use_ema", "grad_accum_steps", "lr"]
)
def test_custom_native_training_profiles_cannot_reuse_standard_estimates(
    monkeypatch: pytest.MonkeyPatch, setting: str
) -> None:
    monkeypatch.setattr(profiles, "prepare_model_assets", _prepared_default)
    model = select_models(("fcos/resnet50_fpn",))[0]
    expected = profiles.training_profile(model, 960, sample_devices())
    native, _ = _prepared_default(model_preset(model.selection), training=True)
    changed = {
        "weights": Path("/custom/detector.pth"),
        "backbone_weights": Path("/custom/backbone.pth"),
        "amp": False,
        "use_ema": False,
        "grad_accum_steps": 2,
        "lr": 0.2,
    }
    native.train = native.train.model_copy(update={setting: changed[setting]})
    actual = profiles.training_profile(model, 960, sample_devices(), native=native)
    assert actual.compatibility_data() != expected.compatibility_data()


@pytest.mark.parametrize(
    "settings",
    [{"amp": False}, {"compile": False}, {"nbs": 32}, {"optimizer": "SGD"}, {"mixup": 0.5}],
)
def test_yolo_nonstandard_recipe_changes_are_incompatible(settings: dict[str, Any]) -> None:
    model = select_models(("yolo11n",))[0]
    baseline = profiles.training_profile(model, 960, sample_devices())
    actual = profiles.training_profile(model, 960, sample_devices(), yolo=settings)
    assert actual.compatibility_data() != baseline.compatibility_data()


def test_untrained_native_profile_does_not_resolve_unused_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Untrained profiles must not fetch pretrained assets")

    monkeypatch.setattr(profiles, "prepare_model_assets", forbidden)
    model = select_models(("fcos/resnet50_fpn",))[0]
    config = model_preset(model.selection)
    config.train.pretrained = False
    profiles.training_profile(model, 960, sample_devices(), native=config)


def test_no_cuda_and_custom_transforms_fail_before_asset_preparation(tmp_path: Path) -> None:
    model = select_models(("yolo11n",))[0]
    with pytest.raises(ValueError, match="resolved CUDA devices"):
        profiles.training_profile(model, 960, ())
    transforms = TransformConfig(mode="albumentations", pipeline_file=tmp_path / "custom.yaml")
    with pytest.raises(ValueError, match="explicit batch"):
        profiles.training_profile(model, 960, sample_devices(), transforms=transforms)


def test_catalogue_metadata_is_reused_but_trials_revalidate_visibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.integrations import batch_probe

    observations: list[None] = []

    def discover() -> tuple[GPUDevice, ...]:
        observations.append(None)
        return sample_devices()

    monkeypatch.setattr(batch_probe, "discover_gpus", discover)
    probe = batch_probe.NativeBatchProbe()
    first = probe.profile(select_models(("yolo11n",))[0], 960, (0,))
    second = probe.profile(select_models(("fcos/resnet50_fpn",))[0], 960, (0, 1))
    assert len(observations) == 1
    assert len(batch_probe._devices(first)) == 1
    assert len(batch_probe._devices(second)) == 2
    assert len(observations) == 3


@pytest.mark.parametrize("backend", ["native", "yolo"])
def test_null_lookup_uses_actual_ordered_devices_and_preserves_requested_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, backend: str
) -> None:
    import ultralytics.utils.torch_utils as native_torch

    monkeypatch.setattr(profiles, "prepare_model_assets", _prepared_default)
    devices = tuple(reversed(sample_devices()))
    monkeypatch.setattr(resolution, "discover_gpus", sample_devices)
    selection = "fcos/resnet50_fpn" if backend == "native" else "yolo11n"
    model = select_models((selection,))[0]
    profile = profiles.training_profile(model, 960, devices)
    store = MemoryStore()
    case = estimate_batches(
        tuple(profile.model_copy(update={"gpus": (gpu,)}) for gpu in profile.gpus),
        SyntheticWorkload(),
        SearchSettings(max_global_batch=8),
        probe=RecordingProbe(),
        store=store,
        now=lambda: "recorded",
    )[0]
    monkeypatch.setattr(resolution, "FileBatchEstimateStore", lambda: store)
    prepared = _dataset(tmp_path)
    if backend == "native":
        config, _ = _prepared_default(model_preset(selection), training=True)
        config.train.batch, config.train.imgsz, config.train.device = None, 960, [1, 0]
        resolved, provenance = resolution.resolve_native_batch(config, prepared, None)
        assert config.train.batch is None
        assert resolved.train.batch == 2 * (case.global_batch or 0)
        assert resolved.train.device == [1, 0]
    else:
        from clearml_yolo.adapters.storage.dataset import apply_dataset_policy
        from clearml_yolo.adapters.yolo.config import execution_settings, native_defaults

        monkeypatch.setattr(native_torch, "parse_device", lambda _: "1,0")
        settings = {"batch": None, "imgsz": 960, "device": "-1,-1"}
        effective, _ = apply_dataset_policy(
            execution_settings(native_defaults() | settings, "train"), prepared.data
        )
        assert effective["cls_remap"] is False
        resolved_settings, provenance = resolution.resolve_yolo_batch(
            "yolo11n.pt", effective, prepared, None
        )
        assert settings == {"batch": None, "imgsz": 960, "device": "-1,-1"}
        assert resolved_settings["batch"] == 2 * (case.global_batch or 0)
        assert resolved_settings["device"] == [1, 0]
    assert provenance is not None
    assert provenance["profile"]["gpus"][0]["uuid"] == "GPU-1"
    assert provenance["global_batch"] == 2 * (case.global_batch or 0)


@pytest.mark.parametrize("device", ["cpu", "mps", "2"])
def test_null_resolution_rejects_non_cuda_or_invisible_devices(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, device: str
) -> None:
    monkeypatch.setattr(resolution, "discover_gpus", sample_devices)
    config = model_preset("fcos/resnet50_fpn")
    config.train.batch, config.train.device = None, device
    with pytest.raises(ValueError, match=r"CUDA|visibility"):
        resolution.resolve_native_batch(config, _dataset(tmp_path), None)
