"""Removed scheduling controls require migration for every command schema."""

import pytest
from omegaconf import OmegaConf

from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys


@pytest.mark.parametrize("setting", ["queue", "autogpu", "auto_gpu"])
@pytest.mark.parametrize("enabled", [True, False])
def test_direct_commands_reject_legacy_controls(setting: str, enabled: bool) -> None:
    config = OmegaConf.create({"ultralytics": {"device": "cpu"}, setting: {"enabled": enabled}})
    with pytest.raises(ValueError, match="cy-queue submit"):
        validate_wrapper_keys(config, lambda ultralytics: None)


@pytest.mark.parametrize("setting", ["queue", "autogpu", "auto_gpu"])
def test_non_model_commands_also_reject_legacy_controls(setting: str) -> None:
    config = OmegaConf.create({"predictions": "outside.csv", setting: {"enabled": False}})
    with pytest.raises(ValueError, match="saved YAML"):
        validate_wrapper_keys(config, lambda predictions: None)
