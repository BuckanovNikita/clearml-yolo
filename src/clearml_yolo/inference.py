"""Convert native manifest inference into the digital-metrics prediction table.

A text manifest preserves filenames and native batching. Every requested image must
produce a result, including empty images; silently skipped images fail the invocation.
"""

from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import pandas as pd
from loguru import logger
from pydantic import BaseModel

from clearml_yolo.filesystem import model_weights_path, temporary_root
from clearml_yolo.native_config import execution_settings
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
    """Checkpoint training size and requested inference size, before native normalization."""

    trained_at: int | None
    scored_at: int | list[int]

    @property
    def was_trained_elsewhere(self) -> bool:
        """Whether requested size differs from recorded training size before normalization."""
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
            verdict = "different requested size; compare the normalized predictor target"
        else:
            verdict = "yes"
        return pd.DataFrame(
            {
                "parameter": [
                    "trained at imgsz",
                    "requested inference imgsz",
                    "same requested size?",
                ],
                "value": [str(trained), str(self.scored_at), verdict],
            }
        )


def trained_imgsz(weights: str | Path) -> int | None:
    """Read checkpoint training resolution for diagnostics, never configuration defaults."""
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
    """Report checkpoint resolution without using it as an inference default."""
    if imgsz is None:
        raise ValueError(
            "Set imgsz explicitly in ultralytics_predict; checkpoint fallback was removed"
        )
    recorded = trained_imgsz(weights)
    if recorded is not None and recorded != imgsz:
        logger.warning(
            "Requested inference imgsz {} differs from weights trained at {}; "
            "compare the recorded normalized predictor target after native stride alignment",
            imgsz,
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
    image_name: ImageNameMode = "name",
    manifest_dir: Path | None = None,
    **model_kwargs: Any,
) -> pd.DataFrame:
    """Score images with native precision, compilation and device settings.

    All native options come from the resolved prediction group. Command-owned
    weights and image membership are the only additions at this boundary.
    """
    if image_name not in ("name", "stem", "path"):
        raise ValueError(f"Unsupported image_name mode: {image_name!r}")
    if "source" in model_kwargs or "stream" in model_kwargs:
        raise ValueError("source and stream are owned by dataset manifest inference")
    settings = execution_settings(model_kwargs | {"model": str(weights), "source": None}, "predict")
    settings.pop("model")
    settings.pop("source")

    paths = [str(path) for path in image_paths]
    if not paths:
        logger.info("Predicted 0 boxes over 0 images")
        return pd.DataFrame(columns=PREDICTION_COLUMNS)

    from ultralytics.models import YOLO

    model = YOLO(str(model_weights_path(weights)))
    if model.task != "detect":
        raise ValueError(f"Prediction requires a detection model; loaded task={model.task!r}")
    names: dict[int, str] = model.names
    logger.info(
        "Predicting on {} images with {} ({})",
        len(paths),
        Path(weights).name,
        ", ".join(f"{key}={value}" for key, value in settings.items()),
    )

    rows: list[dict[str, Any]] = []
    scored: set[str] = set()
    with TemporaryDirectory(prefix="clearml-yolo-inference-", dir=temporary_root()) as temporary:
        workspace = manifest_dir or Path(temporary)
        workspace.mkdir(parents=True, exist_ok=True)
        manifest, by_absolute = _write_manifest(paths, workspace)
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
        frame.attrs["normalized_imgsz"] = predictor.imgsz
    frame.attrs.setdefault("effective_args", settings.copy())
    frame.attrs["effective_args"].update(source=manifest, model=str(weights), mode="predict")
    frame.attrs["requested_args"] = settings | {
        "source": manifest,
        "model": str(weights),
        "mode": "predict",
    }
    native_model: Any = model.model
    frame.attrs["checkpoint_design"] = dict(native_model.yaml)
    frame.attrs["image_paths"] = sorted(by_absolute)
    return frame
