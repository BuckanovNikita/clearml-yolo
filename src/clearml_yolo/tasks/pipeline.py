"""Run train, predict, metrics and report as one ClearML experiment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hydra_zen import instantiate
from loguru import logger
from omegaconf import OmegaConf

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.gpu import AutoGpuConfig
from clearml_yolo.tasks.compare import (
    CompareResult,
    InferenceConfig,
    ModelRef,
    NoBaselineModelError,
)
from clearml_yolo.tasks.compare import compare as run_comparison
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.predict import predict as run_prediction
from clearml_yolo.tasks.report import BaselineConfig, build_reports, discover_dashboards
from clearml_yolo.tasks.train import CHECKPOINT
from clearml_yolo.tasks.train import train as run_training


def _as_dict(config: Any) -> dict[str, Any]:
    """Resolve a stage sub-config into the keyword arguments its task takes.

    A stage is called with this block plus what ``stage_configs`` fills in, and between
    them they cover the task's parameters exactly — checked by
    ``test_every_stage_config_key_is_a_parameter_of_its_task``, so a setting cannot be
    configured and silently unread.

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


# What run_pipeline hands each stage, and therefore what the stage's config block inside
# the pipeline does not declare. configs.py drops exactly these keys, and
# test_every_stage_config_key_is_a_parameter_of_its_task holds the two lists in step: a key
# dropped without being filled, or filled while still declared, fails the suite.
# `compare.inference` is deliberately absent: the comparison declares the two fields it
# owns and the predict stage's settings are merged over them.
PIPELINE_FILLED_KEYS: dict[str, frozenset[str]] = {
    "train": frozenset({"clearml", "auto_gpu", "name"}),
    "predict": frozenset(
        {"clearml", "auto_gpu", "ground_truth", "splits", "weights", "imgsz", "model"}
    ),
    "metrics": frozenset({"clearml", "ground_truth", "splits", "predictions"}),
    "report": frozenset({"clearml", "splits", "metrics_dir"}),
    "compare": frozenset(
        {
            "clearml",
            "auto_gpu",
            "ground_truth",
            "baseline_model",
            "candidate_model",
            "iou_threshold",
            "matching_strategy",
        }
    ),
}


def stage_configs(
    train: Any,
    predict: Any,
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    auto_gpu: AutoGpuConfig,
    ground_truth: str,
    splits: list[str],
    weights: str | Path | None,
) -> dict[str, dict[str, Any]]:
    """Give every stage its own block plus everything the run decided for it.

    A value more than one stage reads is named once — on the command line or in the top
    level of the config file — and reaches each stage from here, so it cannot be changed
    for one stage and silently left stale for another. Producer-to-consumer keys work the
    same way: the metrics stage is told the CSV inference wrote, not a second path that
    was supposed to match it.
    """
    shared_splits = list(splits)
    train_cfg = _as_dict(train) | {
        "clearml": clearml,
        "auto_gpu": auto_gpu,
        "name": clearml.task_name,
    }
    predict_cfg = _as_dict(predict) | {
        "clearml": clearml,
        "auto_gpu": auto_gpu,
        "ground_truth": ground_truth,
        "splits": shared_splits,
        # Inference belongs at the resolution the weights were trained at, on the model
        # the run trained: a batch table is keyed by the architecture.
        "imgsz": train_cfg["imgsz"],
        "model": train_cfg["model"],
        # Training overwrites this with the checkpoint it produced. The template is what a
        # run with skip_train has instead: where training would have written.
        "weights": weights
        or CHECKPOINT.format(project=train_cfg["project"], name=train_cfg["name"]),
    }
    metrics_cfg = _as_dict(metrics) | {
        "clearml": clearml,
        "ground_truth": ground_truth,
        "splits": shared_splits,
        "predictions": predict_cfg["output"],
    }
    report_cfg = _as_dict(report) | {
        "clearml": clearml,
        "splits": shared_splits,
        "metrics_dir": metrics_cfg["output_dir"],
    }
    compare_cfg = _as_dict(compare)
    return {
        "train": train_cfg,
        "predict": predict_cfg,
        "metrics": metrics_cfg,
        "report": report_cfg,
        "compare": compare_cfg
        | {
            "clearml": clearml,
            "auto_gpu": auto_gpu,
            "ground_truth": ground_truth,
            # The report reads the baseline's stored dashboards while the comparison
            # re-infers its checkpoint, and two independent searches of one project can
            # answer with two different runs. `source` is not shared: "local" means a folder
            # of workbooks to the report and a checkpoint path to the comparison.
            "baseline_model": _baseline_model(report_cfg["baseline"]),
            # Scored at the IoU its thresholds were calibrated at, or the diff is not the
            # model.
            "iou_threshold": metrics_cfg["evaluation"].iou_threshold,
            "matching_strategy": metrics_cfg["evaluation"].matching_strategy,
            "inference": _comparison_inference(compare_cfg["inference"], predict_cfg),
        },
    }


def _baseline_model(baseline: BaselineConfig) -> ModelRef:
    """Point the comparison at the task the report compares against, not at another one."""
    return ModelRef(
        source="clearml",
        task_id=baseline.task_id,
        project_name=baseline.project_name,
        task_name=baseline.task_name,
        tags=list(baseline.tags),
    )


