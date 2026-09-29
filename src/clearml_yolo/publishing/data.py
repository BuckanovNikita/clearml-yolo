"""Read immutable CSV snapshots without touching image media on cache hits."""

import csv
import hashlib
import math
from io import StringIO
from pathlib import Path

from pydantic import BaseModel, Field

BOX_COLUMNS = ("bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br")


class PublicationBox(BaseModel):
    label: str
    box: tuple[float, float, float, float]
    confidence: float | None = None
    index: int


class PublicationImage(BaseModel):
    path: Path
    source_path: str
    split: str
    boxes: list[PublicationBox] = Field(default_factory=list)


class DatasetSnapshot(BaseModel):
    sha256: str
    images: dict[str, PublicationImage]

    @property
    def membership(self) -> dict[str, tuple[str, str]]:
        return {name: (str(image.path), image.split) for name, image in self.images.items()}


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read_csv(
    path: Path, required: set[str], *, content: bytes | None = None
) -> list[dict[str, str]]:
    with StringIO(
        (path.read_bytes() if content is None else content).decode("utf-8"), newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        names = reader.fieldnames or []
        if len(set(names)) != len(names) or not required.issubset(names):
            raise ValueError(f"{path}: invalid CSV header; required columns: {sorted(required)}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"{path}: inconsistent CSV row width")
    return rows


def _box(row: dict[str, str], index: int) -> PublicationBox:
    x1, y1, x2, y2 = (float(row[key]) for key in BOX_COLUMNS)
    if not all(math.isfinite(value) for value in (x1, y1, x2, y2)) or x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid publication box at CSV data row {index}")
    confidence = float(row["confidence"]) if "confidence" in row else None
    if confidence is not None and (not math.isfinite(confidence) or not 0 <= confidence <= 1):
        raise ValueError(f"Invalid prediction confidence at CSV data row {index}")
    return PublicationBox(
        label=row["instance_label"], box=(x1, y1, x2, y2), confidence=confidence, index=index
    )


def read_snapshot(path: Path) -> DatasetSnapshot:
    source = path.expanduser().resolve()
    # Hash precisely the bytes being parsed, even if the producer replaces the file.
    content = source.read_bytes()
    required = {"image_name", "image_path", "instance_label", "split", *BOX_COLUMNS}
    rows = _read_csv(source, required, content=content)
    if not rows:
        raise ValueError("Cannot publish an empty ground-truth CSV")
    images: dict[str, PublicationImage] = {}
    path_names: dict[Path, str] = {}
    for index, row in enumerate(rows):
        name = row["image_name"]
        media = Path(row["image_path"]).expanduser()
        media = (source.parent / media).resolve() if not media.is_absolute() else media.resolve()
        if not name or not row["image_path"] or not row["split"]:
            raise ValueError("Publication requires nonempty image_name, image_path, and split")
        current = images.setdefault(
            name, PublicationImage(path=media, source_path=row["image_path"], split=row["split"])
        )
        if current.path != media or current.split != row["split"]:
            raise ValueError(f"Conflicting image identity for {name!r}")
        if path_names.setdefault(media, name) != name:
            raise ValueError(f"Conflicting image identity for {media}")
        if row["instance_label"]:
            current.boxes.append(_box(row, index))
        elif any(row[column] for column in BOX_COLUMNS):
            raise ValueError(f"Unlabelled box at CSV data row {index}")
    return DatasetSnapshot(sha256=hashlib.sha256(content).hexdigest(), images=images)


def prediction_aliases(snapshot: DatasetSnapshot, mode: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for name, image in snapshot.images.items():
        if mode == "stem":
            keys = {image.path.stem}
        elif mode == "path":
            keys = {str(image.path), image.source_path}
        else:
            keys = {name}
        for alias in keys:
            if alias in aliases and aliases[alias] != name:
                raise ValueError(
                    f"Ambiguous prediction image identity {alias!r}; use image_name=name"
                )
            aliases[alias] = name
    return aliases


def read_predictions(path: Path | None, aliases: dict[str, str]) -> dict[str, list[PublicationBox]]:
    grouped: dict[str, list[PublicationBox]] = {}
    if path is None:
        return grouped
    required = {"image_name", "instance_label", "confidence", *BOX_COLUMNS}
    for index, row in enumerate(_read_csv(path, required)):
        name = aliases.get(row["image_name"])
        if name is None:
            raise ValueError(
                f"Prediction image {row['image_name']!r} has no matching ground-truth sample"
            )
        grouped.setdefault(name, []).append(_box(row, index))
    return grouped


def normalize_box(box: tuple[float, float, float, float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = box
    return [x1 / width, y1 / height, (x2 - x1) / width, (y2 - y1) / height]
