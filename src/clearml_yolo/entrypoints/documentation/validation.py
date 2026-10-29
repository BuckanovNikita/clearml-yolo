"""Effect-free request checks for previews; application execution remains authoritative."""

import inspect
from collections.abc import Callable
from dataclasses import fields
from functools import cache
from typing import Any, get_args

from omegaconf import OmegaConf
from pydantic import BaseModel, JsonValue, TypeAdapter, ValidationError

from clearml_yolo.adapters.yolo.config import execution_settings
from clearml_yolo.application.contracts import ClearMLConfig, ClearMLDatasetRef, ModelRef
from clearml_yolo.application.ground_truth import normalize_ground_truth
from clearml_yolo.application.use_cases.compare import compare
from clearml_yolo.application.use_cases.export import export_model
from clearml_yolo.application.use_cases.ground_truth import ground_truth
from clearml_yolo.application.use_cases.metrics import compute_metrics
from clearml_yolo.application.use_cases.pipeline import run_pipeline
from clearml_yolo.application.use_cases.predict import predict
from clearml_yolo.application.use_cases.report import report
from clearml_yolo.application.use_cases.train import train
from clearml_yolo.application.use_cases.val import validate
from clearml_yolo.core.comparison.significance import validate_q
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.evaluation.policy import validate_evaluation_image_name
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import ModelConfig
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.core.transforms import TransformConfig
from clearml_yolo.entrypoints.documentation.values import flatten, selected_values, unresolved
from clearml_yolo.entrypoints.hydra.configs import command_schema
from clearml_yolo.entrypoints.hydra.declarations import NESTED_DECLARATIONS

_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "pipeline": run_pipeline,
    "train": train,
    "predict": predict,
    "val": validate,
    "metrics": compute_metrics,
    "report": report,
    "compare": compare,
    "ground_truth": ground_truth,
    "export": export_model,
}
_SCHEMAS: dict[str, type[BaseModel]] = {
    "model": ModelConfig,
    "clearml": ClearMLConfig,
    "fiftyone": FiftyOneConfig,
    "evaluation": EvaluationConfig,
    "export": ExportSettings,
    "transforms": TransformConfig,
    "baseline_model": ModelRef,
    "candidate_model": ModelRef,
}
_STRUCTURED = set(_SCHEMAS) | {"ultralytics", "ultralytics_predict", *NESTED_DECLARATIONS}


def _materialized(value: JsonValue, selected: dict[str, JsonValue], prefix: str = "") -> JsonValue:
    if isinstance(value, dict):
        return {
            key: _materialized(item, selected, f"{prefix}.{key}" if prefix else key)
            for key, item in value.items()
            if key != "_target_"
        }
    return selected.get(prefix, value)


@cache
def _parameters(command: str) -> dict[str, inspect.Parameter]:
    # Inspect the public function types; never invoke a workflow or construct dependencies.
    return dict(inspect.signature(_FUNCTIONS[command]).parameters)


def _scalar_errors(
    values: dict[str, JsonValue], command: str, defaults: dict[str, JsonValue]
) -> list[str]:
    errors = []
    for name, parameter in _parameters(command).items():
        if name not in values or name in _STRUCTURED or name == "ground_truth":
            continue
        value = values[name]
        if unresolved(value) or (value is None and (defaults.get(name) is None or name == "seed")):
            continue
        try:
            TypeAdapter(parameter.annotation).validate_python(value, strict=True)
        except ValidationError as error:
            errors.append(f"{name}: {error}")
    return errors


def _nested_model(annotation: Any) -> type[BaseModel] | None:
    candidates = [
        item
        for item in (annotation, *get_args(annotation))
        if isinstance(item, type) and issubclass(item, BaseModel)
    ]
    return candidates[0] if len(candidates) == 1 else None


def _partial_model_errors(value: dict[str, JsonValue], schema: type[BaseModel]) -> list[str]:
    """Check independent known leaves when a resolver defers a model's cross-field checks."""
    errors = []
    if schema.model_config.get("extra") == "forbid":
        unknown = set(value) - set(schema.model_fields)
        if unknown:
            errors.append(f"Unsupported {schema.__name__} fields: {sorted(unknown)}")
    for name, field in schema.model_fields.items():
        if name not in value:
            continue
        item = value[name]
        nested = _nested_model(field.annotation)
        if isinstance(item, dict) and nested is not None:
            errors.extend(f"{name}.{error}" for error in _partial_model_errors(item, nested))
        elif not unresolved(item):
            try:
                TypeAdapter(field.rebuild_annotation()).validate_python(item)
            except ValidationError as error:
                errors.append(f"{name}: {error}")
    return errors


