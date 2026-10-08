"""Standalone checkpoint inference followed by frozen-threshold evaluation."""

from pathlib import Path
from typing import Any

from clearml_yolo.application.contracts import ClearMLConfig, MetricsResult
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.application.use_cases.predict import predict
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.publication import FiftyOneConfig


def validate(
    weights: str | Path | None,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    ultralytics: dict[str, Any],
    evaluation: EvaluationConfig,
    splits: list[str] | None = None,
    ultralytics_predict: dict[str, Any] | None = None,
    model_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> MetricsResult:
    deps.tracking.init_task(clearml, stage="val")
    selected = list(dict.fromkeys(splits or ["train", "val", "test"]))
    destination = deps.storage.write_path(output_dir)
    predicted = predict(
        weights,
        ground_truth,
        destination / "predictions.csv",
        clearml,
        ultralytics,
        ultralytics_predict=ultralytics_predict,
        splits=list(dict.fromkeys(["val", *selected])),
        fiftyone=FiftyOneConfig(enabled=False),
        model_label=model_label,
        deps=deps,
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
        model_label=model_label,
        deps=deps,
    )
