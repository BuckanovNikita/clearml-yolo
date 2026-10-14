"""The shared CLI ownership boundary; stage entrypoints remain independent."""

import inspect
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
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
        detector_runtime() if uses_detector else native_runtime(),
        invocation(
            instantiate(config.clearml),
            name,
            config_resolver=lambda document: resolve_config_file(document, config),
        ) as task,
        _gpu_cleanup(True),
    ):
        native = dict(inputs.pop("ultralytics", {}))
        replay = replay_configuration(task, inputs)
        reject_legacy_controls(replay)
        # Run also contains result provenance; only command inputs are executable.
        accepted = set(inspect.signature(function).parameters) - {"deps"}
        if "model" in config:
            accepted.add("model")
        replay = {key: value for key, value in replay.items() if key in accepted}
        _validate_replay_runtime(uses_detector, replay)
        if (
            not uses_detector
            and native
            and not task.running_locally()
            and name in {"pipeline", "train"}
        ):
            # General stores the previous trainer's effective output route. A clone
            # must derive its own route, retaining only current explicit requests.
            # Detector General is observed evidence; its executable settings live
            # under run.model and must never overwrite the inactive YOLO group.
            routing = {key: native[key] for key in ("project", "name", "save_dir") if key in native}
            native = dict(task.connect(native, name="General", ignore_remote_overrides=False))
            for key in ("project", "name", "save_dir"):
                native.pop(key, None)
            native.update(routing)
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
        with native_descendant_scope():
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
