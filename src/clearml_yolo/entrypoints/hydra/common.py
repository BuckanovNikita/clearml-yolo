"""The shared CLI ownership boundary; stage entrypoints remain independent."""

import inspect
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import Any

import hydra
from hydra.core.hydra_config import HydraConfig
from hydra.types import RunMode
from hydra_zen import instantiate, store, zen
from omegaconf import DictConfig, OmegaConf, open_dict

# Populate the shared ConfigStore in fresh CLI processes before Hydra composes examples.
import clearml_yolo.entrypoints.hydra.configs  # noqa: F401
from clearml_yolo.adapters.assets.execution import prepare_model_assets
from clearml_yolo.adapters.assets.preparation import prepare_catalogue
from clearml_yolo.adapters.clearml.naming import initialize_naming
from clearml_yolo.adapters.clearml.session import (
    RemoteReplay,
    active_task,
    fetch_remote_replay,
    invocation,
    publish_model_assets,
    publish_run_configuration,
    replay_configuration,
    replay_training_parameters,
    task_identity,
)
from clearml_yolo.adapters.integrations.native_runtime import (
    detector_runtime,
    native_runtime,
    release_training_memory,
)
from clearml_yolo.adapters.observability.capture import capture_output
from clearml_yolo.adapters.observability.diagnostics import log_exception_safely
from clearml_yolo.adapters.observability.tracing import trace_command, trace_operation
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
from clearml_yolo.adapters.runtime.execution_lifecycle import execution_lifecycle
from clearml_yolo.adapters.runtime.git_workspace import warn_if_unversioned_launch
from clearml_yolo.adapters.runtime.process_tree import native_descendant_scope
from clearml_yolo.adapters.storage.filesystem import initialize_filesystem, runs_root, write_path
from clearml_yolo.adapters.storage.run_identity import task_run_dir
from clearml_yolo.adapters.yolo.config import requested_devices
from clearml_yolo.core.models import ModelConfig, model_preset
from clearml_yolo.entrypoints.hydra.config_resolution import resolve_config_file
from clearml_yolo.entrypoints.hydra.configs import command_schema
from clearml_yolo.entrypoints.hydra.sweeps import new_multirun_tag, tag_multirun_job
from clearml_yolo.entrypoints.hydra.transforms import prepare_transforms, profile_values
from clearml_yolo.entrypoints.hydra.validation import (
    materialize_model_config,
    reject_legacy_controls,
    validate_launch_arguments,
    validate_project_destinations,
    validate_wrapper_keys,
)


@contextmanager
def _gpu_cleanup(enabled: bool) -> Iterator[None]:
    """Release unused allocations before task completion, preserving primary failures."""
    try:
        yield
    finally:
        if enabled:
            primary_error = sys.exception()
            try:
                release_training_memory()
            except BaseException as error:
                if primary_error is None:
                    raise
                log_exception_safely("Native GPU memory cleanup failed", error)


def _validate_replay_runtime(uses_detector: bool, replay: dict[str, Any]) -> None:
    if "model" not in replay:
        return
    selected = ModelConfig.model_validate(replay["model"])
    if (selected.backend != "ultralytics") != uses_detector:
        model = (
            "ultralytics"
            if selected.backend == "ultralytics"
            else f"{selected.backend}/{selected.preset}"
        )
        # Runtime setup precedes ClearML package discovery; replacing it mid-owner
        # would lose callback and path isolation established for this invocation.
        raise ValueError(
            "ClearML replay cannot change the initialized runtime family. "
            f"Relaunch with model={model} to initialize its matching runtime."
        )


def _replay_native_parameters(
    task: Any,
    native: dict[str, Any],
    requested: dict[str, Any],
) -> dict[str, Any]:
    native = replay_training_parameters(task, native)
    # General and canonical run may contain a previous owner's effective output
    # route. A clone retains only its current explicitly requested route.
    for key in ("project", "name", "save_dir"):
        native.pop(key, None)
        if key in requested:
            native[key] = requested[key]
    return native


def _publication_inputs(config: DictConfig) -> dict[str, Any]:
    """Detach executable inputs, omitting the selected backend's inactive groups."""
    resolved = OmegaConf.to_container(config, resolve=True)
    if not isinstance(resolved, dict):
        raise TypeError("Resolved command configuration must be a mapping")
    values = {str(key): value for key, value in resolved.items()}
    values.pop("defaults", None)
    model = values.get("model")
    if isinstance(model, dict):
        if model.get("backend", "ultralytics") == "ultralytics":
            values["model"] = {key: model[key] for key in ("backend", "preset") if key in model}
        else:
            values.pop("ultralytics", None)
            values.pop("ultralytics_predict", None)
            if "dataset_format" in values:
                values["dataset_format"] = "coco"
    return values


