"""Validate public command arguments before scheduling or invoking workflows."""

import inspect
from collections.abc import Callable
from typing import Any

from omegaconf import DictConfig

from clearml_yolo.adapters.integrations.native_runtime import validate_owner_environment
from clearml_yolo.adapters.yolo.config import stage_settings


def validate_wrapper_keys(config: DictConfig, function: Callable[..., Any]) -> None:
    """Validate the command schema, including keys introduced with Hydra's + syntax."""
    validate_owner_environment()
    accepted = set(inspect.signature(function).parameters) - {"deps"}
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unsupported wrapper settings: {sorted(unknown)}")
    for group in ("ultralytics", "ultralytics_predict"):
        if group in config:
            stage_settings(dict(config[group]), "train" if group == "ultralytics" else "predict")
    if "inference" in config:
        unknown = set(config.inference) - {"reuse_existing", "image_name"}
        if unknown:
            raise ValueError(f"Unsupported inference settings: {sorted(unknown)}")
