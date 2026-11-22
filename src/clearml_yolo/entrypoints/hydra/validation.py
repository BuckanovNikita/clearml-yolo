"""Validate public command arguments before waiting for GPUs or invoking workflows.

``validate_command_configuration`` is the per-command preflight: it runs the request checks
listed per command below and in DOCS.md, which the composed configuration alone decides,
before the invocation creates the ClearML task. Other checks, and those that need the task,
files, downloads or the SDK, stay in the use cases.
"""

import inspect
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from hydra.utils import get_object
from omegaconf import DictConfig, OmegaConf, open_dict, read_write
from pydantic import BaseModel, TypeAdapter, ValidationError

from clearml_yolo.adapters.integrations.native_runtime import validate_owner_environment
from clearml_yolo.adapters.storage.dataset_cache import dataset_cache_root
from clearml_yolo.adapters.storage.filesystem import cy_home, runs_root, write_path
from clearml_yolo.adapters.storage.run_identity import resolve_run_dir
from clearml_yolo.adapters.yolo.config import (
    execution_settings,
    native_defaults,
    prediction_defaults,
    prediction_settings,
    stage_settings,
)
from clearml_yolo.application.contracts import (
    ClearMLConfig,
    ModelRef,
    require_specified_candidate,
    require_ultralytics_dataset_format,
    validate_dataset_format,
    validate_test_fraction,
)
from clearml_yolo.application.ground_truth import normalize_ground_truth
from clearml_yolo.application.use_cases.compare import compare as run_comparison
from clearml_yolo.application.use_cases.compare import frozen_evaluation_config, reject_owned_prediction_overrides
from clearml_yolo.application.use_cases.metrics import compute_metrics, frozen_calibration_split
from clearml_yolo.application.use_cases.pipeline import (
    pipeline_stage_settings,
    routed_native,
    run_pipeline,
)
from clearml_yolo.application.use_cases.predict import require_prediction_model
from clearml_yolo.application.use_cases.report import report as run_report
from clearml_yolo.application.use_cases.train import reject_csv_resume, require_training_model
from clearml_yolo.core.comparison.significance import validate_q
from clearml_yolo.core.datasets import csv_dataset_policy
from clearml_yolo.core.evaluation.models import EvaluationConfig
from clearml_yolo.core.evaluation.policy import validate_evaluation_image_name
from clearml_yolo.core.export_requests import ExportSettings
from clearml_yolo.core.models import ModelConfig
from clearml_yolo.core.publication import FiftyOneConfig
from clearml_yolo.entrypoints.hydra.sweeps import compose_jobs
from clearml_yolo.entrypoints.hydra.transforms import prepare_transforms


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
        changed = sorted(key for key, value in values[group].items() if value != defaults[group][key])
        if changed:
            raise ValueError(
                f"Changed model.{group} settings {changed} are inactive for ultralytics; use {owner} instead"
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
        changed = sorted(key for key, value in config[group].items() if value != defaults[group].get(key))
        if changed:
            raise ValueError(
                f"Changed {group} settings {changed} are inactive for "
                f"{model.backend}/{model.preset}; use model.{owner} instead"
            )


def _reject_null_fiftyone(value: object) -> None:
    """Reject ``fiftyone=null``; it would silently publish with defaults."""
    if value is None:
        raise ValueError("fiftyone=null is not supported; use fiftyone.enabled=false to turn FiftyOne publication off")


def validate_wrapper_keys(config: DictConfig, function: Callable[..., Any]) -> None:
    """Validate the command schema, including keys introduced with Hydra's + syntax."""
    reject_legacy_controls(config)
    validate_owner_environment()
    accepted = set(inspect.signature(function).parameters) - {"deps"}
    if "ultralytics" in config or "ultralytics_predict" in config or "export" in config:
        accepted.add("model")
    if function.__name__ in {"train", "run_pipeline"}:
        accepted.add("transforms")
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unsupported wrapper settings: {sorted(unknown)}")
    if (
        "ground_truth" in config
        and not OmegaConf.is_missing(config, "ground_truth")
        and config.ground_truth is not None
    ):
        normalize_ground_truth(config.ground_truth)
    prepare_transforms(config)
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
            write_path(Path(project) / str(name) if project is not None else cy_home() / "runs" / str(name))
        if native.get("save_dir") is not None:
            write_path(native.save_dir)


def _target(request: type[BaseModel]) -> str:
    return f"{request.__module__}.{request.__qualname__}"


def _request_fields(config: object, request: type[BaseModel]) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise TypeError(f"{request.__name__} settings must be a mapping")
    values = {str(key): value for key, value in config.items()}
    target = _target(request)
    if values.pop("_target_", target) != target:
        raise ValueError(f"Submission requires the supported configuration target {target}")
    return values


def _validate_request(config: object, request: type[BaseModel]) -> None:
    request.model_validate(_request_fields(config, request))


def _validate_report_config_path(value: object) -> None:
    if value is not None and not isinstance(value, str):
        raise TypeError("report_config_path must be a path string or null")


def _validate_comparison(compare: dict[str, Any]) -> None:
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


def validate_pipeline_configuration(config: DictConfig, *, direct: bool = False) -> None:
    """Validate known requests and cross-field rules without instantiating SDK effects.

    The default is cy-queue's submission check: strict types, every key present and
    records that name their supported ``_target_``. ``direct=True`` is the direct ``cy``
    preflight. It rejects every value these checks reject, in every stage, whether the
    stage is skipped or follows training. It first applies what the run applies before
    it validates: a detector's ``model.train`` and ``model.predict`` groups and
    ``dataset_format=coco`` replace the Ultralytics groups, and the YOLO prediction group
    is checked as ``run_pipeline`` routes it (the CSV dataset policy when training, then
    the prediction projection). It accepts these loose but valid forms: integer skip
    flags, keys removed with ``~key`` (the use-case signature default applies), a
    ``_target_`` that imports the supported class, Hydra's reserved instantiate keys
    in records and any ``run_id`` next to ``run_dir``. It adds the direct run's own
    checks: the frozen-evaluation backend, the training model, ``resume``, and the
    routes resolved as the run resolves them.
    """
    resolved = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    if not isinstance(resolved, dict):
        raise TypeError("Pipeline settings must be a mapping")
    values = {str(key): value for key, value in resolved.items()}
    if direct:
        values = _direct_pipeline_values(values)
    normalize_ground_truth(values["ground_truth"])
    _validate_pipeline_types(values)
    metrics, report, compare = pipeline_stage_settings(values["metrics"], values["report"], values["compare"])
    _validate_request(metrics["evaluation"], EvaluationConfig)
    if metrics["calibration_split"] != "val":
        raise ValueError("calibration_split must be exactly 'val'")
    _validate_comparison(compare)
    _validate_report_config_path(report["report_config_path"])
    _validate_request(values["clearml"], ClearMLConfig)
    if "fiftyone" in values:
        _reject_null_fiftyone(values["fiftyone"])
        _validate_request(values["fiftyone"], FiftyOneConfig)
    _validate_pipeline_weights(values)
    if values["dataset_format"] not in {"ndjson", "flat", "coco"}:
        raise ValueError("Unsupported pipeline dataset_format")
    if values.get("model", {}).get("backend", "ultralytics") == "ultralytics":
        execution_settings(values["ultralytics"], "train")
        execution_settings(values["ultralytics_predict"], "predict")
    if direct:
        _validate_frozen_evaluation(metrics["evaluation"])
        _validate_train(values)
        _validate_direct_routes(values)
    else:
        _validate_queue_routes(values)


def _validate_pipeline_weights(values: dict[str, Any]) -> None:
    if values["weights"] is not None and not values["skip_train"]:
        raise ValueError("weights is only valid with skip_train=true; training chooses its model")


def _validate_queue_routes(values: dict[str, Any]) -> None:
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


# Loose but valid forms of the direct commands, which cy-queue admission keeps strict.
_SKIP_FLAGS = ("skip_train", "skip_predict", "skip_metrics", "skip_report", "skip_compare")
# Hydra consumes these keys when it instantiates a record.
_HYDRA_RESERVED_KEYS = frozenset({"_convert_", "_recursive_", "_args_", "_partial_"})
_RECORDS: tuple[tuple[str, type[BaseModel]], ...] = (
    ("clearml", ClearMLConfig),
    ("fiftyone", FiftyOneConfig),
    ("evaluation", EvaluationConfig),
    ("baseline_model", ModelRef),
    ("candidate_model", ModelRef),
)
_STAGE_SETTINGS: tuple[tuple[str, Callable[..., Any], tuple[str, ...]], ...] = (
    ("metrics", compute_metrics, ("evaluation", "calibration_split")),
    ("report", run_report, ("report_config_path",)),
    ("compare", run_comparison, ("baseline_model", "q", "bootstrap_iterations", "seed")),
)


def detector_native_groups(model: ModelConfig) -> dict[str, dict[str, Any]]:
    """Return the native groups a detector run executes in place of the Ultralytics groups."""
    return {
        "ultralytics": model.train.model_dump(mode="json") | {"model": model.preset},
        "ultralytics_predict": model.predict.model_dump(mode="json"),
    }


def _names_class(target: object, request: type[BaseModel]) -> bool:
    """Tell whether a ``_target_`` locates the supported class, as Hydra's instantiate does."""
    if not isinstance(target, str):
        return False
    try:
        return get_object(target) is request
    except (ImportError, ValueError):
        # Not locatable: the shared check rejects the unsupported target.
        return False


def _instantiated_record(record: object, request: type[BaseModel]) -> object:
    """Return a record as Hydra instantiates it: reserved keys consumed, an alias resolved."""
    if not isinstance(record, Mapping):
        return record
    values = {str(key): value for key, value in record.items() if key not in _HYDRA_RESERVED_KEYS}
    if _names_class(values.get("_target_"), request):
        values["_target_"] = _target(request)
    return values


def _with_records(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _instantiated_record(value, request) if (request := dict(_RECORDS).get(key)) else value
        for key, value in values.items()
    }


def _with_defaults(
    values: dict[str, Any], function: Callable[..., Any], names: Iterable[str] | None = None, *, prefix: str = ""
) -> dict[str, Any]:
    """Fill settings removed with ``~key`` from the use-case signature, as the direct call does."""
    parameters = inspect.signature(function).parameters
    filled = dict(values)
    for name in names if names is not None else (name for name in parameters if name != "deps"):
        # A removed fiftyone group stays absent: the run publishes with defaults, while
        # an explicit fiftyone=null is rejected.
        if name in filled or name == "fiftyone":
            continue
        default = parameters[name].default
        if default is inspect.Parameter.empty:
            raise ValueError(f"Required setting {prefix}{name} is missing")
        filled[name] = default
    return filled


def _direct_values(values: dict[str, Any], function: Callable[..., Any]) -> dict[str, Any]:
    """Apply what the direct run applies before it validates, then accept the loose forms."""
    model = ModelConfig.model_validate(values["model"]) if "model" in values else None
    if model is not None and model.backend != "ultralytics" and function.__name__ != "export_model":
        # _execute_direct runs a detector's model groups and its COCO dataset.
        values = values | detector_native_groups(model)
        if "dataset_format" in values:
            values["dataset_format"] = "coco"
    return _with_records(_with_defaults(values, function))


def _direct_pipeline_values(values: dict[str, Any]) -> dict[str, Any]:
    """Apply ``_direct_values`` and the routing of the prediction group to cy's settings."""
    values = _direct_values(values, run_pipeline)
    for key, function, names in _STAGE_SETTINGS:
        if isinstance(values[key], Mapping):
            values[key] = _with_records(_with_defaults(dict(values[key]), function, names, prefix=f"{key}."))
    for flag in _SKIP_FLAGS:
        # run_pipeline reads skip flags by truthiness.
        if type(values[flag]) is int:
            values[flag] = bool(values[flag])
    if values["run_dir"]:
        # run_pipeline reads run_id only without run_dir.
        values["run_id"] = None
    prediction = values["ultralytics_predict"]
    if _uses_ultralytics(values) and isinstance(prediction, Mapping):
        # run_pipeline routes the prediction group after the CSV dataset policy (when
        # training) and the prediction projection.
        if not values["skip_train"]:
            prediction, _ = csv_dataset_policy(prediction)
        values["ultralytics_predict"] = prediction_settings(dict(prediction))
    return values


# Without run_dir or run_id the task names the run directory, so no project can match it.
_TASK_RUN_DIRECTORY = Path("<task run directory>")


def _validate_direct_routes(values: dict[str, Any]) -> None:
    directory = None
    if values["run_dir"] or values["run_id"]:
        # The resolved directory run_pipeline routes to; resolving checks containment and creates nothing.
        explicit = Path(values["run_dir"]) if values["run_dir"] else None
        directory = resolve_run_dir(runs_root(), values["run_id"] or "", explicit)
        if dataset_cache_root(values["dataset_cache_dir"]).is_relative_to(directory):
            raise ValueError("dataset_cache_dir must be outside run_dir")
    for group, relative, stage in (
        ("ultralytics", "detect", "train"),
        ("ultralytics_predict", "native", "predict"),
    ):
        settings = values[group]
        try:
            routed_native(settings, directory / relative if directory else _TASK_RUN_DIRECTORY, stage)
        except ValueError as error:
            if directory is not None:
                raise
            raise ValueError("Native pipeline output overrides require an explicit run_dir") from error


def _resolved_values(config: DictConfig) -> dict[str, Any]:
    resolved = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    if not isinstance(resolved, dict):
        raise TypeError("Resolved command configuration must be a mapping")
    return {str(key): value for key, value in resolved.items()}


def _uses_ultralytics(values: dict[str, Any]) -> bool:
    model = values.get("model", {})
    return not isinstance(model, Mapping) or model.get("backend", "ultralytics") == "ultralytics"


def _validate_fiftyone(values: dict[str, Any]) -> None:
    if "fiftyone" in values:
        _reject_null_fiftyone(values["fiftyone"])
        _validate_request(values["fiftyone"], FiftyOneConfig)


def _validate_prediction_model(values: dict[str, Any]) -> None:
    if _uses_ultralytics(values):
        require_prediction_model(prediction_settings(values["ultralytics_predict"] or {}, values["weights"]))
    else:
        # A detector's model.predict has no model field; only weights names its checkpoint.
        require_prediction_model({"model": values["weights"]})


def _validate_train(values: dict[str, Any]) -> None:
    if _uses_ultralytics(values):
        require_ultralytics_dataset_format(values["dataset_format"])
        settings = execution_settings(values["ultralytics"], "train")
        require_training_model(settings)
        reject_csv_resume(settings)


def _validate_frozen_evaluation(evaluation: object) -> None:
    frozen_evaluation_config(None if evaluation is None else _request_fields(evaluation, EvaluationConfig))


def _validate_train_command(values: dict[str, Any]) -> None:
    validate_dataset_format(values["dataset_format"])
    _validate_train(values)


def _validate_predict(values: dict[str, Any]) -> None:
    _validate_prediction_model(values)
    _validate_fiftyone(values)


def _validate_val(values: dict[str, Any]) -> None:
    _validate_prediction_model(values)
    _validate_request(values["evaluation"], EvaluationConfig)
    _validate_frozen_evaluation(values["evaluation"])
    frozen_calibration_split(values["splits"] or (), "val")


def _validate_metrics(values: dict[str, Any]) -> None:
    frozen_calibration_split(values["splits"] or (), values["calibration_split"])
    _validate_request(values["evaluation"], EvaluationConfig)
    _validate_frozen_evaluation(values["evaluation"])
    _validate_fiftyone(values)


def _validate_compare(values: dict[str, Any]) -> None:
    _validate_comparison(values)
    if _uses_ultralytics(values):
        reject_owned_prediction_overrides(values["ultralytics_predict"])
        prediction_settings(values["ultralytics_predict"] or {})
    require_specified_candidate(ModelRef.model_validate(_request_fields(values["candidate_model"], ModelRef)))
    _validate_frozen_evaluation(values["evaluation"])


def _validate_report(values: dict[str, Any]) -> None:
    _validate_report_config_path(values["report_config_path"])


def _validate_export_inputs(values: dict[str, Any]) -> None:
    ExportSettings.model_validate(values["export"]).validate_input_presence(
        has_weights=values["weights"] is not None, has_ground_truth=values["ground_truth"] is not None
    )


def _validate_ground_truth(values: dict[str, Any]) -> None:
    validate_test_fraction(values["test_fraction"])


# Keyed by the command function, like the wrapper schema checks above.
_COMMAND_CHECKS: dict[str, Callable[[dict[str, Any]], None]] = {
    "train": _validate_train_command,
    "predict": _validate_predict,
    "validate": _validate_val,
    "compute_metrics": _validate_metrics,
    "compare": _validate_compare,
    "report": _validate_report,
    "export_model": _validate_export_inputs,
    "ground_truth": _validate_ground_truth,
}


def validate_command_configuration(config: DictConfig, function: Callable[..., Any]) -> None:
    """Run the command's effect-free request checks before its ClearML task is created."""
    if function.__name__ == "run_pipeline":
        validate_pipeline_configuration(config, direct=True)
        return
    check = _COMMAND_CHECKS.get(function.__name__)
    if check is not None:
        check(_direct_values(_resolved_values(config), function))


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
                if group.split("/")[0] in _LEGACY_CONTROLS or (group == "hydra/launcher" and selection == "cy_queue"):
                    raise ValueError(_MIGRATION)
                if isinstance(selection, str):
                    _inspect_saved_configuration(directory, f"{group}/{selection}", visited)


def validate_launch_arguments(name: str) -> str | None:
    """Preflight CLI inputs and return the local source that must precede package defaults."""
    from hydra import initialize, initialize_config_dir
    from hydra._internal.utils import get_args_parser
    from hydra.core.hydra_config import HydraConfig

    arguments = get_args_parser().parse_args()
    local_source = str(Path(arguments.config_dir).expanduser().resolve()) if arguments.config_dir is not None else None
    for override in arguments.overrides:
        key = override.split("=", 1)[0].lstrip("+~").split(".", 1)[0]
        if key in _LEGACY_CONTROLS or override.lstrip("+~") == "hydra/launcher=cy_queue":
            raise ValueError(_MIGRATION)
    if arguments.help or arguments.hydra_help or arguments.shell_completion or arguments.info:
        return local_source
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
            multirun, jobs = compose_jobs(selected_name, arguments.overrides, multirun=arguments.multirun)
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
    return local_source


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
