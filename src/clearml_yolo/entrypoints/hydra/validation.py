"""Validate public command arguments before waiting for GPUs or invoking workflows."""

import inspect
from collections.abc import Callable
from typing import Any

from omegaconf import DictConfig, OmegaConf, open_dict

from clearml_yolo.adapters.integrations.native_runtime import validate_owner_environment
from clearml_yolo.adapters.yolo.config import native_defaults, prediction_defaults, stage_settings
from clearml_yolo.core.execution import ExecutionControl
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import ModelConfig


def materialize_model_config(config: DictConfig) -> ModelConfig | None:
    """Expose native defaults before admission and device replacement read their paths."""
    if "model" not in config:
        return None
    model = ModelConfig.model_validate(OmegaConf.to_container(config.model, resolve=True))
    if model.backend != "ultralytics":
        with open_dict(config):
            config.model = model.model_dump(mode="json")
    return model


def _validate_export(config: DictConfig, model: ModelConfig | None) -> None:
    if "export" not in config:
        return
    if model is not None and model.backend != "fasterrcnn":
        raise ValueError("cy-export supports only Faster R-CNN presets")
    ExportSettings.model_validate(OmegaConf.to_container(config.export, resolve=True))


def _validate_inactive_model_settings(model: ModelConfig) -> None:
    values = model.model_dump(mode="json")
    defaults = ModelConfig().model_dump(mode="json")
    for group, owner in (("train", "ultralytics"), ("predict", "ultralytics_predict")):
        changed = sorted(
            key for key, value in values[group].items() if value != defaults[group][key]
        )
        if changed:
            raise ValueError(
                f"Changed model.{group} settings {changed} are inactive for ultralytics; "
                f"use {owner} instead"
            )


def _validate_inactive_groups(config: DictConfig, model: ModelConfig | None) -> None:
    if model is None:
        return
    if model.backend == "ultralytics":
        _validate_inactive_model_settings(model)
        return
    defaults = OmegaConf.create(
        {
            "ultralytics": stage_settings(native_defaults(), "train"),
            "ultralytics_predict": prediction_defaults(),
        }
    )
    for group, owner in (("ultralytics", "train"), ("ultralytics_predict", "predict")):
        if group not in config:
            continue
        changed = sorted(
            key for key, value in config[group].items() if value != defaults[group].get(key)
        )
        if changed:
            raise ValueError(
                f"Changed {group} settings {changed} are inactive for "
                f"{model.backend}/{model.preset}; use model.{owner} instead"
            )


def validate_wrapper_keys(config: DictConfig, function: Callable[..., Any]) -> None:
    """Validate the command schema, including keys introduced with Hydra's + syntax."""
    validate_owner_environment()
    accepted = set(inspect.signature(function).parameters) - {"deps"}
    if "ultralytics" in config or "ultralytics_predict" in config or "export" in config:
        accepted.update({"queue", "autogpu", "model"})
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unsupported wrapper settings: {sorted(unknown)}")
    model = materialize_model_config(config)
    _validate_export(config, model)
    _validate_inactive_groups(config, model)
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
