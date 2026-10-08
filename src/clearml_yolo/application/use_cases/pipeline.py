"""Compose native execution and current-data evaluation under one tracking owner."""

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from clearml_yolo.application.contracts import (
    ClearMLConfig,
    DatasetFormat,
    InferenceConfig,
    ModelRef,
)
from clearml_yolo.application.ports import Publisher, TaskHandle, WorkflowDependencies
from clearml_yolo.application.use_cases.compare import NoBaselineModelError
from clearml_yolo.application.use_cases.compare import compare as run_comparison
from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.application.use_cases.predict import predict as run_prediction
from clearml_yolo.application.use_cases.publication import prepare_publisher, publish_results
from clearml_yolo.application.use_cases.report import report as run_report
from clearml_yolo.application.use_cases.train import train as run_training
from clearml_yolo.core.publication import FiftyOneConfig

PREDICTIONS_NAME = "predictions.csv"
METRICS_DIR = "metrics"
REPORTS_DIR = "reports"
COMPARISON_DIR = "comparison"


def _as_dict(config: Any) -> dict[str, Any]:
    if is_dataclass(config) and (not isinstance(config, type)):
        values = {field.name: getattr(config, field.name) for field in fields(config)}
    elif isinstance(config, Mapping):
        values = dict(config)
    else:
        raise TypeError("Pipeline stages must be normalized mappings or dataclass requests")
    return {key: value for key, value in values.items() if key != "defaults"}


def routed_native(settings: dict[str, Any], project: Path, name: str) -> dict[str, Any]:
    """Reject conflicting native output keys instead of silently overwriting them."""
    chosen = dict(settings)
    expected = {"project": str(project), "name": name}
    for key, value in expected.items():
        if key in chosen and chosen[key] is not None and (str(chosen[key]) != value):
            raise ValueError(
                f"{key}={chosen[key]!r} conflicts with pipeline run_dir; expected {value}"
            )
    if "save_dir" in chosen:
        raise ValueError("save_dir conflicts with pipeline run_dir; use run_dir to route outputs")
    return chosen | expected


def _stage_values(config: Any, allowed: set[str], stage: str) -> dict[str, Any]:
    values = _as_dict(config)
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(
            f"Pipeline {stage} keys {sorted(unknown)} are unsupported; outputs use run_dir"
        )
    return values


def _comparison_settings(settings: dict[str, Any]) -> InferenceConfig:
    fields = {
        key: settings[key] for key in ("conf", "iou", "imgsz", "batch", "device") if key in settings
    }
    ignored = {"model", "source", "stream", "project", "name", "save_dir", "mode", "task"}
    extras = {key: value for key, value in settings.items() if key not in {*fields, *ignored}}
    return InferenceConfig(**fields, ultralytics=extras)


def _required_training_splits(
    splits: list[str], *, skip_predict: bool, skip_metrics: bool, skip_compare: bool
) -> list[str]:
    """Require only the supplied CSV splits that an enabled pipeline stage consumes."""
    required = ["train", "val"]
    if not skip_predict or not skip_metrics:
        required.extend(splits)
    if not skip_compare:
        required.append("test")
    return list(dict.fromkeys(required))


