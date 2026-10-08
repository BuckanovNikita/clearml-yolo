"""Launch BasicSweeper jobs in isolated processes through the user-wide queue."""

from collections.abc import Sequence
from copy import deepcopy
from typing import override

from hydra.core.hydra_config import HydraConfig
from hydra.core.utils import JobReturn
from hydra.plugins.launcher import Launcher
from hydra.types import HydraContext, TaskFunction
from omegaconf import DictConfig, open_dict, read_write


class QueueLauncher(Launcher):
    def __init__(self) -> None:
        self.config: DictConfig | None = None
        self.hydra_context: HydraContext | None = None

    @override
    def setup(
        self, *, hydra_context: HydraContext, task_function: TaskFunction, config: DictConfig
    ) -> None:
        self.hydra_context = hydra_context
        self.config = config

    @override
    def launch(
        self, job_overrides: Sequence[Sequence[str]], initial_job_idx: int
    ) -> Sequence[JobReturn]:
        from clearml_yolo.entrypoints.hydra.execution import ModelJob, entrypoint, run_jobs

        if self.config is None or self.hydra_context is None:
            raise RuntimeError("Queue launcher has not been set up")
        sweeper = self.config.hydra.sweeper._target_
        if sweeper != "hydra._internal.core_plugins.basic_sweeper.BasicSweeper":
            raise ValueError("The cy_queue launcher supports only Hydra's BasicSweeper")
        command, function = entrypoint()
        jobs: list[ModelJob] = []
        old_hydra = HydraConfig.instance().cfg
        try:
            for index, overrides in enumerate(job_overrides, start=initial_job_idx):
                config = self.hydra_context.config_loader.load_sweep_config(
                    self.config, list(overrides)
                )
                with open_dict(config):
                    config.hydra.job.id = str(index)
                    config.hydra.job.num = index
                HydraConfig.instance().set_config(config)
                # Freeze output identity at composition, rather than after a potentially long wait.
                with read_write(config.hydra.sweep), open_dict(config.hydra.sweep):
                    config.hydra.sweep.dir = str(config.hydra.sweep.dir)
                    config.hydra.sweep.subdir = str(config.hydra.sweep.subdir)
                jobs.append(ModelJob(command, function, deepcopy(config), sweep=True))
        finally:
            HydraConfig.instance().cfg = old_hydra
        return run_jobs(jobs)
