"""Canonical validation for ground-truth detection CSV files."""

import csv
import hashlib
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pandas as pd
from loguru import logger
from PIL import Image

from clearml_yolo.adapters.observability.diagnostics import log_exception
from clearml_yolo.core.datasets import (
    Box,
    ImageRecord,
    InvalidBox,
    Split,
    ValidatedDataset,
    validate_training_box,
)
from clearml_yolo.core.validation import ValidationStage, validate_dataframe

REQUIRED_COLUMNS = (
    "image_name",
    "image_path",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "split",
)
SPLITS = ("train", "val", "test")
NATIVE_IMAGE_EXTENSIONS = frozenset(
    {
        "avif",
        "bmp",
        "dng",
        "heic",
        "heif",
        "jp2",
        "jpeg",
        "jpg",
        "mpo",
        "png",
        "tif",
        "tiff",
        "webp",
    }
)
MINIMUM_IMAGE_DIMENSION = 10

@dataclass(frozen=True)
class _CsvRow:
    number: int
    image_name: str
    image_path: Path
    label: str
    coordinates: tuple[str, str, str, str]
    split: Split

    @property
    def is_background(self) -> bool:
        return self.label == "" and all(value == "" for value in self.coordinates)


def _cell(row: dict[str | None, str | list[str] | None], column: str) -> str:
    value = row.get(column)
    return value if isinstance(value, str) else ""


