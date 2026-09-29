"""Calibrate on validation once, then score every split at frozen thresholds."""

from pathlib import Path
from typing import Any

import pandas as pd
from digital_metrics import summarize_metrics
from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo import artifact_names
from clearml_yolo.clearml_report import report_scalars, report_table
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    expect_artifacts,
    init_task,
    upload_artifact,
)
from clearml_yolo.comparison.scoring import (
    EvaluatedSplit,
    EvaluationConfig,
    calibrate_thresholds,
    classes_from_ground_truth,
    evaluate_split,
    prepare_ground_truth,
    prepare_predictions,
)
from clearml_yolo.progress import track
from clearml_yolo.publishing import create_publisher
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.tasks.publication import prepare_publisher, publish_results

__all__ = ["EvaluationConfig"]


class MetricsResult(BaseModel):
    """Dashboard workbooks and the one frozen threshold map used for each split."""

    output_dir: Path
    dashboards: dict[str, Path] = Field(default_factory=dict)
    best_confidences: dict[str, dict[str, float]] = Field(default_factory=dict)
    evaluations: dict[str, Path] = Field(default_factory=dict)


def _upload(task: Any, name: str, value: Any) -> None:
    if task is None:
        return
    upload_artifact(task, name, value)


def _publish_split(
    task: Any, split: str, evaluated: EvaluatedSplit, evaluation_path: Path
) -> None:
    per_class, summary = summarize_metrics(evaluated.metrics)
    artifacts: dict[str, Any] = {
        artifact_names.DASHBOARD_FULL_PREFIX: evaluated.dashboard_path,
        artifact_names.DASHBOARD_DTRK_PREFIX: evaluated.dtrk_dashboard_path,
        artifact_names.MATCHES_GT_PREFIX: evaluated.gt_matches,
        artifact_names.MATCHES_PREDS_PREFIX: evaluated.pred_matches,
        "metrics_confusion_matrix": evaluated.confusion_matrix_path,
        artifact_names.METRICS_SUMMARY_PREFIX: per_class,
        artifact_names.METRICS_RAW_PREFIX: {
            class_name: metric.model_dump() for class_name, metric in evaluated.metrics.items()
        },
        artifact_names.BEST_CONFIDENCES_PREFIX: evaluated.thresholds,
        "metrics_evaluation": evaluation_path,
        **{f"metrics_plot_{metric}": path for metric, path in evaluated.plot_paths.items()},
    }
    required = set(artifact_names.METRIC_SPLIT_PREFIXES)
    if artifacts.keys() != required:
        raise ValueError(
            f"Split {split!r} artifact inventory mismatch: "
            f"missing={sorted(required - artifacts.keys())}, "
            f"unexpected={sorted(artifacts.keys() - required)}"
        )
    for value in artifacts.values():
        if isinstance(value, Path) and not value.is_file():
            raise FileNotFoundError(f"Required split artifact is not a file: {value}")
    for prefix in artifact_names.METRIC_SPLIT_PREFIXES:
        _upload(task, artifact_names.per_split(prefix, split), artifacts[prefix])
    report_table(task, artifact_names.METRICS_SECTION, split, per_class)
    report_scalars(task, f"{artifact_names.METRICS_SECTION}_{split}", summary)