def _comparison_inference(
    inference: InferenceConfig, predict_cfg: dict[str, Any]
) -> InferenceConfig:
    """Re-run both checkpoints exactly as the candidate was predicted.

    `device` and `reuse_existing` stay the comparison's own: it resolves one card for both
    models itself, and inheriting a device would put a hardware difference inside a
    comparison meant to isolate the model.
    """
    return inference.model_copy(
        update={
            key: predict_cfg[key]
            for key in ("conf", "iou", "imgsz", "batch", "model", "image_name")
        }
    )


def _check_split_choices(splits: list[str], choices: dict[str, str | None]) -> None:
    """Reject a stage that singles out a split the run never scores.

    The pipeline hands every stage the same split list, but that alone cannot express
    that the stages picking one split out of that list have to pick one that is in it.
    Checked before training rather than at the stage itself, so an hour of it is not
    spent to arrive at a comparison that has no thresholds to score against.
    """
    unavailable = {
        key: value for key, value in choices.items() if value is not None and value not in splits
    }
    if unavailable:
        raise ValueError(
            f"{unavailable} name split(s) this run never scores, because splits={splits}. "
            "Add them to splits, or point those stages at a split that is in it."
        )


def _check_weights_choice(weights: str | Path | None, skip_train: bool) -> None:
    """Reject a named checkpoint that training is about to overwrite.

    Training's starting point is ``train.model``, not ``weights``: a run that trains has
    no use for a checkpoint named on the side, and letting it through means an hour of
    training runs only to discard the value the caller asked for, silently.
    """
    if weights is not None and not skip_train:
        raise ValueError(
            f"weights={weights} names a checkpoint for a run that is going to train its "
            "own; set skip_train=true, or drop weights."
        )


def run_pipeline(
    train: Any,
    predict: Any,
    metrics: Any,
    report: Any,
    compare: Any,
    clearml: ClearMLConfig,
    auto_gpu: AutoGpuConfig,
    ground_truth: str,
    splits: list[str],
    weights: str | Path | None = None,
    skip_train: bool = False,
    skip_predict: bool = False,
    skip_metrics: bool = False,
    skip_report: bool = False,
    skip_compare: bool = False,
) -> dict[str, Any]:
    """Thread each stage's output into the next, sharing one ClearML task."""
    _check_weights_choice(weights, skip_train)

    # Created once here so every stage attaches to the same experiment rather than
    # opening its own.
    init_task(clearml, stage="pipeline")

    results: dict[str, Any] = {}
    configs = stage_configs(
        train=train,
        predict=predict,
        metrics=metrics,
        report=report,
        compare=compare,
        clearml=clearml,
        auto_gpu=auto_gpu,
        ground_truth=ground_truth,
        splits=splits,
        weights=weights,
    )
    train_cfg = configs["train"]
    predict_cfg = configs["predict"]
    metrics_cfg = configs["metrics"]
    report_cfg = configs["report"]
    compare_cfg = configs["compare"]

    _check_split_choices(
        list(splits),
        {
            "metrics.calibration_split": None if skip_metrics else metrics_cfg["calibration_split"],
            "compare.split": None if skip_compare else compare_cfg["split"],
        },
    )

    checkpoint = predict_cfg["weights"]
    # Inference after training must reuse training's own card rather than survey again:
    # this process is still holding that card's memory, so a fresh survey would wait for
    # a device the run already owns.
    trained_device: str | None = None
    if skip_train:
        logger.info("Skipping training; using weights {}", checkpoint)
    else:
        trained = run_training(**train_cfg)
        checkpoint = trained.weights
        trained_device = trained.inference_device
        results["weights"] = trained.weights

    if skip_predict:
        logger.info("Skipping inference; using predictions {}", metrics_cfg["predictions"])
    else:
        results["predictions"] = run_predict_stage(predict_cfg, checkpoint, trained_device)

    dashboards: dict[str, Path] = {}
    thresholds: dict[str, dict[str, float]] = {}
    if skip_metrics:
        logger.info("Skipping metrics; reading dashboards from {}", report_cfg["metrics_dir"])
        dashboards = discover_dashboards(report_cfg["metrics_dir"], list(report_cfg["splits"]))
    else:
        metrics_result = compute_metrics(**metrics_cfg)
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
            report_cfg["report_config_path"],
        )

    if skip_compare:
        logger.info("Skipping comparison stage")
    else:
        comparison = run_compare_stage(compare_cfg, checkpoint, thresholds, trained_device)
        if comparison is not None:
            results["comparison"] = comparison

    return results


def run_predict_stage(
    config: dict[str, Any],
    weights: str | Path,
    trained_device: str | None = None,
) -> Path:
    """Infer with the checkpoint this run produced, on the card that produced it."""
    return run_prediction(
        **{
            **config,
            "weights": weights,
            "device": config["device"] or trained_device,
        }
    )


def run_compare_stage(
    config: dict[str, Any],
    weights: str | Path,
    thresholds: dict[str, dict[str, float]],
    trained_device: str | None = None,
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
    # Both models still go on one card — the comparison sets that itself — but after
    # training it is this run's own card, for the reason the predict stage documents.
    inference = config["inference"]
    if inference.device is None and trained_device is not None:
        inference = inference.model_copy(update={"device": trained_device})
    try:
        return run_comparison(
            **{
                **config,
                "candidate_model": candidate,
                "inference": inference,
            }
        )
    except NoBaselineModelError as error:
        logger.warning("Nothing to compare against: {}", error)
        return None