def _builtin_defaults(name: str, config: DictConfig) -> dict[str, Any]:
    """Compose the registered project root and selected preset without user overrides."""
    # The local Zen store retains built-in roots even when a YAML search path
    # shadows their names. Re-entering Hydra would inherit that user's search path.
    defaults = command_schema(name)
    with open_dict(defaults):
        defaults.pop("defaults", None)
        if name in {"train", "pipeline"}:
            defaults.transforms = profile_values("default")
        if "model" in defaults:
            backend = OmegaConf.select(config, "model.backend", default="ultralytics")
            preset = OmegaConf.select(config, "model.preset", default="default")
            selection = "ultralytics" if backend == "ultralytics" else f"{backend}/{preset}"
            defaults.model = model_preset(selection).model_dump(mode="json")
    return _publication_inputs(defaults)


def _executable_replay(
    config: DictConfig, function: Callable[..., Any], replay: dict[str, Any]
) -> dict[str, Any]:
    reject_legacy_controls(replay)
    # Run also contains result provenance; only command inputs are executable.
    accepted = set(inspect.signature(function).parameters) - {"deps"}
    if "model" in config:
        accepted.add("model")
    if function.__name__ in {"train", "run_pipeline"}:
        accepted.add("transforms")
    return {key: value for key, value in replay.items() if key in accepted}


def _restore_agent_inputs(
    config: DictConfig, function: Callable[..., Any]
) -> tuple[RemoteReplay | None, dict[str, Any]]:
    # Agent scripts record a bare entrypoint. Restore inputs before validating
    # required fields or selecting the native runtime; no task is initialized yet.
    snapshot = fetch_remote_replay()
    native = (
        OmegaConf.to_container(config.ultralytics, resolve=False) if "ultralytics" in config else {}
    )
    if not isinstance(native, dict):
        raise TypeError("Native command configuration must be a mapping")
    requested = {str(key): value for key, value in native.items()}
    if snapshot is not None and snapshot.canonical is not None:
        with open_dict(config):
            for key, value in _executable_replay(config, function, snapshot.canonical).items():
                config[key] = deepcopy(value)
    return snapshot, requested


@trace_operation("invocation.execute")
def execute_owned(name: str, config: DictConfig, function: Callable[..., Any]) -> None:
    """Execute native settings unchanged under one invocation-owned task."""
    with trace_operation("filesystem.initialize"):
        initialize_filesystem()
        if HydraConfig.initialized():
            write_path(HydraConfig.get().runtime.output_dir)
    remote_replay, requested_native = _restore_agent_inputs(config, function)
    with trace_operation("configuration.resolve", context={"stage": name}):
        validate_wrapper_keys(config, function)
        resolved = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    if not isinstance(resolved, dict):
        raise TypeError("Resolved command configuration must be a mapping")
    inputs = {str(key): value for key, value in resolved.items()}
    validate_project_destinations(config)
    # Initialize native imports before ClearML starts background package detection;
    # concurrent torch submodule discovery can observe a partially loaded package.
    model_values = inputs.get("model", {})
    uses_detector = (
        isinstance(model_values, dict)
        and model_values.get("backend", "ultralytics") != "ultralytics"
    )
    with (
        execution_lifecycle() as supervised,
        detector_runtime() if uses_detector else native_runtime(),
        invocation(
            instantiate(config.clearml),
            name,
            config_resolver=lambda document: resolve_config_file(document, config),
            remote_replay=remote_replay,
        ) as task,
        _gpu_cleanup(True),
    ):
        remote_native = (
            name in {"pipeline", "train"} and not uses_detector and not task.running_locally()
        )
        replay = (
            replay_configuration(task, inputs, legacy_native_general=True, publish=False)
            if remote_native
            else replay_configuration(task, inputs, publish=False)
        )
        replay = _executable_replay(config, function, replay)
        _validate_replay_runtime(uses_detector, replay)
        native = deepcopy(replay.get("ultralytics", requested_native))
        training = name == "train" or (
            name == "pipeline" and not replay.get("skip_train", inputs.get("skip_train", False))
        )
        if remote_native and native and training:
            # Detector General is observed evidence; its executable settings live
            # under run.model and must never overwrite the inactive YOLO group.
            native = _replay_native_parameters(task, native, requested_native)
        with open_dict(config):
            for key, value in replay.items():
                config[key] = value
            if "ultralytics" in config:
                config.ultralytics = native
        validate_wrapper_keys(config, function)
        validate_project_destinations(config)
        publish_run_configuration(
            task, _publication_inputs(config), _builtin_defaults(name, config)
        )
        initialize_naming(task)
        # Derive paths only after the owner exists; remote task names may differ.
        with open_dict(config):
            if "output_dir" in config and config.output_dir is None:
                config.output_dir = str(task_run_dir(runs_root(), *task_identity(task)) / name)
            if "output" in config and config.output is None:
                config.output = str(task_run_dir(runs_root(), *task_identity(task)) / f"{name}.csv")
        # A supervised job reports computation/publication outcomes. Its parent
        # owns process cleanup and capacity even after this task is finalized.
        with nullcontext() if supervised else native_descendant_scope():
            _execute_direct(name, config, function)


