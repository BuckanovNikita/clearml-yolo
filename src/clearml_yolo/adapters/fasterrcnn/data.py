"""Compatibility exports for shared Torchvision data machinery."""

from clearml_yolo.adapters.torchvision.data import (
    CocoAnnotation,
    CocoCategory,
    CocoDataset,
    CocoImage,
    CocoRecords,
    collate_detection,
    image_tensor,
    prepared_datasets,
)

__all__ = [
    "CocoAnnotation",
    "CocoCategory",
    "CocoDataset",
    "CocoImage",
    "CocoRecords",
    "collate_detection",
    "image_tensor",
    "prepared_datasets",
]
