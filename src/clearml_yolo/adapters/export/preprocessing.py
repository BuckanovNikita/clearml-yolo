"""Portable native letterboxing and inverse coordinates for exported detectors."""

from typing import cast

import numpy as np
from numpy.typing import NDArray

_MAX_BATCH = 4
_RGB_CHANNELS = 3
_STRIDE = 32
_ROW_WIDTH = 6
_TENSOR_RANK = 3


def _resize(values: NDArray[np.float32], size: tuple[int, int]) -> NDArray[np.float32]:
    if values.shape[-2:] == size:
        return values
    axes = []
    for source, target in zip(values.shape[-2:], size, strict=True):
        scale = np.float32(source / target)
        coordinate = (np.arange(target, dtype=np.float32) + np.float32(0.5)) * scale - np.float32(
            0.5
        )
        coordinate = np.maximum(coordinate, np.float32(0))
        lower = coordinate.astype(np.int64)
        upper = np.minimum(lower + 1, source - 1)
        weight = coordinate - lower.astype(np.float32)
        axes.append((lower, upper, weight))
    low, high, weight = axes[1]
    horizontal = values[:, :, low] * (1 - weight) + values[:, :, high] * weight
    low, high, weight = axes[0]
    result = (
        horizontal[:, low, :] * (1 - weight[None, :, None])
        + horizontal[:, high, :] * weight[None, :, None]
    )
    return cast(NDArray[np.float32], result)


def preprocess(
    images: list[NDArray[np.uint8]],
    canvas: tuple[int, int],
    *,
    mean: tuple[float, float, float] = (0.485, 0.456, 0.406),
    std: tuple[float, float, float] = (0.229, 0.224, 0.225),
) -> tuple[NDArray[np.float32], NDArray[np.int64]]:
    """Accept RGB uint8 HWC, normalize before bilinear resize, pad top-left.

    Canvas is (height,width), including stride padding, matching LetterboxTransform.
    """
    if not 1 <= len(images) <= _MAX_BATCH or min(canvas) <= 0 or any(d % _STRIDE for d in canvas):
        raise ValueError("Preprocessing requires batch 1-4 and a positive stride32 canvas")
    mean_array = np.array(mean, dtype=np.float32)[:, None, None]
    std_array = np.array(std, dtype=np.float32)[:, None, None]
    if (
        not np.isfinite(mean_array).all()
        or not np.isfinite(std_array).all()
        or np.any(std_array <= 0)
    ):
        raise ValueError("Normalization requires finite means and positive finite deviations")
    result = np.zeros((len(images), _RGB_CHANNELS, *canvas), dtype=np.float32)
    valid: list[tuple[int, int]] = []
    for index, image in enumerate(images):
        if (
            image.dtype != np.uint8
            or image.ndim != _TENSOR_RANK
            or image.shape[2] != _RGB_CHANNELS
            or min(image.shape[:2]) <= 0
        ):
            raise ValueError("Source images must be nonempty RGB uint8 HWC arrays")
        original = image.shape[:2]
        scale = min(canvas[0] / original[0], canvas[1] / original[1])
        size = tuple(
            max(1, min(limit, round(d * scale))) for d, limit in zip(original, canvas, strict=True)
        )
        normalized = (
            image.transpose(2, 0, 1).astype(np.float32) / np.float32(255) - mean_array
        ) / std_array
        result[index, :, : size[0], : size[1]] = _resize(normalized, size)
        valid.append(size)
    return result, np.array(valid, dtype=np.int64)


def validate_detections(
    detections: NDArray[np.float32],
    counts: NDArray[np.int64],
    *,
    class_count: int | None = None,
    image_sizes: NDArray[np.int64] | None = None,
) -> None:
    """Validate fixed outputs, foreground labels, padding and optional canvas bounds."""
    if (
        detections.dtype != np.float32
        or detections.ndim != _TENSOR_RANK
        or detections.shape[2] != _ROW_WIDTH
    ):
        raise ValueError("detections must be float32 [batch,max_det,6]")
    if counts.dtype != np.int64 or counts.shape != (detections.shape[0],):
        raise ValueError("counts must be int64 [batch]")
    if (
        not np.isfinite(detections).all()
        or np.any(counts < 0)
        or np.any(counts > detections.shape[1])
    ):
        raise ValueError("Detection outputs must be finite with counts inside the padded output")
    if class_count is not None and class_count < 1:
        raise ValueError("Foreground class count must be positive")
    if image_sizes is not None and (
        image_sizes.dtype != np.int64
        or image_sizes.shape != (detections.shape[0], 2)
        or np.any(image_sizes <= 0)
    ):
        raise ValueError("Valid image size metadata does not match the detection batch")
    _validate_rows(detections, counts, class_count, image_sizes)


def _validate_rows(
    detections: NDArray[np.float32],
    counts: NDArray[np.int64],
    class_count: int | None,
    image_sizes: NDArray[np.int64] | None,
) -> None:
    for index, count in enumerate(counts):
        rows = detections[index, :count]
        if np.any(detections[index, count:] != 0):
            raise ValueError("Detection padding must be zero")
        if np.any(rows[:, 4] < 0) or np.any(rows[:, 4] > 1):
            raise ValueError("Detection confidences must lie in [0,1]")
        labels = rows[:, 5]
        if (
            np.any(labels < 1)
            or np.any(labels != np.floor(labels))
            or (class_count is not None and np.any(labels > class_count))
        ):
            raise ValueError("Detection labels must be native integer foreground IDs")
        if np.any(rows[:, :2] < 0) or np.any(rows[:, 2:4] < rows[:, :2]):
            raise ValueError("Detection coordinates must be nonnegative ordered xyxy")
        if image_sizes is not None and np.any(rows[:, 2:4] > image_sizes[index, ::-1]):
            raise ValueError("Detection coordinates exceed the valid resized image")


def postprocess(
    detections: NDArray[np.float32],
    counts: NDArray[np.int64],
    original_sizes: list[tuple[int, int]],
    valid_sizes: NDArray[np.int64],
    *,
    class_count: int | None = None,
) -> list[NDArray[np.float32]]:
    """Return xyxy/conf/zero-based foreground IDs in original image coordinates."""
    validate_detections(detections, counts, class_count=class_count, image_sizes=valid_sizes)
    if len(original_sizes) != detections.shape[0] or any(min(size) <= 0 for size in original_sizes):
        raise ValueError("Original image sizes must be positive and match the detection batch")
    result = []
    for index, original in enumerate(original_sizes):
        rows = detections[index, : int(counts[index])].copy()
        rows[:, (0, 2)] *= np.float32(original[1] / valid_sizes[index, 1])
        rows[:, (1, 3)] *= np.float32(original[0] / valid_sizes[index, 0])
        rows[:, 5] -= 1
        result.append(rows)
    return result
