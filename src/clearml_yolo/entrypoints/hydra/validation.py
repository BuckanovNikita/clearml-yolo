"""Validate public command arguments before waiting for GPUs or invoking workflows."""

import inspect
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from omegaconf import DictConfig, OmegaConf, open_dict, read_write
from pydantic import BaseModel, TypeAdapter, ValidationError

from clearml_yolo.adapters.integrations.native_runtime import validate_owner_environment
from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.adapters.yolo.config import (
    execution_settings,
    native_defaults,
    prediction_defaults,
    stage_settings,
)
from clearml_yolo.application.contracts import ClearMLConfig, ModelRef
from clearml_yolo.application.use_cases.pipeline import (
    pipeline_stage_settings,
    routed_native,
    run_pipeline,
)
from clearml_yolo.core.comparison.significance import validate_q
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.evaluation.policy import validate_evaluation_image_name
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import ModelConfig
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.entrypoints.hydra.sweeps import compose_jobs


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
    reject_legacy_controls(config)
    validate_owner_environment()
    accepted = set(inspect.signature(function).parameters) - {"deps"}
    if "ultralytics" in config or "ultralytics_predict" in config or "export" in config:
        accepted.add("model")
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unsupported wrapper settings: {sorted(unknown)}")
    model = materialize_model_config(config)
    _validate_export(config, model)
    _validate_inactive_groups(config, model)
    for group in ("ultralytics", "ultralytics_predict"):
        if group in config:
            stage_settings(dict(config[group]), "train" if group == "ultralytics" else "predict")
    if "inference" in config:
        validate_evaluation_image_name(config.inference.get("image_name", "name"))
        unknown = set(config.inference) - {"reuse_existing", "image_name"}
        if unknown:
            raise ValueError(f"Unsupported inference settings: {sorted(unknown)}")


_LEGACY_CONTROLS = frozenset({"queue", "autogpu", "auto_gpu"})
_MIGRATION = (
    "Legacy queue/autogpu controls are removed from direct cy commands. "
    "Remove these settings from CLI overrides and saved YAML. "
    "Use cy-queue submit for scheduled execution; direct commands preserve native devices."
)


def reject_legacy_controls(config: Mapping[str, Any] | DictConfig) -> None:
    if _LEGACY_CONTROLS.intersection(config):
        raise ValueError(_MIGRATION)


def validate_project_destinations(config: DictConfig) -> None:
    """Validate all public output routes; input and SDK selectors remain external."""
    for key in ("run_dir", "output_dir", "output", "dataset_cache_dir"):
        if key in config and not OmegaConf.is_missing(config, key):
            value = config[key]
            if value is not None:
                write_path(value)
    for group in ("ultralytics", "ultralytics_predict"):
        if group not in config:
            continue
        native = config[group]
        project = native.get("project")
        name = native.get("name")
        if project is not None:
            write_path(project)
        if name is not None:
            write_path(
                Path(project) / str(name) if project is not None else cy_home() / "runs" / str(name)
            )
        if native.get("save_dir") is not None:
            write_path(native.save_dir)


def _validate_request(config: object, request: type[BaseModel]) -> None:
    if not isinstance(config, Mapping):
        raise TypeError(f"{request.__name__} settings must be a mapping")
    values = dict(config)
    target = f"{request.__module__}.{request.__qualname__}"
    if values.pop("_target_", target) != target:
        raise ValueError(f"Submission requires the supported configuration target {target}")
    request.model_validate(values)


def _validate_pipeline_comparison(compare: dict[str, Any]) -> None:
    _validate_request(compare["baseline_model"], ModelRef)
    validate_q(compare["q"])
    iterations = compare["bootstrap_iterations"]
    if type(iterations) is not int or iterations <= 0:
        raise ValueError("bootstrap_iterations must be a positive integer")
    seed = compare["seed"]
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError("Comparison seed must be a nonnegative integer or null")


def _validate_pipeline_types(values: dict[str, Any]) -> None:
    # Validate the existing public function contract without invoking it or
    # duplicating its scalar/collection schema. Nested target records are checked
    # separately below because they have not been instantiated at submission.
    for name, parameter in inspect.signature(run_pipeline).parameters.items():
        if name in {"deps", "clearml", "fiftyone"}:
            continue
        try:
            TypeAdapter(parameter.annotation).validate_python(values[name], strict=True)
        except ValidationError as error:
            raise ValueError(f"Invalid pipeline setting {name}: {error}") from error


def validate_pipeline_configuration(config: DictConfig) -> None:
    """Validate known requests and cross-field rules without instantiating SDK effects."""
    resolved = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    if not isinstance(resolved, dict):
        raise TypeError("Pipeline settings must be a mapping")
    values = {str(key): value for key, value in resolved.items()}
    _validate_pipeline_types(values)
    metrics, report, compare = pipeline_stage_settings(
        values["metrics"], values["report"], values["compare"]
    )
    _validate_request(metrics["evaluation"], EvaluationConfig)
    if metrics["calibration_split"] != "val":
        raise ValueError("calibration_split must be exactly 'val'")
    _validate_pipeline_comparison(compare)
    if report["report_config_path"] is not None and not isinstance(
        report["report_config_path"], str
    ):
        raise TypeError("report_config_path must be a path string or null")
    _validate_request(values["clearml"], ClearMLConfig)
    if values.get("fiftyone") is not None:
        _validate_request(values["fiftyone"], FiftyOneConfig)
    if values["weights"] is not None and not values["skip_train"]:
        raise ValueError("weights is only valid with skip_train=true; training chooses its model")
    if values["dataset_format"] not in {"ndjson", "flat", "coco"}:
        raise ValueError("Unsupported pipeline dataset_format")
    if values.get("model", {}).get("backend", "ultralytics") == "ultralytics":
        execution_settings(values["ultralytics"], "train")
        execution_settings(values["ultralytics_predict"], "predict")
    _validate_pipeline_routes(values)