def _compare_and_report(
    config: dict[str, Any],
    checkpoint: str | Path,
    thresholds: dict[str, float],
    ground_truth: str | Path,
    directory: Path,
    clearml: ClearMLConfig,
    inference: InferenceConfig,
    evaluation: Any,
    report_config: dict[str, Any],
    skip_report: bool,
    candidate_task_id: str | None = None,
    model_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> dict[str, Any]:
    if candidate_task_id is None:
        local_weights = deps.storage.model_weights_path(checkpoint)
        if isinstance(local_weights, str):
            raise ValueError(
                "Local comparison requires a filesystem checkpoint; "
                "resolve remote weights before comparison"
            )
        candidate = ModelRef(
            source="local", weights=local_weights, thresholds=thresholds, label=model_label
        )
    else:
        candidate = ModelRef(source="clearml", task_id=candidate_task_id)
    task = deps.tracking.init_task(clearml, stage="compare")
    try:
        result = run_comparison(
            **config,
            candidate_model=candidate,
            ground_truth=ground_truth,
            output_dir=directory / COMPARISON_DIR,
            clearml=clearml,
            inference=inference,
            split="test",
            evaluation=evaluation,
            deps=deps,
        )
    except NoBaselineModelError as error:
        deps.tracking.record_run_configuration(
            task, {"comparison_status": {"status": "skipped", "reason": str(error)}}
        )
        return {"comparison_status": "skipped"}
    if result is None:
        return {"comparison_status": "skipped"}
    results: dict[str, Any] = {"comparison": result}
    if not skip_report:
        results["reports"] = run_report(
            comparison_dir=directory / COMPARISON_DIR,
            output_dir=directory / REPORTS_DIR,
            clearml=clearml,
            **report_config,
            deps=deps,
        )
    return results


def _train_from_ground_truth(
    train_params: dict[str, Any],
    clearml: ClearMLConfig,
    ground_truth: str,
    dataset_format: DatasetFormat,
    dataset_cache_dir: str | Path | None,
    required_splits: list[str],
    prediction_data_overrides: dict[str, dict[str, Any]],
    task: TaskHandle | None,
    *,
    deps: WorkflowDependencies,
) -> tuple[Path, Path]:
    trained = run_training(
        train_params,
        clearml,
        ground_truth=ground_truth,
        dataset_format=dataset_format,
        dataset_cache_dir=dataset_cache_dir,
        required_splits=required_splits,
        deps=deps,
    )
    deps.tracking.record_run_configuration(
        task, {"prediction_data_overrides": prediction_data_overrides}
    )
    deps.resources.training_finished()
    return (trained.weights, trained.cleaned_ground_truth)


def _publish_pipeline(
    publisher: Publisher,
    task: TaskHandle | None,
    directory: Path,
    effective_ground_truth: str | Path,
    source_ground_truth: str | Path,
    predictions: Path,
    prediction_splits: list[str],
    evaluations: dict[str, Path],
    checkpoint: str | Path,
    metrics_cfg: dict[str, Any],
    skip_predict: bool,
    *,
    deps: WorkflowDependencies,
) -> None:
    if not publisher.enabled:
        return
    evaluation_metadata = metrics_cfg["evaluation"].model_dump(mode="json") | {
        "calibration_split": metrics_cfg["calibration_split"]
    }
    available_predictions = predictions if deps.storage.is_file(predictions) else None
    publish_results(
        publisher,
        task,
        output_dir=directory,
        ground_truth=effective_ground_truth,
        source_ground_truth=source_ground_truth,
        predictions=available_predictions,
        prediction_splits=prediction_splits if not skip_predict else None,
        evaluations=evaluations,
        metadata={"model": str(checkpoint), "evaluation": evaluation_metadata},
        deps=deps,
    )


def run_pipeline(
    ultralytics: dict[str, Any],
    ultralytics_predict: dict[str, Any],
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    ground_truth: str,
    splits: list[str] | None = None,
    dataset_format: DatasetFormat = "ndjson",
    dataset_cache_dir: str | Path | None = None,
    run_id: str | None = None,
    run_dir: str | Path | None = None,
    weights: str | Path | None = None,
    skip_train: bool = False,
    skip_predict: bool = False,
    skip_metrics: bool = False,
    skip_report: bool = False,
    skip_compare: bool = False,
    fiftyone: FiftyOneConfig | None = None,
    model_label: str | None = None,
    *,
    deps: WorkflowDependencies,
) -> dict[str, Any]:
    """Pass real producer outputs to consumers and preserve files on any failure."""
    task = deps.tracking.init_task(clearml, stage="pipeline")
    publisher = prepare_publisher(task, fiftyone, factory=deps.publisher_factory, deps=deps)
    if weights is not None and (not skip_train):
        raise ValueError("weights is only valid with skip_train=true; training chooses its model")
    splits = list(dict.fromkeys(splits or ["train", "val", "test"]))
    directory = (
        deps.storage.resolve_run_dir(
            deps.storage.runs_root(), run_id or "", Path(run_dir) if run_dir else None
        )
        if run_dir or run_id
        else deps.storage.task_run_dir(deps.storage.runs_root(), *deps.tracking.task_identity(task))
    )
    if deps.dataset.dataset_cache_root(dataset_cache_dir).is_relative_to(
        deps.storage.resolve(directory)
    ):
        raise ValueError("dataset_cache_dir must be outside run_dir")
    metrics_cfg = _stage_values(metrics, {"evaluation", "calibration_split"}, "metrics")
    report_cfg = _stage_values(report, {"report_config_path"}, "report")
    compare_cfg = _stage_values(
        compare, {"baseline_model", "q", "bootstrap_iterations", "seed"}, "compare"
    )
    train_params = routed_native(ultralytics, directory / "detect", "train")
    prediction_overrides = dict(ultralytics_predict)
    prediction_data_overrides: dict[str, dict[str, Any]] = {}
    if not skip_train:
        prediction_overrides, explicit_overrides = deps.dataset.apply_dataset_policy(
            prediction_overrides
        )
        prediction_data_overrides = {"ultralytics_predict": explicit_overrides}
    predict_params = routed_native(
        deps.model.prediction_settings(prediction_overrides), directory / "native", "predict"
    )
    deps.storage.mkdir(directory, parents=True, exist_ok=True)
    deps.storage.point_latest_at(deps.storage.runs_root(), directory)
    results: dict[str, Any] = {"run_dir": directory}
    checkpoint = weights if weights is not None else directory / "detect/train/weights/best.pt"
    effective_ground_truth: str | Path = ground_truth
    if not skip_train:
        checkpoint, effective_ground_truth = _train_from_ground_truth(
            train_params,
            clearml,
            ground_truth,
            dataset_format,
            dataset_cache_dir,
            _required_training_splits(
                splits,
                skip_predict=skip_predict,
                skip_metrics=skip_metrics,
                skip_compare=skip_compare,
            ),
            prediction_data_overrides,
            task,
            deps=deps,
        )
        results["weights"] = checkpoint
    predictions = directory / PREDICTIONS_NAME
    prediction_splits = list(dict.fromkeys(["val", *splits]))
    if not skip_predict:
        predicted = run_prediction(
            checkpoint,
            effective_ground_truth,
            predictions,
            clearml,
            predict_params,
            splits=prediction_splits,
            ultralytics_predict=predict_params,
            fiftyone=FiftyOneConfig(enabled=False),
            model_label=model_label,
            deps=deps,
        )
        predictions = predicted.predictions
        results["predictions"] = predictions
    thresholds_path = directory / METRICS_DIR / "frozen_thresholds.json"
    evaluations: dict[str, Path] = {}
    if not skip_metrics:
        evaluated = compute_metrics(
            predictions,
            effective_ground_truth,
            directory / METRICS_DIR,
            clearml,
            splits=splits,
            fiftyone=FiftyOneConfig(enabled=False),
            model_label=model_label,
            **metrics_cfg,
            deps=deps,
        )
        thresholds = next(iter(evaluated.best_confidences.values()))
        deps.storage.write_text(thresholds_path, json.dumps(thresholds))
        results["metrics"] = evaluated
        evaluations = evaluated.evaluations
    elif not skip_compare:
        thresholds = json.loads(deps.storage.read_text(thresholds_path))
    else:
        thresholds = {}
    if not skip_compare:
        results.update(
            _compare_and_report(
                compare_cfg,
                checkpoint,
                thresholds,
                effective_ground_truth,
                directory,
                clearml,
                _comparison_settings(predict_params),
                metrics_cfg["evaluation"],
                report_cfg,
                skip_report,
                candidate_task_id=str(task.id) if not skip_train and task is not None else None,
                model_label=model_label,
                deps=deps,
            )
        )
    elif not skip_report:
        results["reports"] = run_report(
            comparison_dir=directory / COMPARISON_DIR,
            output_dir=directory / REPORTS_DIR,
            clearml=clearml,
            **report_cfg,
            deps=deps,
        )
    _publish_pipeline(
        publisher,
        task,
        directory,
        effective_ground_truth,
        ground_truth,
        predictions,
        prediction_splits,
        evaluations,
        checkpoint,
        metrics_cfg,
        skip_predict,
        deps=deps,
    )
    return results