def _model_errors(value: JsonValue, schema: type[BaseModel]) -> list[str]:
    if isinstance(value, dict) and unresolved(value):
        return _partial_model_errors(value, schema)
    if unresolved(value):
        return []
    try:
        schema.model_validate(value)
    except ValidationError as error:
        return [str(error)]
    return []


def _validate_groups(value: dict[str, JsonValue]) -> list[str]:
    errors: list[str] = []
    for key, schema in _SCHEMAS.items():
        if key in value and (value[key] is not None or key not in {"fiftyone", "evaluation"}):
            errors.extend(f"{key}: {error}" for error in _model_errors(value[key], schema))
    return errors


def _target_errors(values: JsonValue, defaults: JsonValue) -> list[str]:
    expected = flatten(defaults)
    errors: list[str] = []
    for path, value in flatten(values).items():
        if path.split(".")[-1] != "_target_" or unresolved(value):
            continue
        if path not in expected or value != expected[path]:
            errors.append(
                f"Unsupported configuration target {path}; preserve its public definition"
            )
    return errors


def _comparison_errors(value: dict[str, JsonValue]) -> list[str]:
    errors = []
    q = value.get("q", "???")
    if not unresolved(q):
        try:
            validate_q(TypeAdapter(float).validate_python(q, strict=True))
        except (ValueError, TypeError) as error:
            errors.append(f"q: {error}")
    iterations = value.get("bootstrap_iterations", "???")
    if not unresolved(iterations) and (type(iterations) is not int or iterations <= 0):
        errors.append("bootstrap_iterations must be a positive integer")
    seed = value.get("seed", "???")
    if not unresolved(seed) and seed is not None and (type(seed) is not int or seed < 0):
        errors.append("seed must be a nonnegative integer or null")
    return errors


def _inference_errors(value: JsonValue) -> list[str]:
    if not isinstance(value, dict):
        return []
    errors = []
    image_name = value.get("image_name", "name")
    if not unresolved(image_name):
        try:
            validate_evaluation_image_name(
                TypeAdapter(str).validate_python(image_name, strict=True)
            )
        except (ValueError, TypeError) as error:
            errors.append(f"inference.image_name: {error}")
    reuse = value.get("reuse_existing", True)
    if not unresolved(reuse) and not isinstance(reuse, bool):
        errors.append("inference.reuse_existing must be a boolean")
    return errors


def _wrapper_errors(value: dict[str, JsonValue], command: str) -> list[str]:
    errors = []
    unknown = set(value) - set(command_schema(command))
    if unknown:
        errors.append(f"Unsupported wrapper settings: {sorted(unknown)}")
    for name, declaration in NESTED_DECLARATIONS.items():
        nested = value.get(name)
        if isinstance(nested, dict):
            unknown = set(nested) - {item.name for item in fields(declaration)}
            if unknown:
                errors.append(f"Unsupported {name} settings: {sorted(unknown)}")
        elif name in value and not unresolved(nested):
            errors.append(f"{name} must be a mapping")
    errors.extend(_inference_errors(value.get("inference")))
    metrics = value.get("metrics")
    calibration = (
        metrics.get("calibration_split", "val")
        if isinstance(metrics, dict)
        else value.get("calibration_split", "val")
    )
    if not unresolved(calibration) and calibration != "val":
        errors.append("calibration_split must be val; test thresholds are frozen")
    return errors


def _changed_known(value: JsonValue, defaults: JsonValue) -> list[str]:
    baseline = flatten(defaults)
    return [
        path
        for path, item in flatten(value).items()
        if not unresolved(item) and (path not in baseline or item != baseline[path])
    ]


