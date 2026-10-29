"""Assemble the reference from public declarations and installed effective defaults."""

import json
from dataclasses import fields
from importlib.metadata import distribution, version
from typing import Any

from hydra import compose, initialize_config_module
from hydra_zen import store
from omegaconf import OmegaConf
from pydantic import BaseModel, JsonValue, TypeAdapter

from clearml_yolo.adapters.documentation.files import asset_text
from clearml_yolo.application.contracts import ClearMLConfig, ClearMLDatasetRef, ModelRef
from clearml_yolo.core.documentation import (
    Catalog,
    ConfigurationDoc,
    FieldDetails,
    FieldDoc,
    TutorialDoc,
)
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import (
    DeimAugmentationOverrides,
    ModelConfig,
    PredictSettings,
    Preprocessing,
    RFDETRAugmentationOverrides,
    TrainSettings,
)
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.core.transforms import TransformConfig, TransformSnapshot
from clearml_yolo.entrypoints.documentation.controls import hydra_controls
from clearml_yolo.entrypoints.documentation.native import native_fields
from clearml_yolo.entrypoints.documentation.values import flatten, selected_values
from clearml_yolo.entrypoints.hydra.config_tree import COMMAND_OF_CONFIG
from clearml_yolo.entrypoints.hydra.configs import NATIVE_COMMANDS, command_schema
from clearml_yolo.entrypoints.hydra.declarations import (
    COMMAND_DECLARATIONS,
    NESTED_DECLARATIONS,
)
from clearml_yolo.entrypoints.hydra.transforms import TRAINING_COMMANDS, model_selections
from clearml_yolo.entrypoints.options import OPTION_DECLARATIONS, parser_for

PUBLIC_MODELS: dict[str, type[BaseModel]] = {
    "ground_truth": ClearMLDatasetRef,
    "clearml": ClearMLConfig,
    "model": ModelConfig,
    "model.train": TrainSettings,
    "model.predict": PredictSettings,
    "evaluation": EvaluationConfig,
    "metrics.evaluation": EvaluationConfig,
    "export": ExportSettings,
    "fiftyone": FiftyOneConfig,
    "transforms": TransformConfig,
    "transforms.snapshot": TransformSnapshot,
}
for _prefix in ("baseline_model", "candidate_model", "compare.baseline_model"):
    PUBLIC_MODELS[_prefix] = ModelRef
    PUBLIC_MODELS[f"{_prefix}.preprocessing"] = Preprocessing


def _model_fields(prefix: str, model: type[BaseModel], commands: list[str]) -> list[FieldDoc]:
    properties: dict[str, Any] = model.model_json_schema()["properties"]
    result = []
    for name, field in model.model_fields.items():
        schema = dict(properties[name])
        description = field.description
        if not description:
            raise ValueError(f"Missing field description: {model.__name__}.{name}")
        extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
        result.append(
            FieldDoc(
                id=f"{prefix}.{name}",
                path=f"{prefix}.{name}",
                description=description,
                shapes=str(
                    extra.get(
                        "shapes",
                        schema.get("type", schema.get("anyOf", schema.get("$ref", "mapping"))),
                    )
                ),
                constraints=json.dumps(
                    {
                        key: value
                        for key, value in schema.items()
                        if key
                        not in {
                            "description",
                            "examples",
                            "title",
                            "default",
                            "source",
                            "shapes",
                            "applicability",
                            "classification",
                        }
                    },
                    ensure_ascii=False,
                ),
                applicability=str(extra.get("applicability", model.__name__)),
                examples=TypeAdapter(list[JsonValue]).validate_python(field.examples or []),
                source=f"{model.__module__}.{model.__name__}.{name}",
                commands=commands,
                required=field.is_required(),
                generated=prefix.startswith("transforms.snapshot") or name == "snapshot",
            )
        )
    return result


def _declaration_fields() -> dict[str, FieldDoc]:
    result: dict[str, FieldDoc] = {}
    declarations = [("", name, declaration) for name, declaration in COMMAND_DECLARATIONS.items()]
    declarations.extend(
        (prefix, "compare" if prefix == "inference" else "pipeline", declaration)
        for prefix, declaration in NESTED_DECLARATIONS.items()
    )
    for prefix, command, declaration in declarations:
        for item in fields(declaration):
            path = f"{prefix}.{item.name}" if prefix else item.name
            metadata = item.metadata
            if not all(
                metadata.get(key)
                for key in ("description", "shapes", "constraints", "applicability", "examples")
            ):
                raise ValueError(f"Incomplete command documentation: {command}.{path}")
            detail = FieldDetails(
                description=metadata["description"],
                shapes=metadata["shapes"],
                constraints=metadata["constraints"],
                applicability=metadata["applicability"],
                examples=list(metadata["examples"]),
                source=f"{declaration.__module__}.{declaration.__name__}.{item.name}",
                required=not prefix and OmegaConf.is_missing(command_schema(command), item.name),
            )
            if path in result:
                result[path].commands.append(command)
                result[path].variants[command] = detail
            else:
                result[path] = FieldDoc(
                    id=path,
                    path=path,
                    commands=[command],
                    variants={command: detail},
                    **detail.model_dump(),
                )
    return result


