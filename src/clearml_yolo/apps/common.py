"""The shared CLI ownership boundary; stage entrypoints remain independent."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import hydra
from hydra.core.hydra_config import HydraConfig
from hydra_zen import instantiate, store, zen
from omegaconf import DictConfig, OmegaConf, open_dict

from clearml_yolo.clearml_session import (
    connect_config_file,
    invocation,
    sanitize_configuration,
    upload_artifact,
)
from clearml_yolo.configs import NATIVE_BLOCKS, overlay_ultralytics_files
from clearml_yolo.native_runtime import native_runtime


def _sources(config: DictConfig, name: str, task: Any) -> None:
    for parent in NATIVE_BLOCKS.get(name, []):
        node = OmegaConf.select(config, parent) if parent else config
        if node.get("cfg"):
            effective = connect_config_file(task, f"source_{parent or name}_native", Path(node.cfg))
            with open_dict(node):
                node.cfg = str(effective)
    hydra_config = HydraConfig.get()
    selected = [str(hydra_config.job.config_name)]
    selected.extend(
        f"{group.split('@')[0]}/{choice}"
        for group, choice in hydra_config.runtime.choices.items()
        if choice is not None and not group.startswith("hydra/")
    )
    for index, source in enumerate(hydra_config.runtime.config_sources):
        if source.schema == "file":
            folder = Path(source.path)
            for selected_name in selected:
                path = folder / f"{selected_name}.yaml"
                if path.is_file():
                    connect_config_file(
                        task,
                        f"source_hydra_{index}_{selected_name}",
                        path,
                        allow_remote_override=False,
                    )


def validate_wrapper_keys(config: DictConfig, function: Callable[..., Any]) -> None:
    """Hydra's + syntax must not turn removed wrapper settings into ignored keys."""
    accepted = {*inspect.signature(function).parameters, "cfg"}
    unknown = set(config) - accepted
    if unknown:
        raise ValueError(f"Unsupported wrapper settings: {sorted(unknown)}")


def launch(name: str, function: Callable[..., Any]) -> None:
    """Compose first, then execute every enabled stage under one task owner."""
    store.add_to_hydra_store(overwrite_ok=True)

    @hydra.main(config_name=name, config_path=None, version_base="1.3")
    def execute(config: DictConfig) -> None:
        validate_wrapper_keys(config, function)
        resolved = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
        # Initialize native imports before ClearML starts background package detection;
        # concurrent torch submodule discovery can observe a partially loaded package.
        with (
            native_runtime(),
            invocation(instantiate(config.clearml), name, resolved) as task,
        ):
            _sources(config, name, task)
            overlay_ultralytics_files(name)(config)
            # Standalone output defaults use Hydra's unique invocation directory.
            with open_dict(config):
                if "output_dir" in config and config.output_dir is None:
                    config.output_dir = str(Path(HydraConfig.get().runtime.output_dir) / name)
                if "output" in config and config.output is None:
                    config.output = str(Path(HydraConfig.get().runtime.output_dir) / f"{name}.csv")
            upload_artifact(
                task,
                "effective_configuration",
                sanitize_configuration(OmegaConf.to_container(config, resolve=True)),
            )
            zen(function)(config)

    execute()
