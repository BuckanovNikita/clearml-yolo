"""One raw RGB/box augmentation contract shared by all native detector adapters."""

from collections.abc import Callable
from dataclasses import dataclass
from random import Random
from typing import Any

import numpy as np
from numpy.typing import NDArray

from clearml_yolo.adapters.augmentation.serialization import build_pipeline
from clearml_yolo.core.transforms import TransformSnapshot

_BOX_IDS = "_cy_instance_ids"
_CROWD = "_cy_iscrowd"
_BOX_COLUMNS = 4
_BOX_DIMENSIONS = 2
_RGB_CHANNELS = 3


@dataclass(frozen=True)
class DetectionSample:
    image: NDArray[np.uint8]
    boxes: NDArray[np.float32]
    labels: NDArray[np.int64]
    instance_ids: NDArray[np.int64]
    iscrowd: NDArray[np.int64]

    def copy(self) -> "DetectionSample":
        return DetectionSample(
            self.image.copy(),
            self.boxes.copy(),
            self.labels.copy(),
            self.instance_ids.copy(),
            self.iscrowd.copy(),
        )


def _validate_sample(sample: DetectionSample) -> None:
    if sample.image.dtype != np.uint8 or sample.image.ndim != _RGB_CHANNELS:
        raise ValueError("Augmentation requires an HWC RGB uint8 image")
    if sample.image.shape[2] != _RGB_CHANNELS or min(sample.image.shape[:2]) < 1:
        raise ValueError("Augmentation requires a nonempty three-channel RGB image")
    if sample.boxes.ndim != _BOX_DIMENSIONS or sample.boxes.shape[1] != _BOX_COLUMNS:
        raise ValueError("Augmentation requires boxes shaped (N,4) in absolute xyxy coordinates")
    if not np.isfinite(sample.boxes).all():
        raise ValueError("Augmentation boxes must contain finite coordinates")
    for name, values in (
        ("labels", sample.labels),
        ("instance_ids", sample.instance_ids),
        ("iscrowd", sample.iscrowd),
    ):
        if values.ndim != 1 or len(values) != len(sample.boxes):
            raise ValueError(f"Augmentation {name} must have one value per bounding box")


def _encode_boxes(sample: DetectionSample, bbox_format: str) -> NDArray[np.float32]:
    boxes = sample.boxes.copy()
    height, width = sample.image.shape[:2]
    if bbox_format == "coco":
        boxes[:, 2:] -= boxes[:, :2]
    elif bbox_format == "yolo":
        boxes[:, 2:] -= boxes[:, :2]
        boxes[:, :2] += boxes[:, 2:] / 2
        boxes /= np.array([width, height, width, height], dtype=np.float32)
    elif bbox_format == "albumentations":
        boxes /= np.array([width, height, width, height], dtype=np.float32)
    return boxes


def _decode_boxes(boxes: Any, bbox_format: str, shape: tuple[int, ...]) -> NDArray[np.float32]:
    result = np.array(boxes, dtype=np.float32).reshape(-1, _BOX_COLUMNS)
    height, width = shape[:2]
    if bbox_format in {"albumentations", "yolo"}:
        result *= np.array([width, height, width, height], dtype=np.float32)
    if bbox_format == "yolo":
        result[:, :2] -= result[:, 2:] / 2
        result[:, 2:] += result[:, :2]
    elif bbox_format == "coco":
        result[:, 2:] += result[:, :2]
    return result


class TrainingPipeline:
    def __init__(self, snapshot: TransformSnapshot, seed: int = 0) -> None:
        # Revalidate nested content because frozen Pydantic fields can contain mutable mappings.
        verified = TransformSnapshot.model_validate(snapshot.model_dump(mode="json"))
        self._compiled = build_pipeline(verified.pipeline, seed=seed)
        self._seed = seed
        self._random = Random(seed)  # noqa: S311  # Reproducible augmentation, not security.

    def _input(self, sample: DetectionSample) -> dict[str, Any]:
        _validate_sample(sample)
        return {
            "image": sample.image.copy(),
            "bboxes": _encode_boxes(sample, self._compiled.bbox_format),
            # Strings use the SDK label encoder and avoid losing int64 identities in float32 boxes.
            self._compiled.label_field: [str(value) for value in sample.labels],
            _BOX_IDS: [str(value) for value in sample.instance_ids],
            _CROWD: [str(value) for value in sample.iscrowd],
        }

    def _donors(
        self,
        sample: DetectionSample,
        *,
        index: int,
        size: int,
        load_sample: Callable[[int], DetectionSample],
    ) -> list[dict[str, Any]]:
        mosaic = self._compiled.mosaic
        if mosaic is None or mosaic.p == 0 or self._compiled.transform.p == 0:
            return []
        count = int(mosaic.grid_yx[0] * mosaic.grid_yx[1] - 1)
        candidates = [candidate for candidate in range(size) if candidate != index] or [index]
        indices = (
            self._random.sample(candidates, count)
            if len(candidates) >= count
            else self._random.choices(candidates, k=count)
        )
        next_identity = int(sample.instance_ids.max()) + 1 if len(sample.instance_ids) else 0
        donors: list[dict[str, Any]] = []
        for donor_index in indices:
            donor = load_sample(donor_index).copy()
            occurrence_ids = np.arange(
                next_identity, next_identity + len(donor.boxes), dtype=np.int64
            )
            next_identity += len(donor.boxes)
            donor = DetectionSample(
                donor.image, donor.boxes, donor.labels, occurrence_ids, donor.iscrowd
            )
            donors.append(self._input(donor))
        return donors

    def apply(
        self,
        sample: DetectionSample,
        *,
        index: int,
        size: int,
        load_sample: Callable[[int], DetectionSample],
        seed: int,
    ) -> DetectionSample:
        if not 0 <= index < size:
            raise ValueError("Augmentation sample index must belong to the training population")
        if seed != self._seed:
            self._compiled.transform.set_random_seed(seed)
            self._random.seed(seed)
            self._seed = seed
        data = self._input(sample)
        mosaic = self._compiled.mosaic
        if mosaic is not None:
            data[mosaic.metadata_key] = self._donors(
                sample, index=index, size=size, load_sample=load_sample
            )
        result = self._compiled.transform(**data)
        image = np.asarray(result["image"])
        output = DetectionSample(
            image=image,
            boxes=_decode_boxes(result["bboxes"], self._compiled.bbox_format, image.shape),
            labels=np.asarray(result[self._compiled.label_field], dtype=np.int64),
            instance_ids=np.asarray(result[_BOX_IDS], dtype=np.int64),
            iscrowd=np.asarray(result[_CROWD], dtype=np.int64),
        )
        _validate_sample(output)
        return output
