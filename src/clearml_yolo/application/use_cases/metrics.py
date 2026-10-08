"""Calibrate on validation once, score each split, and publish readable evidence."""

__all__ = ["EvaluationConfig", "MetricsResult"]
import json
from pathlib import Path
from typing import Any

import pandas as pd

from clearml_yolo.application.contracts import ClearMLConfig, MetricsResult
from clearml_yolo.application.evaluation import evaluate_split
from clearml_yolo.application.ports import TaskHandle, WorkflowDependencies
from clearml_yolo.application.use_cases.publication import prepare_publisher, publish_results
from clearml_yolo.core import artifact_names
from clearml_yolo.core.evaluation.models import EvaluatedSplit, EvaluationConfig
from clearml_yolo.core.evaluation.policy import classes_from_ground_truth
from clearml_yolo.core.evaluation.result_rows import assign_source_ids
from clearml_yolo.core.identity import require_model_identity
from clearml_yolo.core.publication import FiftyOneConfig


def _publish_split(
    task: TaskHandle | None,
    split: str,
    evaluated: EvaluatedSplit,
    ground_truth: Path,
    predictions: Path,
    output_dir: Path,
    *,
    deps: WorkflowDependencies,
) -> None:
    per_class, summary = deps.evaluation_writer.summarize_metrics(evaluated.metrics)
    deps.tracking.publish_evaluation(
        task, evaluated, ground_truth, predictions, output_dir=output_dir
    )
    deps.tracking.report_table(
        task,
        artifact_names.METRICS_SECTION,
        split,
        per_class,
        identities={"model": evaluated.model_identity} if evaluated.model_identity else None,
    )
    deps.tracking.report_scalars(
        task, f"{artifact_names.METRICS_SECTION}_{artifact_names.split_component(split)}", summary
    )


def _methodology_frame(values: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "parameter": list(values),
            "value": [
                json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values.values()
            ],
        }
    )


def _write_evaluation_workbook(
    path: Path,
    evaluated: EvaluatedSplit,
    *,
    methodology: dict[str, Any],
    deps: WorkflowDependencies,
) -> dict[str, Path]:
    return deps.renderer.write_evaluation_workbook(path, evaluated, methodology=methodology)