def _inactive_errors(value: dict[str, JsonValue], defaults: dict[str, JsonValue]) -> list[str]:
    model = value.get("model")
    if not isinstance(model, dict) or unresolved(model.get("backend")):
        return []
    backend = model.get("backend", "ultralytics")
    errors = []
    if backend == "ultralytics":
        baseline: JsonValue = TypeAdapter(JsonValue).validate_python(
            ModelConfig().model_dump(mode="json")
        )
        if not isinstance(baseline, dict):
            raise TypeError("Model defaults must be a mapping")
        for group, owner in (("train", "ultralytics"), ("predict", "ultralytics_predict")):
            if group in model and (changed := _changed_known(model[group], baseline[group])):
                errors.append(f"Changed model.{group} fields {changed} are inactive; use {owner}")
    else:
        for group, owner in (("ultralytics", "train"), ("ultralytics_predict", "predict")):
            if group in value and (changed := _changed_known(value[group], defaults.get(group))):
                errors.append(f"Changed {group} fields {changed} are inactive; use model.{owner}")
    if "export" in value and backend != "fasterrcnn":
        errors.append("cy-export supports only Faster R-CNN presets")
    return errors


def _native_errors(value: dict[str, JsonValue], defaults: dict[str, JsonValue]) -> list[str]:
    errors = []
    for group, stage in (("ultralytics", "train"), ("ultralytics_predict", "predict")):
        settings = value.get(group)
        if not isinstance(settings, dict):
            continue
        baseline = defaults.get(group)
        # Replace only deferred leaves with their valid built-in values; independent
        # known inputs still pass through the authoritative native checks.
        known = dict(settings)
        if isinstance(baseline, dict):
            for key, item in settings.items():
                if unresolved(item) and key in baseline:
                    known[key] = baseline[key]
        if unresolved(known):
            continue
        try:
            execution_settings(known, "train" if stage == "train" else "predict")
        except (ValueError, TypeError) as error:
            errors.append(str(error))
    return errors


def _ground_truth_errors(value: dict[str, JsonValue], command: str) -> list[str]:
    selected = value.get("ground_truth", "???")
    if unresolved(selected) or (selected is None and command == "export"):
        return []
    try:
        if isinstance(selected, dict):
            ClearMLDatasetRef.model_validate(selected)
        else:
            normalize_ground_truth(TypeAdapter(str).validate_python(selected, strict=True))
    except (ValueError, TypeError) as error:
        return [f"ground_truth: {error}"]
    return []


def _specific_errors(value: dict[str, JsonValue], command: str) -> list[str]:
    errors = _comparison_errors(value)
    if command == "ground_truth":
        fraction = value.get("test_fraction", "???")
        if not unresolved(fraction):
            try:
                number = TypeAdapter(float).validate_python(fraction, strict=True)
                if not 0 <= number < 1:
                    errors.append("test_fraction must be within [0, 1)")
            except ValidationError as error:
                errors.append(f"test_fraction: {error}")
    if (
        command == "pipeline"
        and value.get("weights") is not None
        and not unresolved(value.get("weights"))
        and value.get("skip_train") is False
    ):
        errors.append("weights is only valid with skip_train=true")
    return errors


def schema_errors(value: JsonValue, command: str) -> list[str]:
    selected = selected_values(flatten(value))
    materialized = _materialized(value, selected)
    if not isinstance(materialized, dict):
        return ["Command configuration must be a mapping"]
    raw_defaults: JsonValue = TypeAdapter(JsonValue).validate_python(
        OmegaConf.to_container(command_schema(command), resolve=False)
    )
    defaults = _materialized(raw_defaults, selected_values(flatten(raw_defaults)))
    if not isinstance(defaults, dict):
        raise TypeError("Command defaults must be a mapping")
    errors = _target_errors(value, raw_defaults)
    errors.extend(_validate_groups(materialized))
    errors.extend(_wrapper_errors(materialized, command))
    errors.extend(_scalar_errors(materialized, command, defaults))
    errors.extend(_ground_truth_errors(materialized, command))
    errors.extend(_specific_errors(materialized, command))
    for name in ("metrics", "compare", "report"):
        nested = materialized.get(name)
        if isinstance(nested, dict):
            errors.extend(f"{name}.{message}" for message in _validate_groups(nested))
            errors.extend(f"{name}.{message}" for message in _scalar_errors(nested, name, {}))
            errors.extend(f"{name}.{message}" for message in _specific_errors(nested, name))
    errors.extend(_inactive_errors(materialized, defaults))
    errors.extend(_native_errors(materialized, defaults))
    return errors
