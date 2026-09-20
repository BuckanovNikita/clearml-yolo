"""Standalone checkpoint inference followed by frozen-threshold evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from clearml_yolo.clearml_session import ClearMLConfig, init_task
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
) -> MetricsResult:
    init_task(clearml, stage="val")
    selected = splits or ["val", "test"]
    destination = Path(output_dir)
    predicted = predict(
        weights,
        ground_truth,
        destination / "predictions.csv",
        clearml,
        ultralytics,
        splits=list(dict.fromkeys(["val", *selected])),
    )
    return compute_metrics(
        predicted.predictions,
        ground_truth,
        destination / "metrics",
        clearml,
        evaluation,
        splits=selected,
        calibration_split="val",
    )
