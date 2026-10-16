"""Compose immutable pipeline submissions without starting a task or native runtime."""

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Sequence
from copy import deepcopy
from importlib.metadata import distributions, version
from pathlib import Path
from typing import Any
from uuid import uuid4

from hydra import initialize, initialize_config_dir
from hydra.core.hydra_config import HydraConfig
from hydra_zen import store
from omegaconf import DictConfig, OmegaConf, open_dict

import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - register shared ConfigStore once
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.application.use_cases.pipeline import run_pipeline
from clearml_yolo.core.queue import JobSnapshot, ResourceRequest
from clearml_yolo.entrypoints.hydra.sweeps import (
    compose_jobs,
    new_multirun_tag,
    tag_multirun_job,
    task_overrides,
)
from clearml_yolo.entrypoints.hydra.validation import (
    reject_saved_legacy_controls,
    validate_hydra_destinations,
    validate_pipeline_configuration,
    validate_project_destinations,
    validate_wrapper_keys,
)

_DEVICE_PATHS = (
    "ultralytics.device",
    "ultralytics_predict.device",
    "model.train.device",
    "model.predict.device",
    "comparison.device",
    "export.device",
)


def package_identity() -> str:
    """Hash actual installed/editable code, so equal versions cannot mask changed code."""
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256(version("clearml-yolo").encode())
    digest.update(sys.version.encode())
    environment = sorted((item.metadata["Name"], item.version) for item in distributions())
    digest.update(json.dumps(environment).encode())
    for source in sorted(root.rglob("*.py")):
        digest.update(source.relative_to(root).as_posix().encode())
        digest.update(source.read_bytes())
    return digest.hexdigest()


def validate_snapshot(snapshot: JobSnapshot) -> None:
    if snapshot.package_version != version("clearml-yolo"):
        raise ValueError("Queued package version changed; resubmit with the current installation")
    if snapshot.package_identity != package_identity():
        raise ValueError("Queued package identity changed; resubmit with the current installation")
    if Path(snapshot.interpreter).absolute() != Path(sys.executable).absolute():
        raise ValueError("Queued interpreter changed; run the worker in the submitting environment")
    if not Path(snapshot.project_root).is_dir() or not Path(snapshot.cwd).is_dir():
        raise ValueError("Queued project or working directory is no longer available")
    if snapshot.command != "pipeline":
        raise ValueError("This queue protocol executes pipeline snapshots only")


def _is_cpu(value: object) -> bool:
    return isinstance(value, str) and value.lower() == "cpu"


def bind_devices(config: DictConfig, count: int) -> DictConfig:
    """Bind every enabled GPU phase while preserving explicit CPU and native settings."""
    if count < 1:
        raise ValueError("A queue allocation must contain at least one GPU")
    result = deepcopy(config)
    backend = OmegaConf.select(result, "model.backend", default="ultralytics")
    paths = (
        ("ultralytics.device", "ultralytics_predict.device")
        if backend == "ultralytics"
        else ("model.train.device", "model.predict.device")
    )
    with open_dict(result):
        for path in (*paths, "comparison.device", "export.device"):
            parent = path.rsplit(".", 1)[0]
            if OmegaConf.select(result, parent) is None:
                continue
            if not _is_cpu(OmegaConf.select(result, path)):
                devices = list(range(count)) if path == paths[0] else [0]
                OmegaConf.update(result, path, devices)
    return result