def _prepare(
    predictions: pd.DataFrame,
    ground_truth: pd.DataFrame,
    config: EvaluationConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    if config.backend is not None:
        raise ValueError(
            "Frozen thresholds require the native digital-metrics backend; "
            f"backend={config.backend!r} is unsupported"
        )
    prepared_gt = prepare_ground_truth(ground_truth, deduplicate=config.preprocess)
    raw_predictions = predictions.copy().reset_index(drop=True)
    prepared_predictions = prepare_predictions(
        raw_predictions,
        preprocess_conf_threshold=config.preprocess_preds_conf_threshold,
        preprocess_nms_containment_threshold=(config.preprocess_preds_nms_containment_threshold),
        preprocess_nms_iou_threshold=config.preprocess_preds_nms_iou_threshold,
    )
    classes = sorted(
        set(classes_from_ground_truth(prepared_gt))
        | {str(value) for value in prepared_predictions["instance_label"].dropna().unique()}
    )
    if not classes:
        raise ValueError("Ground truth contains no labelled objects to evaluate")
    return prepared_gt, raw_predictions, prepared_predictions, classes


def compute_metrics(
    predictions: str | Path,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    evaluation: EvaluationConfig,
    splits: list[str] | None = None,
    calibration_split: str | None = "val",
    fiftyone: FiftyOneConfig | None = None,
) -> MetricsResult:
    """Calibrate once on validation and score requested splits at that exact mapping."""
    task = init_task(clearml, stage="metrics")
    publisher = prepare_publisher(task, fiftyone, factory=create_publisher)
    requested = list(dict.fromkeys(splits or ["train", "val", "test"]))
    if calibration_split != "val":
        raise ValueError(
            "calibration_split must be exactly 'val'; test data must never calibrate thresholds"
        )
    if "all" in requested:
        raise ValueError("split='all' is unsupported for frozen evaluation; name concrete splits")

    expected = ["metrics_predictions", "metrics_ground_truth", "metrics_methodology"]
    for split in requested:
        expected.extend(artifact_names.metric_split_names(split))
    if task is not None:
        expect_artifacts(task, expected)

    predictions_frame = pd.read_csv(predictions, dtype={"image_name": str, "instance_label": str})
    ground_truth_frame = pd.read_csv(
        ground_truth, dtype={"image_name": str, "instance_label": str, "split": str}
    )
    _upload(task, "metrics_predictions", Path(predictions))
    _upload(task, "metrics_ground_truth", Path(ground_truth))
    prepared_gt, raw_predictions, prepared_predictions, classes = _prepare(
        predictions_frame, ground_truth_frame, evaluation
    )

    thresholds = calibrate_thresholds(
        prepared_gt,
        prepared_predictions,
        calibration_split=calibration_split,
        classes=classes,
        iou_threshold=evaluation.iou_threshold,
        matching_strategy=evaluation.matching_strategy,
        confidence_optimization=evaluation.confidence_optimization,
    )

    _upload(
        task,
        "metrics_methodology",
        {
            **evaluation.model_dump(),
            "calibration_split": "val",
            "thresholds": thresholds,
            "evaluated_splits": requested,
            "test_calibration": False,
        },
    )
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    result = MetricsResult(output_dir=destination)
    for split in track(requested, "Scoring splits", unit="split"):
        evaluated = evaluate_split(
            prepared_gt,
            raw_predictions,
            prepared_predictions,
            split=split,
            classes=classes,
            thresholds=thresholds,
            required_classes=classes,
            iou_threshold=evaluation.iou_threshold,
            matching_strategy=evaluation.matching_strategy,
            ap_method=evaluation.ap_method,
            skip_cohen_kappa=evaluation.skip_cohen_kappa,
            output_dir=destination,
            suffix=split,
            methodology=evaluation.model_dump(mode="json"),
        )
        evaluation_path = destination / f"evaluation_{split}.json"
        evaluation_path.write_text(
            evaluated.evaluation_payload.model_dump_json(indent=2), encoding="utf-8"
        )
        _publish_split(task, split, evaluated, evaluation_path)
        result.dashboards[split] = evaluated.dashboard_path
        result.best_confidences[split] = dict(evaluated.thresholds)
        result.evaluations[split] = evaluation_path
        _, summary = summarize_metrics(evaluated.metrics)
        logger.info(
            "Split {!r}: {} classes, mean f1 {:.4f} -> {}",
            split,
            len(evaluated.metrics),
            summary.get("mean_f1_score", float("nan")),
            evaluated.dashboard_path,
        )
    publish_results(
        publisher,
        task,
        output_dir=destination,
        ground_truth=ground_truth,
        predictions=predictions,
        prediction_splits=None,
        evaluations=result.evaluations,
        metadata={
            "evaluation": evaluation.model_dump(mode="json")
            | {"calibration_split": calibration_split}
        },
    )
    return result
