"""Run a checkpoint over a list of images, returning detections in digital-metrics' schema.

This is digital-metrics' ``predict_on_images`` given a progress signal and GPU-side
defaults. It lives here rather than upstream because digital-metrics is consumed as a
released package.

**The source is a manifest, and that is the whole trick.** Ultralytics routes a *list*
source through ``autocast_list`` into ``LoadPilAndNumpy``, which sets ``bs = len(list)``
and never consults the ``batch`` argument, so the whole list becomes one forward pass —
on 748 images that is ~40% slower and 18 GB of VRAM instead of 3 GB. The same loader names
images from PIL's ``filename``, which is lost through ``ImageOps.exif_transpose``'s copy,
so ``Results.path`` comes back as ``image0.jpg``. Both problems belong to the list form
alone. A ``.txt`` of paths goes to ``LoadImagesAndVideos`` instead, which honours
``batch``, reports the real file, and decodes with the same OpenCV call training uses — so
no EXIF rotation appears between training and inference. One ``predict`` call therefore
does the whole run, and every box is attributed by path rather than by position.

Two consequences of that loader are handled here. It absolutises every manifest entry and
sorts the file list, so results arrive neither spelled nor ordered as the caller wrote
them; the join back is keyed on the same absolutisation. And it *skips* an image OpenCV
cannot decode, logging a warning, which would quietly shrink the scored set and surface
downstream as a recall drop that reads like a model regression — so every requested image
is accounted for before returning.

On CUDA, half precision and ``torch.compile`` are both on by default. Measured on 748
KITTI images with a fine-tuned yolo11 on an RTX 5090, neither buys much on a model that
small — preprocess 1.31 ms/img, GPU inference 0.53 ms/img, postprocess 0.93 ms/img, so the
network is a minority of the time, ``half`` measured ~5% slower and ``compile`` costs a
one-off compilation against a ~5% steady-state gain. Both are still on because both scale
with model size, and both are one ``predict_kwargs`` entry away from off.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

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

# Everything ultralytics accepts that is not one of these is a CUDA ordinal ("0", "0,1")
# or an explicit cuda device ("cuda:0").
NON_CUDA_DEVICES = frozenset({"cpu", "mps"})

_MAX_REPORTED_PATHS = 5


def is_cuda_device(device: str | None) -> bool:
    """Whether inference will run on a CUDA card.

    Two defaults hang off this — half precision and ``torch.compile`` — because neither is
    available anywhere else. It also has to reach anything that caches or compares
    predictions, since both change which boxes come back: an FP32 cache scored against
    fresh FP16 detections is a model difference that is not one.

    With no device named, ultralytics picks the card itself, so the question is only
    whether this machine has one.
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


def _precision(accelerated: bool, model_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Ask for FP16 on a card, unless the caller already said something about precision.

    Ultralytics 8.4 deprecated ``half`` in favour of ``quantize`` (16 for FP16, 32 for
    FP32) and forwards the old name onto the new one — but only when ``quantize`` is
    absent. So passing ``quantize`` here unconditionally would make a caller's
    ``half=False`` silently do nothing, which is the sort of override that looks like it
    worked. Naming either one hands the whole decision back.
    """
    if {"half", "quantize"} & model_kwargs.keys():
        return {}
    return {"quantize": 16 if accelerated else 32}


def _write_manifest(paths: list[str], directory: Path) -> tuple[str, dict[str, str]]:
    """Write the file list ultralytics will read, and the map from what it reports back.

    Entries are absolute so the loader's relative-to-the-manifest branch never runs, and
    the returned map is keyed by the same ``Path.absolute()`` the loader applies — the
    identical, deliberately non-normalising transform on both sides is what makes the keys
    meet. The map's values are the caller's own spelling, which ``image_name="path"``
    writes into the join key.
    """
    by_absolute = {str(Path(path).absolute()): path for path in paths}
    manifest = directory / "images.txt"
    manifest.write_text("\n".join(by_absolute.keys()))
    return str(manifest), by_absolute


def _refuse_unscored(by_absolute: dict[str, str], scored: set[str]) -> None:
    """Refuse to return detections for fewer images than were asked for.

    ``LoadImagesAndVideos`` logs a warning and moves on when OpenCV cannot decode a file,
    and drops anything whose suffix it does not recognise as an image without saying
    anything at all. Both leave a smaller scored set behind, which reads downstream as
    missing detections rather than as missing images.
    """
    missing = [path for absolute, path in by_absolute.items() if absolute not in scored]
    if not missing:
        return
    shown = missing[:_MAX_REPORTED_PATHS]
    suffix = "" if len(missing) <= _MAX_REPORTED_PATHS else f" (+{len(missing) - len(shown)})"
    raise ValueError(
        f"Ultralytics returned no result for {len(missing)} of {len(by_absolute)} images; "
        f"they are undecodable or not a recognised image format: {shown}{suffix}"
    )


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

    ``batch`` is mainly the memory knob: it is how many images go through the network at
    once and how many are held decoded at once, so peak RAM and VRAM are both proportional
    to it. Lower it (or ``imgsz``) to fit a smaller card.

    ``conf`` defaults to near zero because per-class thresholds are calibrated downstream,
    and filtering here would discard the detections that calibration needs.

    Half precision and ``torch.compile`` are both on by default wherever the device supports
    them. Both pay off on a model heavy enough to be GPU-bound, and both change which boxes
    come back, so thresholds calibrated without them do not carry over — recalibrate rather
    than mixing. See the module docstring for what each measured on a small model.

    ``model_kwargs`` reach ``model.predict`` untouched, so ``quantize=32`` (or the
    deprecated ``half=False``) and ``compile=False`` turn either back off for a run that has
    to reproduce numbers taken before these defaults.

    Raises:
        ValueError: If ``batch`` is below one, or if any requested image came back
            unscored because ultralytics could not read it.
    """
    if batch < 1:
        raise ValueError(f"batch must be >= 1, got {batch}")

    paths = [str(path) for path in image_paths]
    if not paths:
        logger.info("Predicted 0 boxes over 0 images")
        return pd.DataFrame(columns=PREDICTION_COLUMNS)

    from ultralytics.models import YOLO

    model = YOLO(str(weights))
    names: dict[int, str] = model.names
    accelerated = is_cuda_device(device)
    settings: dict[str, Any] = {
        "conf": conf,
        "iou": iou,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "compile": accelerated,
        **_precision(accelerated, model_kwargs),
        **model_kwargs,
    }
    logger.info(
        "Predicting on {} images with {} ({})",
        len(paths),
        Path(weights).name,
        ", ".join(f"{key}={value}" for key, value in settings.items()),
    )

    rows: list[dict[str, Any]] = []
    scored: set[str] = set()
    with TemporaryDirectory() as workspace:
        manifest, by_absolute = _write_manifest(paths, Path(workspace))
        # Ultralytics types predict as returning `list[Results] | Tensor` regardless of
        # `stream`, so the annotation has to be widened rather than narrowed.
        results: Any = model.predict(source=manifest, stream=True, verbose=False, **settings)
        for result in track(results, "Inference", total=len(paths), unit="img"):
            scored.add(result.path)
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                rows.extend(_detection_rows(by_absolute[result.path], boxes, names, image_name))

    _refuse_unscored(by_absolute, scored)
    logger.info("Predicted {} boxes over {} images", len(rows), len(scored))
    return pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