def _option_fields() -> list[FieldDoc]:
    result = []
    for command, options in OPTION_DECLARATIONS.items():
        parser = parser_for(command)
        for option in options:
            key = option.flags[-1]
            kwargs = option.kwargs
            shape = kwargs.get("type", str)
            shapes = getattr(shape, "__name__", "string")
            if kwargs.get("action") in {"store_true", "store_false"}:
                shapes = "flag (boolean)"
            elif kwargs.get("action") == "help":
                shapes = "flag"
            destination = kwargs.get("dest", key.lstrip("-").replace("-", "_"))
            result.append(
                FieldDoc(
                    id=f"{command}.{key}",
                    path=f"{command}.{key}",
                    description=option.description,
                    shapes=shapes,
                    constraints=(
                        f"flags={','.join(option.flags)}; choices={kwargs.get('choices', '—')}; "
                        f"default={parser.get_default(destination)}; "
                        f"action={kwargs.get('action', 'store')}; nargs={kwargs.get('nargs', None)}"
                    ),
                    applicability=command,
                    examples=list(option.examples),
                    source="clearml_yolo.entrypoints.options.OPTION_DECLARATIONS",
                    commands=[command],
                    required=bool(
                        kwargs.get(
                            "required", not key.startswith("-") and kwargs.get("nargs") != "?"
                        )
                    ),
                )
            )
    return result


def _configurations() -> list[ConfigurationDoc]:
    store.add_to_hydra_store(overwrite_ok=True)
    result = []
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        for command in COMMAND_OF_CONFIG:
            models = model_selections() if command in NATIVE_COMMANDS else [""]
            if command == "export":
                models = [model for model in models if model.startswith("fasterrcnn/")]
            profiles = ["default", "albumentations"] if command in TRAINING_COMMANDS else [""]
            for model in models:
                for profile in profiles:
                    overrides = ([f"model={model}"] if model else []) + (
                        [f"transforms={profile}"] if profile else []
                    )
                    config = compose(config_name=command, overrides=overrides)
                    values = flatten(
                        TypeAdapter(JsonValue).validate_python(
                            OmegaConf.to_container(config, resolve=False)
                        )
                    )
                    result.append(
                        ConfigurationDoc(
                            command=command,
                            model=model,
                            profile=profile,
                            yaml=OmegaConf.to_yaml(config, resolve=False),
                            values=selected_values(values),
                            expressions={
                                key: value
                                for key, value in values.items()
                                if isinstance(value, str) and "${" in value
                            },
                        )
                    )
    return result


def build_catalog() -> Catalog:
    declarations = _declaration_fields()
    for prefix, model in PUBLIC_MODELS.items():
        commands = [
            command
            for command in COMMAND_OF_CONFIG
            if prefix.split(".")[0] in command_schema(command)
        ]
        declarations.update((item.path, item) for item in _model_fields(prefix, model, commands))
    for model in (DeimAugmentationOverrides, RFDETRAugmentationOverrides):
        declarations.update(
            (item.path, item)
            for item in _model_fields("model.train.augmentation", model, list(TRAINING_COMMANDS))
        )
    for item in (
        native_fields(sorted(NATIVE_COMMANDS))
        + _option_fields()
        + hydra_controls(list(COMMAND_OF_CONFIG))
    ):
        declarations[item.path] = item
    configurations = _configurations()
    for config in configurations:
        for path in config.values:
            if path.endswith("._target_") and path not in declarations:
                declarations[path] = FieldDoc(
                    id=path,
                    path=path,
                    description=(
                        "Сгенерированный путь конфигурационного класса. Сохраняется для "
                        "совместимости replay; не заменяет стадии конвейера."
                    ),
                    shapes="string",
                    constraints="Используйте штатное значение.",
                    applicability="Hydra compatibility",
                    examples=[config.values[path]],
                    source=str(config.values[path]),
                    commands=[],
                    generated=True,
                )
    tutorials = TypeAdapter(list[TutorialDoc]).validate_json(asset_text("tutorials/inventory.json"))
    catalog = Catalog(
        version=version("clearml-yolo"),
        commands=COMMAND_OF_CONFIG | {name: name for name in OPTION_DECLARATIONS},
        models=model_selections(),
        profiles=["default", "albumentations"],
        fields=sorted(declarations.values(), key=lambda item: item.path),
        configurations=configurations,
        tutorials=tutorials,
    )
    check_coverage(catalog)
    return catalog


def check_coverage(catalog: Catalog) -> None:
    installed = {
        entry.name
        for entry in distribution("clearml-yolo").entry_points
        if entry.group == "console_scripts"
    }
    if installed != set(catalog.commands.values()):
        raise ValueError(
            f"Command documentation coverage mismatch: "
            f"{sorted(installed ^ set(catalog.commands.values()))}"
        )
    registered = {entry["name"] for entry in store if entry["group"] == "_cy_schemas"}
    if registered != set(COMMAND_DECLARATIONS):
        raise ValueError(
            f"Undocumented registered commands: {registered ^ set(COMMAND_DECLARATIONS)}"
        )
    documented = {item.path: item for item in catalog.fields}
    for config in catalog.configurations:
        for path in config.values:
            if path not in documented:
                raise ValueError(
                    f"Undocumented composed field: "
                    f"{config.command}/{config.model}/{config.profile}: {path}"
                )
    for item in catalog.fields:
        if not all(
            (
                item.description,
                item.shapes,
                item.constraints,
                item.applicability,
                item.source,
                item.examples,
            )
        ):
            raise ValueError(f"Incomplete field reference: {item.path}")