def _prepare(
    predictions: pd.DataFrame,
    ground_truth: pd.DataFrame,
    config: EvaluationConfig,
    *,
    deps: WorkflowDependencies,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    if config.backend is not None:
        raise ValueError(
            "Frozen thresholds require the native digital-metrics backend; "
            f"backend={config.backend!r} is unsupported"
        )
    prepared_gt = deps.evaluation.prepare_ground_truth(ground_truth, deduplicate=config.preprocess)
    raw_predictions = deps.evaluation.filter_invalid_prediction_boxes(
        predictions.reset_index(drop=True)
    )
    prepared_predictions = deps.evaluation.prepare_predictions(
        raw_predictions,
        preprocess_conf_threshold=config.preprocess_preds_conf_threshold,
        preprocess_nms_containment_threshold=config.preprocess_preds_nms_containment_threshold,
        preprocess_nms_iou_threshold=config.preprocess_preds_nms_iou_threshold,
    )
    classes = sorted(
        set(classes_from_ground_truth(prepared_gt))
        | {str(value) for value in prepared_predictions["instance_label"].dropna().unique()}
    )
    if not classes:
        raise ValueError("Ground truth contains no labelled objects to evaluate")
    return (prepared_gt, raw_predictions, prepared_predictions, classes)


def compute_metrics(
    predictions: str | Path,
    ground_truth: str | Path,
    output_dir: str | Path,
    clearml: ClearMLConfig,
    evaluation: EvaluationConfig,
    splits: list[str] | None = None,
    calibration_split: str | None = "val",
    fiftyone: FiftyOneConfig | None = None,
    model_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> MetricsResult:
    """Calibrate once on validation and score requested splits at that exact mapping."""
    task = deps.tracking.init_task(clearml, stage="metrics")
    publisher = prepare_publisher(task, fiftyone, factory=deps.publisher_factory, deps=deps)
    identity = require_model_identity(
        deps.tracking.prediction_model_identity(Path(predictions)),
        model_label,
        checkpoint_hash=deps.tracking.prediction_checkpoint_hash(Path(predictions)),
    )
    requested = list(dict.fromkeys(splits or ["train", "val", "test"]))
    if calibration_split != "val":
        raise ValueError(
            "calibration_split must be exactly 'val'; test data must never calibrate thresholds"
        )
    if "all" in requested:
        raise ValueError("split='all' is unsupported for frozen evaluation; name concrete splits")
    predictions_frame = assign_source_ids(
        deps.storage.read_csv(
            predictions,
            dtype={"image_name": str, "instance_label": str},
            float_precision="round_trip",
        ),
        row_type="prediction",
    )
    ground_truth_frame = assign_source_ids(
        deps.storage.read_csv(
            ground_truth,
            dtype={"image_name": str, "instance_label": str, "split": str},
            float_precision="round_trip",
        ),
        row_type="ground_truth",
    )
    available = set(ground_truth_frame["split"].dropna())
    if missing := (set(requested) - available):
        raise ValueError(f"No ground-truth rows for splits {sorted(missing)}")
    destination = deps.storage.write_path(output_dir)
    represented_splits = ground_truth_frame.loc[
        ground_truth_frame["image_name"].isin(predictions_frame["image_name"]), "split"
    ].dropna()
    export_splits = list(dict.fromkeys(["val", *requested, *map(str, represented_splits)]))
    deps.tracking.register_predictions(
        task,
        Path(ground_truth),
        Path(predictions),
        output_dir=destination,
        splits=export_splits,
        model_identity=identity,
    )
    prepared_gt, raw_predictions, prepared_predictions, classes = _prepare(
        predictions_frame, ground_truth_frame, evaluation, deps=deps
    )
    thresholds = deps.evaluation.calibrate_thresholds(
        prepared_gt,
        prepared_predictions,
        calibration_split=calibration_split,
        classes=classes,
        iou_threshold=evaluation.iou_threshold,
        matching_strategy=evaluation.matching_strategy,
        confidence_optimization=evaluation.confidence_optimization,
    )
    destination = deps.storage.write_path(output_dir)
    deps.storage.mkdir(destination, parents=True, exist_ok=True)
    threshold_path = destination / f"{artifact_names.BEST_CONFIDENCES_VAL}.csv"
    deps.storage.write_csv(
        pd.DataFrame(sorted(thresholds.items()), columns=["class_name", "confidence"]),
        threshold_path,
        index=False,
        float_format="%.17g",
    )
    if task is not None:
        deps.tracking.upload_artifact(task, artifact_names.BEST_CONFIDENCES_VAL, threshold_path)
        if deps.tracking.has_owned_native_model(task):
            deps.tracking.associate_calibration_thresholds(
                task,
                thresholds,
                prediction_checkpoint_sha256=deps.tracking.prediction_checkpoint_hash(
                    Path(predictions)
                ),
            )
        deps.tracking.record_run_configuration(
            task,
            {
                "evaluation_result": {
                    **evaluation.model_dump(mode="json"),
                    "calibration_split": "val",
                    "evaluated_splits": requested,
                    "model_identity": identity.model_dump(mode="json"),
                }
            },
        )
    result = MetricsResult(output_dir=destination)
    for split in deps.resources.track(requested, "Scoring splits", unit="split"):
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
            source_ground_truth=ground_truth_frame,
            source_predictions=predictions_frame,
            model_identity=identity,
            deps=deps,
        )
        evaluation_path = destination / f"evaluation_{artifact_names.split_component(split)}.json"
        deps.storage.write_text(
            evaluation_path,
            evaluated.evaluation_payload.model_dump_json(indent=2),
            encoding="utf-8",
        )
        workbook_path = (
            destination
            / f"{artifact_names.EVALUATION_PREFIX}_{artifact_names.split_component(split)}.xlsx"
        )
        _write_evaluation_workbook(
            workbook_path,
            evaluated,
            methodology={
                **evaluation.model_dump(mode="json"),
                "calibration_split": calibration_split,
                "evaluated_splits": requested,
                "test_calibration": False,
            },
            deps=deps,
        )
        _publish_split(
            task, split, evaluated, Path(ground_truth), Path(predictions), destination, deps=deps
        )
        result.dashboards[split] = evaluated.dashboard_path
        result.best_confidences[split] = dict(evaluated.thresholds)
        result.evaluations[split] = evaluation_path
        _, summary = deps.evaluation_writer.summarize_metrics(evaluated.metrics)
        deps.resources.log(
            "INFO",
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
        deps=deps,
    )
    return result
