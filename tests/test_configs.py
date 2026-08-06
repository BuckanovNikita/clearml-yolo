"""Config composition: every app resolves, and ClearML naming reaches every stage."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import instantiate, store

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.gpu import AutoGpuConfig
from clearml_yolo.tasks.compare import InferenceConfig, ModelRef, compare
from clearml_yolo.tasks.metrics import compute_metrics
from clearml_yolo.tasks.pipeline import _as_dict
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
# What the pipeline fills in from the run itself rather than from config: the candidate is
# the model it just trained, which no config key may name.
FILLED_IN_AT_RUNTIME = {"compare": {"candidate_model"}}


@pytest.fixture(scope="module", autouse=True)
def hydra_store() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


@pytest.mark.parametrize("app", [*STAGES, "pipeline"])
def test_app_config_composes(app: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=app)

    assert config is not None


def test_clearml_name_reaches_every_pipeline_stage() -> None:
    """One override must name the whole experiment, not just the top-level block."""
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=["clearml.project_name=my-proj", "clearml.task_name=exp-42"],
        )

    assert config.clearml.project_name == "my-proj"
    for stage in STAGES:
        assert config[stage].clearml.project_name == "my-proj", stage
        assert config[stage].clearml.task_name == "exp-42", stage


def _pipeline_stages(overrides: list[str]) -> dict[str, dict[str, object]]:
    """Compose the pipeline and resolve each stage the way run_pipeline does.

    Composing alone is not enough to prove an interpolation works: it leaves the ``${...}``
    unresolved, and a node interpolation only turns back into a real config object when
    ``_as_dict`` instantiates it.
    """
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline", overrides=overrides)
    return {stage: _as_dict(config[stage]) for stage in ALL_STAGES}


@pytest.mark.parametrize("stage", ALL_STAGES)
def test_every_stage_config_key_is_a_parameter_of_its_task(stage: str) -> None:
    """The pipeline forwards a stage's whole config block as keyword arguments.

    A key that is not a parameter is a setting the run accepts and silently ignores; a
    parameter that is not a key is a TypeError raised an hour into a run. Neither is
    visible to the type checker once the block is a dict, so it is checked here.
    """
    supplied = FILLED_IN_AT_RUNTIME.get(stage, set())
    keys = set(_pipeline_stages([])[stage]) | supplied

    assert keys == set(inspect.signature(TASK_OF_STAGE[stage]).parameters)


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
    """A whole config node is interpolated here, not a string, so it must survive instantiate."""
    stages = _pipeline_stages(["auto_gpu.wait_timeout_seconds=120.0"])

    for stage in ("train", "predict", "compare"):
        auto_gpu = stages[stage]["auto_gpu"]
        assert isinstance(auto_gpu, AutoGpuConfig), stage
        assert auto_gpu.wait_timeout_seconds == 120.0, stage


def test_the_run_name_follows_the_experiment_name() -> None:
    """train.name is the run directory, and having to repeat the task name is how the two
    stopped matching."""
    stages = _pipeline_stages(["clearml.task_name=kitti-candidate"])

    assert stages["train"]["name"] == "kitti-candidate"
    assert stages["predict"]["weights"] == "runs/detect/kitti-candidate/weights/best.pt"


def test_each_stage_reads_what_the_previous_one_wrote() -> None:
    """These keys were dead before: the pipeline read the producing stage's key instead,
    so changing metrics.output_dir left report.metrics_dir silently stale."""
    stages = _pipeline_stages(
        ["predict.output=runs/kitti_preds.csv", "metrics.output_dir=runs/kitti_metrics"]
    )

    assert stages["metrics"]["predictions"] == "runs/kitti_preds.csv"
    assert stages["report"]["metrics_dir"] == "runs/kitti_metrics"


def test_the_comparison_re_infers_exactly_as_the_predict_stage_did() -> None:
    """Both models must be scored the way the candidate was, or the diff is not the model."""
    stages = _pipeline_stages(["predict.conf=0.005", "predict.imgsz=1280", "predict.batch=8"])

    inference = stages["compare"]["inference"]
    assert isinstance(inference, InferenceConfig)
    assert (inference.conf, inference.imgsz, inference.batch) == (0.005, 1280, 8)
    # The card stays the comparison's own: inheriting it would let the two models be
    # re-inferred on different hardware, which is the one thing this must not compare.
    assert inference.device is None


def test_inference_runs_at_the_resolution_the_model_was_trained_at() -> None:
    """A model trained at 1280 and inferred at 640 is scored on images it never saw the
    like of, and the number would otherwise have to be given to two stages by hand."""
    stages = _pipeline_stages(["train.imgsz=1280"])

    assert stages["predict"]["imgsz"] == 1280
    inference = stages["compare"]["inference"]
    assert isinstance(inference, InferenceConfig)
    assert inference.imgsz == 1280


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
def test_the_comparison_still_resolves_when_the_report_baseline_is_swapped(source: str) -> None:
    """The two share a task identity but not a source: "local" means a folder of workbooks
    to the report and a checkpoint to the comparison."""
    stages = _pipeline_stages([f"report/baseline={source}"])

    baseline_model = stages["compare"]["baseline_model"]
    assert isinstance(baseline_model, ModelRef)
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


def test_auto_gpu_defaults_are_valid() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train")

    auto_gpu = instantiate(config.auto_gpu)
    assert auto_gpu.enabled is True
    assert auto_gpu.batch_per_gpu >= 1
    assert auto_gpu.reference_vram_gb > 0
