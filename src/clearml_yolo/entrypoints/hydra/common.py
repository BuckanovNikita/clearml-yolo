"""The shared CLI ownership boundary; stage entrypoints remain independent."""

import inspect
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import partial
from typing import Any

import hydra
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
    native_runtime,
    release_training_memory,
)
from clearml_yolo.adapters.observability.diagnostics import log_exception
from clearml_yolo.adapters.runtime.gpu_resources import job_request
from clearml_yolo.adapters.runtime.gpu_wait import wait_for_available_gpus
from clearml_yolo.adapters.storage.filesystem import initialize_filesystem, runs_root, write_path
from clearml_yolo.adapters.storage.run_identity import task_run_dir
from clearml_yolo.adapters.yolo.config import requested_devices
from clearml_yolo.entrypoints.hydra.config_resolution import resolve_config_file
from clearml_yolo.entrypoints.hydra.validation import validate_wrapper_keys


def _device_values(config: DictConfig) -> dict[str, Any]:
    result = {}
    for group in ("ultralytics", "ultralytics_predict"):
        if group in config:
            values = OmegaConf.to_container(config[group], resolve=True)
            if not isinstance(values, dict):
                raise TypeError(f"{group} must be a mapping")
            result[group] = values.get("device")
    return result


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
            except Exception as error:
                if primary_error is None:
                    raise
                log_exception("Native GPU memory cleanup failed", error, level="ERROR")


def execute_owned(name: str, config: DictConfig, function: Callable[..., Any]) -> None:
    """Wait for free GPUs, then execute directly under one invocation-owned task."""
    from hydra.core.hydra_config import HydraConfig

    initialize_filesystem()
    if HydraConfig.initialized():
        write_path(HydraConfig.get().runtime.output_dir)
    validate_wrapper_keys(config, function)
    resolved = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    if not isinstance(resolved, dict):
        raise TypeError("Resolved command configuration must be a mapping")
    inputs = {str(key): value for key, value in resolved.items()}
    devices = wait_for_available_gpus(job_request(name, inputs))
    # Initialize native imports before ClearML starts background package detection;
    # concurrent torch submodule discovery can observe a partially loaded package.
    with (
        native_runtime(),
        invocation(
            instantiate(config.clearml),
            name,
            config_resolver=lambda document: resolve_config_file(document, config),
        ) as task,
        _gpu_cleanup(bool(devices)),
    ):
        native = dict(inputs.pop("ultralytics", {}))
        replay = replay_configuration(task, inputs)
        # Run also contains result provenance; only command inputs are executable.
        accepted = set(inspect.signature(function).parameters) - {"deps"}
        replay = {key: value for key, value in replay.items() if key in accepted}
        if native and not task.running_locally() and name in {"pipeline", "train"}:
            # General stores the previous trainer's effective output route. A clone
            # must derive its own route, retaining only current explicit requests.
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
        initialize_naming(task)
        # Derive paths only after the owner exists; remote task names may differ.
        with open_dict(config):
            if "output_dir" in config and config.output_dir is None:
                config.output_dir = str(task_run_dir(runs_root(), *task_identity(task)) / name)
            if "output" in config and config.output is None:
                config.output = str(task_run_dir(runs_root(), *task_identity(task)) / f"{name}.csv")
        _execute_assigned(name, config, function, task, devices)


def _execute_assigned(
    name: str,
    config: DictConfig,
    function: Callable[..., Any],
    task: Any,
    devices: tuple[int, ...],
) -> None:
    from clearml_yolo.adapters.clearml.session import record_run_configuration
    from clearml_yolo.entrypoints.hydra.execution import effective_configuration

    resolved_job = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    if not isinstance(resolved_job, dict):
        raise TypeError("Command configuration must be a mapping")
    if job_request(name, {str(k): v for k, v in resolved_job.items()}) > len(devices):
        raise ValueError("ClearML replay requires more GPUs than the available selection")
    effective = effective_configuration(config, devices)
    requests = _device_values(config)
    if devices:
        record_run_configuration(
            task,
            {
                "gpu_selection": {
                    "selected_devices": list(devices),
                    "requested_devices": requests,
                    "effective_devices": _device_values(effective),
                }
            },
        )
    with requested_devices(requests):
        if "deps" in inspect.signature(function).parameters:
            from clearml_yolo.entrypoints.composition import build_dependencies

            # Supply concrete capabilities outside the public Hydra configuration.
            bound = partial(function, deps=build_dependencies())
            zen(bound, exclude="deps")(effective)
        else:
            zen(function)(effective)


def launch(name: str, function: Callable[..., Any]) -> None:
    """Compose and execute directly, including Hydra's standard sequential multirun."""
    initialize_filesystem()
    store.add_to_hydra_store(overwrite_ok=True)

    @hydra.main(config_name=name, config_path=None, version_base="1.3")
    def execute(config: DictConfig) -> None:
        execute_owned(name, config, function)

    execute()
