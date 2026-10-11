"""Validate public command arguments before waiting for GPUs or invoking workflows."""

import inspect
from collections.abc import Callable
from typing import Any

from omegaconf import DictConfig

from clearml_yolo.adapters.integrations.native_runtime import validate_owner_environment
from clearml_yolo.adapters.yolo.config import stage_settings
from clearml_yolo.core.execution import ExecutionControl


def validate_wrapper_keys(config: DictConfig, function: Callable[..., Any]) -> None:
    """Validate the command schema, including keys introduced with Hydra's + syntax."""
    validate_owner_environment()
    accepted = set(inspect.signature(function).parameters) - {"deps"}
    if "ultralytics" in config or "ultralytics_predict" in config:
        accepted.update({"queue", "autogpu"})
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unsupported wrapper settings: {sorted(unknown)}")
    for control in ("queue", "autogpu"):
        if control in config:
            values = dict(config[control])
            values.pop("_target_", None)
            ExecutionControl.model_validate(values)
    for group in ("ultralytics", "ultralytics_predict"):
        if group in config:
            stage_settings(dict(config[group]), "train" if group == "ultralytics" else "predict")
    if "inference" in config:
        unknown = set(config.inference) - {"reuse_existing", "image_name"}
        if unknown:
            raise ValueError(f"Unsupported inference settings: {sorted(unknown)}")
