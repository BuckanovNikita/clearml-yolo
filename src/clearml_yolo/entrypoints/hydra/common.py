"""The shared CLI ownership boundary; stage entrypoints remain independent."""

import inspect
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from functools import partial
from typing import Any

import hydra
from hydra.core.hydra_config import HydraConfig
from hydra.types import RunMode
from hydra_zen import instantiate, store, zen
from omegaconf import DictConfig, OmegaConf, open_dict

# Populate the shared ConfigStore in fresh CLI processes before Hydra composes examples.
import clearml_yolo.entrypoints.hydra.configs  # noqa: F401
from clearml_yolo.adapters.clearml.naming import initialize_naming
from clearml_yolo.adapters.clearml.parameters import project_native_parameters
from clearml_yolo.adapters.clearml.session import (
    invocation,
    replay_configuration,
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
from clearml_yolo.adapters.runtime.process_tree import native_descendant_scope
from clearml_yolo.adapters.storage.filesystem import initialize_filesystem, runs_root, write_path
from clearml_yolo.adapters.storage.run_identity import task_run_dir
from clearml_yolo.adapters.yolo.config import requested_devices
from clearml_yolo.core.models import ModelConfig
from clearml_yolo.entrypoints.hydra.config_resolution import resolve_config_file
from clearml_yolo.entrypoints.hydra.sweeps import new_multirun_tag, tag_multirun_job
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
    scientific = task.connect(
        project_native_parameters(native), name="General", ignore_remote_overrides=False
    )
    native.update(project_native_parameters(scientific))
    # General and canonical run may contain a previous owner's effective output
    # route. A clone retains only its current explicitly requested route.
    for key in ("project", "name", "save_dir"):
        native.pop(key, None)
        if key in requested:
            native[key] = requested[key]
    return native


@trace_operation("invocation.execute")
def execute_owned(name: str, config: DictConfig, function: Callable[..., Any]) -> None:
    """Execute native settings unchanged under one invocation-owned task."""
    with trace_operation("filesystem.initialize"):
        initialize_filesystem()
        if HydraConfig.initialized():
            write_path(HydraConfig.get().runtime.output_dir)
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
        ) as task,
        _gpu_cleanup(True),
    ):
        requested_native = dict(inputs.get("ultralytics", {}))
        remote_native = (
            name in {"pipeline", "train"} and not uses_detector and not task.running_locally()
        )
        replay = (
            replay_configuration(task, inputs, legacy_native_general=True)
            if remote_native
            else replay_configuration(task, inputs)
        )
        reject_legacy_controls(replay)
        # Run also contains result provenance; only command inputs are executable.
        accepted = set(inspect.signature(function).parameters) - {"deps"}
        if "model" in config:
            accepted.add("model")
        replay = {key: value for key, value in replay.items() if key in accepted}
        _validate_replay_runtime(uses_detector, replay)
        native = deepcopy(replay.get("ultralytics", requested_native))
        if remote_native and native:
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


def _execute_direct(name: str, config: DictConfig, function: Callable[..., Any]) -> None:
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

                selected = (
                    ModelConfig.model_validate(
                        OmegaConf.to_container(effective.model, resolve=True)
                    )
                    if "model" in effective
                    else ModelConfig()
                )
                dependencies = (
                    build_dependencies()
                    if selected.backend == "ultralytics"
                    else build_dependencies(selected)
                )

            with open_dict(effective):
                effective.pop("model", None)
                if selected.backend != "ultralytics" and name != "export":
                    effective.ultralytics = selected.train.model_dump(mode="json") | {
                        "model": selected.preset,
                    }
                    effective.ultralytics_predict = selected.predict.model_dump(mode="json")
                    if "dataset_format" in effective:
                        effective.dataset_format = "coco"

            # Supply concrete capabilities outside the public Hydra configuration.
            bound = partial(function, deps=dependencies)
            zen(bound, exclude="deps")(effective)
        else:
            zen(function)(effective)


def launch(name: str, function: Callable[..., Any]) -> None:
    """Compose and execute within one owned runtime lifetime."""
    with runtime_environment() as arena, capture_output(arena / "logs"):
        # Watchdogs inherit the captured descriptors, including native diagnostics.
        trace_command(name)(_launch)(name, function)


def _launch(name: str, function: Callable[..., Any]) -> None:
    with trace_operation("configuration.startup", context={"stage": name}):
        initialize_filesystem()
        store.add_to_hydra_store(overwrite_ok=True)
        validate_launch_arguments(name)

    multirun_tag: str | None = None

    @hydra.main(config_name=name, config_path=None, version_base="1.3")
    def execute(config: DictConfig) -> None:
        nonlocal multirun_tag
        if HydraConfig.initialized() and HydraConfig.get().mode == RunMode.MULTIRUN:
            if multirun_tag is None:
                multirun_tag = new_multirun_tag()
            tag_multirun_job(config, multirun_tag)
        execute_owned(name, config, function)

    execute()
