"""Run train, predict, metrics and report as one ClearML experiment."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hydra_zen import instantiate
from loguru import logger
from omegaconf import OmegaConf

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.gpu import AutoGpuConfig
from clearml_yolo.inference import ScoredResolution
from clearml_yolo.run_identity import (
    LATEST_LINK_NAME,
    point_latest_at,
    resolve_run_dir,
    resolve_run_id,
)
from clearml_yolo.tasks.compare import (
    CompareResult,
    InferenceConfig,
    ModelRef,
    NoBaselineModelError,
)
from clearml_yolo.tasks.compare import compare as run_comparison
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.predict import PredictResult
from clearml_yolo.tasks.predict import predict as run_prediction
from clearml_yolo.tasks.report import BaselineConfig, build_reports, discover_dashboards
from clearml_yolo.tasks.train import CHECKPOINT
from clearml_yolo.tasks.train import train as run_training

# Hydra's own key for a config's defaults list, not a setting any task takes. Hydra
# consumes it during composition and it is gone from the composed DictConfig — but `zen`
# hands each top-level field over already instantiated, as the generated dataclass, and
# that dataclass declares `defaults` as an ordinary field. So it comes back as data on
# exactly the path the CLI takes and no other, which is why it has to be dropped here
# rather than trusted to have been consumed.
COMPOSITION_ONLY_KEYS = frozenset({"defaults"})

# Every path a run writes hangs off one directory of its own, under this root. Two runs
# started in the same folder used to share `runs/detect/<task_name>` with ultralytics'
# `exist_ok` set, which is not a merge but a deletion: the DDP launcher clears the save
# directory before spawning its children. The leaf names are what each directory was
# called when they all sat directly under the root.
RUNS_ROOT = Path("runs")
TRAIN_DIR = "detect"
PREDICTIONS_NAME = "predictions.csv"
METRICS_DIR = "metrics"
REPORTS_DIR = "reports"
COMPARISON_DIR = "comparison"


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
    if not isinstance(resolved, dict) and not OmegaConf.is_config(resolved):
        # A dataclass instance, which is what `zen` passes: read its fields back out.
        resolved = OmegaConf.structured(resolved)
    values = dict(resolved) if not isinstance(resolved, dict) else resolved
    return {
        key: OmegaConf.to_object(value) if OmegaConf.is_config(value) else value
        for key, value in values.items()
        if key not in COMPOSITION_ONLY_KEYS
    }


# What run_pipeline hands each stage, and therefore what the stage's config block inside
# the pipeline does not declare. configs.py drops exactly these keys, and
# test_every_stage_config_key_is_a_parameter_of_its_task holds the two lists in step: a key
# dropped without being filled, or filled while still declared, fails the suite.
# `compare.inference` is deliberately absent: the comparison declares the two fields it
# owns and the predict stage's settings are merged over them.
# `train.name` and `predict.imgsz` are deliberately absent, though the run does decide
# both. They live inside the shared `ultralytics` group file, which is one file for the
# standalone app and the pipeline alike, so a key cannot be dropped from it here — and
# overwriting it instead would make it a key a run can set and the pipeline silently
# discards. Both are `null` there and answered by a source that cannot go stale: the
# ClearML task name, and the resolution recorded in the checkpoint.
# `train.ultralytics.project` lives in that same shared file and so cannot be dropped
# either, but unlike those two the run does overwrite it: a run directory a stage could
# opt out of would isolate nothing, and `run_dir` is the key that moves it.
PIPELINE_FILLED_KEYS: dict[str, frozenset[str]] = {
    "train": frozenset({"clearml", "auto_gpu"}),
    "predict": frozenset(
        {"clearml", "auto_gpu", "ground_truth", "splits", "weights", "model", "output"}
    ),
    "metrics": frozenset({"clearml", "ground_truth", "splits", "predictions", "output_dir"}),
    "report": frozenset({"clearml", "splits", "metrics_dir", "output_dir"}),
    "compare": frozenset(
        {
            "clearml",
            "auto_gpu",
            "ground_truth",
            "baseline_model",
            "candidate_model",
            "iou_threshold",
            "output_dir",
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
    run_dir: Path,
    previous_run_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Give every stage its own block plus everything the run decided for it.

    A value more than one stage reads is named once — on the command line or in the top
    level of the config file — and reaches each stage from here, so it cannot be changed
    for one stage and silently left stale for another. Producer-to-consumer keys work the
    same way: the metrics stage is told the CSV inference wrote, not a second path that
    was supposed to match it.

    Every path a stage writes is one of those values, because none of them is really a
    stage's own choice: they are one directory, named after the run, and a stage allowed
    to leave it would put this run's output back where a peer run overwrites it.
    ``previous_run_dir`` is the one path pointing outside, and it is read rather than
    written: a run that skips training loads the checkpoint the run before it produced.
    """
    shared_splits = list(splits)
    train_cfg = _as_dict(train) | {"clearml": clearml, "auto_gpu": auto_gpu}
    train_params = train_cfg["ultralytics"] | {"project": str(run_dir / TRAIN_DIR)}
    train_cfg["ultralytics"] = train_params
    predict_cfg = _as_dict(predict) | {
        "clearml": clearml,
        "auto_gpu": auto_gpu,
        "ground_truth": ground_truth,
        "splits": shared_splits,
        "output": str(run_dir / PREDICTIONS_NAME),
        # The model the run trained: a batch table is keyed by the architecture. The
        # resolution is not passed across — the predict block leaves it null and the
        # checkpoint answers it, which is the same number from a source that cannot
        # disagree with the weights it describes.
        "model": train_params["model"],
        # Training overwrites this with the checkpoint it produced. The template is what a
        # run with skip_train has instead: where training last wrote. That is the previous
        # run's directory, never this one's, which is empty until this run trains. `name`
        # is null in the config and resolved to the experiment's name by the train task, so
        # it is resolved the same way here rather than read back out of the block.
        "weights": weights
        or CHECKPOINT.format(
            project=previous_run_dir / TRAIN_DIR, name=train_params["name"] or clearml.task_name
        ),
    }
    metrics_cfg = _as_dict(metrics) | {
        "clearml": clearml,
        "ground_truth": ground_truth,
        "splits": shared_splits,
        "predictions": predict_cfg["output"],
        "output_dir": str(run_dir / METRICS_DIR),
    }
    report_cfg = _as_dict(report) | {
        "clearml": clearml,
        "splits": shared_splits,
        "metrics_dir": metrics_cfg["output_dir"],
        "output_dir": str(run_dir / REPORTS_DIR),
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
            "output_dir": str(run_dir / COMPARISON_DIR),
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

    Most of what the comparison needs is an ultralytics parameter and comes out of the
    predict stage's block; `model` and `image_name` are this project's own and sit beside
    it. `device` and `reuse_existing` stay the comparison's own: it resolves one card for
    both models itself, and inheriting a device would put a hardware difference inside a
    comparison meant to isolate the model.
    """
    predict_params = predict_cfg["ultralytics"]
    return inference.model_copy(
        update={
            **{
                key: predict_params[key]
                for key in ("conf", "iou", "imgsz", "batch", "quantize")
            },
            **{key: predict_cfg[key] for key in ("model", "image_name")},
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


def _check_ground_truth(ground_truth: str, readers: list[str]) -> None:
    """Reject a ground-truth CSV that is not there, before training rather than after it.

    Every stage that scores anything reads this file, and the first of them runs once
    training is done, so a path that does not exist costs the whole training run before
    pandas reports it — and reports it as a bare filename, naming neither the key that
    set it nor the command that writes it.
    """
    if not readers or Path(ground_truth).is_file():
        return
    raise FileNotFoundError(
        f"ground_truth={ground_truth} does not exist, and the {', '.join(readers)} "
        f"stage(s) read it. Write it first with `cy-ground-truth data_yaml=<your "
        f"data.yaml> output={ground_truth}`."
    )


def _check_comparison_baseline(baseline: ModelRef, clearml: ClearMLConfig) -> None:
    """Reject a comparison with no way to reach its baseline, before training.

    Inside the pipeline the baseline is always a ClearML task, so a run with tracking off
    has nowhere to look one up unless the task or its project is named outright. The
    comparison is the last stage, so without this the run trains, predicts, scores and
    reports, and only then fails on a lookup that could never have succeeded.
    """
    if baseline.task_id or baseline.project_name or clearml.enabled:
        return
    raise ValueError(
        "The comparison stage resolves its baseline out of ClearML, but "
        "clearml.enabled=false leaves it no project to search. Pass skip_compare=true to "
        "run without the comparison, or name the baseline task outright with "
        "report.baseline.task_id=<id>."
    )


def _check_resolution_choice(
    train_params: dict[str, Any], predict_params: dict[str, Any], has_reader: bool
) -> None:
    """Reject scoring this run's own model at a scale it is not being trained at.

    A model generalises to the scale it was shown, so training at one resolution and
    inferring at another measures it on images unlike anything it ever saw. Off-resolution
    inference is a real thing to want — the predict stage warns and proceeds — but wanting
    it *of the model this same run is about to train* is not a thing anyone wants, and
    finding out costs the whole training run, because the checkpoint the warning compares
    against does not exist until training has finished.

    ``predict.imgsz`` left null is the answer, not the problem: it is filled from the
    checkpoint, which cannot disagree with the weights it describes. Only a resolution named
    outright can conflict. Both values must be ints to be compared at all — the ultralytics
    files note that predict and export may take ``[h, w]``, and a shape this cannot read is
    left to the stage that understands it rather than guessed at here.
    """
    trained_at = train_params.get("imgsz")
    scored_at = predict_params.get("imgsz")
    if not has_reader or scored_at is None:
        return
    if not isinstance(trained_at, int) or not isinstance(scored_at, int):
        return
    if trained_at == scored_at:
        return
    raise ValueError(
        f"This run trains at imgsz={trained_at} and would score at imgsz={scored_at}, so it "
        "would measure the model it just built on images at a scale it was never shown. "
        "Leave predict.ultralytics.imgsz null and the checkpoint answers it, or train at "
        f"imgsz={scored_at}."
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


def _check_checkpoint(weights: str | Path, readers: list[str]) -> None:
    """Reject a run that skips training with no checkpoint to skip it with.

    A run writes into a directory of its own now, so the model a previous run trained is
    reached through the ``latest`` link rather than through a fixed path — and in a folder
    no run has finished in yet, that link is not there. Without this the run reaches
    ultralytics with a path to nothing, which reports it as a failed download of a
    pretrained model and names neither the link nor the key that would have set it.
    """
    if not readers or Path(weights).is_file():
        return
    raise FileNotFoundError(
        f"skip_train=true, but {weights} does not exist and the {', '.join(readers)} "
        f"stage(s) load it. Name the checkpoint outright with weights=<path/to/best.pt>, "
        f"or drop skip_train and let this run train its own."
    )


def _preflight(
    configs: dict[str, dict[str, Any]],
    clearml: ClearMLConfig,
    ground_truth: str,
    splits: list[str],
    skipped: dict[str, bool],
) -> None:
    """Everything that has to hold, checked while checking it is still free.

    Every one of these is a cross-stage mismatch that config alone cannot express, and every
    one of them would otherwise surface after training — the most expensive moment to learn
    that the run was never going to produce what was asked for. They are grouped rather than
    spelled out in the run so that "what is checked up front" is one list, and a new check
    lands in it rather than wherever there was room.
    """
    metrics_cfg = configs["metrics"]
    compare_cfg = configs["compare"]

    _check_split_choices(
        splits,
        {
            "metrics.calibration_split": (
                None if skipped["metrics"] else metrics_cfg["calibration_split"]
            ),
            "compare.split": None if skipped["compare"] else compare_cfg["split"],
        },
    )
    _check_resolution_choice(
        configs["train"]["ultralytics"],
        configs["predict"]["ultralytics"],
        # The comparison is the second reader of the predict block's resolution — see
        # `_comparison_inference` — so a run that skips inference but still compares would
        # otherwise hit the same mismatch, an hour later, on the checkpoint it just trained.
        has_reader=not skipped["train"] and not (skipped["predict"] and skipped["compare"]),
    )
    _check_ground_truth(
        ground_truth,
        [stage for stage in ("predict", "metrics", "compare") if not skipped[stage]],
    )
    if skipped["train"]:
        _check_checkpoint(
            configs["predict"]["weights"],
            [stage for stage in ("predict", "compare") if not skipped[stage]],
        )
    if not skipped["compare"]:
        _check_comparison_baseline(compare_cfg["baseline_model"], clearml)


def _resolve_run_directories(
    clearml: ClearMLConfig, run_id: str | None, run_dir: str | Path | None
) -> tuple[Path, Path]:
    """Name this run, and read where the previous one left its model.

    The two come from here together because their order is the whole point: ``latest``
    still names the run before this one until this run repoints it, and that is where a
    run with ``skip_train`` and no ``weights`` finds a checkpoint. Resolved once, so the
    path survives the link moving on.
    """
    identity = resolve_run_id(clearml.task_name, run_id, datetime.now(tz=UTC))
    directory = resolve_run_dir(RUNS_ROOT, identity, Path(run_dir) if run_dir is not None else None)
    previous = (RUNS_ROOT / LATEST_LINK_NAME).resolve()
    logger.info("Run {} writes everything it produces to {}", identity, directory)
    return directory, previous


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
    run_id: str | None = None,
    run_dir: str | Path | None = None,
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

    directory, previous = _resolve_run_directories(clearml, run_id, run_dir)

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
        run_dir=directory,
        previous_run_dir=previous,
    )
    train_cfg = configs["train"]
    predict_cfg = configs["predict"]
    metrics_cfg = configs["metrics"]
    report_cfg = configs["report"]
    compare_cfg = configs["compare"]

    _preflight(
        configs,
        clearml,
        ground_truth,
        list(splits),
        {
            "train": skip_train,
            "predict": skip_predict,
            "metrics": skip_metrics,
            "compare": skip_compare,
        },
    )

    # Only now, with every pre-flight check passed: a run that refuses writes nothing, and
    # pointing the link at its empty directory would hide the last run that did.
    directory.mkdir(parents=True, exist_ok=True)
    point_latest_at(RUNS_ROOT, directory)

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

    # Known only when this run inferred: the scale the numbers downstream were measured at.
    resolution: ScoredResolution | None = None
    if skip_predict:
        logger.info("Skipping inference; using predictions {}", metrics_cfg["predictions"])
    else:
        predicted = run_predict_stage(predict_cfg, checkpoint, trained_device)
        resolution = predicted.resolution
        results["predictions"] = predicted.predictions

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
            resolution,
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
) -> PredictResult:
    """Infer with the checkpoint this run produced, on the card that produced it."""
    params = config["ultralytics"]
    return run_prediction(
        **{
            **config,
            "weights": weights,
            "ultralytics": params | {"device": params["device"] or trained_device},
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
