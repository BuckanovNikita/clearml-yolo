"""Calibrate on validation once, score each split, and publish readable evidence."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
from digital_metrics import summarize_metrics
from loguru import logger
from pydantic import BaseModel, Field

from clearml_yolo import artifact_names
from clearml_yolo.clearml_native import associate_calibration_thresholds, owned_native_model
from clearml_yolo.clearml_report import report_scalars, report_table
from clearml_yolo.clearml_results import (
    prediction_checkpoint_hash,
    prediction_model_identity,
    publish_evaluation,
    register_predictions,
)
from clearml_yolo.clearml_session import (
    ClearMLConfig,
    init_task,
    record_run_configuration,
    upload_artifact,
)
from clearml_yolo.comparison.scoring import (
    EvaluatedSplit,
    EvaluationConfig,
    calibrate_thresholds,
    classes_from_ground_truth,
    evaluate_split,
    filter_invalid_prediction_boxes,
    prepare_ground_truth,
    prepare_predictions,
)
from clearml_yolo.filesystem import write_path
from clearml_yolo.model_identity import require_model_identity
from clearml_yolo.progress import track
from clearml_yolo.publishing import create_publisher
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.result_export import assign_source_ids
from clearml_yolo.tasks.publication import prepare_publisher, publish_results
from clearml_yolo.workbook_identity import annotate_workbook, read_dashboard

__all__ = ["EvaluationConfig"]


class MetricsResult(BaseModel):
    """Dashboard workbooks and the one frozen threshold map used for each split."""

    output_dir: Path
    dashboards: dict[str, Path] = Field(default_factory=dict)
    best_confidences: dict[str, dict[str, float]] = Field(default_factory=dict)
    evaluations: dict[str, Path] = Field(default_factory=dict)


def _publish_split(
    task: Any,
    split: str,
    evaluated: EvaluatedSplit,
    ground_truth: Path,
    predictions: Path,
    output_dir: Path,
) -> None:
    per_class, summary = summarize_metrics(evaluated.metrics)
    publish_evaluation(
        task,
        evaluated,
        ground_truth,
        predictions,
        output_dir=output_dir,
    )
    report_table(
        task, artifact_names.METRICS_SECTION, split, per_class,
        identities={"model": evaluated.model_identity} if evaluated.model_identity else None,
    )
    report_scalars(
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
) -> dict[str, Path]:
    """Write metric tables to Excel and row-level evidence/metadata to CSV."""
    required_diagnostics = [
        evaluated.dashboard_path,
        evaluated.dtrk_dashboard_path,
        evaluated.confusion_matrix_path,
        *evaluated.plot_paths.values(),
    ]
    missing = [str(item) for item in required_diagnostics if not item.is_file()]
    if missing:
        raise FileNotFoundError(f"Required local evaluation diagnostics are missing: {missing}")
    expected_plots = {"recall", "precision", "perebrak", "nedobrak"}
    if set(evaluated.plot_paths) != expected_plots:
        raise ValueError(
            f"Evaluation plot inventory mismatch: expected={sorted(expected_plots)}, "
            f"actual={sorted(evaluated.plot_paths)}"
        )
    per_class, summary = summarize_metrics(evaluated.metrics)
    confusion = read_dashboard(evaluated.confusion_matrix_path, index_col=0)
    thresholds = pd.DataFrame(
        sorted(evaluated.thresholds.items()), columns=["class_name", "confidence"]
    )
    summary_frame = pd.DataFrame([summary])
    per_class_frame = per_class.rename_axis("class_name").reset_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_frame.to_excel(writer, sheet_name="summary", index=False)
        per_class_frame.to_excel(writer, sheet_name="per_class", index=False)
        confusion.to_excel(writer, sheet_name="confusion_matrix")
    if evaluated.model_identity is not None:
        annotate_workbook(path, {"model": evaluated.model_identity})
    tables: dict[str, Path] = {}
    for title, frame in {
        "ground_truth_matches": evaluated.gt_matches,
        "prediction_matches": evaluated.pred_matches,
        "thresholds": thresholds,
        "methodology": _methodology_frame(methodology),
    }.items():
        table_path = path.with_name(f"{path.stem}_{title}.csv")
        frame.to_csv(table_path, index=False, float_format="%.17g")
        tables[table_path.stem] = table_path
    return tables


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
    raw_predictions = filter_invalid_prediction_boxes(predictions.reset_index(drop=True))
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
    model_label: str | None = None,
) -> MetricsResult:
    """Calibrate once on validation and score requested splits at that exact mapping."""
    task = init_task(clearml, stage="metrics")
    publisher = prepare_publisher(task, fiftyone, factory=create_publisher)
    identity = require_model_identity(
        prediction_model_identity(Path(predictions)), model_label,
        checkpoint_hash=prediction_checkpoint_hash(Path(predictions)),
    )
    requested = list(dict.fromkeys(splits or ["train", "val", "test"]))
    if calibration_split != "val":
        raise ValueError(
            "calibration_split must be exactly 'val'; test data must never calibrate thresholds"
        )
    if "all" in requested:
        raise ValueError("split='all' is unsupported for frozen evaluation; name concrete splits")
    predictions_frame = assign_source_ids(
        pd.read_csv(
            predictions,
            dtype={"image_name": str, "instance_label": str},
            float_precision="round_trip",
        ),
        row_type="prediction",
    )
    ground_truth_frame = assign_source_ids(
        pd.read_csv(
            ground_truth,
            dtype={"image_name": str, "instance_label": str, "split": str},
            float_precision="round_trip",
        ),
        row_type="ground_truth",
    )
    available = set(ground_truth_frame["split"].dropna())
    if missing := set(requested) - available:
        raise ValueError(f"No ground-truth rows for splits {sorted(missing)}")
    destination = write_path(output_dir)
    represented_splits = ground_truth_frame.loc[
        ground_truth_frame["image_name"].isin(predictions_frame["image_name"]), "split"
    ].dropna()
    export_splits = list(dict.fromkeys(["val", *requested, *map(str, represented_splits)]))
    register_predictions(
        task, Path(ground_truth), Path(predictions), output_dir=destination, splits=export_splits,
        model_identity=identity,
    )
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

    destination = write_path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    threshold_path = destination / f"{artifact_names.BEST_CONFIDENCES_VAL}.csv"
    pd.DataFrame(sorted(thresholds.items()), columns=["class_name", "confidence"]).to_csv(
        threshold_path, index=False, float_format="%.17g"
    )
    if task is not None:
        upload_artifact(task, artifact_names.BEST_CONFIDENCES_VAL, threshold_path)
        if owned_native_model(task) is not None:
            associate_calibration_thresholds(
                task,
                thresholds,
                prediction_checkpoint_sha256=prediction_checkpoint_hash(Path(predictions)),
            )
        record_run_configuration(
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
            source_ground_truth=ground_truth_frame,
            source_predictions=predictions_frame,
            model_identity=identity,
        )
        evaluation_path = destination / f"evaluation_{artifact_names.split_component(split)}.json"
        evaluation_path.write_text(
            evaluated.evaluation_payload.model_dump_json(indent=2), encoding="utf-8"
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
        )
        _publish_split(task, split, evaluated, Path(ground_truth), Path(predictions), destination)
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
