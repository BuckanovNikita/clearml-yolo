"""Prepared datasets retain cleaned truth and enforce CSV data ownership."""

import csv
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest
from PIL import Image


def _source(directory: Path) -> Path:
    directory.mkdir()
    fields = [
        "image_name",
        "image_path",
        "instance_label",
        "bbox_x_tl",
        "bbox_y_tl",
        "bbox_x_br",
        "bbox_y_br",
        "split",
    ]
    source = directory / "truth.csv"
    with source.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        for split in ("train", "val", "test"):
            image = directory / f"{split}.png"
            Image.new("RGB", (32, 24)).save(image)
            writer.writerow([image.name, image.name, "cat", 1, 2, 17, 20, split])
            writer.writerow([image.name, image.name, "cat", -1, 2, 17, 20, split])
    return source


@pytest.mark.parametrize("dataset_format", ["ndjson", "flat"])
def test_preparation_retains_clean_truth_and_nonimage_artifacts(
    tmp_path: Path,
    dataset_format: Any,
) -> None:
    from clearml_yolo.dataset import prepare_dataset

    source = _source(tmp_path / "input")
    original = source.read_bytes()
    result = prepare_dataset(source, tmp_path / "prepared", dataset_format)
    assert result.data.is_file()
    assert result.dataset_format == dataset_format
    with result.ground_truth.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3
    assert {row["split"] for row in rows} == {"train", "val", "test"}
    assert all(float(row["bbox_x_tl"]) == 1 for row in rows)
    assert all(Path(row["image_path"]).is_absolute() for row in rows)
    metadata = json.loads(result.manifest.read_text())
    assert metadata["counts"] == {"input_boxes": 6, "valid_boxes": 3, "invalid_boxes": 3}
    assert metadata["splits"] == {"train": 1, "val": 1, "test": 1}
    assert len(metadata["invalid_boxes"]) == 3
    assert len(metadata["input_sha256"]) == 64
    assert source.read_bytes() == original
    assert all(path.is_file() for path in result.artifacts)
    assert not any(path.suffix in {".png", ".jpg"} for path in result.artifacts)
    with ZipFile(tmp_path / "prepared" / "labels.zip") as archive:
        assert len(archive.namelist()) == 3
        assert all(
            name.startswith("labels/") and name.endswith(".txt") for name in archive.namelist()
        )


def test_preparation_refuses_reused_directory(tmp_path: Path) -> None:
    from clearml_yolo.dataset import prepare_dataset

    source = _source(tmp_path / "input")
    output = tmp_path / "prepared"
    output.mkdir()
    sentinel = output / "user.txt"
    sentinel.write_text("keep")
    with pytest.raises(FileExistsError):
        prepare_dataset(source, output)
    assert sentinel.read_text() == "keep"


def test_invalid_format_fails_without_output(tmp_path: Path) -> None:
    from clearml_yolo.dataset import prepare_dataset

    source = _source(tmp_path / "input")
    with pytest.raises(ValueError, match=r"ndjson.*flat"):
        prepare_dataset(source, tmp_path / "output", "jsonl")  # type: ignore[arg-type]
    assert not (tmp_path / "output").exists()


def test_ndjson_preparation_preserves_original_basename_and_extension_case(tmp_path: Path) -> None:
    from clearml_yolo.dataset import prepare_dataset

    source = _source(tmp_path / "input")
    rows = list(csv.DictReader(source.open()))
    old_image = source.parent / rows[0]["image_path"]
    renamed = source.parent / "Camera.Frame.PNG"
    old_image.rename(renamed)
    for row in rows:
        if row["split"] == "train":
            row["image_name"] = renamed.name
            row["image_path"] = renamed.name
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = prepare_dataset(source, tmp_path / "prepared", "ndjson")

    assert (result.data.parent / "images/train/Camera.Frame.PNG").is_file()
    assert (result.data.parent / "labels/train/Camera.Frame.txt").is_file()
    metadata = json.loads(result.manifest.read_text())
    train = next(item for item in metadata["images"] if item["split"] == "train")
    assert Path(train["generated_path"]).name == "Camera.Frame.PNG"


def test_data_policy_records_owned_changes_and_preserves_native_controls(tmp_path: Path) -> None:
    from clearml_yolo.dataset import apply_dataset_policy

    requested = {
        "data": "old.yaml",
        "classes": [5],
        "single_cls": True,
        "fraction": 0.1,
        "cls_remap": True,
        "split": "test",
        "epochs": 10,
        "device": "cpu",
        "batch": 8,
        "amp": False,
        "mosaic": 0.5,
    }
    settings, overrides = apply_dataset_policy(requested, tmp_path / "data.yaml")
    assert settings["data"] == str(tmp_path / "data.yaml")
    assert settings["classes"] is None
    assert settings["single_cls"] is False
    assert settings["fraction"] == 1.0
    assert settings["cls_remap"] is False
    assert settings["split"] == "val"
    assert settings["task"] == "detect"
    assert settings["epochs"] == 10
    assert settings["device"] == "cpu"
    assert settings["batch"] == 8
    assert settings["amp"] is False
    assert settings["mosaic"] == 0.5
    assert overrides["data"] == {"requested": "old.yaml", "effective": str(tmp_path / "data.yaml")}
    assert requested["classes"] == [5]


@pytest.mark.parametrize("resume", [True, "old.pt"])
def test_resume_cannot_restore_other_data(tmp_path: Path, resume: Any) -> None:
    from clearml_yolo.dataset import apply_dataset_policy

    with pytest.raises(ValueError, match="resume"):
        apply_dataset_policy({"resume": resume}, tmp_path / "data.yaml")


def test_prediction_policy_keeps_inference_controls() -> None:
    from clearml_yolo.dataset import apply_dataset_policy

    settings, overrides = apply_dataset_policy({"classes": [1], "conf": 0.02, "imgsz": 96})
    assert settings == {"classes": None, "conf": 0.02, "imgsz": 96, "task": "detect"}
    assert overrides["classes"]["requested"] == [1]


def test_unsupported_task_rejected() -> None:
    from clearml_yolo.dataset import apply_dataset_policy

    with pytest.raises(ValueError, match="detect"):
        apply_dataset_policy({"task": "segment"})


def test_csv_policy_satisfies_installed_native_configuration(tmp_path: Path) -> None:
    from ultralytics.cfg import get_cfg

    from clearml_yolo.dataset import apply_dataset_policy

    settings, _ = apply_dataset_policy({"cls_remap": True}, tmp_path / "data.yaml")
    native = get_cfg(overrides=settings)
    assert native.cls_remap is False
    assert native.fraction == 1.0
