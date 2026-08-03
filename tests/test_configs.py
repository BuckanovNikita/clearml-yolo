"""Config composition: every app resolves, and ClearML naming reaches every stage."""

from __future__ import annotations

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import instantiate, store

import clearml_yolo.configs  # noqa: F401  registers every config

STAGES = ["train", "predict", "metrics", "report"]


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


def test_augmentations_instantiate_to_none_by_default() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train")

    assert instantiate(config.augmentations) is None


def test_auto_gpu_defaults_are_valid() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="train")

    auto_gpu = instantiate(config.auto_gpu)
    assert auto_gpu.enabled is True
    assert auto_gpu.batch_per_gpu >= 1
    assert auto_gpu.reference_vram_gb > 0