def _execution_model(name: str, config: DictConfig) -> ModelConfig:
    selected = (
        ModelConfig.model_validate(OmegaConf.to_container(config.model, resolve=True))
        if "model" in config
        else ModelConfig()
    )
    training = name == "train" or (name == "pipeline" and not config.skip_train)
    prepared, assets = prepare_model_assets(selected, training=training)
    publish_model_assets(active_task(), assets)
    return prepared


def _execute_direct(name: str, config: DictConfig, function: Callable[..., Any]) -> None:
    if name == "pipeline":
        prepare_catalogue(automatic=True)
    materialize_model_config(config)
    effective = deepcopy(config)
    requests: dict[str, Any] = {}
    for group in ("ultralytics", "ultralytics_predict"):
        if group in config:
            value = config[group].get("device")
            requests[group] = (
                OmegaConf.to_container(value, resolve=True) if OmegaConf.is_config(value) else value
            )
    with requested_devices(requests):
        if "deps" in inspect.signature(function).parameters:
            with trace_operation("configuration.dependencies"):
                from clearml_yolo.entrypoints.composition import build_dependencies

                selected = _execution_model(name, effective)
                transforms = prepare_transforms(effective)
                if transforms.mode == "native":
                    dependencies = (
                        build_dependencies()
                        if selected.backend == "ultralytics"
                        else build_dependencies(selected)
                    )
                else:
                    dependencies = build_dependencies(selected, transforms=transforms)

            with open_dict(effective):
                effective.pop("model", None)
                effective.pop("transforms", None)
                if selected.backend != "ultralytics" and name != "export":
                    effective.ultralytics = selected.train.model_dump(mode="json") | {
                        "model": selected.preset,
                    }
                    effective.ultralytics_predict = selected.predict.model_dump(mode="json")
                    if "dataset_format" in effective:
                        effective.dataset_format = "coco"

            # Supply concrete capabilities outside the public Hydra configuration.
            if name == "train" or (name == "pipeline" and not effective.skip_train):
                parameters = dependencies.model.execution_settings(
                    dict(effective.ultralytics), "train"
                )
                if not parameters.get("model"):
                    raise ValueError(
                        "Set ultralytics.model explicitly; no training model fallback is provided"
                    )
                dependencies.tracking.publish_training_parameters(
                    dependencies.tracking.init_task(instantiate(effective.clearml), stage=name),
                    parameters | {"mode": "train"},
                )
            bound = partial(function, deps=dependencies)
            zen(bound, exclude="deps")(effective)
        else:
            zen(function)(effective)


def launch(name: str, function: Callable[..., Any]) -> None:
    """Compose and execute within one owned runtime lifetime."""
    launch_directory = Path.cwd()
    with runtime_environment() as arena, capture_output(arena / "logs"):
        warn_if_unversioned_launch(launch_directory)
        # Watchdogs inherit the captured descriptors, including native diagnostics.
        trace_command(name)(_launch)(name, function)


def _launch(name: str, function: Callable[..., Any]) -> None:
    with trace_operation("configuration.startup", context={"stage": name}):
        initialize_filesystem()
        store.add_to_hydra_store(overwrite_ok=True)
        config_path = validate_launch_arguments(name)

    multirun_tag: str | None = None
    # Hydra appends --config-dir after search-path plugins. Make that directory
    # the main source too, keeping edited local groups ahead of packaged fallbacks.

    @hydra.main(config_name=name, config_path=config_path, version_base="1.3")
    def execute(config: DictConfig) -> None:
        nonlocal multirun_tag
        if HydraConfig.initialized() and HydraConfig.get().mode == RunMode.MULTIRUN:
            if multirun_tag is None:
                multirun_tag = new_multirun_tag()
            tag_multirun_job(config, multirun_tag)
        execute_owned(name, config, function)

    execute()
