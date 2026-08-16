"""Config composition: every app resolves, and ClearML naming reaches every stage."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import instantiate, store

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.gpu import AutoGpuConfig
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, compare
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.pipeline import PIPELINE_FILLED_KEYS, stage_configs
from clearml_yolo.tasks.predict import predict
from clearml_yolo.tasks.report import report
from clearml_yolo.tasks.train import train

STAGES = ["train", "predict", "metrics", "report"]
ALL_STAGES = [*STAGES, "compare"]

TASK_OF_STAGE: dict[str, Callable[..., Any]] = {
    "train": train,
    "predict": predict,
    "metrics": compute_metrics,
    "report": report,
    "compare": compare,
}


@pytest.fixture(scope="module", autouse=True)
def hydra_store() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


@pytest.mark.parametrize("app", [*STAGES, "pipeline"])
def test_app_config_composes(app: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=app)

    assert config is not None


RUN_DIR = Path("runs/exp-here")
PREVIOUS_RUN_DIR = Path("runs/exp-before")


def _pipeline_stages(
    overrides: list[str], run_dir: Path = RUN_DIR
) -> dict[str, dict[str, object]]:
    """Compose the pipeline and build each stage's kwargs the way run_pipeline does.

    Composing alone proves nothing about what a stage receives: the shared values are not
    in the stage blocks at all, they are handed over by ``stage_configs``.

    The two directories are named here rather than resolved, because ``run_pipeline``
    names them too: what a run decides cannot be read back out of the composed config.

    Each block is instantiated first, because that is what ``zen`` does before calling
    ``run_pipeline`` and the shape differs: a composed block is a ``DictConfig`` with
    Hydra's ``defaults`` key already consumed, while an instantiated one is the generated
    dataclass, which declares ``defaults`` as an ordinary field and hands it back as data.
    Passing the ``DictConfig`` here tested a shape the CLI never produces, and a stray
    ``defaults`` reaching a task as a keyword argument went unnoticed until a run.
    """
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=overrides)
    return stage_configs(
        train=instantiate(config.train),
        predict=instantiate(config.predict),
        metrics=instantiate(config.metrics),
        report=instantiate(config.report),
        compare=instantiate(config.compare),
        clearml=instantiate(config.clearml),
        auto_gpu=instantiate(config.auto_gpu),
        ground_truth=config.ground_truth,
        splits=config.splits,
        weights=config.get("weights"),
        run_dir=run_dir,
        previous_run_dir=PREVIOUS_RUN_DIR,
    )


def _ultralytics(overrides: list[str], stage: str, run_dir: Path = RUN_DIR) -> dict[str, Any]:
    """One stage's ultralytics block, as the task would be handed it."""
    params: dict[str, Any] = _pipeline_stages(overrides, run_dir)[stage]["ultralytics"]  # type: ignore[assignment]
    return params


def test_clearml_name_reaches_every_pipeline_stage() -> None:
    """One override must name the whole experiment, not just the top-level block."""
    stages = _pipeline_stages(["clearml.project_name=my-proj", "clearml.task_name=exp-42"])

    for stage in ALL_STAGES:
        clearml = stages[stage]["clearml"]
        assert isinstance(clearml, ClearMLConfig)
        assert clearml.project_name == "my-proj", stage
        assert clearml.task_name == "exp-42", stage


@pytest.mark.parametrize("stage", ALL_STAGES)
def test_every_stage_config_key_is_a_parameter_of_its_task(stage: str) -> None:
    """The pipeline calls a stage with its whole block plus what the run filled in.

    A key that is not a parameter is a setting the run accepts and silently ignores; a
    parameter that is neither a key nor filled in is a TypeError raised an hour into a run.
    Neither is visible to the type checker once the block is a dict, so it is checked here.

    The union alone would also pass a key that ``PIPELINE_FILLED_KEYS`` names but
    ``stage_configs`` never actually fills — that key is a config key silently omitted with
    nothing supplying it, the same TypeError an hour into a run. The second assertion pins
    every filled key to one ``stage_configs`` actually produces, except ``candidate_model``:
    ``run_compare_stage`` fills that one from the model this run just trained, not
    ``stage_configs``, and
    ``tests/test_pipeline.py::test_comparison_scores_the_model_this_run_just_built`` covers it.
    """
    stage_kwargs = set(_pipeline_stages([])[stage])
    keys = stage_kwargs | PIPELINE_FILLED_KEYS[stage]

    assert keys == set(inspect.signature(TASK_OF_STAGE[stage]).parameters)
    assert PIPELINE_FILLED_KEYS[stage] - {"candidate_model"} <= stage_kwargs