def _arguments(arguments: Sequence[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(prog="cy-queue submit --", add_help=False)
    parser.add_argument("-m", "--multirun", action="store_true")
    parser.add_argument("--config-dir", "--config-path", dest="config_dir")
    parser.add_argument("--config-name", default="pipeline")
    options, overrides = parser.parse_known_args(arguments)
    if any("=" not in value or value.startswith("--") for value in overrides):
        raise ValueError("After --, use Hydra overrides and optional -m/--config-dir/--config-name")
    for value in overrides:
        key = value.split("=", 1)[0].lstrip("+~")
        if key.split(".", 1)[0] in {"queue", "autogpu", "auto_gpu"} or key == "hydra/launcher":
            raise ValueError(
                "Legacy queue/autogpu controls are removed; use cy-queue allocation options"
            )
    return options, overrides


def _validate_devices(config: DictConfig, overrides: list[str]) -> None:
    explicit = {value.split("=", 1)[0].lstrip("+") for value in overrides}
    for path in _DEVICE_PATHS:
        value = OmegaConf.select(config, path)
        if _is_cpu(value) or value is None:
            continue
        anonymous = value in ("cuda", -1, [-1])
        if path in explicit or not anonymous:
            raise ValueError(
                f"{path} conflicts with the queue allocation; use cy-queue --devices or --gpus, "
                "and remove native GPU device overrides (explicit CPU phases are supported)"
            )


def _resolved(
    config: DictConfig,
    index: int,
    project_root: Path,
    *,
    multirun: bool,
    multirun_tag: str | None,
) -> dict[str, Any]:
    previous = HydraConfig.instance().cfg
    try:
        with open_dict(config):
            config.hydra.job.num = index
            config.hydra.job.id = str(index)
            # Every queued job has its own Hydra output even when submitted in one sweep.
            raw_run = OmegaConf.to_container(
                config.hydra.sweep if multirun else config.hydra.run, resolve=False
            )
            if "cy_run_token" in str(raw_run):
                config.hydra.run.dir = str(project_root / "outputs" / f"queue-{uuid4().hex}")
            elif multirun:
                config.hydra.run.dir = str(Path(config.hydra.sweep.dir) / config.hydra.sweep.subdir)
            config.hydra.runtime.output_dir = config.hydra.run.dir
        HydraConfig.instance().set_config(config)
        if multirun_tag is not None:
            # Explicit tags may reference hydra:job.num or another job-local value.
            tag_multirun_job(config, multirun_tag)
        validate_hydra_destinations(config)
        protected = {
            "CUDA_VISIBLE_DEVICES",
            "CY_HOME",
            "CY_MODEL_PROCESS_OWNER",
            "CY_DIRECT_MODEL_PROCESS_OWNER",
            "CY_PROGRESS_FILE",
            "PYTHONUNBUFFERED",
        }
        if protected.intersection(config.hydra.job.env_set):
            raise ValueError("Hydra environment overrides conflict with queue allocation ownership")
        hydra_settings = {
            "run": {"dir": str(config.hydra.run.dir)},
            "job": {
                "chdir": config.hydra.job.chdir,
                "env_set": OmegaConf.to_container(config.hydra.job.env_set, resolve=True),
            },
            "output_subdir": config.hydra.output_subdir,
            "job_logging": OmegaConf.to_container(config.hydra.job_logging, resolve=True),
            "hydra_logging": OmegaConf.to_container(config.hydra.hydra_logging, resolve=True),
        }
        write_path(hydra_settings["run"]["dir"])
        application = deepcopy(config)
        with open_dict(application):
            del application["hydra"]
        validate_wrapper_keys(application, run_pipeline)
        validate_project_destinations(application)
        validate_pipeline_configuration(application)
        values = OmegaConf.to_container(application, resolve=True, throw_on_missing=True)
        if not isinstance(values, dict):
            raise TypeError("Pipeline configuration must be a mapping")
        return {str(key): value for key, value in values.items()} | {"hydra": hydra_settings}
    finally:
        HydraConfig.instance().cfg = previous


def compose_snapshots(
    arguments: Sequence[str], request: ResourceRequest, *, project_root: Path
) -> tuple[JobSnapshot, ...]:
    """Expand and validate the entire batch before a storage adapter receives any job."""
    options, overrides = _arguments(arguments)
    if options.config_dir:
        reject_saved_legacy_controls(Path(options.config_dir).resolve(), options.config_name)
    store.add_to_hydra_store(overwrite_ok=True)
    context = (
        initialize_config_dir(
            config_dir=str(Path(options.config_dir).resolve()), version_base="1.3"
        )
        if options.config_dir
        else initialize(config_path=None, version_base="1.3")
    )
    identity = package_identity()
    snapshots: list[JobSnapshot] = []
    with context:
        multirun, jobs = compose_jobs(options.config_name, overrides, multirun=options.multirun)
        multirun_tag = new_multirun_tag() if multirun else None
        for index, config in enumerate(jobs):
            _validate_devices(config, task_overrides(config))
            values = _resolved(
                config, index, project_root, multirun=multirun, multirun_tag=multirun_tag
            )
            clearml_values = values.get("clearml")
            task_name = (
                clearml_values.get("task_name") if isinstance(clearml_values, dict) else None
            )
            snapshots.append(
                JobSnapshot(
                    command="pipeline",
                    label=task_name if isinstance(task_name, str) and task_name else "Pipeline",
                    config_json=json.dumps(values, allow_nan=False),
                    project_root=str(project_root.resolve()),
                    cwd=str(Path.cwd()),
                    interpreter=str(Path(sys.executable).absolute()),
                    package_version=version("clearml-yolo"),
                    package_identity=identity,
                    request=request,
                )
            )
    return tuple(snapshots)


def write_execution_config(snapshot: JobSnapshot, count: int, directory: Path) -> Path:
    validate_snapshot(snapshot)
    os.environ["CY_HOME"] = snapshot.project_root
    config = bind_devices(OmegaConf.create(json.loads(snapshot.config_json)), count)
    target = write_path(directory / "queued.yaml")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(OmegaConf.to_yaml(config, resolve=True))
    return target
