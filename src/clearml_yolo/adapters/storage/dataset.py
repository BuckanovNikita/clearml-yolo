"""Prepare CSV-owned datasets and retain the exact truth used by every stage."""

import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from loguru import logger

from clearml_yolo.adapters.storage.dataset_export import (
    DatasetFormat,
    export_dataset,
    exported_image_filename,
)
from clearml_yolo.adapters.storage.dataset_records import validate_ground_truth
from clearml_yolo.application.contracts import (
    PreparedDataset as PreparedDataset,  # noqa: PLC0414 - typed adapter interface
)
from clearml_yolo.core.datasets import ValidatedDataset

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


def _snapshot_csv(source: Path, source_bytes: bytes) -> str:
    """Resolve relative image paths while preserving the captured CSV rows."""
    rows = list(csv.reader(io.StringIO(source_bytes.decode("utf-8"), newline="")))
    if not rows or rows[0].count("image_path") != 1:
        return source_bytes.decode("utf-8")
    image_path_index = rows[0].index("image_path")
    for row in rows[1:]:
        if len(row) <= image_path_index or row[image_path_index] == "":
            continue
        image_path = Path(row[image_path_index]).expanduser()
        if not image_path.is_absolute():
            image_path = source.parent / image_path
        row[image_path_index] = str(image_path.resolve())
    snapshot = io.StringIO(newline="")
    csv.writer(snapshot).writerows(rows)
    return snapshot.getvalue()


def _validate_source(
    source: Path,
    directory: Path,
    required_splits: tuple[str, ...],
    source_bytes: bytes | None,
) -> ValidatedDataset:
    if source_bytes is None:
        return validate_ground_truth(source, required_splits=required_splits)
    snapshot = directory / ".source.csv"
    snapshot.write_text(_snapshot_csv(source, source_bytes), encoding="utf-8")
    try:
        records = validate_ground_truth(snapshot, required_splits=required_splits)
    finally:
        snapshot.unlink(missing_ok=True)
    return records.model_copy(
        update={
            "source": source,
            "input_sha256": hashlib.sha256(source_bytes).hexdigest(),
        }
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
                    directory
                    / "images"
                    / image.split
                    / exported_image_filename(image, index, dataset_format)
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
    *,
    source_bytes: bytes | None = None,
) -> PreparedDataset:
    """Reserve fresh output, clean once, and export the requested native representation."""
    if dataset_format not in {"ndjson", "flat"}:
        raise ValueError("dataset_format must be one of: ndjson, flat")
    directory = directory.expanduser().absolute()
    # Exclusive reservation rejects stale files and symlinks instead of reusing another run.
    directory.mkdir(parents=True, exist_ok=False)
    source_path = Path(source).expanduser().resolve()
    records = _validate_source(source_path, directory, required_splits, source_bytes)
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
