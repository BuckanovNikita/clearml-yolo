"""Pure validated dataset records and recoverable training-box policy."""

import math
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

Split = Literal["train", "val", "test"]


class Box(BaseModel):
    label: str
    x1: float
    y1: float
    x2: float
    y2: float


class ImageRecord(BaseModel):
    name: str
    path: Path
    width: int
    height: int
    split: Split
    boxes: list[Box]


class InvalidBox(BaseModel):
    row: int
    image_name: str
    reason: str


class ValidatedDataset(BaseModel):
    source: Path
    input_sha256: str
    images: list[ImageRecord]
    names: dict[int, str]
    errors: list[InvalidBox]
    input_boxes: int


def validate_training_box(
    label: str, coordinates: tuple[str, str, str, str], width: int, height: int
) -> tuple[Box | None, str | None]:
    reasons: list[str] = []
    if label == "":
        reasons.append("missing label")
    if any(value == "" for value in coordinates):
        reasons.append("incomplete coordinates")
        return None, "; ".join(reasons)

    try:
        x1, y1, x2, y2 = (float(value) for value in coordinates)
    except ValueError:
        reasons.append("coordinates must be numeric")
        return None, "; ".join(reasons)

    if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
        reasons.append("coordinates must be finite")
        return None, "; ".join(reasons)
    if x2 <= x1 or y2 <= y1:
        reasons.append("box width and height must be positive")
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
        reasons.append(f"coordinates are outside image bounds 0..{width} x 0..{height}")
    if reasons:
        return None, "; ".join(reasons)
    return Box(label=label, x1=x1, y1=y1, x2=x2, y2=y2), None
