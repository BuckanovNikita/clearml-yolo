"""Run inference over the dataset and persist predictions in digital-metrics' schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from clearml_yolo.clearml_models import resolve_weights
from clearml_yolo.clearml_session import ClearMLConfig, init_task, upload_dataframe
from clearml_yolo.gpu import AutoGpuConfig, resolve_inference_device


def predict(
    weights: str | Path,
    ground_truth: str | Path,
    output: str | Path,
    clearml: ClearMLConfig,
    auto_gpu: AutoGpuConfig | None = None,
    conf: float = 0.001,
    iou: float = 0.7,
    imgsz: int = 640,
    batch: int = 16,
    device: str | None = None,
    splits: list[str] | None = None,
    image_name: str = "name",
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
    """
    from digital_metrics import Evaluation

    task = init_task(clearml, stage="predict")
    checkpoint = resolve_weights(weights)
    if device is None and auto_gpu is not None and auto_gpu.enabled:
        device = resolve_inference_device(auto_gpu)

    evaluation = Evaluation(None, str(ground_truth))
    frame: pd.DataFrame = evaluation.predict_to_dataframe(
        str(checkpoint),
        split=splits,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        batch=batch,
        device=device,
        image_name=image_name,
        **(predict_kwargs or {}),
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    logger.info("Wrote {} predictions to {}", len(frame), output_path)

    upload_dataframe(task, "predictions", frame)
    return output_path
