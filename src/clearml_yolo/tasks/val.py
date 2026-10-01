"""Standalone checkpoint inference followed by frozen-threshold evaluation."""

from pathlib import Path
from typing import Any

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.filesystem import write_path
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.tasks.metrics import EvaluationConfig, MetricsResult, compute_metrics
from clearml_yolo.tasks.predict import predict


def validate(
    weights: str | Path | None,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    ultralytics: dict[str, Any],
    evaluation: EvaluationConfig,
    splits: list[str] | None = None,
    ultralytics_predict: dict[str, Any] | None = None,
) -> MetricsResult:
    init_task(clearml, stage="val")
    selected = list(dict.fromkeys(splits or ["train", "val", "test"]))
    destination = write_path(output_dir)
    predicted = predict(
        weights,
        ground_truth,
        destination / "predictions.csv",
        clearml,
        ultralytics,
        ultralytics_predict=ultralytics_predict,
        splits=list(dict.fromkeys(["val", *selected])),
        fiftyone=FiftyOneConfig(enabled=False),
    )
    return compute_metrics(
        predicted.predictions,
        ground_truth,
        destination / "metrics",
        clearml,
        evaluation,
        splits=selected,
        calibration_split="val",
        fiftyone=FiftyOneConfig(enabled=False),
    )
