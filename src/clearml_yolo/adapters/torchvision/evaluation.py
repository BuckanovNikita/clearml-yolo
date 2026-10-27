"""Native COCO validation for actual best-checkpoint selection."""

import importlib
import io
import math
from collections.abc import Iterator
from contextlib import redirect_stdout
from typing import Any

import torch
from pydantic import BaseModel, ConfigDict, JsonValue
from torch import Tensor, distributed

from clearml_yolo.adapters.torchvision.data import CocoDataset


class DetectionPopulation(BaseModel):
    """Image identities remain present even when a rank predicts no boxes."""

    model_config = ConfigDict(extra="forbid")
    image_ids: list[int]
    detections: list[dict[str, JsonValue]]


def _detections(
    model: Any,
    batches: Iterator[tuple[list[Tensor], list[dict[str, Tensor]]]],
    device: torch.device,
    dataset: CocoDataset,
) -> DetectionPopulation:
    records: list[dict[str, JsonValue]] = []
    image_ids: list[int] = []
    model.eval()
    with torch.inference_mode():
        for images, targets in batches:
            predictions = model([image.to(device) for image in images])
            for target, prediction in zip(targets, predictions, strict=True):
                image_id = int(target["image_id"])
                image_ids.append(image_id)
                for box, score, label in zip(
                    prediction["boxes"].cpu().tolist(),
                    prediction["scores"].cpu().tolist(),
                    prediction["labels"].cpu().tolist(),
                    strict=True,
                ):
                    category = int(label) - dataset.label_offset
                    if not 0 <= category < dataset.num_classes:
                        raise ValueError(
                            "Torchvision validation emitted an unknown foreground label"
                        )
                    records.append(
                        {
                            "image_id": image_id,
                            "category_id": category,
                            "bbox": [box[0], box[1], box[2] - box[0], box[3] - box[1]],
                            "score": score,
                        }
                    )
    return DetectionPopulation(image_ids=image_ids, detections=records)


def _score(
    dataset: CocoDataset,
    population: DetectionPopulation,
) -> dict[str, float]:
    expected = sorted(image.id for image in dataset.records.images)
    if sorted(population.image_ids) != expected:
        raise ValueError("Validation must evaluate every image exactly once across all ranks")
    records = population.detections
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


def evaluate_coco(
    model: Any,
    dataset: CocoDataset,
    batches: Iterator[tuple[list[Tensor], list[dict[str, Tensor]]]],
    device: torch.device,
) -> dict[str, float]:
    # The caller supplies an unwrapped model. Uneven nonpadding validation shards
    # must not enter DDP forward-time buffer broadcasts or other collectives.
    population = _detections(model, batches, device, dataset)
    if not distributed.is_available() or not distributed.is_initialized():
        return _score(dataset, population)
    rank = distributed.get_rank()
    gathered: list[Any] | None = [None] * distributed.get_world_size() if rank == 0 else None
    distributed.gather_object(population.model_dump(mode="json"), gathered, dst=0)
    result: list[Any] = [None]
    if gathered is not None:
        partitions = [DetectionPopulation.model_validate(value) for value in gathered]
        combined = DetectionPopulation(
            image_ids=[image for part in partitions for image in part.image_ids],
            detections=[record for part in partitions for record in part.detections],
        )
        result[0] = _score(dataset, combined)
    distributed.broadcast_object_list(result, src=0)
    return {str(key): float(value) for key, value in result[0].items()}
