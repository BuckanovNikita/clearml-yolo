"""Pure composition preview; never launch or instantiate submitted configuration."""

import itertools
import json
import re
import shlex
from pathlib import PurePosixPath
from typing import Any

from hydra import compose, initialize_config_dir, initialize_config_module
from hydra.core.override_parser.overrides_parser import OverridesParser
from hydra.errors import HydraException
from hydra_zen import store
from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException
from pydantic import JsonValue, TypeAdapter

from clearml_yolo.adapters.documentation.files import MAX_REQUEST_BYTES, preview_directory
from clearml_yolo.core.documentation import PreviewJob, PreviewRequest, PreviewResult
from clearml_yolo.entrypoints.documentation.validation import schema_errors
from clearml_yolo.entrypoints.documentation.values import flatten, selected_values, unresolved
from clearml_yolo.entrypoints.hydra.config_tree import COMMAND_OF_CONFIG

MAX_JOBS = 100
DEFERRED = [
    "Файлы датасета, веса, JSON аугментаций и внешние ссылки не открывались.",
    "ClearML, права доступа, доступность устройств и память проверяются при запуске.",
    "Выражения окружения и пользовательские resolver-функции не выполнялись.",
    "Предпросмотр не заменяет полную проверку команды перед обучением.",
]


def _guard_mapping(value: Any, *, path: str = "") -> None:
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        qualified = f"{path}.{key}" if path else str(key)
        # Hydra reads its own settings while composing, including interpolated
        # aliases to searchpath. Keep all submitted runtime controls out of compose.
        if qualified == "hydra" or qualified.startswith("hydra."):
            raise ValueError(
                f"Preview forbids {qualified} runtime settings, including searchpath; "
                "apply Hydra runtime controls only in the terminal"
            )
        if key == "defaults":
            text = json.dumps(item)
            remaining = re.sub(r"\$\{[\w./-]+\}", "", text)
            if "${" in remaining or re.search(r"\bhydra\b|searchpath|://|\.\.", text):
                raise ValueError("Preview forbids external or resolver-based defaults/plugins")
        _guard_mapping(item, path=qualified)


def _guard(request: PreviewRequest) -> None:
    if request.command not in COMMAND_OF_CONFIG:
        raise ValueError(f"Unknown preview command: {request.command}")
    if len(request.model_dump_json().encode()) > MAX_REQUEST_BYTES:
        raise ValueError("Preview request exceeds 1 MiB")
    for text in request.documents.values():
        packages = re.findall(r"^\s*#\s*@package\s+(\S+)", text, re.MULTILINE)
        if any({"hydra", "_cy_schemas"} & set(package.split(".")) for package in packages):
            raise ValueError("Preview forbids replacing Hydra packages")
        parsed = OmegaConf.create(text)
        if not isinstance(parsed, DictConfig):
            raise TypeError("YAML documents must be mappings")
        _guard_mapping(OmegaConf.to_container(parsed, resolve=False))
    groups = {
        str(parent)
        for name in request.documents
        for parent in PurePosixPath(name).parents
        if str(parent) != "."
    } | {"model", "transforms", "transform_overrides", "ultralytics", "ultralytics_predict"}
    _guard_overrides(request.overrides, groups)


def _guard_overrides(overrides: list[str], groups: set[str]) -> None:
    for item in overrides:
        if re.search(r"\b(?:shuffle|sort|glob)\s*\(", item):
            raise ValueError("Preview supports bounded literal choice/range sweeps only")
        key = item.split("=", 1)[0].lstrip("+~")
        group, separator, package = key.partition("@")
        group = group.lstrip("/")
        if {"hydra", "_cy_schemas"} & set(package.split(".")):
            raise ValueError("Preview forbids Hydra/schema package overrides")
        if ".." in key or "\\" in key:
            raise ValueError("Preview forbids external group paths")
        if group == "hydra" or group.startswith(("hydra.", "hydra/")):
            raise ValueError(f"Preview forbids {key}; apply Hydra runtime controls in the terminal")
        if (
            group.startswith("_cy_schemas")
            or key == "defaults"
            or ("_target_" in key and key.startswith("hydra"))
        ):
            raise ValueError(f"Preview forbids {key}")
        if separator or group in groups or group.split("/")[0] in groups:
            _guard_selection(item.partition("=")[2])


def _guard_selection(value: str) -> None:
    # Hydra's file source joins group selections without enforcing containment.
    # Check every textual choice before sweep parsing/materialization as well.
    if "${" in value:
        raise ValueError("Preview group selectors must be literal")
    if any(token in value for token in ("..", "\\", "://")) or re.search(
        r"""(?:^|[,\[\s"'])/""", value
    ):
        raise ValueError("Preview forbids external group selection paths")


def _expanded(request: PreviewRequest) -> list[list[str]]:
    parser = OverridesParser.create()
    parsed = parser.parse_overrides(request.overrides)
    if not any(item.is_sweep_override() for item in parsed):
        return [request.overrides]
    dimensions: dict[str, list[str]] = {}
    total = 1
    for item in parsed:
        if item.is_sweep_override():
            if not request.sweep:
                raise ValueError("Enable sweep to preview multiple jobs")
            # Range/choice iterators are bounded before Cartesian materialization.
            values: list[str] = list(itertools.islice(item.sweep_string_iterator(), MAX_JOBS + 1))
            if len(values) > MAX_JOBS:
                raise ValueError("Preview sweep exceeds 100 jobs")
            dimension = [f"{item.get_key_element()}={value}" for value in values]
        else:
            dimension = [item.input_line or ""]
        dimensions[item.get_key_element()] = dimension
    for dimension in dimensions.values():
        total *= len(dimension)
        if total > MAX_JOBS:
            raise ValueError("Preview sweep exceeds 100 jobs")
    if not total:
        raise ValueError("Preview sweep has no jobs")
    return [list(values) for values in itertools.product(*dimensions.values())]


def _job(configuration: DictConfig, command: str) -> PreviewJob:
    value: JsonValue = TypeAdapter(JsonValue).validate_python(
        OmegaConf.to_container(configuration, resolve=False)
    )
    flattened = flatten(value)
    selected = selected_values(flattened)
    return PreviewJob(
        yaml=OmegaConf.to_yaml(configuration, resolve=False),
        values=selected,
        unresolved=[key for key, item in selected.items() if unresolved(item)],
        errors=schema_errors(value, command),
    )


def preview(request: PreviewRequest) -> PreviewResult:
    """Called inside a fresh worker by the server; standalone calls are useful for tests."""
    try:
        _guard(request)
        expanded = _expanded(request)
        store.add_to_hydra_store(overwrite_ok=True)
        with preview_directory(request.documents) as directory:
            context = (
                initialize_config_dir(config_dir=str(directory), version_base="1.3")
                if request.documents
                else initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3")
            )
            name = (
                next(iter(request.documents)).rsplit(".", 1)[0]
                if request.documents
                else request.command
            )
            with context:
                jobs = [
                    _job(compose(config_name=name, overrides=overrides), request.command)
                    for overrides in expanded
                ]
        command = [COMMAND_OF_CONFIG[request.command]]
        if request.documents:
            command.extend(["--config-dir", "./configs", "--config-name", name])
        if request.sweep:
            command.append("-m")
        command.extend(request.overrides)
        return PreviewResult(jobs=jobs, deferred=DEFERRED, command=shlex.join(command))
    except (ValueError, TypeError, HydraException, OmegaConfBaseException) as error:
        return PreviewResult(errors=[str(error)], deferred=DEFERRED)
