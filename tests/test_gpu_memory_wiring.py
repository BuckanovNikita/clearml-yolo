"""The launch memory policy reaches direct waiting, queued admission and replay."""

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import hydra
import pytest
from hydra_zen import store
from omegaconf import OmegaConf, open_dict

from clearml_yolo.adapters.runtime.gpu_resources import GPUDevice, GPUInventory
from clearml_yolo.entrypoints.hydra import common
from clearml_yolo.entrypoints.hydra.execution import ModelJob


@pytest.fixture
def memory_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expose a 3 GiB device before an idle device without contacting NVML."""
    monkeypatch.setattr(GPUInventory, "visible", lambda self: ("GPU-loaded", "GPU-idle"))

    def snapshot(self: GPUInventory) -> tuple[GPUDevice, ...]:
        return (
            GPUDevice("GPU-loaded", self.max_used_memory_gib <= 3),
            GPUDevice("GPU-idle", False),
        )

    monkeypatch.setattr(GPUInventory, "snapshot", snapshot)


@pytest.mark.parametrize(("limit", "selected"), [(None, (1,)), (4.0, (0,))])
def test_direct_selection_uses_default_or_project_memory_limit(
    memory_inventory: None, limit: float | None, selected: tuple[int, ...]
) -> None:
    controls: dict[str, Any] = {"enabled": True}
    if limit is not None:
        controls["max_used_memory_gib"] = limit
    assert (
        common._selected_devices(
            "predict",
            {"ultralytics_predict": {"device": -1}, "autogpu": controls},
            automatic=True,
        )
        == selected
    )


@pytest.mark.parametrize("automatic", [True, False])
@pytest.mark.parametrize(("limit", "selected"), [(None, "GPU-idle"), (4.0, "GPU-loaded")])
def test_queued_selection_uses_project_limit_in_automatic_and_exact_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    memory_inventory: None,
    automatic: bool,
    limit: float | None,
    selected: str,
) -> None:
    from hydra_queue_fixture import record_exact_job
    from test_hydra_queue_launcher import _job_config

    store.add_to_hydra_store(overwrite_ok=True)
    monkeypatch.setenv("CY_GPU_QUEUE_ROOT", str(tmp_path / "queue"))
    config = _job_config(tmp_path, index=0, value="memory", delay=0)
    with open_dict(config):
        config.ultralytics = {"device": -1 if automatic else 0}
        config.ultralytics_predict = {"device": -1 if automatic else 0}
        config.queue = {"enabled": True}
        config.autogpu = {"enabled": automatic}
        if limit is not None:
            config.autogpu.max_used_memory_gib = limit
    job = ModelJob("pipeline", record_exact_job, config)
    try:
        job.prepare()
        assert job.ticket is not None
        # Exact selection waits for its written identity rather than substituting idle GPU.
        assert job.ticket.try_acquire() == ((selected,) if automatic or limit else None)
    finally:
        job.close()


@pytest.mark.parametrize(("automatic", "device"), [(True, "cpu"), (False, -1)])
def test_direct_cpu_and_disabled_controls_do_not_construct_inventory(
    monkeypatch: pytest.MonkeyPatch, automatic: bool, device: object
) -> None:
    def forbidden_inventory(**kwargs: Any) -> GPUInventory:
        pytest.fail("GPU inventory constructed for a bypassed request")

    monkeypatch.setattr(common, "GPUInventory", forbidden_inventory)
    assert (
        common._selected_devices(
            "predict", {"ultralytics_predict": {"device": device}}, automatic=automatic
        )
        == ()
    )


@pytest.mark.parametrize(("queued", "device"), [(True, "cpu"), (False, -1)])
def test_queued_cpu_and_disabled_controls_do_not_construct_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, queued: bool, device: object
) -> None:
    from clearml_yolo.entrypoints.hydra import execution
    from hydra_queue_fixture import record_exact_job
    from test_hydra_queue_launcher import _job_config

    def forbidden_inventory(**kwargs: Any) -> GPUInventory:
        pytest.fail("GPU inventory constructed for a bypassed queued request")

    store.add_to_hydra_store(overwrite_ok=True)
    monkeypatch.setattr(execution, "GPUInventory", forbidden_inventory)
    config = _job_config(tmp_path, index=0, value="bypass", delay=0)
    with open_dict(config):
        config.ultralytics = {"device": device}
        config.ultralytics_predict = {"device": device}
        config.queue = {"enabled": queued}
        config.autogpu = {"enabled": queued, "max_used_memory_gib": 4.0}
    job = ModelJob("pipeline", record_exact_job, config)
    try:
        job.prepare()
        assert job.ticket is None
        assert job.queue is None
    finally:
        job.close()


def test_queue_freezes_policy_from_job_environment_before_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, memory_inventory: None
) -> None:
    from hydra_queue_fixture import record_exact_job
    from test_hydra_queue_launcher import _job_config

    store.add_to_hydra_store(overwrite_ok=True)
    monkeypatch.setenv("CY_GPU_QUEUE_ROOT", str(tmp_path / "queue"))
    monkeypatch.setenv("CY_TEST_GPU_LIMIT", "2")
    config = _job_config(tmp_path, index=0, value="job-environment", delay=0)
    with open_dict(config):
        config.ultralytics = {"device": -1}
        config.ultralytics_predict = {"device": -1}
        config.queue = {"enabled": True}
        config.autogpu = {
            "enabled": True,
            "max_used_memory_gib": "${oc.decode:${oc.env:CY_TEST_GPU_LIMIT}}",
        }
        config.hydra.job.env_set.CY_TEST_GPU_LIMIT = "4"
    job = ModelJob("pipeline", record_exact_job, config)
    try:
        job.prepare()
        assert job.ticket is not None
        assert job.ticket.try_acquire() == ("GPU-loaded",)
        assert OmegaConf.to_container(job.config.autogpu, resolve=False) == {
            "enabled": True,
            "force": False,
            "max_used_memory_gib": 4.0,
        }
        monkeypatch.setenv("CY_TEST_GPU_LIMIT", "0.5")
        assert config.autogpu.max_used_memory_gib == 4.0
    finally:
        job.close()


@pytest.mark.parametrize("route", ["controls", "single", "sweep"])
def test_queue_routing_does_not_resolve_policy_before_job_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, memory_inventory: None, route: str
) -> None:
    from hydra.types import HydraContext, TaskFunction

    from clearml_yolo.adapters.runtime.gpu_scheduling import execution_controls
    from clearml_yolo.entrypoints.hydra import execution
    from hydra_plugins.cy_queue.launcher import QueueLauncher
    from hydra_queue_fixture import record_exact_job
    from test_hydra_queue_launcher import _job_config

    store.add_to_hydra_store(overwrite_ok=True)
    monkeypatch.setenv("CY_GPU_QUEUE_ROOT", str(tmp_path / "queue"))
    monkeypatch.delenv("CY_TEST_GPU_LIMIT", raising=False)
    config = _job_config(tmp_path, index=0, value="routing-environment", delay=0)
    with open_dict(config):
        config.ultralytics = {"device": -1}
        config.ultralytics_predict = {"device": -1}
        config.queue = {"enabled": True}
        config.autogpu = {
            "enabled": True,
            "max_used_memory_gib": "${oc.decode:${oc.env:CY_TEST_GPU_LIMIT}}",
        }
        config.hydra.job.env_set.CY_TEST_GPU_LIMIT = "4"
    job = ModelJob("pipeline", record_exact_job, config)

    def prepare(jobs: list[ModelJob]) -> list[Any]:
        assert len(jobs) == 1
        job.config = jobs[0].config
        job.prepare()
        return []

    try:
        if route == "controls":
            assert execution_controls(config) == (True, True)
            job.prepare()
        elif route == "single":

            def main(**kwargs: Any) -> Callable[..., Any]:
                return lambda function: lambda: function(config)

            monkeypatch.setattr(hydra, "main", main)
            monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
            monkeypatch.setattr(execution, "configure_entrypoint", lambda *args: None)
            monkeypatch.setattr(
                execution,
                "schedule_single",
                lambda command, function, cfg: prepare([ModelJob(command, function, cfg)]),
            )
            common._launch("pipeline", record_exact_job)
        else:
            launcher = QueueLauncher()
            launcher.setup(
                hydra_context=cast(
                    HydraContext,
                    SimpleNamespace(
                        config_loader=SimpleNamespace(
                            load_sweep_config=lambda base, overrides: config
                        )
                    ),
                ),
                task_function=cast(TaskFunction, record_exact_job),
                config=config,
            )
            launcher._full_sweep_validated = True
            monkeypatch.setattr(execution, "_ENTRYPOINT", ("pipeline", record_exact_job))
            monkeypatch.setattr(execution, "run_jobs", prepare)
            assert launcher.launch([[]], initial_job_idx=0) == []
        assert job.ticket is not None
        assert job.ticket.try_acquire() == ("GPU-loaded",)
        assert OmegaConf.to_container(job.config.autogpu, resolve=False) == {
            "enabled": True,
            "force": False,
            "max_used_memory_gib": 4.0,
        }
    finally:
        job.close()


def test_replay_cannot_change_memory_limit_before_native_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def runtime() -> Iterator[None]:
        yield

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield SimpleNamespace(running_locally=lambda: True)

    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    monkeypatch.setattr(
        common,
        "replay_configuration",
        lambda task, values: values | {"autogpu": {"enabled": True, "max_used_memory_gib": 4.0}},
    )

    def workflow(ultralytics_predict: dict[str, Any], clearml: Any) -> None:
        pytest.fail("Native workflow executed with changed admission policy")

    config = OmegaConf.create(
        {
            "ultralytics_predict": {"device": "cpu"},
            "clearml": {},
            "queue": {"enabled": False},
            "autogpu": {"enabled": True, "max_used_memory_gib": 2.0},
        }
    )
    with pytest.raises(ValueError, match="cannot change launch control autogpu"):
        common.execute_owned("predict", config, workflow)


@pytest.mark.parametrize("limit", [4.0, "${hydra:job.num}"])
def test_worker_contraction_preserves_project_memory_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    memory_inventory: None,
    limit: float | str,
) -> None:
    from hydra.core.hydra_config import HydraConfig

    from clearml_yolo.adapters.clearml import session
    from clearml_yolo.adapters.integrations import native_runtime
    from clearml_yolo.adapters.runtime import gpu_runtime
    from clearml_yolo.entrypoints.hydra import worker
    from hydra_queue_fixture import record_exact_job
    from test_hydra_queue_launcher import _job_config

    store.add_to_hydra_store(overwrite_ok=True)
    monkeypatch.setenv("CY_GPU_QUEUE_ROOT", str(tmp_path / "queue"))
    monkeypatch.setattr(GPUInventory, "visible", lambda self: ("GPU-idle", "GPU-loaded"))
    config = _job_config(tmp_path, index=0, value="worker-memory", delay=0)
    with open_dict(config):
        config.ultralytics = {"device": [-1, -1]}
        config.ultralytics_predict = {"device": -1}
        config.queue = {"enabled": True}
        config.autogpu = {"enabled": True, "max_used_memory_gib": limit}
        config.hydra.job.num = 4
    job = ModelJob("pipeline", record_exact_job, config)
    previous_hydra = HydraConfig.instance().cfg
    retained: list[tuple[str, ...]] = []

    def execute(*args: Any) -> None:
        gpu_runtime.training_finished()
        retained.append(gpu_runtime.assigned_devices())

    monkeypatch.setattr(common, "execute_owned", execute)
    monkeypatch.setattr(native_runtime, "release_training_memory", lambda: None)
    monkeypatch.setattr(session, "active_task", lambda: None)
    monkeypatch.setattr(session, "record_run_configuration", lambda task, values: None)
    try:
        job.prepare()
        assert job.ticket is not None
        assert job.ticket.try_acquire() == ("GPU-idle", "GPU-loaded")
        payload = tmp_path / "payload.yaml"
        OmegaConf.save(
            OmegaConf.create(
                {
                    "command": "pipeline",
                    "module": "hydra_queue_fixture",
                    "function": "record_exact_job",
                    "sys_path": sys.path,
                    "config": OmegaConf.to_container(config, resolve=False),
                    "queue_root": str(tmp_path / "queue"),
                    "ticket": job.ticket.id,
                    "sweep": False,
                }
            ),
            payload,
        )
        monkeypatch.setattr(sys, "argv", ["worker", str(payload)])
        HydraConfig.instance().cfg = None
        worker._run()
        assert retained == [("GPU-idle",)]
        assert job.ticket.devices == ("GPU-idle",)
    finally:
        HydraConfig.instance().cfg = previous_hydra
        job.close()
