"""Run inference over the dataset and persist predictions in digital-metrics' schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from clearml_yolo.clearml_session import ClearMLConfig, init_task, upload_dataframe


def predict(
    weights: str | Path,
    ground_truth: str | Path,
    output: str | Path,
    clearml: ClearMLConfig,
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
    """
    from digital_metrics import Evaluation

    task = init_task(clearml, stage="predict")

    evaluation = Evaluation(None, str(ground_truth))
    frame: pd.DataFrame = evaluation.predict_to_dataframe(
        str(weights),
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
