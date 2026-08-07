"""Run inference over the dataset and persist predictions in digital-metrics' schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from clearml_yolo import artifact_names
from clearml_yolo.clearml_models import resolve_weights
from clearml_yolo.clearml_session import ClearMLConfig, init_task, upload_dataframe
from clearml_yolo.gpu import AutoGpuConfig, remember_batch, resolve_inference
from clearml_yolo.inference import ImageNameMode, predict_on_images, resolution_of


def images_to_score(ground_truth: pd.DataFrame, splits: list[str] | None) -> list[str]:
    """The images of the requested splits, each named once.

    Ground truth carries one row per annotation, so an image with twelve boxes would
    otherwise be inferred twelve times.
    """
    if "image_path" not in ground_truth.columns:
        raise ValueError(
            "Ground truth has no 'image_path' column, so there is nothing to run inference "
            f"on. Got columns: {sorted(ground_truth.columns)}"
        )
    rows = ground_truth
    if splits is not None:
        if "split" not in ground_truth.columns:
            raise ValueError(
                f"Splits {splits} were requested but the ground truth has no 'split' column"
            )
        rows = ground_truth[ground_truth["split"].isin(splits)]
        if rows.empty:
            available = sorted({str(value) for value in ground_truth["split"].unique()})
            raise ValueError(f"No ground-truth rows for splits {splits}; available: {available}")
    return [str(path) for path in rows["image_path"].unique()]


def predict(
    weights: str | Path,
    ground_truth: str | Path,
    output: str | Path,
    clearml: ClearMLConfig,
    auto_gpu: AutoGpuConfig | None = None,
    model: str | None = None,
    conf: float = 0.001,
    iou: float = 0.7,
    imgsz: int | None = None,
    batch: int | None = None,
    device: str | None = None,
    splits: list[str] | None = None,
    image_name: ImageNameMode = "name",
    predict_kwargs: dict[str, Any] | None = None,
) -> Path:
    """Infer over the dataset images and write a predictions CSV.

    The default ``conf`` is deliberately near zero: per-class thresholds are chosen
    later during evaluation, so filtering here would discard the detections that
    calibration needs.

    ``weights`` may be a local checkpoint or a ClearML task id, so inference can be run
    against a previously trained model without that model's files on hand. When no
    ``device`` is given the run waits for a free card rather than letting ultralytics
    grab whichever one it likes.

    ``imgsz`` and ``batch`` left unset are answered by the checkpoint and by ``auto_gpu``
    respectively, so neither has to be repeated from the training that produced the
    weights. ``model`` names the architecture those weights are of — it is what a batch
    table is keyed by, and nothing is loaded from it.
    """
    task = init_task(clearml, stage="predict")
    checkpoint = resolve_weights(weights)
    selection = resolve_inference(auto_gpu, device, batch, model=model, stage="predict")

    frame = predict_on_images(
        checkpoint,
        images_to_score(pd.read_csv(ground_truth), splits),
        conf=conf,
        iou=iou,
        imgsz=resolution_of(checkpoint, imgsz),
        batch=selection.batch,
        device=selection.device_name,
        image_name=image_name,
        **(predict_kwargs or {}),
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Wrote {} predictions to {}", len(frame), output_path)

    if auto_gpu is not None:
        remember_batch(auto_gpu, "predict", model, selection)
    upload_dataframe(task, artifact_names.PREDICTIONS, frame)
    return output_path
