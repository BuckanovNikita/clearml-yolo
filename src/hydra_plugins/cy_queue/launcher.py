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
        self.task_function: TaskFunction | None = None
        self._full_sweep_validated = False

    @override
    def setup(
        self, *, hydra_context: HydraContext, task_function: TaskFunction, config: DictConfig
    ) -> None:
        self.hydra_context = hydra_context
        self.config = config
        self.task_function = task_function
        self._full_sweep_validated = False

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
        if not self._full_sweep_validated:
            self._validate_full_sweep()
            self._full_sweep_validated = True
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
        from clearml_yolo.adapters.runtime.gpu_scheduling import execution_controls

        modes = {execution_controls(job.config)[0] for job in jobs}
        if len(modes) > 1:
            raise ValueError("Mixed queue modes in one sweep are unsupported")
        if modes == {False}:
            from hydra._internal.core_plugins.basic_launcher import BasicLauncher

            if self.task_function is None:
                raise RuntimeError("Queue launcher task function is missing")
            launcher = BasicLauncher()
            launcher.setup(
                hydra_context=self.hydra_context,
                task_function=self.task_function,
                config=self.config,
            )
            return launcher.launch(job_overrides, initial_job_idx)
        return run_jobs(jobs)

    def _validate_full_sweep(self) -> None:
        """Inspect every BasicSweeper combination before its first batch reserves capacity."""
        from hydra._internal.core_plugins.basic_sweeper import BasicSweeper
        from hydra.core.override_parser.overrides_parser import OverridesParser

        from clearml_yolo.adapters.runtime.gpu_scheduling import execution_controls

        if self.config is None or self.hydra_context is None:
            raise RuntimeError("Queue launcher has not been set up")
        params = self.config.hydra.sweeper.get("params") or {}
        arguments = [f"{key}={value}" for key, value in params.items()]
        arguments.extend(str(value) for value in self.config.hydra.overrides.task)
        parser = OverridesParser.create(config_loader=self.hydra_context.config_loader)
        overrides = parser.parse_overrides(arguments)
        if not any(override.is_sweep_override() for override in overrides):
            return
        (all_jobs,) = BasicSweeper.split_arguments(overrides, max_batch_size=None)
        modes: set[bool] = set()
        previous = HydraConfig.instance().cfg
        try:
            for overrides_for_job in all_jobs:
                config = self.hydra_context.config_loader.load_sweep_config(
                    self.config, overrides_for_job
                )
                HydraConfig.instance().set_config(config)
                modes.add(execution_controls(config)[0])
                if len(modes) > 1:
                    raise ValueError("Mixed queue modes across the full sweep are unsupported")
        finally:
            HydraConfig.instance().cfg = previous