def test_the_comparison_declares_only_the_inference_it_owns() -> None:
    """Every other inference setting comes from the predict stage, merged in by
    ``stage_configs``. Declaring one here would be a key a run can set in ``compare.inference``
    that a pipeline run then silently overwrites — the same defect class this branch removes
    everywhere else, and it would slip in unnoticed the moment ``ComparisonInferenceConf``
    gains ``populate_full_signature=True`` like every other ``builds(...)`` in configs.py."""
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")

    assert set(config.compare.inference) - {"_target_"} == {"device", "reuse_existing"}


def test_one_ground_truth_reaches_inference_scoring_and_comparison() -> None:
    """Three stages read the same CSV; naming it three times is how they drift apart."""
    stages = _pipeline_stages(["ground_truth=runs/kitti_gt.csv"])

    for stage in ("predict", "metrics", "compare"):
        assert stages[stage]["ground_truth"] == "runs/kitti_gt.csv", stage


def test_one_split_list_reaches_every_stage_that_reads_one() -> None:
    stages = _pipeline_stages(["splits=[val,test]"])

    for stage in ("predict", "metrics", "report"):
        assert stages[stage]["splits"] == ["val", "test"], stage


def test_the_gpu_policy_is_named_once_for_all_three_stages() -> None:
    """auto_gpu reaches every stage as the AutoGpuConfig instance stage_configs was given,
    not resolved down to a string or a stripped dict."""
    stages = _pipeline_stages(["auto_gpu.wait_timeout_seconds=120.0"])

    for stage in ("train", "predict", "compare"):
        auto_gpu = stages[stage]["auto_gpu"]
        assert isinstance(auto_gpu, AutoGpuConfig), stage
        assert auto_gpu.wait_timeout_seconds == 120.0, stage


def test_the_run_name_follows_the_experiment_name() -> None:
    """train.name is the run directory, and having to repeat the task name is how the two
    stopped matching."""
    named = ["clearml.task_name=kitti-candidate"]

    # `train.ultralytics.name` stays null: the train task resolves it, and the pipeline
    # builds the same path here rather than writing into a key a run may have set.
    assert _ultralytics(named, "train")["name"] is None
    assert _pipeline_stages(named)["predict"]["weights"] == (
        "runs/exp-before/detect/kitti-candidate/weights/best.pt"
    )


def test_a_named_run_directory_wins_over_the_experiment_name() -> None:
    """A run that says where its checkpoints go must be predicted at that path, or a
    skipped training stage looks for a file training never wrote."""
    stages = _pipeline_stages(
        ["clearml.task_name=kitti-candidate", "train.ultralytics.name=sweep-07"]
    )

    assert stages["predict"]["weights"] == "runs/exp-before/detect/sweep-07/weights/best.pt"


def test_a_skipped_training_stage_reads_the_checkpoint_the_last_run_wrote() -> None:
    """Nothing produced a checkpoint this run, and this run's own directory is empty by
    construction — every run writes into one of its own now. The model to load is the one
    the previous run left behind, which is what `runs/latest` points at."""
    stages = _pipeline_stages(["skip_train=true", "clearml.task_name=kitti-candidate"])

    assert stages["predict"]["weights"] == (
        "runs/exp-before/detect/kitti-candidate/weights/best.pt"
    )


