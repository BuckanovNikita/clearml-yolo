"""Compose native execution and current-data evaluation under one tracking owner."""

from __future__ import annotations

import json
from dataclasses import is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hydra_zen import instantiate

from clearml_yolo.clearml_session import ClearMLConfig, init_task, upload_artifact
from clearml_yolo.run_identity import RUNS_ROOT, point_latest_at, resolve_run_dir, resolve_run_id
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, NoBaselineModelError
from clearml_yolo.tasks.compare import compare as run_comparison
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.predict import predict as run_prediction
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
    return {key: value for key, value in values.items() if key not in {"defaults", "cfg"}}


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


def _compare_and_report(
    config: dict[str, Any],
    checkpoint: Path,
    thresholds: dict[str, float],
    ground_truth: str,
    directory: Path,
    clearml: ClearMLConfig,
    inference: InferenceConfig,
    evaluation: Any,
    report_config: dict[str, Any],
    skip_report: bool,
) -> dict[str, Any]:
    task = init_task(clearml, stage="compare")
    try:
        result = run_comparison(
            **config,
            candidate_model=ModelRef(source="local", weights=checkpoint, thresholds=thresholds),
            ground_truth=ground_truth,
            output_dir=directory / COMPARISON_DIR,
            clearml=clearml,
            inference=inference,
            split="test",
            iou_threshold=evaluation.iou_threshold,
            matching_strategy=evaluation.matching_strategy,
            evaluation=evaluation,
        )
    except NoBaselineModelError as error:
        upload_artifact(task, "comparison_status", {"status": "skipped", "reason": str(error)})
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


def run_pipeline(
    train: Any,
    predict: Any,
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    ground_truth: str,
    splits: list[str],
    run_id: str | None = None,
    run_dir: str | Path | None = None,
    weights: str | Path | None = None,
    skip_train: bool = False,
    skip_predict: bool = False,
    skip_metrics: bool = False,
    skip_report: bool = False,
    skip_compare: bool = False,
) -> dict[str, Any]:
    """Pass real producer outputs to consumers and preserve files on any failure."""
    task = init_task(clearml, stage="pipeline")
    if weights is not None and not skip_train:
        raise ValueError("weights is only valid with skip_train=true; training chooses its model")
    identity = resolve_run_id(clearml.task_name, run_id, datetime.now(tz=UTC))
    directory = resolve_run_dir(RUNS_ROOT, identity, Path(run_dir) if run_dir else None)
    train_cfg = _stage_values(train, {"ultralytics"}, "train")
    predict_cfg = _stage_values(predict, {"ultralytics"}, "predict")
    metrics_cfg = _stage_values(metrics, {"evaluation", "calibration_split"}, "metrics")
    report_cfg = _stage_values(report, {"report_config_path"}, "report")
    compare_cfg = _stage_values(
        compare, {"baseline_model", "q", "bootstrap_iterations", "seed"}, "compare"
    )
    train_params = routed_native(train_cfg["ultralytics"], directory / "detect", "train")
    predict_params = routed_native(predict_cfg["ultralytics"], directory / "native", "predict")
    directory.mkdir(parents=True, exist_ok=True)
    point_latest_at(RUNS_ROOT, directory)
    results: dict[str, Any] = {"run_dir": directory}
    checkpoint = Path(weights) if weights else directory / "detect/train/weights/best.pt"
    if not skip_train:
        trained = run_training(train_params, clearml)
        checkpoint = trained.weights
        results["weights"] = checkpoint
    predictions = directory / PREDICTIONS_NAME
    if not skip_predict:
        predicted = run_prediction(
            checkpoint,
            ground_truth,
            predictions,
            clearml,
            predict_params,
            splits=list(dict.fromkeys(["val", *splits])),
        )
        predictions = predicted.predictions
        results["predictions"] = predictions
    thresholds_path = directory / METRICS_DIR / "frozen_thresholds.json"
    if not skip_metrics:
        evaluated = compute_metrics(
            predictions,
            ground_truth,
            directory / METRICS_DIR,
            clearml,
            splits=splits,
            **metrics_cfg,
        )
        thresholds = next(iter(evaluated.best_confidences.values()))
        thresholds_path.write_text(json.dumps(thresholds))
        upload_artifact(task, "frozen_thresholds", thresholds_path)
        results["metrics"] = evaluated
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
                ground_truth,
                directory,
                clearml,
                _comparison_settings(predict_params),
                metrics_cfg["evaluation"],
                report_cfg,
                skip_report,
            )
        )
    elif not skip_report:
        results["reports"] = run_report(
            comparison_dir=directory / COMPARISON_DIR,
            output_dir=directory / REPORTS_DIR,
            clearml=clearml,
            **report_cfg,
        )
    return results
