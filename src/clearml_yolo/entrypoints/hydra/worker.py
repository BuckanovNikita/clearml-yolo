"""Private fresh-process execution target for supervised model jobs."""

import importlib
import json
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from typing import cast

from hydra._internal.callbacks import Callbacks
from hydra._internal.config_loader_impl import ConfigLoaderImpl
from hydra._internal.utils import create_config_search_path
from hydra.core.hydra_config import HydraConfig
from hydra.core.utils import JobRuntime, JobStatus, run_job, setup_globals
from hydra.types import HydraContext, TaskFunction
from omegaconf import DictConfig, OmegaConf, open_dict

from clearml_yolo.adapters.runtime.gpu_queue import GPUQueue
from clearml_yolo.adapters.runtime.gpu_runtime import reservation
from clearml_yolo.entrypoints.hydra.common import execute_owned
from clearml_yolo.entrypoints.hydra.execution import interruption, restore_hydra_config


def main() -> None:
    payload = OmegaConf.load(sys.argv[1])
    if not isinstance(payload, DictConfig):
        raise TypeError("Job payload must be a mapping")
    gate = payload.get("start_gate")
    if gate is not None:
        deadline = time.monotonic() + 30
        while not Path(gate).exists():
            if time.monotonic() >= deadline:
                raise RuntimeError("Supervisor did not establish worker process ownership")
            time.sleep(0.05)
    sys.path[:] = list(payload.sys_path)
    function = cast(
        TaskFunction, getattr(importlib.import_module(payload.module), payload.function)
    )
    # Absolute OmegaConf interpolations must resolve from the job, not its transport envelope.
    configuration = OmegaConf.create(OmegaConf.to_container(payload.config, resolve=False))
    if not isinstance(configuration, DictConfig):
        raise TypeError("Job configuration must be a mapping")
    config = restore_hydra_config(configuration)
    setup_globals()
    JobRuntime.instance().set("name", str(payload.command))
    queue = GPUQueue(root=Path(payload.queue_root)) if payload.ticket is not None else None
    ownership = queue.claim_worker(str(payload.ticket)) if queue is not None else nullcontext(None)
    with interruption(), ownership as claim, reservation(claim):
        if claim is not None and "CUDA_VISIBLE_DEVICES" in config.hydra.job.env_set:
            with open_dict(config.hydra.job.env_set):
                config.hydra.job.env_set.CUDA_VISIBLE_DEVICES = ",".join(claim.devices)

        def execute(application: DictConfig) -> None:
            execute_owned(str(payload.command), application, function)

        if payload.sweep:
            context = HydraContext(
                config_loader=ConfigLoaderImpl(create_config_search_path(None)),
                callbacks=Callbacks(config),
            )
            result = run_job(
                task_function=execute, config=config, job_dir_key="hydra.sweep.dir",
                job_subdir_key="hydra.sweep.subdir", hydra_context=context,
            )
            Path(payload.result).write_text(
                json.dumps({"status": result.status.name, "working_dir": result.working_dir}),
                encoding="utf-8",
            )
            if result.status != JobStatus.COMPLETED:
                _ = result.return_value
        else:
            HydraConfig.instance().set_config(config)
            keys = [str(key) for key in config if key != "hydra"]
            application = OmegaConf.masked_copy(config, keys)
            execute(application)


if __name__ == "__main__":
    main()
