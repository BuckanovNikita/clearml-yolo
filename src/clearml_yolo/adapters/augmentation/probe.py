"""Execute fixed-shape custom recipes with conservative synthetic target populations."""

import math

import numpy as np

from clearml_yolo.adapters.augmentation.pipeline import DetectionSample, TrainingPipeline
from clearml_yolo.adapters.augmentation.serialization import build_pipeline
from clearml_yolo.core.transforms import TransformConfig, TransformSnapshot


class SyntheticAugmentation:
    """Actual CPU augmentation while native probe model/optimizer allocations stay live.

    Stochastic filtering must not lower the GPU target envelope: restore the maximal
    population with synthetic boxes after execution. Inputs are square worst-case
    model-sized images; geometry-changing pipelines must preserve that shape.
    """

    def __init__(
        self, config: TransformConfig, shape: tuple[int, int], classes: int, objects: int, *, seed: int = 0
    ) -> None:
        if config.mode != "albumentations" or config.snapshot is None:
            raise ValueError("Custom capacity inputs require a resolved augmentation snapshot")
        snapshot = TransformSnapshot.model_validate(config.snapshot.model_dump(mode="json"))
        compiled = build_pipeline(snapshot.pipeline, seed=seed)
        mosaic = compiled.mosaic
        multiplier = (
            int(mosaic.grid_yx[0] * mosaic.grid_yx[1])
            if mosaic is not None and mosaic.p > 0 and compiled.transform.p > 0
            else 1
        )
        self.pipeline = TrainingPipeline(snapshot, seed=seed)
        self.shape, self.classes, self.objects, self.seed = shape, classes, objects, seed
        self.target_bound = objects * multiplier

    def raw_sample(self, index: int) -> DetectionSample:
        height, width = self.shape
        random = np.random.default_rng(self.seed + index)
        image = random.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
        grid = math.ceil(math.sqrt(self.objects))
        positions = np.arange(self.objects)
        left = (positions % grid).astype(np.float32) * (width / grid)
        top = (positions // grid).astype(np.float32) * (height / grid)
        boxes = np.stack((left, top, left + width / grid * 0.8, top + height / grid * 0.8), axis=1)
        return DetectionSample(
            image,
            boxes.astype(np.float32),
            (positions % self.classes).astype(np.int64),
            positions.astype(np.int64),
            np.zeros(self.objects, dtype=np.int64),
        )

    def sample(self, index: int) -> DetectionSample:
        # Four distinct synthetic donor slots suffice for the campaign's 2x2
        # Mosaic; larger supported grids reuse donors through the production API.
        original = self.raw_sample(index)
        sample = self.pipeline.apply(
            original, index=index, size=max(index + 1, 4), load_sample=self.raw_sample, seed=self.seed
        )
        if sample.image.shape[:2] != self.shape:
            raise ValueError("Custom capacity pipeline must preserve the measured input shape")
        missing = self.target_bound - len(sample.boxes)
        if missing < 0:
            raise ValueError("Custom augmentation exceeded its measured synthetic target bound")
        indices = np.arange(missing) % self.objects
        boxes = np.concatenate((sample.boxes, original.boxes[indices]))
        labels = np.concatenate((sample.labels, original.labels[indices]))
        return DetectionSample(
            sample.image,
            boxes,
            labels,
            np.arange(self.target_bound, dtype=np.int64),
            np.concatenate((sample.iscrowd, np.zeros(missing, dtype=np.int64))),
        )
