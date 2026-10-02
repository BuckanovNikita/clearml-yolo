"""Compose native execution and current-data evaluation under one tracking owner."""

import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

from hydra_zen import instantiate

from clearml_yolo.clearml_session import (
    ClearMLConfig,
    init_task,
    record_run_configuration,
    task_identity,
)
from clearml_yolo.dataset import apply_dataset_policy
from clearml_yolo.dataset_cache import dataset_cache_root
from clearml_yolo.dataset_export import DatasetFormat
from clearml_yolo.filesystem import model_weights_path, runs_root
from clearml_yolo.native_config import prediction_settings
from clearml_yolo.publishing import Publisher, create_publisher
from clearml_yolo.publishing.models import FiftyOneConfig
from clearml_yolo.run_identity import point_latest_at, resolve_run_dir, task_run_dir
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, NoBaselineModelError
from clearml_yolo.tasks.compare import compare as run_comparison
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.predict import predict as run_prediction
from clearml_yolo.tasks.publication import prepare_publisher, publish_results
from clearml_yolo.tasks.report import report as run_report
from clearml_yolo.tasks.train import train as run_training

PREDICTIONS_NAME = "predictions.csv"
METRICS_DIR = "metrics"
REPORTS_DIR = "reports"
COMPARISON_DIR = "comparison"


def _as_dict(config: Any) -> dict[str, Any]:
    # zen already instantiates nested Pydantic objects inside generated stage dataclasses.
    # Instantiating that dataclass again would rebuild an OmegaConf wrapper around it.
    values = vars(config) if is_dataclass(config) else instantiate(config, _convert_="all")
    return {key: value for key, value in values.items() if key != "defaults"}


def routed_native(settings: dict[str, Any], project: Path, name: str) -> dict[str, Any]:
    """Reject conflicting native output keys instead of silently overwriting them."""
    chosen = dict(settings)
    expected = {"project": str(project), "name": name}
    for key, value in expected.items():
        if key in chosen and chosen[key] is not None and str(chosen[key]) != value:
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
) -> dict[str, Any]:
    if candidate_task_id is None:
        local_weights = model_weights_path(checkpoint)
        if isinstance(local_weights, str):
            raise ValueError(
                "Local comparison requires a filesystem checkpoint; "
                "resolve remote weights before comparison"
            )
        candidate = ModelRef(source="local", weights=local_weights, thresholds=thresholds)
    else:
        candidate = ModelRef(source="clearml", task_id=candidate_task_id)
    task = init_task(clearml, stage="compare")
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
        )
    except NoBaselineModelError as error:
        record_run_configuration(
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
    task: Any,
) -> tuple[Path, Path]:
    trained = run_training(
        train_params,
        clearml,
        ground_truth=ground_truth,
        dataset_format=dataset_format,
        dataset_cache_dir=dataset_cache_dir,
        required_splits=required_splits,
    )
    record_run_configuration(task, {"prediction_data_overrides": prediction_data_overrides})
    return trained.weights, trained.cleaned_ground_truth


def _publish_pipeline(
    publisher: Publisher,
    task: Any,
    directory: Path,
    effective_ground_truth: str | Path,
    source_ground_truth: str | Path,
    predictions: Path,
    prediction_splits: list[str],
    evaluations: dict[str, Path],
    checkpoint: str | Path,
    metrics_cfg: dict[str, Any],
    skip_predict: bool,
) -> None:
    if not publisher.enabled:
        return
    evaluation_metadata = metrics_cfg["evaluation"].model_dump(mode="json") | {
        "calibration_split": metrics_cfg["calibration_split"]
    }
    available_predictions = predictions if predictions.is_file() else None
    publish_results(
        publisher,
        task,
        output_dir=directory,
        ground_truth=effective_ground_truth,
        source_ground_truth=source_ground_truth,
        predictions=available_predictions,
        prediction_splits=(prediction_splits if not skip_predict else None),
        evaluations=evaluations,
        metadata={"model": str(checkpoint), "evaluation": evaluation_metadata},
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
) -> dict[str, Any]:
    """Pass real producer outputs to consumers and preserve files on any failure."""
    task = init_task(clearml, stage="pipeline")
    publisher = prepare_publisher(task, fiftyone, factory=create_publisher)
    if weights is not None and not skip_train:
        raise ValueError("weights is only valid with skip_train=true; training chooses its model")
    splits = list(dict.fromkeys(splits or ["train", "val", "test"]))
    directory = (
        resolve_run_dir(runs_root(), run_id or "", Path(run_dir) if run_dir else None)
        if run_dir or run_id
        else task_run_dir(runs_root(), *task_identity(task))
    )
    if dataset_cache_root(dataset_cache_dir).is_relative_to(directory.resolve()):
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
        # Validate both native groups before starting the expensive native training call.
        prediction_overrides, explicit_overrides = apply_dataset_policy(prediction_overrides)
        prediction_data_overrides = {
            "ultralytics_predict": explicit_overrides,
        }
    predict_params = routed_native(
        prediction_settings(prediction_overrides), directory / "native", "predict"
    )
    directory.mkdir(parents=True, exist_ok=True)
    point_latest_at(runs_root(), directory)
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
            **metrics_cfg,
        )
        thresholds = next(iter(evaluated.best_confidences.values()))
        thresholds_path.write_text(json.dumps(thresholds))
        results["metrics"] = evaluated
        evaluations = evaluated.evaluations
    elif not skip_compare:
        thresholds = json.loads(thresholds_path.read_text())
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
                candidate_task_id=str(task.id) if not skip_train else None,
            )
        )
    elif not skip_report:
        results["reports"] = run_report(
            comparison_dir=directory / COMPARISON_DIR,
            output_dir=directory / REPORTS_DIR,
            clearml=clearml,
            **report_cfg,
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
    )
    return results