def _validate_pipeline_routes(values: dict[str, Any]) -> None:
    directory = Path(values["run_dir"]) if values["run_dir"] else None
    if directory is None and values["run_id"]:
        directory = write_path(cy_home() / "runs" / values["run_id"])
    if (
        directory is not None
        and values["dataset_cache_dir"] is not None
        and Path(values["dataset_cache_dir"]).resolve().is_relative_to(directory.resolve())
    ):
        raise ValueError("dataset_cache_dir must be outside run_dir")
    for group, relative, stage in (
        ("ultralytics", "detect", "train"),
        ("ultralytics_predict", "native", "predict"),
    ):
        settings = values[group]
        if directory is None:
            if any(settings.get(key) is not None for key in ("project", "name", "save_dir")):
                raise ValueError("Native pipeline output overrides require an explicit run_dir")
        else:
            routed_native(settings, directory / relative, stage)


def reject_saved_legacy_controls(directory: Path, name: str) -> None:
    """Explain retired defaults before Hydra attempts to import missing plugins."""
    _inspect_saved_configuration(directory, name, set())


def _inspect_saved_configuration(directory: Path, name: str, visited: set[Path]) -> None:
    selected = (directory / f"{name}.yaml").resolve()
    if not selected.is_file() or selected in visited:
        return
    visited.add(selected)
    document = OmegaConf.load(selected)
    if not isinstance(document, DictConfig):
        return
    reject_legacy_controls(document)
    for entry in document.get("defaults", []):
        if isinstance(entry, str) and entry != "_self_":
            target = entry.lstrip("/")
            if target.split("/")[0] in _LEGACY_CONTROLS:
                raise ValueError(_MIGRATION)
            _inspect_saved_configuration(directory, target, visited)
        elif isinstance(entry, DictConfig):
            for raw_group, selection in entry.items():
                group = str(raw_group).removeprefix("override ").lstrip("/")
                if group.split("/")[0] in _LEGACY_CONTROLS or (
                    group == "hydra/launcher" and selection == "cy_queue"
                ):
                    raise ValueError(_MIGRATION)
                if isinstance(selection, str):
                    _inspect_saved_configuration(directory, f"{group}/{selection}", visited)


def validate_launch_arguments(name: str) -> None:
    """Compose actual CLI inputs before Hydra logging/output directory creation."""
    from hydra import initialize, initialize_config_dir
    from hydra._internal.utils import get_args_parser
    from hydra.core.hydra_config import HydraConfig

    arguments = get_args_parser().parse_args()
    for override in arguments.overrides:
        key = override.split("=", 1)[0].lstrip("+~").split(".", 1)[0]
        if key in _LEGACY_CONTROLS or override.lstrip("+~") == "hydra/launcher=cy_queue":
            raise ValueError(_MIGRATION)
    if arguments.help or arguments.hydra_help or arguments.shell_completion or arguments.info:
        return
    selected_name = arguments.config_name or name
    directory = arguments.config_dir or arguments.config_path
    if directory is not None:
        directory = Path(directory).expanduser().resolve()
        reject_saved_legacy_controls(directory, selected_name)
    context = (
        initialize_config_dir(config_dir=str(directory), version_base="1.3")
        if directory is not None
        else initialize(config_path=None, version_base="1.3")
    )
    previous = HydraConfig.instance().cfg
    try:
        with context:
            multirun, jobs = compose_jobs(
                selected_name, arguments.overrides, multirun=arguments.multirun
            )
            for index, job in enumerate(jobs):
                reject_legacy_controls(job)
                with open_dict(job):
                    job.hydra.job.num = index
                    job.hydra.job.id = str(index)
                HydraConfig.instance().set_config(job)
                validate_hydra_destinations(job, multirun=multirun)
                validate_project_destinations(job)
    finally:
        HydraConfig.instance().cfg = previous


def validate_hydra_destinations(config: DictConfig, *, multirun: bool = False) -> None:
    """Cover Hydra logging handlers and config snapshots before its first write."""
    settings = config.hydra
    run = write_path(settings.run.dir).absolute()
    sweep = write_path(settings.sweep.dir).absolute()
    sweep_job = write_path(sweep / settings.sweep.subdir)
    output = sweep_job if multirun else run
    with read_write(settings.runtime), open_dict(settings.runtime):
        settings.runtime.output_dir = str(output)
    if multirun:
        write_path(sweep / "multirun.yaml")
    if settings.output_subdir is not None:
        directory = write_path(output / settings.output_subdir)
        for name in ("config.yaml", "hydra.yaml", "overrides.yaml"):
            write_path(directory / name)
    # Hydra configures job logging after an optional chdir, while its own logging
    # starts in the invocation cwd. Resolve relative handler filenames accordingly.
    for selected, directory in (
        (settings.job_logging, output if settings.job.chdir else Path.cwd()),
        (settings.hydra_logging, Path.cwd()),
    ):
        if not isinstance(selected, DictConfig):
            continue
        for handler in selected.get("handlers", {}).values():
            if isinstance(handler, DictConfig) and handler.get("filename") is not None:
                write_path(directory / handler.filename)
