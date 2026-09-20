"""Every retained CLI composes while removed fields fail explicitly."""

from __future__ import annotations

import pytest
from hydra import compose, initialize_config_module
from hydra.errors import ConfigCompositionException
from hydra_zen import store

import clearml_yolo.configs  # noqa: F401

COMMANDS = ["train", "predict", "val", "metrics", "report", "compare", "ground_truth", "pipeline"]


@pytest.fixture(autouse=True)
def registered() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


@pytest.mark.parametrize("command", COMMANDS)
def test_command_composes(command: str) -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=command)
    assert "clearml" in config
    assert "enabled" not in config.clearml


@pytest.mark.parametrize("override", ["auto_gpu.force=true", "clearml.enabled=false"])
def test_removed_overrides_fail(override: str) -> None:
    with (
        initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"),
        pytest.raises(ConfigCompositionException),
    ):
        compose(config_name="pipeline", overrides=[override])


def test_native_mapping_starts_sparse_and_accepts_explicit_values() -> None:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="train", overrides=["+ultralytics.epochs=100", "+ultralytics.amp=false"]
        )
    assert dict(config.ultralytics) == {"epochs": 100, "amp": False}
