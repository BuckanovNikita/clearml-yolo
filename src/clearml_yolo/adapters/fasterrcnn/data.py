"""COCO prepared records with zero-based public classes and one-based detector labels."""

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, override

import numpy as np
import torch
import yaml
from PIL import Image
from pydantic import BaseModel, ConfigDict
from torch import Tensor
from torch.utils.data import Dataset

from clearml_yolo.adapters.augmentation.torch_data import training_pipeline, worker_seed
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.transforms import TransformConfig

if TYPE_CHECKING:
    from clearml_yolo.adapters.augmentation.pipeline import DetectionSample


class CocoImage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    file_name: str
    height: int
    width: int


class CocoAnnotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_id: int
    category_id: int
    bbox: tuple[float, float, float, float]
    area: float
    iscrowd: int = 0


class CocoCategory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str


class CocoRecords(BaseModel):
    model_config = ConfigDict(extra="ignore")
    images: list[CocoImage]
    annotations: list[CocoAnnotation]
    categories: list[CocoCategory]


def image_tensor(path: Path) -> Tensor:
    with Image.open(path) as source:
        pixels = np.array(source.convert("RGB"), dtype=np.uint8, copy=True)
    return torch.from_numpy(pixels).permute(2, 0, 1).float().div(255)


class CocoDataset(Dataset[tuple[Tensor, dict[str, Tensor]]]):
    def __init__(
        self,
        annotation_file: Path,
        names: tuple[str, ...],
        *,
        transforms: TransformConfig | None = None,
        seed: int = 0,
    ) -> None:
        self.annotation_file = annotation_file
        self.pipeline = training_pipeline(transforms, seed)
        self.seed = seed
        self.records = CocoRecords.model_validate_json(annotation_file.read_text(encoding="utf-8"))
        categories = sorted(self.records.categories, key=lambda item: item.id)
        if [(item.id, item.name) for item in categories] != list(enumerate(names)):
            raise ValueError("COCO category IDs and names must match the checkpoint vocabulary")
        self.annotations: dict[int, list[CocoAnnotation]] = defaultdict(list)
        image_ids = {image.id for image in self.records.images}
        if len(image_ids) != len(self.records.images):
            raise ValueError("COCO image IDs must be unique")
        for annotation in self.records.annotations:
            if annotation.image_id not in image_ids or not 0 <= annotation.category_id < len(names):
                raise ValueError("COCO annotation references an unknown image or class")
            if annotation.bbox[2] <= 0 or annotation.bbox[3] <= 0:
                raise ValueError("COCO training boxes must have positive width and height")
            self.annotations[annotation.image_id].append(annotation)

    def __len__(self) -> int:
        return len(self.records.images)

    @override
    def __getitem__(self, index: int) -> tuple[Tensor, dict[str, Tensor]]:
        if self.pipeline is not None:
            return self._augmented_item(index)
        image = self.records.images[index]
        pixels = image_tensor(self.annotation_file.parent / image.file_name)
        if tuple(pixels.shape[-2:]) != (image.height, image.width):
            raise ValueError("COCO image dimensions disagree with source pixels")
        annotations = self.annotations[image.id]
        boxes = [
            [x, y, x + width, y + height]
            for x, y, width, height in (annotation.bbox for annotation in annotations)
        ]
        target = {
            "boxes": torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4),
            "labels": torch.tensor(
                [annotation.category_id + 1 for annotation in annotations], dtype=torch.int64
            ),
            "image_id": torch.tensor(image.id, dtype=torch.int64),
            "area": torch.tensor([annotation.area for annotation in annotations]),
            "iscrowd": torch.tensor([annotation.iscrowd for annotation in annotations]),
        }
        return pixels, target

    def raw_sample(self, index: int) -> "DetectionSample":
        """Read original RGB pixels for primary images and unaugmented mosaic donors."""
        from clearml_yolo.adapters.augmentation.pipeline import DetectionSample

        image = self.records.images[index]
        with Image.open(self.annotation_file.parent / image.file_name) as source:
            pixels = np.array(source.convert("RGB"), dtype=np.uint8, copy=True)
        if pixels.shape[:2] != (image.height, image.width):
            raise ValueError("COCO image dimensions disagree with source pixels")
        annotations = self.annotations[image.id]
        return DetectionSample(
            image=pixels,
            boxes=np.array(
                [
                    [x, y, x + width, y + height]
                    for x, y, width, height in (item.bbox for item in annotations)
                ],
                dtype=np.float32,
            ).reshape(-1, 4),
            labels=np.array([item.category_id for item in annotations], dtype=np.int64),
            instance_ids=np.arange(len(annotations), dtype=np.int64),
            iscrowd=np.array([item.iscrowd for item in annotations], dtype=np.int64),
        )

    def _augmented_item(self, index: int) -> tuple[Tensor, dict[str, Tensor]]:
        if self.pipeline is None:
            raise RuntimeError("Custom training requires an augmentation pipeline")
        sample = self.pipeline.apply(
            self.raw_sample(index),
            index=index,
            size=len(self),
            load_sample=self.raw_sample,
            seed=worker_seed(self.seed),
        )
        boxes = torch.from_numpy(sample.boxes.copy())
        target = {
            "boxes": boxes,
            "labels": torch.from_numpy(sample.labels.copy()) + 1,
            "image_id": torch.tensor(self.records.images[index].id, dtype=torch.int64),
            "area": (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]),
            "iscrowd": torch.from_numpy(sample.iscrowd.copy()),
        }
        pixels = torch.from_numpy(sample.image.copy()).permute(2, 0, 1).float().div(255)
        return pixels, target


def prepared_datasets(
    prepared: PreparedDataset,
    *,
    transforms: TransformConfig | None = None,
    seed: int = 0,
) -> tuple[CocoDataset, CocoDataset, tuple[str, ...]]:
    if prepared.dataset_format != "coco":
        raise ValueError("Faster R-CNN requires the prepared COCO dataset format")
    contents = yaml.safe_load(prepared.data.read_text())
    names_value = contents["names"]
    names = (
        tuple(names_value[key] for key in sorted(names_value))
        if isinstance(names_value, dict)
        else tuple(names_value)
    )
    root = Path(contents.get("path", prepared.data.parent))
    if not root.is_absolute():
        root = prepared.data.parent / root
    train = CocoDataset(
        root / contents["train"] / "_annotations.coco.json", names, transforms=transforms, seed=seed
    )
    validation = CocoDataset(root / contents["val"] / "_annotations.coco.json", names)
    if not len(train) or not len(validation) or not validation.records.annotations:
        raise ValueError("Training needs images; validation needs labeled boxes to select best mAP")
    return train, validation, names


def collate_detection(
    batch: list[tuple[Tensor, dict[str, Tensor]]],
) -> tuple[list[Tensor], list[dict[str, Tensor]]]:
    return [image for image, _ in batch], [target for _, target in batch]
