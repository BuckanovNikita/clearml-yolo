"""Load a user-supplied albumentations pipeline from JSON and fit it into YOLO training.

Ultralytics takes a *list* of transforms rather than a Compose: ``v8_transforms`` wraps
whatever it is handed in its own ``A.Compose`` with
``bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels", "idx"])``. Handing
it a Compose would nest one inside the other and detach the bbox handling, so what
:func:`load_augmentations` returns is the transform list.

Which of those transforms ultralytics considered spatial used to be decided by a hardcoded
list of class names, and anything the list did not name — a transform nested in an
``A.OneOf``, a subclass of your own, a class albumentations added later — was taken for a
pixel-level one: the image turned and the boxes stayed where they were. This project
carried a monkey-patch for that. Ultralytics 8.4.117 took the fix upstream, which is what
the dependency floor in ``pyproject.toml`` is for: ``Albumentations.__init__`` now walks
the pipeline and asks whether a ``DualTransform`` is in it at any depth instead of matching
names, and ``ultralytics/utils/dist.py`` round-trips the ``augmentations`` override through
``A.to_dict``/``A.from_dict`` so every DDP child rebuilds the same transforms. Nothing here
patches ultralytics any more, and nothing here should.

``v8_transforms`` places the custom Compose in the middle of ultralytics' own augmentation
stack rather than instead of it::

    Mosaic -> CopyPaste -> RandomPerspective -> MixUp -> CutMix
        -> Albumentations(custom)
        -> RandomHSV -> RandomFlip(vertical) -> RandomFlip(horizontal)

so by default ultralytics keeps rotating, scaling, hue-shifting and flipping on top of the
JSON. :func:`replace_duplicated_augmentations` switches the duplicated hyperparameters off
so the file is the single source of truth, and refuses the combinations that cannot be made
to agree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

# Ultralytics runs these around the custom pipeline — RandomPerspective before it, the bgr
# swap at load time, RandomHSV and RandomFlip after — so leaving them enabled applies a
# second, unrequested augmentation to every image the JSON pipeline already produced.
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

# Ultralytics closes mosaic for the last N epochs by rebuilding the transforms with mosaic
# at zero and every other hyperparameter untouched. `scale` would survive that rebuild as a
# plain random zoom stacked on the custom pipeline, so the schedule has to go for the
# augmentation regime to hold for the whole run.
MOSAIC_SCHEDULE_HYPERPARAMETER = "close_mosaic"

# Mosaic and friends stitch several images together before the custom pipeline ever sees a
# sample, and no albumentations transform can express that, so they stay as configured.
KEPT_WITH_CUSTOM_PIPELINE = (
    "mosaic",
    "mixup",
    "cutmix",
    "copy_paste",
    "copy_paste_mode",
)

# What `mosaic: null` means. Null in an ultralytics parameter file is "leave ultralytics'
# own default alone", and its own default is a mosaic on every sample — reading the null as
# "off" here would zero `scale` under a mosaic that is in fact running.
ULTRALYTICS_DEFAULT_MOSAIC = 1.0


def _is_enabled(value: Any) -> bool:
    """Ultralytics treats a zero probability or gain as "off"; anything else is on."""
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return True


def load_augmentations(path: str | Path | None) -> list[Any] | None:
    """Read an albumentations JSON file into the transform list ultralytics expects.

    Returns None when no path is configured, which leaves ultralytics' own default
    augmentation block in place, and None again when the file holds a pipeline with no
    transforms in it — an empty Compose would otherwise replace that block with nothing at
    all, which is a silent way to train without augmentation.
    """
    if path is None:
        return None

    augmentation_path = Path(path)
    if not augmentation_path.is_file():
        raise FileNotFoundError(f"Albumentations pipeline not found: {augmentation_path}")

    import albumentations as A

    pipeline = A.load(augmentation_path, data_format="json")
    transforms: list[Any] = list(pipeline.transforms)
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


def replace_duplicated_augmentations(
    composed: dict[str, Any], packaged: dict[str, Any]
) -> dict[str, Any]:
    """Switch off the ultralytics augmentations a custom pipeline has already applied.

    ``composed`` is one stage's fully composed ultralytics block; ``packaged`` is the same
    stage's packaged defaults, as ``conf/ultralytics/<stage>.yaml`` writes them. Without an
    ``augmentations`` path nothing changes at all. With one, every hyperparameter in
    :data:`REPLACED_BY_CUSTOM_PIPELINE` goes to zero so the JSON is the single source of
    truth, and :data:`KEPT_WITH_CUSTOM_PIPELINE` stays as configured because albumentations
    cannot express a multi-image augmentation.

    A key still equal to its packaged default was chosen by nobody and is zeroed in
    silence. A key that differs was written on the command line or in a config file, and if
    it is also enabled it is refused rather than silently overruled — the same rule
    :func:`clearml_yolo.configs._overlaid` states one layer up, where a value beats a file.

    >>> replace_duplicated_augmentations({"augmentations": None, "fliplr": 0.5}, {})
    {'augmentations': None, 'fliplr': 0.5}
    """
    if composed.get("augmentations") is None:
        return composed

    disabled: dict[str, Any] = dict.fromkeys(REPLACED_BY_CUSTOM_PIPELINE, 0.0)
    mosaic = ULTRALYTICS_DEFAULT_MOSAIC if composed.get("mosaic") is None else composed["mosaic"]
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

    asked_for = sorted(
        key
        for key in disabled
        if composed.get(key) != packaged.get(key) and _is_enabled(composed.get(key))
    )
    if asked_for:
        raise ValueError(
            f"{', '.join(asked_for)}: asked for alongside a custom albumentations pipeline, and "
            "each of them either augments images the pipeline has already augmented or changes "
            "the augmentation regime part-way through the run. Express them in the JSON pipeline "
            "instead, or leave them at their packaged defaults."
        )

    logger.info(
        "Custom pipeline replaces ultralytics' augmentations {}; {} still apply.",
        sorted(disabled),
        list(KEPT_WITH_CUSTOM_PIPELINE),
    )
    return {**composed, **disabled}
