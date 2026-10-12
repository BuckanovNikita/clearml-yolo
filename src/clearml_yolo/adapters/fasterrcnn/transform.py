"""Shared RGB normalization, aspect-preserving canvas resize and box restoration."""

import importlib
from collections.abc import Sequence
from typing import Any, override

import torch
from torch import Tensor, nn
from torch.nn import functional

from clearml_yolo.adapters.fasterrcnn.configuration import MEAN, STD, STRIDE
from clearml_yolo.core.models import ImageSize


def canvas_size(size: ImageSize) -> tuple[int, int]:
    """ImageSize pairs are height/width; round the canvas up to the feature stride."""
    height, width = (size, size) if isinstance(size, int) else size
    return ((height + STRIDE - 1) // STRIDE * STRIDE, (width + STRIDE - 1) // STRIDE * STRIDE)


def resize_shape(original: tuple[int, int], canvas: tuple[int, int]) -> tuple[int, int]:
    scale = min(canvas[0] / original[0], canvas[1] / original[1])
    return (
        max(1, min(canvas[0], round(original[0] * scale))),
        max(1, min(canvas[1], round(original[1] * scale))),
    )


def scale_boxes(boxes: Tensor, source: tuple[int, int], destination: tuple[int, int]) -> Tensor:
    factors = boxes.new_tensor(
        [
            destination[1] / source[1],
            destination[0] / source[0],
            destination[1] / source[1],
            destination[0] / source[0],
        ]
    )
    return boxes * factors


class LetterboxTransform(nn.Module):
    """Torchvision-compatible transform with a fixed canvas and unpadded image sizes.

    Padding is zero in normalized RGB space (the mean color). Images resize using
    bilinear interpolation without antialiasing; the portable runner reproduces this
    exact contract. The ImageList type is opaque because Torchvision ships no stubs.
    """

    def __init__(self, image_size: ImageSize) -> None:
        super().__init__()
        self.canvas_size = canvas_size(image_size)
        self.image_mean = list(MEAN)
        self.image_std = list(STD)
        self.size_divisible = STRIDE

    def normalize(self, image: Tensor) -> Tensor:
        mean = image.new_tensor(self.image_mean)[:, None, None]
        std = image.new_tensor(self.image_std)[:, None, None]
        return (image - mean) / std

    @override
    def forward(
        self, images: list[Tensor], targets: list[dict[str, Tensor]] | None = None
    ) -> tuple[Any, list[dict[str, Tensor]] | None]:
        resized: list[Tensor] = []
        sizes: list[tuple[int, int]] = []
        transformed = [dict(target) for target in targets] if targets is not None else None
        for index, image in enumerate(images):
            original = (image.shape[-2], image.shape[-1])
            size = resize_shape(original, self.canvas_size)
            normalized = self.normalize(image)
            pixels = functional.interpolate(
                normalized[None],
                size=size,
                mode="bilinear",
                align_corners=False,
                antialias=False,
            )[0]
            resized.append(
                functional.pad(
                    pixels, (0, self.canvas_size[1] - size[1], 0, self.canvas_size[0] - size[0])
                )
            )
            sizes.append(size)
            if transformed is not None:
                transformed[index]["boxes"] = scale_boxes(
                    transformed[index]["boxes"], original, size
                )
        image_list = importlib.import_module("torchvision.models.detection.image_list")
        return image_list.ImageList(torch.stack(resized), sizes), transformed

    def postprocess(
        self,
        results: list[dict[str, Tensor]],
        image_shapes: Sequence[tuple[int, int]],
        original_image_sizes: Sequence[tuple[int, int]],
    ) -> list[dict[str, Tensor]]:
        if self.training:
            return results
        for result, source, destination in zip(
            results, image_shapes, original_image_sizes, strict=True
        ):
            result["boxes"] = scale_boxes(result["boxes"], source, destination)
        return results
