"""Convert native manifest inference into the digital-metrics prediction table.

A text manifest preserves filenames and native batching. Every requested image must
produce a result, including empty images; silently skipped images fail the invocation.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import pandas as pd
from loguru import logger
from pydantic import BaseModel

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

_MAX_REPORTED_PATHS = 5


class ScoredResolution(BaseModel):
    """The scale a checkpoint was trained at, beside the one it is being scored at.

    The two travel together because the second is only meaningful next to the first: 640 on
    its own says nothing, and 640 against weights trained at 1280 says the numbers that
    follow were measured on images unlike anything the model ever saw. ``trained_at`` is
    None when the checkpoint does not record it, which is not the same as agreeing.
    """

    trained_at: int | None
    scored_at: int | list[int]

    @property
    def was_trained_elsewhere(self) -> bool:
        """Whether the model is being scored at a scale it was never shown."""
        return self.trained_at is not None and self.trained_at != self.scored_at

    def as_table(self) -> pd.DataFrame:
        """The pair as a two-column table, for the run record rather than for the log.

        Rendered once here because both places that keep it — the ClearML plots tab and the
        sheet appended to the dev workbook — have to say the same thing, and a reader who
        finds one of them and not the other must not get two different answers. The verdict
        is spelled out rather than left as two numbers to compare, since the whole point is
        that a reader skimming for it should not have to notice they differ.
        """
        trained = "not recorded in the checkpoint" if self.trained_at is None else self.trained_at
        if self.trained_at is None:
            verdict = "unknown: the checkpoint does not say what it was trained at"
        elif self.was_trained_elsewhere:
            verdict = "NO — scored at a scale this model was never shown"
        else:
            verdict = "yes"
        return pd.DataFrame(
            {
                "parameter": ["trained at imgsz", "scored at imgsz", "same resolution?"],
                "value": [str(trained), str(self.scored_at), verdict],
            }
        )


def trained_imgsz(weights: str | Path) -> int | None:
    """The resolution these weights were trained at, or None if the file does not say.

    Ultralytics writes the whole training configuration into every checkpoint it saves,
    so the number does not have to be carried alongside the file and cannot go stale
    against it. A stage handed a checkpoint and no resolution asks it here rather than
    falling back to a library default, which is how a model trained at 1280 came to be
    scored at 640 without anything saying so.
    """
    from ultralytics.nn.tasks import torch_safe_load

    checkpoint, _ = torch_safe_load(str(weights))  # type: ignore[no-untyped-call]
    recorded = checkpoint.get("train_args", {}).get("imgsz")
    if isinstance(recorded, int):
        return recorded
    logger.warning(
        "{} records imgsz={!r}, which is not one resolution this can infer at",
        Path(weights).name,
        recorded,
    )
    return None


def resolution_of(weights: str | Path, imgsz: int | list[int] | None) -> ScoredResolution:
    """The resolution to infer at: the one asked for, or the one the weights were trained at.

    A model is shown images at one scale and generalises to that scale, so inferring at
    another scores it on images unlike anything it ever saw. The pipeline keeps the two in
    step itself, handing predict the resolution train just used, but a checkpoint reached
    any other way — a ClearML task, a file handed over — carries no such link, and 640 is
    a plausible enough number to be wrong without ever looking wrong.

    Both numbers come back rather than only the one inference needs. The checkpoint is read
    here either way, and a caller that reports how a result was produced would otherwise
    have to open it a second time to say what the model was built for.
    """
    recorded = trained_imgsz(weights)
    if imgsz is None:
        if recorded is None:
            raise ValueError(
                f"{Path(weights).name} does not record the resolution it was trained at, "
                "so there is nothing to infer imgsz from. Set imgsz explicitly."
            )
        logger.info(
            "Inferring at imgsz {}, the resolution {} was trained at",
            recorded,
            Path(weights).name,
        )
        return ScoredResolution(trained_at=recorded, scored_at=recorded)
    if recorded is not None and recorded != imgsz:
        logger.warning(
            "Inferring at imgsz {} on weights trained at {}: the model was never shown "
            "images at this scale, and thresholds calibrated here do not carry back to {}",
            imgsz,
            recorded,
            recorded,
        )
    return ScoredResolution(trained_at=recorded, scored_at=imgsz)


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
    imgsz: int | list[int] = 640,
    batch: int = 1,
    device: str | int | list[int] | None = None,
    image_name: ImageNameMode = "name",
    **model_kwargs: Any,
) -> pd.DataFrame:
    """Score images with native precision, compilation and device settings.

    The low confidence default retains detections for later validation calibration.
    Explicit native arguments override defaults without hardware-dependent rewriting.
    """
    if image_name not in ("name", "stem", "path"):
        raise ValueError(f"Unsupported image_name mode: {image_name!r}")
    if batch < 1:
        raise ValueError(f"batch must be >= 1, got {batch}")

    paths = [str(path) for path in image_paths]
    if not paths:
        logger.info("Predicted 0 boxes over 0 images")
        return pd.DataFrame(columns=PREDICTION_COLUMNS)

    from ultralytics.models import YOLO

    model = YOLO(str(weights))
    names: dict[int, str] = model.names
    settings: dict[str, Any] = {
        "conf": conf,
        "iou": iou,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "rect": True,
        **model_kwargs,
    }
    if "source" in settings or "stream" in settings:
        raise ValueError("source and stream are owned by dataset manifest inference")
    settings.setdefault("verbose", False)
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
        results: Any = model.predict(source=manifest, stream=True, **settings)
        for result in track(results, "Inference", total=len(paths), unit="img"):
            scored.add(result.path)
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                rows.extend(_detection_rows(by_absolute[result.path], boxes, names, image_name))

    _refuse_unscored(by_absolute, scored)
    logger.info("Predicted {} boxes over {} images", len(rows), len(scored))
    frame = pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
    # Opaque native predictor objects carry the arguments after native normalization.
    predictor: Any = getattr(model, "predictor", None)
    if predictor is not None:
        frame.attrs["effective_args"] = dict(vars(predictor.args))
        frame.attrs["save_dir"] = str(predictor.save_dir)
    frame.attrs["image_paths"] = sorted(by_absolute)
    return frame
