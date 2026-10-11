"""The queue launcher preserves Hydra job semantics across fresh worker processes."""

import json
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from hydra import compose, initialize_config_module
from hydra.core.hydra_config import HydraConfig
from hydra.core.utils import JobStatus
from hydra.types import HydraContext, TaskFunction
from hydra_zen import store
from omegaconf import DictConfig, OmegaConf, open_dict

import clearml_yolo.entrypoints.hydra.configs  # noqa: F401
from clearml_yolo.entrypoints.hydra import execution
from clearml_yolo.entrypoints.hydra.execution import ModelJob, run_jobs
from hydra_plugins.cy_queue.launcher import QueueLauncher
from hydra_queue_fixture import record_job


@pytest.fixture(autouse=True)
def registered() -> None:
    store.add_to_hydra_store(overwrite_ok=True)


def _job_config(
    root: Path,
    *,
    index: int,
    value: str,
    fail: bool = False,
    delay: float = 0.3,
) -> DictConfig:
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="predict",
            return_hydra_config=True,
            overrides=["ultralytics_predict.device=cpu", "hydra.job.chdir=true"],
        )
    with open_dict(config):
        for key in [str(key) for key in config if key != "hydra"]:
            del config[key]
        output = root / "outputs" / str(index)
        config.hydra.job.id = str(index)
        config.hydra.job.num = index
        config.hydra.job.name = "queue-fixture"
        config.hydra.job.env_set = {"HYDRA_QUEUE_MARKER": value}
        config.hydra.overrides.task = [f"value={value}"]
        config.hydra.sweep.dir = str(root / "outputs")
        config.hydra.sweep.subdir = str(index)
        config.hydra.callbacks = {
            "fixture": {
                "_target_": "hydra_queue_fixture.RecordingCallback",
                "path": str(root / f"callback-{index}.json"),
            }
        }
        config.ultralytics_predict = {"device": "cpu"}
        config.receipt = str(root / f"receipt-{index}.json")
        config.value = value
        config.delay = delay
        config.fail = fail
    assert output == Path(config.hydra.sweep.dir) / str(config.hydra.sweep.subdir)
    return config


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


class _SweepConfigLoader:
    def __init__(self, root: Path, *, initial_job_idx: int) -> None:
        self.root = root
        self.initial_job_idx = initial_job_idx
        self.calls: list[list[str]] = []

    def load_sweep_config(self, _config: DictConfig, overrides: list[str]) -> DictConfig:
        position = len(self.calls)
        self.calls.append(overrides)
        (override,) = overrides
        key, value = override.split("=", maxsplit=1)
        if key != "value":
            raise ValueError(f"Unsupported test override: {override}")
        index = self.initial_job_idx + position
        config = _job_config(self.root, index=index, value=value)
        with open_dict(config.hydra.sweep):
            config.hydra.sweep.subdir = "${hydra.job.num}"
        return config


def test_cpu_sweep_runs_concurrently_in_fresh_workers_with_hydra_context(
    tmp_path: Path,
) -> None:
    jobs = [
        ModelJob("predict", record_job, _job_config(tmp_path, index=0, value="first"), sweep=True),
        ModelJob("predict", record_job, _job_config(tmp_path, index=1, value="second"), sweep=True),
    ]

    results = run_jobs(jobs)

    assert [result.status for result in results] == [JobStatus.COMPLETED, JobStatus.COMPLETED]
    assert all(job.queue is None and job.ticket is None for job in jobs)
    assert [result.cfg.value for result in results if result.cfg is not None] == ["first", "second"]
    records = [_load(tmp_path / f"receipt-{index}.json") for index in range(2)]
    assert len({record["pid"] for record in records}) == 2
    assert all(record["pid"] != os.getpid() for record in records)
    assert [record["marker"] for record in records] == ["first", "second"]
    assert isinstance(records[0]["started"], float)
    assert isinstance(records[0]["finished"], float)
    assert isinstance(records[1]["started"], float)
    assert isinstance(records[1]["finished"], float)
    assert records[0]["started"] < records[1]["finished"]
    assert records[1]["started"] < records[0]["finished"]

    expected_directories = [str(tmp_path / "outputs" / str(index)) for index in range(2)]
    assert [record["cwd"] for record in records] == expected_directories
    assert [result.working_dir for result in results] == expected_directories
    for index, expected in enumerate(expected_directories):
        callbacks = json.loads((tmp_path / f"callback-{index}.json").read_text())
        assert callbacks == [
            {
                "event": "start",
                "pid": records[index]["pid"],
                "cwd": expected,
                "marker": ("first", "second")[index],
                "status": None,
            },
            {
                "event": "end",
                "pid": records[index]["pid"],
                "cwd": expected,
                # Hydra restores env_set after the task and before on_job_end.
                "marker": None,
                "status": "COMPLETED",
            },
        ]


