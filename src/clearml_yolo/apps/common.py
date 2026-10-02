"""The shared CLI ownership boundary; stage entrypoints remain independent."""

import inspect
from collections.abc import Callable
from typing import Any

import hydra
from hydra_zen import instantiate, store, zen
from omegaconf import DictConfig, OmegaConf, open_dict

# Populate the shared ConfigStore in fresh CLI processes before Hydra composes examples.
import clearml_yolo.configs  # noqa: F401
from clearml_yolo.apps.config_resolution import resolve_config_file
from clearml_yolo.clearml_session import (
    invocation,
    replay_configuration,
    task_identity,
)
from clearml_yolo.filesystem import runs_root, write_path
from clearml_yolo.native_config import stage_settings
from clearml_yolo.native_runtime import native_runtime
from clearml_yolo.run_identity import task_run_dir


def validate_wrapper_keys(config: DictConfig, function: Callable[..., Any]) -> None:
    """Validate the command schema, including keys introduced with Hydra's + syntax."""
    accepted = set(inspect.signature(function).parameters)
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unsupported wrapper settings: {sorted(unknown)}")
    for group in ("ultralytics", "ultralytics_predict"):
        if group in config:
            stage_settings(dict(config[group]), "train" if group == "ultralytics" else "predict")
    if "inference" in config:
        unknown = set(config.inference) - {"reuse_existing", "image_name"}
        if unknown:
            raise ValueError(f"Unsupported inference settings: {sorted(unknown)}")


def launch(name: str, function: Callable[..., Any]) -> None:
    """Compose first, then execute every enabled stage under one task owner."""
    store.add_to_hydra_store(overwrite_ok=True)

    @hydra.main(config_name=name, config_path=None, version_base="1.3")
    def execute(config: DictConfig) -> None:
        from hydra.core.hydra_config import HydraConfig

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
            accepted = set(inspect.signature(function).parameters)
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
            # Derive paths only after the owner exists; remote task names may differ.
            with open_dict(config):
                if "output_dir" in config and config.output_dir is None:
                    config.output_dir = str(task_run_dir(runs_root(), *task_identity(task)) / name)
                if "output" in config and config.output is None:
                    config.output = str(
                        task_run_dir(runs_root(), *task_identity(task)) / f"{name}.csv"
                    )
            zen(function)(config)

    execute()
