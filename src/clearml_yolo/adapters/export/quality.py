"""Actual COCO bbox quality for original-image zero-based detection records.

The contract uses the standard COCO maximum of 100 detections per image, averaged
across IoU 0.50:0.95 and all annotated categories. Missing-GT categories have recall 0.
"""

import hashlib
import importlib
import importlib.metadata
import io
import math
from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from clearml_yolo.core.datasets import ImageRecord
from clearml_yolo.core.export_quality import QualityMetrics, validate_detections

COCO_MAX_DETECTIONS = 100


def _actual_evaluator() -> ModuleType:
    evaluation = importlib.import_module("pycocotools.cocoeval")
    if evaluation.COCOeval.__module__ != "pycocotools.cocoeval":
        raise ValueError(
            "Export quality requires actual pycocotools COCOeval, not an aliased evaluator"
        )
    return evaluation


def evaluator_identity() -> dict[str, str]:
    """Bind reports to the actual evaluator implementation, package and source bytes."""
    evaluation = _actual_evaluator()
    if evaluation.__file__ is None:
        raise ValueError("Actual pycocotools evaluator does not expose its source module")
    return {
        "module": str(evaluation.COCOeval.__module__),
        "class": str(evaluation.COCOeval.__name__),
        "package_version": importlib.metadata.version("pycocotools"),
        "source_sha256": hashlib.sha256(Path(evaluation.__file__).read_bytes()).hexdigest(),
    }


def _population(
    images: Sequence[ImageRecord],
    class_names: Sequence[str],
    detections: Mapping[str, NDArray[np.float32]],
) -> dict[str, int]:
    paths = [str(image.path) for image in images]
    if len(set(paths)) != len(paths) or set(detections) != set(paths):
        raise ValueError("Detection population must match unique image paths exactly")
    if (
        not class_names
        or len(set(class_names)) != len(class_names)
        or any(not name for name in class_names)
    ):
        raise ValueError("COCO class names must be unique and nonempty")
    return {name: index for index, name in enumerate(class_names)}


def _truth(images: Sequence[ImageRecord], labels: Mapping[str, int]) -> dict[str, Any]:
    image_rows: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    for index, image in enumerate(images):
        if image.width <= 0 or image.height <= 0:
            raise ValueError("COCO images require positive dimensions")
        image_rows.append(
            {
                "id": index,
                "file_name": str(image.path),
                "width": image.width,
                "height": image.height,
            }
        )
        for box in image.boxes:
            if box.label not in labels:
                raise ValueError(f"Unknown ground-truth class: {box.label}")
            coordinates = (box.x1, box.y1, box.x2, box.y2)
            if not all(math.isfinite(value) for value in coordinates) or not (
                0 <= box.x1 < box.x2 <= image.width and 0 <= box.y1 < box.y2 <= image.height
            ):
                raise ValueError("COCO ground-truth boxes must be finite and inside image bounds")
            width, height = box.x2 - box.x1, box.y2 - box.y1
            annotations.append(
                {
                    "id": len(annotations) + 1,
                    "image_id": index,
                    "category_id": labels[box.label],
                    "bbox": [box.x1, box.y1, width, height],
                    "area": width * height,
                    "iscrowd": 0,
                }
            )
    return {
        "info": {},
        "images": image_rows,
        "categories": [{"id": index, "name": name} for name, index in labels.items()],
        "annotations": annotations,
    }


def _prediction_rows(
    images: Sequence[ImageRecord],
    class_count: int,
    detections: Mapping[str, NDArray[np.float32]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, image in enumerate(images):
        rows = validate_detections(detections[str(image.path)])
        if np.any(rows[:, 5] >= class_count):
            raise ValueError("Unknown prediction class in COCO detections")
        for x1, y1, x2, y2, score, label in rows:
            records.append(
                {
                    "image_id": index,
                    "category_id": int(label),
                    "bbox": [float(x1), float(y1), float(x2 - x1), float(y2 - y1)],
                    "score": float(score),
                }
            )
    return records


def _available_mean(values: NDArray[np.float64]) -> float:
    if not np.isfinite(values).all():
        raise ValueError("COCO evaluation produced nonfinite recall")
    available = values[values >= 0]
    return float(available.mean()) if available.size else 0.0


def _metric(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("COCO evaluation produced a nonfinite metric")
    return max(0.0, value)


def evaluate_detections(
    images: Sequence[ImageRecord],
    class_names: Sequence[str],
    detections: Mapping[str, NDArray[np.float32]],
) -> QualityMetrics:
    """Evaluate every requested image, including empty images, with actual COCOeval."""
    labels = _population(images, class_names, detections)
    dataset = _truth(images, labels)
    records = _prediction_rows(images, len(labels), detections)
    coco = importlib.import_module("pycocotools.coco")
    evaluation = _actual_evaluator()
    # COCO progress tables are noisy library stdout; failures still propagate.
    with redirect_stdout(io.StringIO()):
        truth = coco.COCO()
        truth.dataset = dataset
        truth.createIndex()
        if records:
            predictions = truth.loadRes(records)
        else:
            predictions = coco.COCO()
            predictions.dataset = dataset | {"annotations": []}
            predictions.createIndex()
        evaluator = evaluation.COCOeval(truth, predictions, "bbox")
        evaluator.params.imgIds = list(range(len(images)))
        evaluator.params.catIds = list(labels.values())
        evaluator.params.maxDets = [1, 10, COCO_MAX_DETECTIONS]
        evaluator.evaluate()
        evaluator.accumulate()
        evaluator.summarize()
    class_recall = {
        name: _available_mean(
            np.asarray(evaluator.eval["recall"][:, index, 0, -1], dtype=np.float64)
        )
        for name, index in labels.items()
    }
    return QualityMetrics(
        mAP=_metric(float(evaluator.stats[0])),
        map50=_metric(float(evaluator.stats[1])),
        recall=_metric(float(evaluator.stats[8])),
        per_class_recall=class_recall,
    )