def test_cpu_sweep_returns_ordered_failure_without_cancelling_siblings(tmp_path: Path) -> None:
    jobs = [
        ModelJob(
            "predict",
            record_job,
            _job_config(tmp_path, index=4, value="failed", fail=True, delay=0.1),
            sweep=True,
        ),
        ModelJob(
            "predict",
            record_job,
            _job_config(tmp_path, index=5, value="completed", delay=0.2),
            sweep=True,
        ),
    ]

    results = run_jobs(jobs)

    assert all(job.queue is None and job.ticket is None for job in jobs)
    assert [result.cfg.value for result in results if result.cfg is not None] == [
        "failed",
        "completed",
    ]
    assert [result.status for result in results] == [JobStatus.FAILED, JobStatus.COMPLETED]
    with pytest.raises(RuntimeError, match="process exited with status"):
        _ = results[0].return_value
    assert results[1].return_value is None
    assert _load(tmp_path / "receipt-4.json")["value"] == "failed"
    assert _load(tmp_path / "receipt-5.json")["value"] == "completed"


def test_queue_launcher_composes_and_submits_ordered_jobs_from_initial_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial_job_idx = 7
    loader = _SweepConfigLoader(tmp_path, initial_job_idx=initial_job_idx)
    context = cast(HydraContext, SimpleNamespace(config_loader=loader))
    base_config = _job_config(tmp_path, index=99, value="base")
    launcher = QueueLauncher()
    launcher.setup(
        hydra_context=context,
        task_function=cast(TaskFunction, record_job),
        config=base_config,
    )
    monkeypatch.setattr(execution, "_ENTRYPOINT", ("predict", record_job))

    hydra = HydraConfig.instance()
    previous_hydra = hydra.cfg
    sentinel = _job_config(tmp_path, index=100, value="sentinel")
    hydra.set_config(sentinel)
    expected_hydra = hydra.cfg
    try:
        results = launcher.launch([["value=first"], ["value=second"]], initial_job_idx)

        assert hydra.cfg is expected_hydra
    finally:
        hydra.cfg = previous_hydra

    assert loader.calls == [["value=first"], ["value=second"]]
    assert [result.status for result in results] == [JobStatus.COMPLETED, JobStatus.COMPLETED]
    assert [result.cfg.value for result in results if result.cfg is not None] == [
        "first",
        "second",
    ]
    hydra_configs: list[DictConfig] = []
    for result in results:
        assert result.hydra_cfg is not None
        hydra_configs.append(result.hydra_cfg)
    assert [config.hydra.job.num for config in hydra_configs] == [7, 8]
    assert [result.working_dir for result in results] == [
        str(tmp_path / "outputs" / "7"),
        str(tmp_path / "outputs" / "8"),
    ]
    assert [OmegaConf.to_container(config.hydra.overrides.task) for config in hydra_configs] == [
        ["value=first"],
        ["value=second"],
    ]


def test_sweep_task_can_resolve_its_runtime_output_directory(tmp_path: Path) -> None:
    config = _job_config(tmp_path, index=2, value="runtime-path")
    with open_dict(config):
        config.receipt = "${hydra:runtime.output_dir}/receipt.json"
    result = run_jobs([ModelJob("predict", record_job, config, sweep=True)])[0]
    assert result.status == JobStatus.COMPLETED
    assert _load(tmp_path / "outputs" / "2" / "receipt.json")["value"] == "runtime-path"


def test_queue_disabled_launcher_delegates_to_basic_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader = _SweepConfigLoader(tmp_path, initial_job_idx=0)
    original = loader.load_sweep_config

    def disabled(config: DictConfig, overrides: list[str]) -> DictConfig:
        job = original(config, overrides)
        with open_dict(job):
            job.queue = {"enabled": False}
        return job

    monkeypatch.setattr(loader, "load_sweep_config", disabled)
    calls: list[object] = []
    launcher = QueueLauncher()
    launcher.setup(
        hydra_context=cast(HydraContext, SimpleNamespace(config_loader=loader)),
        task_function=cast(TaskFunction, record_job),
        config=_job_config(tmp_path, index=0, value="base"),
    )
    monkeypatch.setattr(execution, "_ENTRYPOINT", ("predict", record_job))
    from hydra._internal.core_plugins.basic_launcher import BasicLauncher

    monkeypatch.setattr(BasicLauncher, "setup", lambda self, **kwargs: calls.append("setup"))

    def delegated_launch(self: object, overrides: object, initial_job_idx: int) -> list[object]:
        calls.append((overrides, initial_job_idx))
        return []

    monkeypatch.setattr(BasicLauncher, "launch", delegated_launch)
    assert launcher.launch([["value=first"]], 0) == []
    assert calls == ["setup", ([["value=first"]], 0)]


