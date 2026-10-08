"""The shared CLI ownership boundary; stage entrypoints remain independent."""

import inspect
from collections.abc import Callable
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
from clearml_yolo.adapters.integrations.native_runtime import native_runtime
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


def execute_owned(name: str, config: DictConfig, function: Callable[..., Any]) -> None:
    """Execute under the sole invocation-owned task, inside an admitted child when queued."""
    from hydra.core.hydra_config import HydraConfig

    initialize_filesystem()
    if HydraConfig.initialized():
        write_path(HydraConfig.get().runtime.output_dir)
    validate_wrapper_keys(config, function)
    resolved = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    # Initialize native imports before ClearML starts background package detection;
    # concurrent torch submodule discovery can observe a partially loaded package.
    with (
        native_runtime(),
        invocation(
            instantiate(config.clearml),
            name,
            config_resolver=lambda document: resolve_config_file(document, config),
        ) as task,
    ):
        if not isinstance(resolved, dict):
            raise TypeError("Resolved command configuration must be a mapping")
        inputs = {str(key): value for key, value in resolved.items()}
        native = dict(inputs.pop("ultralytics", {}))
        replay = replay_configuration(task, inputs)
        # Run also contains result provenance; only command inputs are executable.
        accepted = set(inspect.signature(function).parameters) - {"deps"}
        replay = {key: value for key, value in replay.items() if key in accepted}
        if native and not task.running_locally() and name in {"pipeline", "train"}:
            # General stores the previous trainer's effective output route. A clone
            # must derive its own route, retaining only current explicit requests.
            routing = {
                key: native[key] for key in ("project", "name", "save_dir") if key in native
            }
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
                config.output = str(
                    task_run_dir(runs_root(), *task_identity(task)) / f"{name}.csv"
                )
        _execute_assigned(name, config, function, task)


def _execute_assigned(
    name: str, config: DictConfig, function: Callable[..., Any], task: Any
) -> None:
    from clearml_yolo.adapters.clearml.session import record_run_configuration
    from clearml_yolo.adapters.runtime.gpu_resources import job_request
    from clearml_yolo.adapters.runtime.gpu_runtime import assigned_devices, scheduled
    from clearml_yolo.entrypoints.hydra.execution import effective_configuration

    devices = assigned_devices()
    if scheduled():
        resolved_job = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
        if not isinstance(resolved_job, dict):
            raise TypeError("Command configuration must be a mapping")
        if job_request(name, {str(k): v for k, v in resolved_job.items()}) > len(devices):
            raise ValueError("ClearML replay requires more GPUs than the admitted reservation")
    effective = effective_configuration(config, devices)
    requests = _device_values(config)
    if devices:
        record_run_configuration(task, {
            "gpu_scheduler": {
                "phase": "training" if name in {"pipeline", "train"} else "inference",
                "reserved_uuids": list(devices),
                "requested_devices": requests,
                "effective_devices": _device_values(effective),
            }
        })
    with requested_devices(requests):
        if "deps" in inspect.signature(function).parameters:
            from clearml_yolo.entrypoints.composition import build_dependencies

            # Keep the importable unbound function in worker payloads; only this
            # invocation receives concrete capabilities, never Hydra configuration.
            bound = partial(function, deps=build_dependencies())
            zen(bound, exclude="deps")(effective)
        else:
            zen(function)(effective)


def launch(name: str, function: Callable[..., Any]) -> None:
    """Compose configuration before queuing model work or executing CPU-only stages."""
    from hydra.core.hydra_config import HydraConfig

    from clearml_yolo.entrypoints.hydra.configs import NATIVE_COMMANDS
    from clearml_yolo.entrypoints.hydra.execution import configure_entrypoint, schedule_single

    initialize_filesystem()
    configure_entrypoint(name, function)
    store.add_to_hydra_store(overwrite_ok=True)

    @hydra.main(config_name=name, config_path=None, version_base="1.3")
    def execute(config: DictConfig) -> None:
        if name in NATIVE_COMMANDS and HydraConfig.initialized():
            target = HydraConfig.get().launcher._target_
            if target != "hydra_plugins.cy_queue.launcher.QueueLauncher":
                raise ValueError("Model commands require hydra/launcher=cy_queue")
            schedule_single(name, function, config)
        else:
            execute_owned(name, config, function)

    execute()
