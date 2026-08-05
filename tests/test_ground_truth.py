"""Ground-truth conversion tests over a synthetic YOLO dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from clearml_yolo.ground_truth import GROUND_TRUTH_COLUMNS, build_ground_truth

TRAIN_IMAGE_SIZE = (100, 50)
VAL_IMAGE_SIZE = (200, 100)
VAL_IMAGE_COUNT = 6
VAL_LABEL = "0 0.5 0.5 0.2 0.4\n"


def _write_image(path: Path, size: tuple[int, int]) -> None:
    Image.new("RGB", size, color=(12, 34, 56)).save(path)


def _write_dataset(root: Path) -> Path:
    for split in ("train", "val"):
        (root / "images" / split).mkdir(parents=True)
        (root / "labels" / split).mkdir(parents=True)

    _write_image(root / "images" / "train" / "train_a.jpg", TRAIN_IMAGE_SIZE)
    (root / "labels" / "train" / "train_a.txt").write_text(
        "0 0.5 0.5 0.4 0.2\n1 0.25 0.5 0.5 1.0\n"
    )
    _write_image(root / "images" / "train" / "train_b.jpg", TRAIN_IMAGE_SIZE)
    (root / "labels" / "train" / "train_b.txt").write_text("1 0.5 0.5 1.0 1.0\n")

    for index in range(VAL_IMAGE_COUNT):
        _write_image(root / "images" / "val" / f"val_{index}.jpg", VAL_IMAGE_SIZE)
        (root / "labels" / "val" / f"val_{index}.txt").write_text(VAL_LABEL)

    yaml_path = root / "data.yaml"
    yaml_path.write_text(
        f"path: {root}\ntrain: images/train\nval: images/val\nnames:\n  0: cat\n  1: dog\n"
    )
    return yaml_path


@pytest.fixture
def dataset_yaml(tmp_path: Path) -> Path:
    return _write_dataset(tmp_path / "dataset")


def _build(
    dataset_yaml: Path,
    tmp_path: Path,
    name: str = "gt.csv",
    *,
    test_fraction: float = 0.5,
    seed: int = 0,
) -> pd.DataFrame:
    output = build_ground_truth(
        dataset_yaml, tmp_path / name, test_fraction=test_fraction, seed=seed
    )
    return pd.read_csv(output)


def test_schema_and_pixel_conversion(dataset_yaml: Path, tmp_path: Path) -> None:
    frame = _build(dataset_yaml, tmp_path)

    assert list(frame.columns) == GROUND_TRUTH_COLUMNS

    first = frame[(frame["image_name"] == "train_a.jpg") & (frame["instance_label"] == "cat")]
    assert len(first) == 1
    row = first.iloc[0]
    assert (row["bbox_x_tl"], row["bbox_y_tl"], row["bbox_x_br"], row["bbox_y_br"]) == (
        30.0,
        20.0,
        70.0,
        30.0,
    )
    assert row["image_path"] == str(dataset_yaml.parent / "images" / "train" / "train_a.jpg")
    assert Path(row["image_path"]).is_absolute()
    assert row["split"] == "train"

    full_frame_box = frame[frame["image_name"] == "train_b.jpg"].iloc[0]
    assert (
        full_frame_box["bbox_x_tl"],
        full_frame_box["bbox_y_tl"],
        full_frame_box["bbox_x_br"],
        full_frame_box["bbox_y_br"],
    ) == (0.0, 0.0, 100.0, 50.0)


def test_class_indices_become_names(dataset_yaml: Path, tmp_path: Path) -> None:
    frame = _build(dataset_yaml, tmp_path)
    assert set(frame["instance_label"]) == {"cat", "dog"}


def test_splits_are_disjoint_by_image_name(dataset_yaml: Path, tmp_path: Path) -> None:
    frame = _build(dataset_yaml, tmp_path)

    assert set(frame["split"]) == {"train", "val", "test"}
    per_split = frame.groupby("image_name")["split"].nunique()
    assert per_split.max() == 1

    val_names = set(frame.loc[frame["split"] == "val", "image_name"])
    test_names = set(frame.loc[frame["split"] == "test", "image_name"])
    assert len(test_names) == VAL_IMAGE_COUNT // 2
    assert val_names | test_names == {f"val_{index}.jpg" for index in range(VAL_IMAGE_COUNT)}


def test_split_is_deterministic_per_seed(dataset_yaml: Path, tmp_path: Path) -> None:
    first = _build(dataset_yaml, tmp_path, name="a.csv", seed=0)
    again = _build(dataset_yaml, tmp_path, name="b.csv", seed=0)
    other_seed = _build(dataset_yaml, tmp_path, name="c.csv", seed=7)

    def test_names(frame: pd.DataFrame) -> set[str]:
        return set(frame.loc[frame["split"] == "test", "image_name"])

    assert test_names(first) == test_names(again)
    assert test_names(first) != test_names(other_seed)


def test_zero_test_fraction_keeps_val_whole(dataset_yaml: Path, tmp_path: Path) -> None:
    frame = _build(dataset_yaml, tmp_path, test_fraction=0.0)

    assert set(frame["split"]) == {"train", "val"}
    assert frame.loc[frame["split"] == "val", "image_name"].nunique() == VAL_IMAGE_COUNT


def test_background_images_contribute_no_rows(dataset_yaml: Path, tmp_path: Path) -> None:
    root = dataset_yaml.parent
    _write_image(root / "images" / "train" / "no_label.jpg", TRAIN_IMAGE_SIZE)
    _write_image(root / "images" / "train" / "empty_label.jpg", TRAIN_IMAGE_SIZE)
    (root / "labels" / "train" / "empty_label.txt").write_text("\n  \n")

    frame = _build(dataset_yaml, tmp_path)

    assert not {"no_label.jpg", "empty_label.jpg"} & set(frame["image_name"])
    assert len(frame) == 3 + VAL_IMAGE_COUNT


def test_manifest_split_entry_is_supported(dataset_yaml: Path, tmp_path: Path) -> None:
    root = dataset_yaml.parent
    manifest = root / "val.txt"
    manifest.write_text(
        "./images/val/val_0.jpg\n" + str(root / "images" / "val" / "val_1.jpg") + "\n"
    )
    dataset_yaml.write_text(
        f"path: {root}\ntrain: images/train\nval: val.txt\nnames:\n  0: cat\n  1: dog\n"
    )

    frame = _build(dataset_yaml, tmp_path)

    assert set(frame.loc[frame["split"].isin(["val", "test"]), "image_name"]) == {
        "val_0.jpg",
        "val_1.jpg",
    }


def test_unsupported_split_entry_raises(dataset_yaml: Path, tmp_path: Path) -> None:
    root = dataset_yaml.parent
    dataset_yaml.write_text(
        f"path: {root}\ntrain: images/train\nval: images/missing\nnames:\n  0: cat\n  1: dog\n"
    )

    with pytest.raises(FileNotFoundError):
        build_ground_truth(dataset_yaml, tmp_path / "gt.csv")


def test_segment_labels_are_rejected(dataset_yaml: Path, tmp_path: Path) -> None:
    label = dataset_yaml.parent / "labels" / "train" / "train_a.txt"
    label.write_text("0 0.1 0.1 0.2 0.1 0.2 0.2 0.1 0.2\n")

    with pytest.raises(ValueError, match="segment labels"):
        build_ground_truth(dataset_yaml, tmp_path / "gt.csv")


def test_unknown_class_index_is_rejected(dataset_yaml: Path, tmp_path: Path) -> None:
    label = dataset_yaml.parent / "labels" / "train" / "train_a.txt"
    label.write_text("5 0.5 0.5 0.4 0.2\n")

    with pytest.raises(ValueError, match="references class 5"):
        build_ground_truth(dataset_yaml, tmp_path / "gt.csv")


def test_image_name_shared_between_splits_is_rejected(dataset_yaml: Path, tmp_path: Path) -> None:
    root = dataset_yaml.parent
    _write_image(root / "images" / "val" / "train_a.jpg", VAL_IMAGE_SIZE)
    (root / "labels" / "val" / "train_a.txt").write_text(VAL_LABEL)

    with pytest.raises(ValueError, match="more than one file"):
        build_ground_truth(dataset_yaml, tmp_path / "gt.csv")


def test_image_name_repeated_within_a_split_is_rejected(dataset_yaml: Path, tmp_path: Path) -> None:
    root = dataset_yaml.parent
    nested = root / "images" / "train" / "camera_b"
    nested.mkdir()
    _write_image(nested / "train_a.jpg", TRAIN_IMAGE_SIZE)
    (root / "labels" / "train" / "camera_b").mkdir()
    (root / "labels" / "train" / "camera_b" / "train_a.txt").write_text(VAL_LABEL)

    with pytest.raises(ValueError, match="more than one file"):
        build_ground_truth(dataset_yaml, tmp_path / "gt.csv")


def test_non_positive_box_size_is_rejected(dataset_yaml: Path, tmp_path: Path) -> None:
    label = dataset_yaml.parent / "labels" / "train" / "train_a.txt"
    label.write_text("0 0.5 0.5 -0.2 0.4\n")

    with pytest.raises(ValueError, match="non-positive box size"):
        build_ground_truth(dataset_yaml, tmp_path / "gt.csv")


def test_invalid_test_fraction_is_rejected(dataset_yaml: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="test_fraction"):
        build_ground_truth(dataset_yaml, tmp_path / "gt.csv", test_fraction=1.0)
