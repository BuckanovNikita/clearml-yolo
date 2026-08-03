"""Pipeline stage configs must resolve to plain Python before reaching third parties."""

from __future__ import annotations

import pickle

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf

import clearml_yolo.configs  # noqa: F401  registers every config
from clearml_yolo.tasks.pipeline import _as_dict

STAGES = ["train", "predict", "metrics", "report"]


@pytest.fixture(scope="module", autouse=True)
def hydra_store() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


def _stage_config(stage: str) -> dict:  # type: ignore[type-arg]
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name="pipeline")
    return _as_dict(config[stage])


@pytest.mark.parametrize("stage", STAGES)
def test_no_omegaconf_containers_survive(stage: str) -> None:
    for key, value in _stage_config(stage).items():
        assert not OmegaConf.is_config(value), f"{stage}.{key} is still {type(value)}"


def test_train_kwargs_are_picklable() -> None:
    """Ultralytics pickles trainer.args when saving a checkpoint, so anything passed
    into train_kwargs must survive pickling — a DictConfig does not."""
    train_kwargs = _stage_config("train")["train_kwargs"]

    assert isinstance(train_kwargs, dict)
    pickle.loads(pickle.dumps(train_kwargs))


@pytest.mark.parametrize("stage", STAGES)
def test_whole_stage_config_is_picklable(stage: str) -> None:
    config = _stage_config(stage)
    # The pydantic sub-configs are ours and pickle fine; this guards the rest.
    plain = {k: v for k, v in config.items() if not hasattr(v, "model_dump")}

    pickle.loads(pickle.dumps(plain))
