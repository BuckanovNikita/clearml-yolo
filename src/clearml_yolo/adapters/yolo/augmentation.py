"""Raw YOLO training samples with the shared pipeline and native final formatting."""

from copy import deepcopy
from typing import Any, override

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image, ImageOps
from ultralytics.data.augment import Compose, Format, LetterBox
from ultralytics.data.dataset import YOLODataset
from ultralytics.utils.instance import Instances

from clearml_yolo.adapters.augmentation.pipeline import DetectionSample, TrainingPipeline
from clearml_yolo.core.transforms import TransformConfig


class AugmentedYOLODataset(YOLODataset):
    """The native dataset retains indexing/cache labels, while pixels stay unresized."""

    def __init__(self, *args: Any, transforms: TransformConfig, **kwargs: Any) -> None:
        if transforms.snapshot is None:
            raise ValueError("YOLO custom training requires a resolved transform snapshot")
        self.pipeline = TrainingPipeline(transforms.snapshot, seed=int(torch.initial_seed()))
        super().__init__(*args, **kwargs)

    @override
    def load_image(
        self, i: int, rect_mode: bool = True, resize_short: bool = False
    ) -> tuple[NDArray[np.uint8], tuple[int, int], tuple[int, int]]:
        del rect_mode, resize_short
        # Do not read upstream .npy/RAM caches that may contain eagerly resized pixels.
        # PIL decoding also guarantees the RGB contract for grayscale/alpha sources.
        with Image.open(self.im_files[i]) as source:
            # Native decoding and cached label dimensions already honor EXIF orientation.
            rgb = np.array(
                ImageOps.exif_transpose(source).convert("RGB"), dtype=np.uint8, copy=True
            )
        height, width = rgb.shape[:2]
        return np.ascontiguousarray(rgb[:, :, ::-1]), (height, width), (height, width)

    def raw_sample(self, index: int) -> DetectionSample:
        bgr, _, (height, width) = self.load_image(index)
        label = self.update_labels_info(deepcopy(self.labels[index]))
        instances = label["instances"]
        instances.convert_bbox("xyxy")
        instances.denormalize(width, height)
        count = len(label["cls"])
        return DetectionSample(
            image=np.ascontiguousarray(bgr[:, :, ::-1]),
            boxes=np.asarray(instances.bboxes, dtype=np.float32).reshape(-1, 4),
            labels=np.asarray(label["cls"], dtype=np.int64).reshape(-1),
            instance_ids=np.arange(count, dtype=np.int64),
            iscrowd=np.zeros(count, dtype=np.int64),
        )

    @override
    def build_transforms(self, hyp: Any = None) -> Any:
        del hyp
        # Native preprocessing consumes BGR uint8 and returns RGB CHW uint8.
        # Division by255 remains the trainer's responsibility.
        return Compose(  # type: ignore[no-untyped-call]  # Native composition is unannotated.
            [
                LetterBox(new_shape=self.imgsz, scaleup=True),
                Format(bbox_format="xywh", normalize=True, batch_idx=True, bgr=0.0),
            ]
        )

    @override
    def __getitem__(self, index: int) -> dict[str, Any]:
        original = self.raw_sample(index)
        sample = self.pipeline.apply(
            original,
            index=index,
            size=len(self),
            load_sample=self.raw_sample,
            seed=int(torch.initial_seed()),
        )
        labels: dict[str, Any] = {
            "im_file": self.im_files[index],
            "ori_shape": original.image.shape[:2],
            "resized_shape": sample.image.shape[:2],
            "ratio_pad": (1.0, 1.0),
            "img": np.ascontiguousarray(sample.image[:, :, ::-1]),
            "cls": sample.labels.astype(np.float32).reshape(-1, 1),
            "instances": Instances(
                sample.boxes,
                np.zeros((0, 1000, 2), dtype=np.float32),
                bbox_format="xyxy",
                normalized=False,
            ),
        }
        if self.rect:
            labels["rect_shape"] = self.batch_shapes[self.batch[index]]
        result: dict[str, Any] = self.transforms(labels)
        return result