def test_mixed_queue_batch_fails_before_run_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader = _SweepConfigLoader(tmp_path, initial_job_idx=0)
    original = loader.load_sweep_config

    def mixed(config: DictConfig, overrides: list[str]) -> DictConfig:
        job = original(config, overrides)
        with open_dict(job):
            job.queue = {"enabled": job.value == "first"}
        return job

    monkeypatch.setattr(loader, "load_sweep_config", mixed)
    monkeypatch.setattr(execution, "run_jobs", lambda jobs: pytest.fail("admission occurred"))
    launcher = QueueLauncher()
    launcher.setup(
        hydra_context=cast(HydraContext, SimpleNamespace(config_loader=loader)),
        task_function=cast(TaskFunction, record_job),
        config=_job_config(tmp_path, index=0, value="base"),
    )
    monkeypatch.setattr(execution, "_ENTRYPOINT", ("predict", record_job))
    with pytest.raises(ValueError, match="Mixed queue"):
        launcher.launch([["value=first"], ["value=second"]], 0)


def test_mixed_modes_in_later_batch_reject_before_first_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _job_config(tmp_path, index=0, value="base")
    with open_dict(base):
        base.hydra.overrides.task = ["queue.enabled=true,false"]
        base.hydra.sweeper.max_batch_size = 1
    calls: list[list[str]] = []

    class Loader:
        def load_sweep_config(self, config: DictConfig, overrides: list[str]) -> DictConfig:
            calls.append(overrides)
            result = deepcopy(config)
            assert isinstance(result, DictConfig)
            with open_dict(result):
                result.queue = {"enabled": overrides[0].lower() == "queue.enabled=true"}
            return result

    launcher = QueueLauncher()
    launcher.setup(
        hydra_context=cast(HydraContext, SimpleNamespace(config_loader=Loader())),
        task_function=cast(TaskFunction, record_job),
        config=base,
    )
    monkeypatch.setattr(execution, "run_jobs", lambda jobs: pytest.fail("admission occurred"))
    with pytest.raises(ValueError, match="full sweep"):
        launcher.launch([["queue.enabled=true"]], 0)
    assert [[value.lower() for value in call] for call in calls] == [
        ["queue.enabled=true"],
        ["queue.enabled=false"],
    ]


def test_fresh_worker_retains_trace_command_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    config = _job_config(tmp_path, index=0, value="trace", delay=0)
    result = run_jobs([ModelJob("predict", record_job, config, sweep=True)])[0]
    assert result.status is JobStatus.COMPLETED
    captured = capfd.readouterr()
    assert "command.worker" in captured.err
    assert "command.return" in captured.err


def test_exact_union_mapping_survives_fresh_worker_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.runtime.gpu_resources import GPUDevice
    from hydra_queue_fixture import record_exact_job

    class Inventory:
        def visible(self) -> tuple[str, ...]:
            return ("GPU-a", "GPU-b", "GPU-c")

        def snapshot(self) -> tuple[GPUDevice, ...]:
            return tuple(GPUDevice(uuid, False) for uuid in self.visible())

    monkeypatch.setattr(execution, "GPUInventory", Inventory)
    root = tmp_path / "shared-queue"
    monkeypatch.setenv("CY_GPU_QUEUE_ROOT", str(root))
    config = _job_config(tmp_path, index=0, value="exact", delay=0)
    with open_dict(config):
        config.ultralytics = {"device": [2, 0]}
        config.ultralytics_predict = {"device": 1}
        config.queue = {"enabled": True}
        config.autogpu = {"enabled": False}
    result = run_jobs([ModelJob("pipeline", record_exact_job, config, sweep=True)])[0]
    assert result.status is JobStatus.COMPLETED
    record = _load(tmp_path / "receipt-0.json")
    assert record["visibility"] == "GPU-b,GPU-c,GPU-a"
    assert record["training"] == [1, 2]
    assert record["inference"] == [0]
    assert record["original"] == ["GPU-a", "GPU-b", "GPU-c"]
    assert record["admitted"] == ["GPU-b", "GPU-c", "GPU-a"]
    assert record["pid"] != os.getpid()
    assert _load(root / "registry.json")["requests"] == []
