"""Run a checkpoint over a list of images, returning detections in digital-metrics' schema.

This is digital-metrics' ``predict_on_images`` made faster and given a progress signal. It
lives here rather than upstream because digital-metrics is consumed as a released package.

**Where the time actually goes.** Measured on 748 KITTI images with a fine-tuned yolo11 on
an RTX 5090: preprocess 1.31 ms/img, GPU inference 0.53 ms/img, postprocess 0.93 ms/img,
image decode ~0.9 ms/img. The network is under a tenth of the wall clock, so neither a
bigger batch nor half precision buys anything — both measured *slower*. What does buy
something is decoding off the main thread: ultralytics decodes a list source inline, one
image at a time, so the card idles through it. Decoding the next chunk while the current
one is on the GPU took the same 748 images from 3.9 s to 1.7 s, to the box.

**Two ultralytics behaviours are load-bearing, and both are the opposite of what the API
suggests.** A *list* source is not read like a directory: ``check_source`` hands it to
``autocast_list`` and the resulting ``LoadPilAndNumpy`` sets ``bs = len(list)``, so the whole
list becomes one forward pass and the ``batch`` predict argument is never consulted.
Chunking is therefore the only way to choose a batch size, and the chunk length *is* the
batch. Passing all 748 images at once costs both ways: ~40% slower and 18 GB of VRAM
instead of 3 GB.

And ``Results.path`` cannot be trusted for a list source — ``LoadPilAndNumpy`` names images
from PIL's ``filename``, which is lost through ``ImageOps.exif_transpose``'s copy, so paths
come back as ``image0.jpg``. Order *is* input order (nothing sorts a list source), so pairing
positionally is both correct and the only option; ``strict=True`` turns any future
divergence into an exception rather than silently mislabelled detections.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

import numpy.typing as npt
import pandas as pd
from loguru import logger

from clearml_yolo.progress import track

ImageNameMode = Literal["name", "stem", "path"]

# The seven columns digital-metrics' Evaluation requires of a predictions frame.
PREDICTION_COLUMNS = [
    "image_name",
    "instance_label",
    "confidence",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
]

# Decoding is what the card waits on, and it is I/O plus a GIL-releasing OpenCV call, so
# threads are enough. Four saturated the measurement; eight added nothing, so this is not
# exposed as a config key that would then have to be kept in step with three others.
DECODE_WORKERS = 4


def _image_id(path: str, mode: ImageNameMode) -> str:
    """Derive the ``image_name`` that joins a detection back to the ground truth."""
    if mode == "stem":
        return Path(path).stem
    if mode == "path":
        return path
    return Path(path).name


def _detection_rows(path: str, boxes: Any, names: dict[int, str], mode: ImageNameMode) -> Any:
    """Convert one image's detections into schema rows."""
    image_name = _image_id(path, mode)
    return [
        {
            "image_name": image_name,
            "instance_label": names[int(class_index)],
            "confidence": float(score),
            "bbox_x_tl": float(x1),
            "bbox_y_tl": float(y1),
            "bbox_x_br": float(x2),
            "bbox_y_br": float(y2),
        }
        for (x1, y1, x2, y2), score, class_index in zip(
            boxes.xyxy.cpu().numpy(),
            boxes.conf.cpu().numpy(),
            boxes.cls.cpu().numpy(),
            strict=True,
        )
    ]


def _read_image(path: str) -> npt.NDArray[Any]:
    """Decode one image the way ultralytics does for a directory source and for training.

    OpenCV rather than PIL, so inference sees the same pixels training did. The difference
    that matters is EXIF orientation, which OpenCV ignores and PIL applies; ultralytics'
    own file loaders ignore it too, so this follows them rather than the list-source path.
    """
    import cv2

    image: npt.NDArray[Any] | None = cv2.imread(path)
    if image is None:
        raise ValueError(f"Cannot decode {path} as an image")
    return image


def _decoded_chunks(
    paths: list[str], batch: int, workers: int
) -> Iterator[tuple[list[str], list[npt.NDArray[Any]]]]:
    """Yield each chunk already decoded, having decoded it while the previous one ran.

    Ultralytics decodes a list source inline, so without this the card sits idle for the
    ~0.9 ms per image that decoding costs — comparable to everything else put together.
    """
    chunks = [paths[start : start + batch] for start in range(0, len(paths), batch)]
    if not chunks:
        return
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = [pool.submit(_read_image, path) for path in chunks[0]]
        for index, chunk in enumerate(chunks):
            images = [future.result() for future in pending]
            if index + 1 < len(chunks):
                pending = [pool.submit(_read_image, path) for path in chunks[index + 1]]
            yield chunk, images


def _scored_images(
    model: Any, paths: list[str], batch: int, settings: dict[str, Any]
) -> Iterator[tuple[str, Any]]:
    """Yield ``(path, result)`` for every image, one ``predict`` call per ``batch`` of them."""
    for chunk, images in _decoded_chunks(paths, batch, DECODE_WORKERS):
        results = model.predict(source=images, stream=True, verbose=False, **settings)
        yield from zip(chunk, results, strict=True)


def predict_on_images(
    weights: str | Path,
    image_paths: Sequence[str],
    *,
    conf: float = 0.001,
    iou: float = 0.7,
    imgsz: int = 640,
    batch: int = 16,
    device: str | None = None,
    image_name: ImageNameMode = "name",
    **model_kwargs: Any,
) -> pd.DataFrame:
    """Score ``image_paths`` with ``weights`` and return the detections as a DataFrame.

    ``batch`` is both the throughput knob and the memory knob: it is how many images go
    through the network at once and how many are held decoded at once, so peak RAM and VRAM
    are both proportional to it. Lower it (or ``imgsz``) to fit a smaller card.

    ``conf`` defaults to near zero because per-class thresholds are calibrated downstream,
    and filtering here would discard the detections that calibration needs.

    ``model_kwargs`` reach ``model.predict`` untouched, so ``half=True`` is how to ask for
    FP16. It is not the default: the network is under a tenth of this loop's wall clock, so
    half precision measured *slower* here while still shifting confidences enough to move
    calibrated thresholds. Turn it on only for a model heavy enough to be GPU-bound, and
    re-calibrate afterwards.
    """
    if batch < 1:
        raise ValueError(f"batch must be >= 1, got {batch}")

    from ultralytics.models import YOLO

    paths = [str(path) for path in image_paths]
    model = YOLO(str(weights))
    names: dict[int, str] = model.names
    settings: dict[str, Any] = {
        "conf": conf,
        "iou": iou,
        "imgsz": imgsz,
        "device": device,
        **model_kwargs,
    }
    logger.info(
        "Predicting on {} images with {} (batch={}, {})",
        len(paths),
        Path(weights).name,
        batch,
        ", ".join(f"{key}={value}" for key, value in settings.items()),
    )

    rows: list[dict[str, Any]] = []
    scored = 0
    for path, result in track(
        _scored_images(model, paths, batch, settings), "Inference", total=len(paths), unit="img"
    ):
        scored += 1
        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            rows.extend(_detection_rows(path, boxes, names, image_name))

    logger.info("Predicted {} boxes over {} images", len(rows), scored)
    return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
