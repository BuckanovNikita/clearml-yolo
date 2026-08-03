"""Albumentations JSON round-trip into the transform list ultralytics expects."""

from __future__ import annotations

from pathlib import Path

import albumentations as A
import pytest

from clearml_yolo.augment import load_augmentations


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
    """Without a known spatial transform ultralytics omits bbox_params entirely."""
    pipeline = A.Compose([A.RandomBrightnessContrast(p=1.0)])
    destination = tmp_path / "pixel_only.json"
    A.save(pipeline, str(destination), data_format="json")

    transforms = load_augmentations(destination)

    assert transforms is not None
    assert [type(t).__name__ for t in transforms] == ["RandomBrightnessContrast"]
