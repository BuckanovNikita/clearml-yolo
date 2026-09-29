"""Prepare CSV-owned datasets and retain the exact truth used by every stage."""

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from loguru import logger
from pydantic import BaseModel

from clearml_yolo.dataset_export import DatasetFormat, export_dataset
from clearml_yolo.dataset_records import ValidatedDataset, validate_ground_truth

_COLUMNS = (
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
)


class PreparedDataset(BaseModel):
    """Only explicit non-image files are eligible for preparation artifact uploads."""

    data: Path
    ground_truth: Path
    manifest: Path
    dataset_format: DatasetFormat
    artifacts: list[Path]


def _write_cleaned_truth(records: ValidatedDataset, path: Path) -> None:
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(_COLUMNS)
        for image in records.images:
            if not image.boxes:
                writer.writerow([image.name, str(image.path), "", "", "", "", "", image.split])
            for box in image.boxes:
                writer.writerow(
                    [
                        image.name,
                        str(image.path),
                        box.label,
                        box.x1,
                        box.y1,
                        box.x2,
                        box.y2,
                        image.split,
                    ]
                )


def _preparation_record(
    records: ValidatedDataset,
    directory: Path,
    dataset_format: DatasetFormat,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": str(records.source),
        "input_sha256": records.input_sha256,
        "dataset_format": dataset_format,
        "class_names": records.names,
        "counts": {
            "input_boxes": records.input_boxes,
            "valid_boxes": sum(len(image.boxes) for image in records.images),
            "invalid_boxes": len(records.errors),
        },
        "splits": dict(Counter(image.split for image in records.images)),
        "invalid_boxes": [error.model_dump(mode="json") for error in records.errors],
        "images": [
            {
                "image_name": image.name,
                "image_path": str(image.path),
                "split": image.split,
                "width": image.width,
                "height": image.height,
                "boxes": len(image.boxes),
                "generated_path": str(
                    directory / "images" / image.split / f"{index:08d}{image.path.suffix.lower()}"
                ),
            }
            for index, image in enumerate(records.images, start=1)
        ],
    }


def prepare_dataset(
    source: str | Path,
    directory: Path,
    dataset_format: DatasetFormat = "ndjson",
    required_splits: tuple[str, ...] = ("train", "val"),
) -> PreparedDataset:
    """Reserve fresh output, clean once, and export the requested native representation."""
    if dataset_format not in {"ndjson", "flat"}:
        raise ValueError("dataset_format must be one of: ndjson, flat")
    directory = directory.expanduser().absolute()
    # Exclusive reservation rejects stale files and symlinks instead of reusing another run.
    directory.mkdir(parents=True, exist_ok=False)
    records = validate_ground_truth(source, required_splits=required_splits)
    ground_truth = directory / "ground_truth.csv"
    _write_cleaned_truth(records, ground_truth)
    manifest = directory / "preparation.json"
    metadata = _preparation_record(records, directory, dataset_format)
    manifest.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    data = export_dataset(records, directory, dataset_format)
    labels = directory / "labels.zip"
    with ZipFile(labels, "x", compression=ZIP_DEFLATED) as archive:
        for label in sorted((directory / "labels").rglob("*.txt")):
            archive.write(label, label.relative_to(directory).as_posix())
    artifacts = [ground_truth, manifest, data, labels]
    if dataset_format == "ndjson":
        artifacts.append(directory / "dataset.ndjson")
    logger.info("Prepared {} dataset at {}", dataset_format, directory)
    return PreparedDataset(
        data=data,
        ground_truth=ground_truth,
        manifest=manifest,
        dataset_format=dataset_format,
        artifacts=artifacts,
    )


def apply_dataset_policy(
    settings: dict[str, Any],
    data: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Keep CSV membership/class meaning authoritative, recording effective changes."""
    if settings.get("task") not in {None, "detect"}:
        raise ValueError("CSV ground-truth training supports task=detect only")
    owned: dict[str, Any] = {"task": "detect", "classes": None}
    if data is not None:
        if settings.get("resume"):
            raise ValueError(
                "resume is unsupported with ground_truth; use model weights to fine-tune"
            )
        owned.update(
            data=str(data),
            single_cls=False,
            fraction=1.0,
            cls_remap=False,
            split="val",
        )
    overrides = {
        key: {"requested": settings.get(key), "effective": value}
        for key, value in owned.items()
        if key not in settings or settings[key] != value
    }
    for key, values in overrides.items():
        logger.info("CSV dataset owns {}: {} -> {}", key, values["requested"], values["effective"])
    return settings | owned, overrides
