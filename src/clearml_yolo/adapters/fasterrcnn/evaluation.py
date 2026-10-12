"""Native COCO validation for actual best-checkpoint selection."""

import importlib
import io
import math
from collections.abc import Iterator
from contextlib import redirect_stdout
from typing import Any

import torch
from torch import Tensor

from clearml_yolo.adapters.fasterrcnn.data import CocoDataset


def _detections(
    model: Any,
    batches: Iterator[tuple[list[Tensor], list[dict[str, Tensor]]]],
    device: torch.device,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    model.eval()
    with torch.inference_mode():
        for images, targets in batches:
            predictions = model([image.to(device) for image in images])
            for target, prediction in zip(targets, predictions, strict=True):
                image_id = int(target["image_id"])
                for box, score, label in zip(
                    prediction["boxes"].cpu().tolist(),
                    prediction["scores"].cpu().tolist(),
                    prediction["labels"].cpu().tolist(),
                    strict=True,
                ):
                    records.append(
                        {
                            "image_id": image_id,
                            "category_id": label - 1,
                            "bbox": [box[0], box[1], box[2] - box[0], box[3] - box[1]],
                            "score": score,
                        }
                    )
    return records


def evaluate_coco(
    model: Any,
    dataset: CocoDataset,
    batches: Iterator[tuple[list[Tensor], list[dict[str, Tensor]]]],
    device: torch.device,
) -> dict[str, float]:
    records = _detections(model, batches, device)
    coco = importlib.import_module("pycocotools.coco")
    evaluation = importlib.import_module("pycocotools.cocoeval")
    # COCO writes progress tables directly to stdout; metrics flow only through the
    # invocation's callback. Exceptions still propagate with their original traceback.
    with redirect_stdout(io.StringIO()):
        truth = coco.COCO(str(dataset.annotation_file))
        if records:
            predictions = truth.loadRes(records)
        else:
            predictions = coco.COCO()
            predictions.dataset = {
                "images": truth.dataset["images"],
                "categories": truth.dataset["categories"],
                "annotations": [],
            }
            predictions.createIndex()
        evaluator = evaluation.COCOeval(truth, predictions, "bbox")
        evaluator.params.imgIds = [image.id for image in dataset.records.images]
        evaluator.evaluate()
        evaluator.accumulate()
        evaluator.summarize()
    metrics = {
        "val/map50_95": float(evaluator.stats[0]),
        "val/map50": float(evaluator.stats[1]),
        "val/recall": float(evaluator.stats[8]),
    }
    if any(not math.isfinite(value) or value < 0 for value in metrics.values()):
        raise ValueError("Validation could not produce finite COCO metrics for model selection")
    return metrics
