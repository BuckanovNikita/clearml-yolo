"""Compose real native configuration for tests that call task functions directly."""

from typing import Any

from omegaconf import OmegaConf

from clearml_yolo.native_config import native_defaults, prediction_defaults, stage_settings


def training_settings(**overrides: Any) -> dict[str, Any]:
    return stage_settings(native_defaults(), "train") | overrides


def prediction_config(**overrides: Any) -> dict[str, Any]:
    config = OmegaConf.create(
        {"ultralytics": native_defaults(), "ultralytics_predict": prediction_defaults()}
    )
    values = OmegaConf.to_container(config.ultralytics_predict, resolve=True)
    assert isinstance(values, dict)
    return {str(key): value for key, value in values.items()} | overrides