def _resolved_image_path(value: str, csv_parent: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = csv_parent / path
    return path.resolve()


def _validate_header(header: Sequence[str] | None, source: Path) -> None:
    columns = header or []
    duplicate_headers = sorted(column for column, count in Counter(columns).items() if count > 1)
    if duplicate_headers:
        raise ValueError(f"{source}: Duplicate CSV header(s): {', '.join(duplicate_headers)}")
    missing = sorted(set(REQUIRED_COLUMNS) - set(columns))
    if missing:
        raise ValueError(f"{source}: missing required columns: {', '.join(missing)}")


def _parse_row(signature: tuple[str, ...], number: int, source: Path) -> _CsvRow:
    image_name = signature[0]
    image_path_value = signature[1]
    label = signature[2]
    split_value = signature[7]
    if image_name == "":
        raise ValueError(f"{source}: row {number} has an empty image_name")
    if image_path_value == "":
        raise ValueError(f"{source}: row {number} has an empty image_path")
    if split_value not in SPLITS:
        raise ValueError(
            f"{source}: row {number} has invalid split {split_value!r}; "
            "expected train, val, or test"
        )

    split = cast(Split, split_value)
    image_path = _resolved_image_path(image_path_value, source.parent)
    if image_name != image_path.name:
        raise ValueError(
            f"{source}: row {number} image_name {image_name!r} must match "
            f"resolved path basename {image_path.name!r}"
        )
    return _CsvRow(
        number=number,
        image_name=image_name,
        image_path=image_path,
        label=label,
        coordinates=(signature[3], signature[4], signature[5], signature[6]),
        split=split,
    )


def _claim_identity(
    row: _CsvRow,
    source: Path,
    name_owners: dict[str, tuple[Path, Split]],
    path_owners: dict[Path, tuple[str, Split]],
) -> None:
    owner = name_owners.get(row.image_name)
    if owner is not None:
        owner_path, owner_split = owner
        if owner_path != row.image_path:
            raise ValueError(
                f"{source}: image name {row.image_name!r} refers to both "
                f"{owner_path} and {row.image_path} (row {row.number})"
            )
        if owner_split != row.split:
            raise ValueError(
                f"{source}: image {row.image_name!r} belongs to both split "
                f"{owner_split!r} and {row.split!r} (row {row.number})"
            )
    else:
        name_owners[row.image_name] = (row.image_path, row.split)

    path_owner = path_owners.get(row.image_path)
    if path_owner is not None:
        owner_name, owner_split = path_owner
        if owner_name != row.image_name:
            raise ValueError(
                f"{source}: canonical path {row.image_path} identifies both "
                f"{owner_name!r} and {row.image_name!r} (row {row.number})"
            )
        if owner_split != row.split:
            raise ValueError(
                f"{source}: canonical path {row.image_path} belongs to both split "
                f"{owner_split!r} and {row.split!r} (row {row.number})"
            )
    else:
        path_owners[row.image_path] = (row.image_name, row.split)


def _read_rows(source: Path) -> list[_CsvRow]:
    rows: list[_CsvRow] = []
    signatures: set[tuple[str, ...]] = set()
    name_owners: dict[str, tuple[Path, Split]] = {}
    path_owners: dict[Path, tuple[str, Split]] = {}

    with source.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        _validate_header(reader.fieldnames, source)
        for number, raw_row in enumerate(reader, start=2):
            signature = tuple(_cell(raw_row, column) for column in REQUIRED_COLUMNS)
            row = _parse_row(signature, number, source)
            if signature in signatures and row.is_background:
                raise ValueError(f"{source}: Duplicate background row {number}")
            signatures.add(signature)
            _claim_identity(row, source, name_owners, path_owners)
            rows.append(row)

    if not rows:
        raise ValueError(f"{source}: CSV contains no data rows")
    validate_dataframe(pd.DataFrame([
        {"image_name": row.image_name, "image_path": str(row.image_path),
         "instance_label": row.label, **dict(zip(REQUIRED_COLUMNS[3:7], row.coordinates,
                                                strict=True)), "split": row.split}
        for row in rows
    ], index=[row.number for row in rows]), ValidationStage.RAW_GROUND_TRUTH)
    return rows


def _group_rows(rows: list[_CsvRow], source: Path) -> dict[str, list[_CsvRow]]:
    grouped: dict[str, list[_CsvRow]] = {}
    for row in rows:
        grouped.setdefault(row.image_name, []).append(row)

    for image_name, image_rows in grouped.items():
        has_background = any(row.is_background for row in image_rows)
        has_annotation = any(not row.is_background for row in image_rows)
        if has_background and has_annotation:
            raise ValueError(
                f"{source}: image {image_name!r} mixes an explicit background row "
                "with an annotation row"
            )
    return grouped


def _read_image_size(row: _CsvRow, source: Path) -> tuple[int, int]:
    extension = row.image_path.suffix.removeprefix(".").lower()
    if extension not in NATIVE_IMAGE_EXTENSIONS:
        supported = ", ".join(sorted(NATIVE_IMAGE_EXTENSIONS))
        raise ValueError(
            f"{source}: image {row.image_name!r} has unsupported extension "
            f"{row.image_path.suffix!r}; supported extensions: {supported}"
        )
    try:
        with Image.open(row.image_path) as image:
            image.verify()
            width, height = image.size
            image_format = (image.format or "").lower()
            if image_format == "jpeg":
                try:
                    if image.getexif().get(274) in {6, 8}:
                        width, height = height, width
                except (OSError, SyntaxError, TypeError, ValueError) as error:
                    log_exception(
                        "Could not read EXIF orientation; using decoded dimensions",
                        error,
                        context={
                            "image": row.image_name,
                            "source": row.image_path,
                            "width": width,
                            "height": height,
                        },
                    )
    except (OSError, SyntaxError) as error:
        raise ValueError(
            f"{source}: image {row.image_name!r} at {row.image_path} cannot be read"
        ) from error
    # Pillow reports the decoded JP2 format as JPEG2000, matching native validation.
    if image_format not in NATIVE_IMAGE_EXTENSIONS | {"jpeg2000"}:
        raise ValueError(
            f"{source}: image {row.image_name!r} decodes as unsupported format {image_format!r}"
        )
    if width < MINIMUM_IMAGE_DIMENSION or height < MINIMUM_IMAGE_DIMENSION:
        raise ValueError(
            f"{source}: image {row.image_name!r} is {width} x {height} pixels; "
            f"both dimensions must be at least {MINIMUM_IMAGE_DIMENSION} pixels"
        )
    return int(width), int(height)




def _validate_requested_splits(required_splits: tuple[str, ...]) -> set[str]:
    unsupported = sorted(set(required_splits) - set(SPLITS))
    if unsupported:
        raise ValueError(
            f"Unsupported required split(s): {', '.join(unsupported)}; expected train, val, or test"
        )
    return {"train", "val", *required_splits}


def _validate_prepared_images(images: list[ImageRecord]) -> None:
    prepared_rows: list[dict[str, str | int | float | None]] = []
    for image in images:
        common: dict[str, str | int | float | None] = {
            "image_name": image.name, "image_path": str(image.path),
            "split": image.split, "width": image.width, "height": image.height,
        }
        if not image.boxes:
            prepared_rows.append({**common, "instance_label": None,
                                  **dict.fromkeys(REQUIRED_COLUMNS[3:7])})
        prepared_rows.extend(
            {**common, "instance_label": box.label,
             "bbox_x_tl": box.x1, "bbox_y_tl": box.y1,
             "bbox_x_br": box.x2, "bbox_y_br": box.y2}
            for box in image.boxes
        )
    validate_dataframe(pd.DataFrame(prepared_rows), ValidationStage.TRAINING_GROUND_TRUTH)


def validate_ground_truth(
    source: str | Path, required_splits: tuple[str, ...] = ("train", "val")
) -> ValidatedDataset:
    """Read and validate a detection CSV without modifying its source data."""
    required = _validate_requested_splits(required_splits)
    source_path = Path(source).expanduser().resolve()
    input_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    rows = _read_rows(source_path)
    grouped = _group_rows(rows, source_path)

    labels = sorted({row.label for row in rows if row.label != ""})
    input_boxes = sum(not row.is_background for row in rows)
    images: list[ImageRecord] = []
    errors: list[InvalidBox] = []

    for image_name, image_rows in grouped.items():
        first = image_rows[0]
        width, height = _read_image_size(first, source_path)
        boxes: list[Box] = []
        box_rows: dict[tuple[str, float, float, float, float], int] = {}
        for row in image_rows:
            if row.is_background:
                continue
            box, reason = validate_training_box(row.label, row.coordinates, width, height)
            if reason is not None:
                errors.append(InvalidBox(row=row.number, image_name=image_name, reason=reason))
            elif box is not None:
                key = (box.label, box.x1, box.y1, box.x2, box.y2)
                previous_row = box_rows.get(key)
                if previous_row is not None:
                    raise ValueError(
                        f"{source_path}: Duplicate box for image {image_name!r} at row "
                        f"{row.number}; numerically repeats row {previous_row}"
                    )
                box_rows[key] = row.number
                boxes.append(box)
        boxes.sort(key=lambda box: (box.label, box.x1, box.y1, box.x2, box.y2))
        images.append(
            ImageRecord(
                name=image_name,
                path=first.image_path,
                width=width,
                height=height,
                split=first.split,
                boxes=boxes,
            )
        )

    _validate_prepared_images(images)
    images.sort(key=lambda image: (image.name, str(image.path)))
    logger.info("Invalid bounding boxes dropped: {}", len(errors))

    available_splits = {image.split for image in images}
    missing_splits = sorted(required - available_splits)
    if missing_splits:
        raise ValueError(
            f"{source_path}: required split(s) contain no images: {', '.join(missing_splits)}"
        )

    training_labels = {
        box.label for image in images if image.split == "train" for box in image.boxes
    }
    if not training_labels:
        raise ValueError(f"{source_path}: at least one valid training box is required")
    for label in sorted(set(labels) - training_labels):
        logger.warning("Class {!r} has no valid training examples", label)

    return ValidatedDataset(
        source=source_path,
        input_sha256=input_sha256,
        images=images,
        names=dict(enumerate(labels)),
        errors=errors,
        input_boxes=input_boxes,
    )
