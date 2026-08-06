"""Run train, predict, metrics and report as one ClearML experiment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hydra_zen import instantiate
from loguru import logger
from omegaconf import OmegaConf

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.tasks.compare import CompareResult, ModelRef, NoBaselineModelError
from clearml_yolo.tasks.compare import compare as run_comparison
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.predict import predict as run_prediction
from clearml_yolo.tasks.report import build_reports, discover_dashboards
from clearml_yolo.tasks.train import TrainResult
from clearml_yolo.tasks.train import train as run_training


def _as_dict(config: Any) -> dict[str, Any]:
    """Resolve a stage sub-config, leaving no OmegaConf containers behind.

    Nested containers must become plain dicts and lists: ultralytics stores whatever
    it receives into trainer.args and pickles that when saving a checkpoint, and a
    DictConfig backed by a generated dataclass cannot be pickled.
    """
    resolved = instantiate(config)
    values = dict(resolved) if not isinstance(resolved, dict) else resolved
    return {
        key: OmegaConf.to_object(value) if OmegaConf.is_config(value) else value
        for key, value in values.items()
    }


def run_pipeline(
    train: Any,
    predict: Any,
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    skip_train: bool = False,
    skip_predict: bool = False,
    skip_metrics: bool = False,
    skip_report: bool = False,
    skip_compare: bool = False,
) -> dict[str, Any]:
    """Thread each stage's output into the next, sharing one ClearML task."""
    # Created once here so every stage attaches to the same experiment rather than
    # opening its own.
    init_task(clearml, stage="pipeline")

    results: dict[str, Any] = {}
    train_cfg = _as_dict(train)
    predict_cfg = _as_dict(predict)
    metrics_cfg = _as_dict(metrics)
    report_cfg = _as_dict(report)

    weights = predict_cfg["weights"]
    # Inference after training must reuse training's own card rather than survey again:
    # this process is still holding that card's memory, so a fresh survey would wait for
    # a device the run already owns.
    trained_device: str | None = None
    if skip_train:
        logger.info("Skipping training; using weights {}", weights)
    else:
        trained = run_train_stage(train_cfg, clearml)
        weights = trained.weights
        trained_device = trained.inference_device
        results["weights"] = trained.weights

    if skip_predict:
        logger.info("Skipping inference; using predictions {}", metrics_cfg["predictions"])
    else:
        results["predictions"] = run_predict_stage(predict_cfg, weights, clearml, trained_device)

    dashboards: dict[str, Path] = {}
    thresholds: dict[str, dict[str, float]] = {}
    if skip_metrics:
        logger.info("Skipping metrics; reading dashboards from {}", report_cfg["metrics_dir"])
        dashboards = discover_dashboards(report_cfg["metrics_dir"], list(report_cfg["splits"]))
    else:
        metrics_result = run_metrics_stage(metrics_cfg, clearml)
        dashboards = metrics_result.dashboards
        thresholds = metrics_result.best_confidences
        results["dashboards"] = dashboards

    if skip_report:
        logger.info("Skipping report stage")
    else:
        results["reports"] = build_reports(
            dashboards,
            report_cfg["output_dir"],
            clearml,
            report_cfg["baseline"],
            report_cfg.get("report_config_path"),
        )

    if skip_compare:
        logger.info("Skipping comparison stage")
    else:
        comparison = run_compare_stage(_as_dict(compare), weights, thresholds, clearml)
        if comparison is not None:
            results["comparison"] = comparison

    return results


def run_train_stage(config: dict[str, Any], clearml: ClearMLConfig) -> TrainResult:
    return run_training(
        model=config["model"],
        data=config["data"],
        epochs=config["epochs"],
        imgsz=config["imgsz"],
        batch=config["batch"],
        project=config["project"],
        name=config["name"],
        auto_gpu=config["auto_gpu"],
        clearml=clearml,
        device=config["device"],
        train_kwargs=config["train_kwargs"],
    )


def run_predict_stage(
    config: dict[str, Any],
    weights: str | Path,
    clearml: ClearMLConfig,
    trained_device: str | None = None,
) -> Path:
    return run_prediction(
        weights=weights,
        ground_truth=config["ground_truth"],
        output=config["output"],
        clearml=clearml,
        auto_gpu=config["auto_gpu"],
        conf=config["conf"],
        iou=config["iou"],
        imgsz=config["imgsz"],
        batch=config["batch"],
        device=config["device"] or trained_device,
        splits=config["splits"],
        image_name=config["image_name"],
        predict_kwargs=config["predict_kwargs"],
    )


def run_compare_stage(
    config: dict[str, Any],
    weights: str | Path,
    thresholds: dict[str, dict[str, float]],
    clearml: ClearMLConfig,
) -> CompareResult | None:
    """Compare the model this run just trained against the previous one.

    The candidate side is filled in from what the run already has — the checkpoint from
    training and the thresholds the metrics stage calibrated — rather than from config,
    which could otherwise name a different model than the one just built. The baseline
    side stays configurable and defaults to the last finished task of the project.

    Returns None instead of raising when there is nothing to compare against: a first run
    in an empty project, or a run whose metrics stage was skipped and so has no
    thresholds. Reporting must not fail a run that already produced valid results.
    """
    split = config["split"]
    if split not in thresholds:
        logger.warning(
            "No calibrated thresholds for split {!r}, so the new model cannot be scored at "
            "its own production thresholds; skipping the comparison",
            split,
        )
        return None

    candidate = ModelRef(source="local", weights=Path(weights), thresholds=thresholds[split])
    try:
        return run_comparison(
            baseline_model=config["baseline_model"],
            candidate_model=candidate,
            ground_truth=config["ground_truth"],
            output_dir=config["output_dir"],
            clearml=clearml,
            inference=config["inference"],
            auto_gpu=config["auto_gpu"],
            split=split,
            iou_threshold=config["iou_threshold"],
            matching_strategy=config["matching_strategy"],
            q=config["q"],
            bootstrap_iterations=config["bootstrap_iterations"],
            seed=config["seed"],
        )
    except NoBaselineModelError as error:
        logger.warning("Nothing to compare against: {}", error)
        return None


def run_metrics_stage(config: dict[str, Any], clearml: ClearMLConfig) -> Any:
    return compute_metrics(
        predictions=config["predictions"],
        ground_truth=config["ground_truth"],
        output_dir=config["output_dir"],
        clearml=clearml,
        evaluation=config["evaluation"],
        splits=list(config["splits"]),
        calibration_split=config["calibration_split"],
    )
