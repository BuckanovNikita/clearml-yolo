"""Native tensor boundaries around project-owned RGB detection samples."""

import importlib
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image

from clearml_yolo.core.transforms import TransformConfig

if TYPE_CHECKING:
    from clearml_yolo.adapters.augmentation.pipeline import DetectionSample, TrainingPipeline


def training_pipeline(config: TransformConfig | None, seed: int) -> "TrainingPipeline | None":
    if config is None or config.mode == "native":
        return None
    if config.snapshot is None:
        raise ValueError("Resolve the augmentation JSON snapshot before native training")
    from clearml_yolo.adapters.augmentation.pipeline import TrainingPipeline

    return TrainingPipeline(config.snapshot, seed=seed)


def worker_seed(seed: int) -> int:
    """Use distinct Torch worker streams without replacing the configured owner seed."""
    torch = importlib.import_module("torch")
    worker = torch.utils.data.get_worker_info()
    return seed if worker is None else int(worker.seed)


def detection_sample(image: Image.Image, target: dict[str, Any]) -> "DetectionSample":
    from clearml_yolo.adapters.augmentation.pipeline import DetectionSample

    boxes = np.asarray(target["boxes"], dtype=np.float32).reshape(-1, 4).copy()
    return DetectionSample(
        image=np.array(image.convert("RGB"), dtype=np.uint8, copy=True),
        boxes=boxes,
        labels=np.asarray(target["labels"], dtype=np.int64).copy(),
        instance_ids=np.arange(len(boxes), dtype=np.int64),
        iscrowd=np.asarray(
            target.get("iscrowd", np.zeros(len(boxes), dtype=np.int64)), dtype=np.int64
        ).copy(),
    )


def tensor_target(
    sample: "DetectionSample", original: dict[str, Any], *, bounding_boxes: bool = False
) -> dict[str, Any]:
    """Keep image identity while rebuilding every detection-aligned target field."""
    torch = importlib.import_module("torch")
    boxes = torch.from_numpy(sample.boxes.copy())
    if bounding_boxes:
        tensors = importlib.import_module("torchvision.tv_tensors")
        boxes = tensors.BoundingBoxes(boxes, format="XYXY", canvas_size=sample.image.shape[:2])
    target = original | {
        "boxes": boxes,
        "labels": torch.from_numpy(sample.labels.copy()),
        "iscrowd": torch.from_numpy(sample.iscrowd.copy()),
        "area": torch.from_numpy(
            (sample.boxes[:, 2] - sample.boxes[:, 0]) * (sample.boxes[:, 3] - sample.boxes[:, 1])
        ),
    }
    if "size" in target:
        target["size"] = torch.tensor(sample.image.shape[:2], dtype=torch.int64)
    return target