@pytest.mark.parametrize("run_dir", [RUN_DIR, Path("/data/yolo/exp-elsewhere")])
def test_no_stage_writes_outside_the_run_directory(run_dir: Path) -> None:
    """One run, one directory, and a directory the run alone names.

    A stage keeping a fixed path of its own is the collision this exists to remove: two
    runs started in the same folder wrote into the same `runs/detect/<task_name>`, and
    with ultralytics' `exist_ok` set that is not a merge but a deletion. So it is not
    enough that the paths differ from each other — every one of them has to be inside the
    directory this run was given, wherever that was pointed.
    """
    stages = _pipeline_stages([], run_dir=run_dir)
    written = {
        "train": _ultralytics([], "train", run_dir=run_dir)["project"],
        "predict": stages["predict"]["output"],
        "metrics": stages["metrics"]["output_dir"],
        "report": stages["report"]["output_dir"],
        "compare": stages["compare"]["output_dir"],
    }

    for stage, path in written.items():
        assert Path(str(path)).is_relative_to(run_dir), f"{stage} writes to {path}"


def test_each_stage_reads_what_the_previous_one_wrote() -> None:
    """These keys were dead before: the pipeline read the producing stage's key instead,
    so changing metrics.output_dir left report.metrics_dir silently stale. Now that both
    ends of each pair are the run's own decision there is nothing left to leave stale, and
    what has to hold is that the consumer is handed the producer's path and not a second
    one built the same way."""
    stages = _pipeline_stages([])

    assert stages["metrics"]["predictions"] == stages["predict"]["output"]
    assert stages["report"]["metrics_dir"] == stages["metrics"]["output_dir"]


def test_the_comparison_re_infers_exactly_as_the_predict_stage_did() -> None:
    """Both models must be scored the way the candidate was, or the diff is not the model."""
    stages = _pipeline_stages(
        [
            "predict.ultralytics.conf=0.005",
            "predict.ultralytics.imgsz=1280",
            "predict.ultralytics.batch=8",
            "predict.ultralytics.quantize=32",
        ]
    )

    inference = stages["compare"]["inference"]
    assert isinstance(inference, InferenceConfig)
    assert (inference.conf, inference.imgsz, inference.batch) == (0.005, 1280, 8)
    # A run that pinned FP32 to reproduce older numbers must not have the comparison
    # silently score both models at FP16 instead.
    assert inference.quantize == 32
    # The card stays the comparison's own: inheriting it would let the two models be
    # re-inferred on different hardware, which is the one thing this must not compare.
    assert inference.device is None


def test_the_comparison_keeps_the_inference_settings_it_owns() -> None:
    """Everything else about inference is the predict stage's, merged in over these two."""
    stages = _pipeline_stages(
        ["compare.inference.reuse_existing=false", "predict.ultralytics.conf=0.02"]
    )

    inference = stages["compare"]["inference"]
    assert isinstance(inference, InferenceConfig)
    assert inference.reuse_existing is False
    assert inference.device is None
    assert inference.conf == 0.02


def test_inference_asks_the_checkpoint_what_resolution_to_run_at() -> None:
    """A model trained at 1280 and inferred at 640 is scored on images it never saw the
    like of. The number is not copied across from the train block: the checkpoint records
    it, and that is the one source that cannot disagree with the weights it describes —
    including for a run that skipped training and was handed somebody else's model."""
    stages = _pipeline_stages(["train.ultralytics.imgsz=1280"])

    assert _ultralytics(["train.ultralytics.imgsz=1280"], "predict")["imgsz"] is None
    inference = stages["compare"]["inference"]
    assert isinstance(inference, InferenceConfig)
    assert inference.imgsz is None


def test_the_model_under_test_is_named_once_for_the_whole_run() -> None:
    """Batch sizing is keyed by it, and inference and the comparison would otherwise have
    to be told a second and third time which model they are running."""
    stages = _pipeline_stages(["train.ultralytics.model=yolo11x.pt"])

    assert stages["predict"]["model"] == "yolo11x.pt"
    inference = stages["compare"]["inference"]
    assert isinstance(inference, InferenceConfig)
    assert inference.model == "yolo11x.pt"


@pytest.mark.parametrize("stage", ["train", "predict"])
def test_no_stage_pins_a_batch_the_hardware_never_saw(stage: str) -> None:
    """Unset is what hands the decision to auto_gpu, so a default number here would be a
    pin — and a pin that reached the run without anyone choosing it is how the configured
    batch came to be ignored in the first place."""
    assert _ultralytics([], stage)["batch"] is None


@pytest.mark.parametrize("stage", ["train", "predict"])
def test_no_stage_pins_a_card_the_run_did_not_survey(stage: str) -> None:
    assert _ultralytics([], stage)["device"] is None


