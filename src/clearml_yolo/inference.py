"""Run a checkpoint over a list of images, returning detections in digital-metrics' schema.

This replaces ``digital_metrics.inference.predict_on_images``, which issues one
``model.predict`` call per chunk of paths but never passes ``batch``. Ultralytics builds
its dataloader with ``batch=self.args.batch`` (default 1), so every image got its own
forward pass and the card sat idle between them; the chunking bounded peak VRAM but the
batch argument does that too, and fills the GPU while it is at it.

The other difference is how detections are attributed to images. Ultralytics sorts a list
source and rewrites the paths to absolute, so zipping its results against the input order
misattributes boxes whenever the caller's list is not already sorted. Every result here is
keyed by ``Results.path`` instead, which ultralytics sets to the file it actually read.
"""

from __future__ import annotations

from collections.abc import Sequence
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

# Devices that cannot run half precision. Everything else ultralytics accepts is a CUDA
# ordinal ("0", "0,1") or an explicit cuda device ("cuda:0").
NON_CUDA_DEVICES = frozenset({"cpu", "mps"})


def uses_half_precision(device: str | None) -> bool:
    """Whether inference on ``device`` should run in FP16.

    Half precision roughly halves inference time on a CUDA card and is unsupported
    elsewhere. With no device named, ultralytics picks the card itself, so the question is
    simply whether this machine has one.
    """
    if not device:
        from torch.cuda import is_available

        return bool(is_available())
    return not any(part.strip().lower() in NON_CUDA_DEVICES for part in str(device).split(","))


def _image_id(path: str, mode: ImageNameMode) -> str:
    """Derive the ``image_name`` that joins a detection back to the ground truth."""
    if mode == "stem":
        return Path(path).stem
    if mode == "path":
        return path
    return Path(path).name


def _detection_rows(
    path: str,
    xyxy: npt.NDArray[Any],
    confidence: npt.NDArray[Any],
    classes: npt.NDArray[Any],
    names: dict[int, str],
    mode: ImageNameMode,
) -> list[dict[str, Any]]:
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
        for (x1, y1, x2, y2), score, class_index in zip(xyxy, confidence, classes, strict=True)
    ]


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

    ``batch`` is both the throughput knob and the memory knob: ultralytics runs one forward
    pass per batch and holds that many images' tensors at a time, so peak VRAM stays
    proportional to it. Lower it (or ``imgsz``) to fit a smaller card.

    ``conf`` defaults to near zero because per-class thresholds are calibrated downstream,
    and filtering here would discard the detections that calibration needs.

    ``model_kwargs`` reach ``model.predict`` untouched, which is also how to override the
    ``half`` default (``half=False`` to force FP32 on a CUDA card).
    """
    if batch < 1:
        raise ValueError(f"batch must be >= 1, got {batch}")

    from ultralytics.models import YOLO

    paths = [str(path) for path in image_paths]
    # Ultralytics reports each result under the absolute path it opened, while the caller
    # joins on the string it passed in; `image_name="path"` makes the difference visible.
    source_of_result = {str(Path(path).absolute()): path for path in paths}

    model = YOLO(str(weights))
    names: dict[int, str] = model.names
    settings: dict[str, Any] = {
        "conf": conf,
        "iou": iou,
        "imgsz": imgsz,
        "device": device,
        "half": uses_half_precision(device),
        **model_kwargs,
    }
    logger.info(
        "Predicting on {} images with {} (batch={}, {})",
        len(paths),
        Path(weights).name,
        batch,
        ", ".join(f"{key}={value}" for key, value in settings.items()),
    )

    # Ultralytics types this as yielding Results or, under `embed=`, raw tensors; nothing
    # here asks for embeddings, so the generator is opaque rather than a union to narrow.
    results: Any = model.predict(
        source=paths, stream=True, batch=batch, verbose=False, **settings
    )

    rows: list[dict[str, Any]] = []
    scored = 0
    for result in track(results, "Inference", total=len(paths), unit="img"):
        scored += 1
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue
        rows.extend(
            _detection_rows(
                source_of_result.get(result.path, result.path),
                boxes.xyxy.cpu().numpy(),
                boxes.conf.cpu().numpy(),
                boxes.cls.cpu().numpy(),
                names,
                image_name,
            )
        )

    if scored != len(paths):
        # Ultralytics silently drops sources whose extension it does not recognise as an
        # image, which would otherwise show up much later as unexplained missed detections.
        logger.warning(
            "Asked for {} images but ultralytics returned {}; the difference was not "
            "recognised as image files",
            len(paths),
            scored,
        )
    logger.info("Predicted {} boxes over {} images", len(rows), scored)
    return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
