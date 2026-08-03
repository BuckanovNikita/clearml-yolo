"""Load a user-supplied albumentations pipeline from JSON.

Ultralytics accepts a *list* of transforms rather than a Compose: it wraps them in its
own ``A.Compose`` with ``bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"])``.
Passing a Compose would nest one inside the other and detach the bbox handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

# Ultralytics attaches bbox_params only when a transform's class name appears in this
# set, so a spatial transform outside it moves the image while leaving boxes behind.
ULTRALYTICS_SPATIAL_TRANSFORMS = frozenset(
    {
        "Affine",
        "BBoxSafeRandomCrop",
        "CenterCrop",
        "CoarseDropout",
        "Crop",
        "CropAndPad",
        "CropNonEmptyMaskIfExists",
        "D4",
        "ElasticTransform",
        "Flip",
        "GridDistortion",
        "GridDropout",
        "HorizontalFlip",
        "Lambda",
        "LongestMaxSize",
        "MaskDropout",
        "Morphological",
        "NoOp",
        "OpticalDistortion",
        "PadIfNeeded",
        "Perspective",
        "PiecewiseAffine",
        "PixelDropout",
        "RandomCrop",
        "RandomCropFromBorders",
        "RandomGridShuffle",
        "RandomResizedCrop",
        "RandomRotate90",
        "RandomScale",
        "RandomSizedBBoxSafeCrop",
        "RandomSizedCrop",
        "Resize",
        "Rotate",
        "SafeRotate",
        "ShiftScaleRotate",
        "SmallestMaxSize",
        "Transpose",
        "VerticalFlip",
        "XYMasking",
    }
)


def _warn_about_unknown_spatial_transforms(transforms: list[Any]) -> None:
    names = {type(transform).__name__ for transform in transforms}
    unknown = sorted(names - ULTRALYTICS_SPATIAL_TRANSFORMS)
    if unknown and not (names & ULTRALYTICS_SPATIAL_TRANSFORMS):
        logger.warning(
            "None of {} is a spatial transform ultralytics recognises, so it will build "
            "the pipeline without bbox_params. If any of these move pixels around, boxes "
            "will not follow and labels will be wrong.",
            unknown,
        )


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

    _warn_about_unknown_spatial_transforms(transforms)
    logger.info(
        "Loaded {} albumentations transform(s) from {}: {}",
        len(transforms),
        augmentation_path,
        [type(transform).__name__ for transform in transforms],
    )
    return transforms
