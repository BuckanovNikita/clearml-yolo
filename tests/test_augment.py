"""Albumentations JSON round-trip into the transform list ultralytics expects."""

from __future__ import annotations

from pathlib import Path

import albumentations as A
import pytest

from clearml_yolo.augment import (
    KEPT_WITH_CUSTOM_PIPELINE,
    MOSAIC_DEPENDENT_HYPERPARAMETER,
    MOSAIC_SCHEDULE_HYPERPARAMETER,
    REPLACED_BY_CUSTOM_PIPELINE,
    load_augmentations,
    resolve_train_augmentations,
)

TRANSFORMS = [A.HorizontalFlip(p=0.5)]


@pytest.fixture
def pipeline_json(tmp_path: Path) -> Path:
    pipeline = A.Compose(
        [A.HorizontalFlip(p=0.5), A.RandomBrightnessContrast(p=0.3)],
        bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]),
    )
    destination = tmp_path / "augmentations.json"
    A.save(pipeline, str(destination), data_format="json")
    return destination


def test_returns_transform_list_not_compose(pipeline_json: Path) -> None:
    """Ultralytics builds its own Compose, so it needs the bare transforms."""
    transforms = load_augmentations(pipeline_json)

    assert transforms is not None
    assert not isinstance(transforms, A.Compose)
    assert [type(t).__name__ for t in transforms] == [
        "HorizontalFlip",
        "RandomBrightnessContrast",
    ]


def test_transforms_survive_the_ddp_serialization_round_trip(pipeline_json: Path) -> None:
    """Ultralytics 8.4 ships transforms to DDP children via to_dict/from_dict."""
    transforms = load_augmentations(pipeline_json)
    assert transforms is not None

    rebuilt = [A.from_dict(A.to_dict(t)) for t in transforms]

    assert [type(t).__name__ for t in rebuilt] == [type(t).__name__ for t in transforms]


def test_none_path_keeps_ultralytics_defaults() -> None:
    assert load_augmentations(None) is None


def test_missing_file_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_augmentations(tmp_path / "absent.json")


def test_pixel_only_pipeline_still_loads(tmp_path: Path) -> None:
    """Without a spatial transform ultralytics omits bbox_params, which is correct here."""
    pipeline = A.Compose([A.RandomBrightnessContrast(p=1.0)])
    destination = tmp_path / "pixel_only.json"
    A.save(pipeline, str(destination), data_format="json")

    transforms = load_augmentations(destination)

    assert transforms is not None
    assert [type(t).__name__ for t in transforms] == ["RandomBrightnessContrast"]


def test_nested_transforms_round_trip(tmp_path: Path) -> None:
    """Ultralytics cannot see geometry inside a OneOf; clearml_yolo.ultralytics_patch
    teaches it to, so loading one has to keep the wrapper intact."""
    pipeline = A.Compose([A.OneOf([A.Rotate(p=1.0), A.Affine(p=1.0)], p=1.0)])
    destination = tmp_path / "nested.json"
    A.save(pipeline, str(destination), data_format="json")

    transforms = load_augmentations(destination)

    assert transforms is not None
    assert [type(t).__name__ for t in transforms] == ["OneOf"]
    assert len(transforms[0].transforms) == 2


def test_no_pipeline_leaves_train_kwargs_untouched() -> None:
    assert resolve_train_augmentations({"fliplr": 0.5, "hsv_h": 0.1}, None) == {
        "fliplr": 0.5,
        "hsv_h": 0.1,
    }


def test_custom_pipeline_disables_the_augmentations_it_duplicates() -> None:
    resolved = resolve_train_augmentations({"mosaic": 0.0}, TRANSFORMS)

    for name in REPLACED_BY_CUSTOM_PIPELINE:
        assert resolved[name] == 0.0
    assert resolved[MOSAIC_DEPENDENT_HYPERPARAMETER] == 0.0
    assert resolved["augmentations"] is TRANSFORMS


def test_multi_image_augmentations_are_left_alone() -> None:
    """Mosaic and friends stitch images together before the pipeline runs, so albumentations
    cannot express them and they must survive."""
    requested = {name: 0.5 for name in KEPT_WITH_CUSTOM_PIPELINE if name != "copy_paste_mode"}

    resolved = resolve_train_augmentations(dict(requested), TRANSFORMS)

    assert {name: resolved[name] for name in requested} == requested


def test_scale_survives_because_mosaic_needs_it_to_resample_the_canvas() -> None:
    """RandomPerspective is what fits the double-sized mosaic canvas back into imgsz."""
    resolved = resolve_train_augmentations({"mosaic": 1.0}, TRANSFORMS)

    assert MOSAIC_DEPENDENT_HYPERPARAMETER not in resolved


def test_the_close_mosaic_schedule_is_dropped_while_scale_is_load_bearing() -> None:
    """close_mosaic rebuilds the transforms with mosaic at zero and everything else
    untouched, which would leave `scale` running as a plain zoom for the final epochs."""
    resolved = resolve_train_augmentations({"mosaic": 1.0}, TRANSFORMS)

    assert resolved[MOSAIC_SCHEDULE_HYPERPARAMETER] == 0
    # close_mosaic is an int-only ultralytics argument and a float would be rejected.
    assert isinstance(resolved[MOSAIC_SCHEDULE_HYPERPARAMETER], int)


def test_an_explicit_close_mosaic_schedule_is_rejected() -> None:
    with pytest.raises(ValueError, match="close_mosaic"):
        resolve_train_augmentations({"mosaic": 1.0, "close_mosaic": 10}, TRANSFORMS)


def test_the_close_mosaic_schedule_is_harmless_once_mosaic_is_off() -> None:
    """With mosaic off `scale` is already zero, so the rebuild changes nothing."""
    resolved = resolve_train_augmentations({"mosaic": 0.0, "close_mosaic": 10}, TRANSFORMS)

    assert resolved[MOSAIC_SCHEDULE_HYPERPARAMETER] == 10


def test_explicitly_enabling_a_replaced_augmentation_is_rejected() -> None:
    with pytest.raises(ValueError, match="fliplr"):
        resolve_train_augmentations({"fliplr": 0.5}, TRANSFORMS)


def test_explicit_scale_is_allowed_while_mosaic_needs_it() -> None:
    resolved = resolve_train_augmentations({"mosaic": 1.0, "scale": 0.5}, TRANSFORMS)

    assert resolved["scale"] == 0.5


def test_explicit_scale_is_rejected_once_mosaic_no_longer_needs_it() -> None:
    with pytest.raises(ValueError, match="scale"):
        resolve_train_augmentations({"mosaic": 0.0, "scale": 0.5}, TRANSFORMS)


def test_explicitly_disabling_a_replaced_augmentation_is_not_a_conflict() -> None:
    resolved = resolve_train_augmentations({"fliplr": 0.0}, TRANSFORMS)

    assert resolved["fliplr"] == 0.0


def test_the_escape_hatch_keeps_both_stacks() -> None:
    resolved = resolve_train_augmentations(
        {"fliplr": 0.5}, TRANSFORMS, keep_default_augmentations=True
    )

    assert resolved == {"fliplr": 0.5, "augmentations": TRANSFORMS}


def test_augmentations_inside_train_kwargs_is_rejected() -> None:
    """It would be overwritten by the config field, so silently doing nothing is worse."""
    with pytest.raises(ValueError, match="collides"):
        resolve_train_augmentations({"augmentations": TRANSFORMS}, TRANSFORMS)
