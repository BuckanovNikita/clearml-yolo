"""Run train, predict, metrics and report as one ClearML experiment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hydra_zen import instantiate
from loguru import logger
from omegaconf import OmegaConf

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.predict import predict as run_prediction
from clearml_yolo.tasks.report import build_reports, discover_dashboards
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
    clearml: ClearMLConfig,
    skip_train: bool = False,
    skip_predict: bool = False,
    skip_metrics: bool = False,
    skip_report: bool = False,
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
    if skip_train:
        logger.info("Skipping training; using weights {}", weights)
    else:
        weights = run_train_stage(train_cfg, clearml)
        results["weights"] = weights

    predictions = Path(predict_cfg["output"])
    if skip_predict:
        logger.info("Skipping inference; using predictions {}", predictions)
    else:
        predictions = run_predict_stage(predict_cfg, weights, clearml)
        results["predictions"] = predictions

    metrics_dir = Path(metrics_cfg["output_dir"])
    dashboards: dict[str, Path] = {}
    if skip_metrics:
        logger.info("Skipping metrics; reading dashboards from {}", metrics_dir)
        dashboards = discover_dashboards(metrics_dir, list(metrics_cfg["splits"]))
    else:
        metrics_result = run_metrics_stage(metrics_cfg, predictions, clearml)
        dashboards = metrics_result.dashboards
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

    return results


def run_train_stage(config: dict[str, Any], clearml: ClearMLConfig) -> Path:
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
        augmentations=config["augmentations"],
        keep_default_augmentations=config["keep_default_augmentations"],
        train_kwargs=config["train_kwargs"],
    )


def run_predict_stage(config: dict[str, Any], weights: str | Path, clearml: ClearMLConfig) -> Path:
    return run_prediction(
        weights=weights,
        ground_truth=config["ground_truth"],
        output=config["output"],
        clearml=clearml,
        conf=config["conf"],
        iou=config["iou"],
        imgsz=config["imgsz"],
        batch=config["batch"],
        device=config["device"],
        splits=config["splits"],
        image_name=config["image_name"],
        predict_kwargs=config["predict_kwargs"],
    )


def run_metrics_stage(
    config: dict[str, Any], predictions: str | Path, clearml: ClearMLConfig
) -> Any:
    return compute_metrics(
        predictions=predictions,
        ground_truth=config["ground_truth"],
        output_dir=config["output_dir"],
        clearml=clearml,
        evaluation=config["evaluation"],
        splits=list(config["splits"]),
        calibration_split=config["calibration_split"],
    )
