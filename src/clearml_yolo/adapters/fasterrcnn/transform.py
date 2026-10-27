"""Compatibility exports for shared Torchvision transform machinery."""

from clearml_yolo.adapters.torchvision.transform import (
    LetterboxTransform,
    canvas_size,
    resize_shape,
    scale_boxes,
)

__all__ = ["LetterboxTransform", "canvas_size", "resize_shape", "scale_boxes"]
