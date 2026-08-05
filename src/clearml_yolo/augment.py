"""Load a user-supplied albumentations pipeline from JSON and fit it into YOLO training.

Ultralytics accepts a *list* of transforms rather than a Compose: it wraps them in its
own ``A.Compose`` with ``bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"])``.
Passing a Compose would nest one inside the other and detach the bbox handling.
Which transforms it considers worth a ``bbox_params`` is corrected in
:mod:`clearml_yolo.ultralytics_patch`.

``v8_transforms`` places that Compose in the middle of its own augmentation stack::

    Mosaic -> CopyPaste -> RandomPerspective -> MixUp -> CutMix
        -> Albumentations(custom)
        -> RandomHSV -> RandomFlip(vertical) -> RandomFlip(horizontal)

so a custom pipeline does not replace anything by default — ultralytics keeps rotating,
scaling, hue-shifting and flipping on top of it. This module switches the duplicated
hyperparameters off and rejects the combinations that cannot be made to agree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

# Ultralytics runs these around the custom pipeline — RandomPerspective before it, the
# bgr swap at load time, RandomHSV and RandomFlip after — so leaving them enabled applies
# a second, unrequested augmentation to every image the JSON pipeline already produced.
REPLACED_BY_CUSTOM_PIPELINE = (
    "hsv_h",
    "hsv_s",
    "hsv_v",
    "bgr",
    "degrees",
    "translate",
    "shear",
    "perspective",
    "flipud",
    "fliplr",
)

# RandomPerspective is also what resamples the double-sized mosaic canvas back down to
# imgsz, and `scale` is the zoom it uses to do it. Zeroing it while mosaic runs would
# quietly demote mosaic to a centre crop, so it only counts as duplicated once mosaic is
# off.
MOSAIC_DEPENDENT_HYPERPARAMETER = "scale"

# Ultralytics closes mosaic for the last N epochs by rebuilding the transforms with
# mosaic at zero and every other hyperparameter untouched. `scale` would survive that
# rebuild as a plain random zoom stacked on the custom pipeline, so the schedule has to
# go for the augmentation regime to hold for the whole run.
MOSAIC_SCHEDULE_HYPERPARAMETER = "close_mosaic"

# Mosaic and friends stitch several images together before the custom pipeline ever sees
# a sample, and no albumentations transform can express that, so they stay as configured.
KEPT_WITH_CUSTOM_PIPELINE = (
    "mosaic",
    "mixup",
    "cutmix",
    "copy_paste",
    "copy_paste_mode",
)

ULTRALYTICS_DEFAULT_MOSAIC = 1.0


def _is_enabled(value: Any) -> bool:
    """Ultralytics treats a zero probability or gain as "off"; anything else is on."""
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return True


def resolve_train_augmentations(
    train_kwargs: dict[str, Any] | None,
    augmentations: list[Any] | None,
    keep_default_augmentations: bool = False,
) -> dict[str, Any]:
    """Build the extra ``model.train()`` kwargs for a custom albumentations pipeline.

    Without a pipeline nothing changes. With one, ultralytics' own image-level
    augmentations are switched off so the JSON is the single source of truth, and any
    that the caller asked for explicitly are rejected rather than silently overruled.
    """
    extra = dict(train_kwargs or {})
    if "augmentations" in extra:
        raise ValueError(
            "train_kwargs.augmentations collides with the augmentations config field, which "
            "would win and discard it. Point augmentations.path at the JSON instead."
        )
    if augmentations is None:
        return extra

    extra["augmentations"] = augmentations
    if keep_default_augmentations:
        logger.warning(
            "keep_default_augmentations is set: ultralytics' own augmentations {} keep running "
            "on top of the custom pipeline.",
            list(REPLACED_BY_CUSTOM_PIPELINE),
        )
        return extra

    disabled: dict[str, float] = dict.fromkeys(REPLACED_BY_CUSTOM_PIPELINE, 0.0)
    mosaic = extra.get("mosaic", ULTRALYTICS_DEFAULT_MOSAIC)
    if _is_enabled(mosaic):
        disabled[MOSAIC_SCHEDULE_HYPERPARAMETER] = 0
        logger.info(
            "Keeping ultralytics' scale hyperparameter because mosaic={} needs it to resample "
            "the mosaic canvas back to imgsz, and dropping the close_mosaic schedule so it stays "
            "load-bearing for the whole run.",
            mosaic,
        )
    else:
        disabled[MOSAIC_DEPENDENT_HYPERPARAMETER] = 0.0

    if "cfg" in extra:
        logger.warning(
            "train_kwargs.cfg={} is loaded before the explicit kwargs, so any augmentation it "
            "sets is overruled here rather than rejected. Move augmentations out of it.",
            extra["cfg"],
        )

    requested = sorted(name for name in disabled if _is_enabled(extra.get(name)))
    if requested:
        raise ValueError(
            f"train_kwargs enables {requested} alongside a custom albumentations pipeline, and "
            "each of those would augment images the pipeline has already augmented. Express them "
            "in the JSON instead, or set keep_default_augmentations=true to run both stacks."
        )

    logger.info(
        "Custom pipeline replaces ultralytics' augmentations {}; {} still apply.",
        sorted(disabled),
        list(KEPT_WITH_CUSTOM_PIPELINE),
    )
    return {**disabled, **extra}


def load_augmentations(path: str | Path | None) -> list[Any] | None:
    """Read an albumentations JSON file into the transform list ultralytics expects.

    Returns None when no path is configured, which leaves ultralytics' own default
    augmentation pipeline in place.
    """
    if path is None:
        return None

    augmentation_path = Path(path)
    if not augmentation_path.is_file():
        raise FileNotFoundError(f"Albumentations pipeline not found: {augmentation_path}")

    import albumentations as A

    pipeline = A.load(augmentation_path, data_format="json")
    transforms = list(getattr(pipeline, "transforms", pipeline))
    if not transforms:
        logger.warning("Albumentations pipeline {} is empty", augmentation_path)
        return None

    logger.info(
        "Loaded {} albumentations transform(s) from {}: {}",
        len(transforms),
        augmentation_path,
        [type(transform).__name__ for transform in transforms],
    )
    return transforms
