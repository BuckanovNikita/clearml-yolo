"""Visible training profiles and snapshot preparation at the composition boundary."""

from typing import Any

from loguru import logger
from omegaconf import DictConfig, OmegaConf, open_dict

from clearml_yolo.core.models import PRESETS, ModelConfig
from clearml_yolo.core.transforms import TransformConfig

TRAINING_COMMANDS = frozenset({"train", "pipeline"})
YOLO_DISABLED: dict[str, Any] = {
    "hsv_h": 0.0,
    "hsv_s": 0.0,
    "hsv_v": 0.0,
    "degrees": 0.0,
    "translate": 0.0,
    "scale": 0.0,
    "shear": 0.0,
    "perspective": 0.0,
    "flipud": 0.0,
    "fliplr": 0.0,
    "bgr": 0.0,
    "mosaic": 0.0,
    "mixup": 0.0,
    "cutmix": 0.0,
    "copy_paste": 0.0,
    "auto_augment": None,
    "erasing": 0.0,
    "multi_scale": 0.0,
    "close_mosaic": 0,
    "augmentations": [],
}
DEIM_DISABLED: dict[str, Any] = {
    "mosaic_prob": 0.0,
    "mixup_prob": 0.0,
    "copyblend_prob": 0.0,
    "base_size_repeat": None,
    "ops": [],
}
RFDETR_DISABLED: dict[str, Any] = {
    "aug_config": {},
    "augmentation_backend": "torchvision",
    "scale_jitter": False,
    "multi_scale": "off",
}


def model_selections() -> list[str]:
    return [
        "ultralytics" if backend == "ultralytics" else f"{backend}/{preset}"
        for backend, presets in PRESETS.items()
        for preset in presets
    ]


def profile_values(profile: str) -> dict[str, Any]:
    return {
        "mode": "native" if profile == "default" else "albumentations",
        "pipeline_file": None,
        "snapshot": None,
    }


def native_overlay(selection: str, profile: str) -> dict[str, Any]:
    if profile == "default":
        return {}
    backend = selection.split("/", maxsplit=1)[0]
    if backend == "ultralytics":
        return {"ultralytics": YOLO_DISABLED}
    values = {"deimv2": DEIM_DISABLED, "rfdetr": RFDETR_DISABLED, "fasterrcnn": {}, "fcos": {}}
    return {"model": {"train": {"augmentation": values[backend]}}}


def prepare_transforms(config: DictConfig) -> TransformConfig:
    """Normalize conflicts before model validation and freeze files before queue snapshots."""
    if "transforms" not in config:
        return TransformConfig()
    raw = OmegaConf.to_container(config.transforms, resolve=True)
    if not isinstance(raw, dict):
        raise TypeError("transforms must contain a training profile mapping")
    # A new explicit file selection must not accidentally reuse an old replay snapshot.
    snapshot = raw.get("snapshot")
    selector = raw.get("pipeline_file")
    if isinstance(snapshot, dict) and selector is not None and snapshot.get("source") != selector:
        raw["snapshot"] = None
    selected = TransformConfig.model_validate(raw)
    if selected.mode == "native":
        if config.get("model", {}).get("train", {}).get("augmentation") is not None:
            raise ValueError("model.train.augmentation requires transforms=albumentations")
        return selected
    from clearml_yolo.adapters.augmentation.configuration import resolve_transform_config

    resolved = resolve_transform_config(selected)
    backend = str(config.model.backend)
    if backend != "ultralytics":
        # Check spelling/types before replacement so conflicts cannot hide malformed inputs.
        ModelConfig.model_validate(OmegaConf.to_container(config.model, resolve=True))
    overlay = native_overlay(backend, "albumentations")
    destination = config.ultralytics if backend == "ultralytics" else config.model.train
    disabled = overlay["ultralytics"] if backend == "ultralytics" else overlay["model"]["train"]
    prefix = "ultralytics" if backend == "ultralytics" else "model.train"
    with open_dict(config):
        for key, value in disabled.items():
            requested = (
                OmegaConf.to_container(destination[key], resolve=True)
                if OmegaConf.is_config(destination.get(key))
                else destination.get(key)
            )
            if requested != value:
                logger.warning(
                    "Custom transforms override {}.{}: {} -> {}", prefix, key, requested, value
                )
            destination[key] = value
        config.transforms = resolved.model_dump(mode="json")
    return resolved