def test_prediction_keeps_every_detection_calibration_needs() -> None:
    """Ultralytics' own predict default is 0.25, which would drop the low-confidence
    detections the per-class thresholds are chosen from — a recall collapse that reads as
    a model regression. The key-union test cannot see a wrong value, so it is pinned here."""
    assert _ultralytics([], "predict")["conf"] < 0.01


def test_the_report_and_the_comparison_resolve_the_same_baseline() -> None:
    """Both look a baseline up in the same project by the same tag, so two independent
    searches can answer with two different runs: a report against one model next to a
    comparison against another."""
    stages = _pipeline_stages(["report.baseline.task_id=abc123"])

    baseline_model = stages["compare"]["baseline_model"]
    assert isinstance(baseline_model, ModelRef)
    assert baseline_model.task_id == "abc123"


def test_promoting_a_different_tag_moves_both_sides_of_the_baseline() -> None:
    stages = _pipeline_stages(["report.baseline.tags=[release]"])

    baseline_model = stages["compare"]["baseline_model"]
    assert isinstance(baseline_model, ModelRef)
    assert baseline_model.tags == ["release"]


@pytest.mark.parametrize("source", ["clearml", "local", "none"])
def test_the_baseline_can_be_pinned_whichever_report_the_run_asks_for(source: str) -> None:
    """Wanting a comparison against a named prod model but no dashboard report is an
    ordinary ask, so the key that pins it must stay reachable when the report's own
    baseline is switched off. The two share a task identity but not a source: "local"
    means a folder of workbooks to the report and a checkpoint to the comparison."""
    stages = _pipeline_stages([f"report/baseline={source}", "report.baseline.task_id=abc123"])

    baseline_model = stages["compare"]["baseline_model"]
    assert isinstance(baseline_model, ModelRef)
    assert baseline_model.task_id == "abc123"
    assert baseline_model.source == "clearml"


def test_the_comparison_scores_at_the_iou_its_thresholds_were_calibrated_at() -> None:
    stages = _pipeline_stages(
        ["metrics.evaluation.iou_threshold=0.35", "metrics.evaluation.matching_strategy=greedy"]
    )

    assert stages["compare"]["iou_threshold"] == 0.35
    assert stages["compare"]["matching_strategy"] == "greedy"


def test_the_pipeline_offers_no_candidate_model_to_set() -> None:
    """The pipeline fills the candidate in from the model it just trained, so offering the
    key would only let a run name a different model than the one under test."""
    stages = _pipeline_stages([])

    assert "candidate_model" not in stages["compare"]
    assert "baseline_model" in stages["compare"]


def test_the_standalone_comparison_still_names_both_sides() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="compare")

    assert config.candidate_model is not None
    assert config.baseline_model is not None


@pytest.mark.parametrize("source", ["clearml", "local", "none"])
def test_baseline_group_swaps_standalone(source: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="report", overrides=[f"baseline={source}"])

    assert instantiate(config.baseline).source == source


@pytest.mark.parametrize("source", ["clearml", "local", "none"])
def test_baseline_group_swaps_inside_pipeline(source: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=[f"report/baseline={source}"])

    assert instantiate(config.report.baseline).source == source


@pytest.mark.parametrize("stage", ALL_STAGES)
def test_a_pipeline_stage_declares_nothing_the_run_fills_in(stage: str) -> None:
    """A key that is both declared and filled is a setting a run can change with no effect."""
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")

    assert not set(config[stage]) & PIPELINE_FILLED_KEYS[stage]


def test_a_named_checkpoint_wins_over_the_one_training_would_have_written() -> None:
    """Which is the whole point of the key: skip_train with weights from somewhere else."""
    stages = _pipeline_stages(["skip_train=true", "weights=runs/old/best.pt"])

    assert stages["predict"]["weights"] == "runs/old/best.pt"


def test_auto_gpu_defaults_are_valid() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train")

    auto_gpu = instantiate(config.auto_gpu)
    assert auto_gpu.enabled is True
    assert auto_gpu.batch_per_gpu >= 1
    assert auto_gpu.reference_vram_gb > 0
