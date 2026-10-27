"""Offline contracts for the physical native harness; no CUDA or ClearML calls."""

import csv
import importlib
import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from clearml_yolo.adapters.runtime.workers import WorkerCommand
from ddp_gpu_harness import GPUOptions
from native_backend_ddp_harness import (
    SELECTIONS,
    instrument_command,
    pipeline_arguments,
    request_document,
    validate_failure,
    validate_publication,
    validate_ranks,
    validate_ready,
)


def _evidence(
    tmp_path: Path, selection: str = "fcos/resnet50_fpn"
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    request = request_document(GPUOptions("0,1", "native-tests", tmp_path), selection, "none")
    request["uuids"] = ["GPU-a", "GPU-b"]
    ranks = [
        {
            "rank": rank,
            "local_rank": rank,
            "world_size": 2,
            "backend": "nccl",
            "selection": selection,
            "uuid": request["uuids"][rank],
            "global_batch": 4,
            "per_rank_batch": 2,
            "accumulation": request["accumulation"],
            "optimizer_steps": request["train_count"] // 4 // request["accumulation"],
            "initial_parameters": "initial",
            "parameters": "changed",
            "model": "model-state",
            "ema": "ema-state",
            "optimizer": "adam-state",
            "finite": True,
            "ema_updates": 2,
            "checkpoints": ["best.pth"] if rank == 0 else [],
            "expected_train_ids": list(range(request["train_count"])),
            "expected_val_ids": list(range(5)),
            "train_ids": list(range(rank, request["train_count"], 2)),
            "validation_ids": list(range(rank, 5, 2)),
            "train_batches": [2] * (request["train_count"] // 4),
            "train_labels": [0] * 7,
        }
        for rank in range(2)
    ]
    return request, ranks


@pytest.mark.parametrize("selection", SELECTIONS)
def test_public_pipeline_commands_select_actual_native_global_batch(
    tmp_path: Path, selection: str
) -> None:
    request = request_document(GPUOptions("3,1", "owned", tmp_path), selection, "none")
    argv = pipeline_arguments(tmp_path, request)
    assert argv[1:3] == ["-m", "clearml_yolo.entrypoints.pipeline"]
    assert f"model={selection}" in argv
    assert "model.train.device=[0, 1]" in argv
    assert "model.train.batch=4" in argv
    assert "model.predict.device=0" in argv
    assert "model.train.use_ema=true" in argv
    assert not any("ultralytics." in arg for arg in argv)
    assert request["val_count"] == 5
    assert request["accumulation"] == (1 if selection.startswith("deimv2/") else 2)


def test_rank_wrapper_preserves_production_requests_and_supervision(tmp_path: Path) -> None:
    command = WorkerCommand(
        argv=(
            "python",
            "-m",
            "clearml_yolo.adapters.integrations.training_worker",
            "request.json",
            "1",
        ),
        environment={"RANK": "1", "WORLD_SIZE": "2", "TORCHELASTIC_RUN_ID": "token"},
        log_path=tmp_path / "rank.log",
    )
    wrapped = instrument_command(command)
    assert wrapped.argv[0] == command.argv[0]
    assert wrapped.argv[-3:] == ("rank", "request.json", "1")
    assert wrapped.environment == command.environment
    assert wrapped.log_path == command.log_path
    with pytest.raises(ValueError, match="unexpected"):
        instrument_command(
            WorkerCommand(argv=("wrong",), environment={}, log_path=command.log_path)
        )


@pytest.mark.parametrize("selection", SELECTIONS)
def test_consistent_native_rank_evidence_passes(tmp_path: Path, selection: str) -> None:
    request, ranks = _evidence(tmp_path, selection)
    validate_ranks(request, ranks)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("rank", 0, "identities"),
        ("global_batch", 2, "global batch"),
        ("per_rank_batch", 4, "rank batch"),
        ("local_rank", 0, "local rank"),
        ("uuid", "GPU-wrong", "device mapping"),
        ("backend", "gloo", "NCCL"),
        ("optimizer_steps", 0, "actual updates"),
        ("ema_updates", 0, "EMA"),
        ("ema", "divergent", "Divergent ema"),
        ("optimizer", "different", "Divergent optimizer"),
        ("model", "different", "Divergent model"),
        ("parameters", "different", "Divergent parameters"),
        ("finite", False, "Nonfinite"),
        ("checkpoints", ["also-best.pth"], "Checkpoint ownership"),
        ("validation_ids", [1, 3, 0], "duplicate validation"),
        ("train_ids", [0, 2, 4, 6, 8, 10, 12, 14], "duplicate train"),
        ("train_batches", [1, 1, 1, 1], "microbatch"),
        ("train_batches", [], "Missing training"),
        ("train_labels", [1], "class zero"),
    ],
)
def test_bad_rank_evidence_is_rejected(
    tmp_path: Path, field: str, value: Any, message: str
) -> None:
    request, ranks = _evidence(tmp_path)
    ranks[1][field] = value
    with pytest.raises(AssertionError, match=message):
        validate_ranks(request, ranks)


def test_missing_rank_is_not_partial_acceptance(tmp_path: Path) -> None:
    request, ranks = _evidence(tmp_path)
    with pytest.raises(AssertionError, match="Missing native rank"):
        validate_ranks(request, ranks[:1])


def test_real_owner_and_checkpoint_readback_contract(tmp_path: Path) -> None:
    request, _ = _evidence(tmp_path)
    events = [
        {"kind": "task-init", "pid": 100, "task_id": "task"},
        {"kind": "model-attempt", "pid": 100, "rank": -1},
    ]
    publication = {
        "task_ids": ["task"],
        "status": "completed",
        "output_models": 1,
        "download_sha256": "hash",
        "native_sha256": "hash",
        "unwrapped": True,
        "selection": request["selection"],
        "reload_images": 3,
    }
    validate_publication(request, events, publication)
    for field, value, message in (
        ("task_ids", ["task", "worker"], "Unexpected ClearML"),
        ("native_sha256", "wrong", "hash mismatch"),
        ("unwrapped", False, "wrapper prefixes"),
        ("reload_images", 2, "reload lost"),
    ):
        with pytest.raises(AssertionError, match=message):
            validate_publication(request, events, publication | {field: value})
    worker_events = deepcopy(events)
    worker_events[1].update(rank=1, pid=101)
    with pytest.raises(AssertionError, match="Worker publication"):
        validate_publication(request, worker_events, publication)
    with pytest.raises(AssertionError, match="one ClearML"):
        validate_publication(request, [*events, events[0]], publication)


@pytest.mark.parametrize("fault", ["crash", "oom", "cancel"])
def test_fault_requires_matching_native_observation_and_failed_exit(
    tmp_path: Path, fault: Any
) -> None:
    request = request_document(GPUOptions("0,1", "owned", tmp_path), SELECTIONS[0], fault)
    event = {
        "kind": f"fault-{fault}",
        "rank": -1 if fault == "cancel" else 1,
        "confirmed_cuda_oom": True,
        "exit_code": 73,
        "signal": "SIGINT",
        "target_pid": 100,
    }
    events: list[dict[str, Any]] = [{"kind": "task-init", "pid": 100}, event]
    validate_failure(request, events, 73)
    with pytest.raises(AssertionError, match="unexpectedly succeeded"):
        validate_failure(request, [event], 0)
    with pytest.raises(AssertionError, match="not observed"):
        validate_failure(request, [], 73)
    if fault == "oom":
        with pytest.raises(AssertionError, match="actual CUDA"):
            validate_failure(request, [event | {"confirmed_cuda_oom": False}], 1)


@pytest.mark.parametrize("selection", SELECTIONS)
def test_native_public_command_composes_without_execution(tmp_path: Path, selection: str) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401

    request = request_document(GPUOptions("0,1", "owned", tmp_path), selection, "none")
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline", overrides=pipeline_arguments(tmp_path, request)[3:]
        )
    assert f"{config.model.backend}/{config.model.preset}" == selection
    assert config.model.train.batch == 4
    assert config.model.train.device == [0, 1]
    assert config.model.train.pretrained is False


def test_fixture_contains_uneven_validation_and_background_images(tmp_path: Path) -> None:
    from native_backend_ddp_worker import prepare

    request, _ = _evidence(tmp_path)
    prepare(tmp_path, request)
    with (tmp_path / "ground_truth.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    for split in ("train", "val", "test"):
        subset = [row for row in rows if row["split"] == split]
        assert len(subset) == request[f"{split}_count"]
        assert sum(not row["instance_label"] for row in subset) == 1
        assert all(Path(row["image_path"]).is_file() for row in subset)
    assert request["val_count"] % request["world_size"] == 1
    source = (tmp_path / "instrumentation/sitecustomize.py").read_text()
    compile(source, "sitecustomize.py", "exec")


def test_readiness_requires_real_world_metadata_even_for_faults(tmp_path: Path) -> None:
    request, ranks = _evidence(tmp_path)
    ranks[0]["uuid"] = "A"
    validate_ready(request, ranks)
    ranks[1]["backend"] = "gloo"
    with pytest.raises(AssertionError, match="NCCL"):
        validate_ready(request, ranks)


def test_owner_wrapper_forwards_live_ownership_monitor_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from native_backend_ddp_observers import install_owner

    module: Any = importlib.import_module("clearml_yolo.adapters.integrations.distributed_training")
    observed: dict[str, Any] = {}

    def supervisor(commands: Any, **kwargs: Any) -> str:
        observed.update(commands=commands, **kwargs)
        return "real-supervisor-result"

    monkeypatch.setenv("CY_DDP_TRACE", str(tmp_path))
    monkeypatch.setattr(module, "run_workers", supervisor)
    monkeypatch.setattr("native_backend_ddp_observers._install_sdk", lambda *_args: None)
    install_owner()

    def monitor(owned: Callable[[], tuple[int, ...]]) -> tuple[int, ...]:
        return owned()

    command = WorkerCommand(
        argv=("python", "-m", "clearml_yolo.adapters.integrations.training_worker", "request", "1"),
        environment={"RANK": "1"},
        log_path=tmp_path / "rank.log",
    )
    assert (
        module.run_workers([command], monitor=monitor, timeout_seconds=17)
        == "real-supervisor-result"
    )
    assert observed["monitor"] is monitor
    assert observed["monitor"](lambda: (123, 456)) == (123, 456)
    assert observed["timeout_seconds"] == 17
    assert observed["commands"][0].environment == command.environment


def _observer(tmp_path: Path, fault: str = "none") -> Any:
    from clearml_yolo.application.contracts import PreparedDataset
    from clearml_yolo.application.training_workers import TrainingWorkerRequest
    from clearml_yolo.core.models import ModelConfig, TrainSettings
    from native_backend_ddp_observers import RankObserver

    options, _ = _evidence(tmp_path)
    options["fault"] = fault
    (tmp_path / "request.json").write_text(json.dumps(options))
    for split in ("train", "valid"):
        directory = tmp_path / split
        directory.mkdir(exist_ok=True)
        (directory / "_annotations.coco.json").write_text(json.dumps({"images": [{"id": 7}]}))
    request = TrainingWorkerRequest(
        token=uuid4().hex,
        world_size=2,
        output=tmp_path,
        config=ModelConfig(backend="fcos", preset="resnet50_fpn", train=TrainSettings(batch=4)),
        prepared=PreparedDataset(
            data=tmp_path / "data.yaml",
            ground_truth=tmp_path / "truth.csv",
            manifest=tmp_path / "manifest.json",
            dataset_format="coco",
            artifacts=[],
        ),
    )
    return RankObserver(tmp_path, request, 1)


def test_cpu_observer_tracks_real_updates_hashes_and_original_samples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import torch
    from torch.optim.swa_utils import AveragedModel

    from native_backend_ddp_observers import ObservedBatches, state_digest

    observer = _observer(tmp_path)
    model = torch.nn.Linear(2, 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    ema = AveragedModel(model)
    # Only readiness telemetry is stubbed; optimizer, EMA, serialization and hashes run on CPU.
    monkeypatch.setenv("LOCAL_RANK", "1")
    monkeypatch.setattr(torch.distributed, "is_initialized", lambda: True)
    monkeypatch.setattr(torch.distributed, "get_backend", lambda: "nccl")
    monkeypatch.setattr(torch.distributed, "get_world_size", lambda: 2)
    monkeypatch.setattr(torch.cuda, "current_device", lambda: 1)
    monkeypatch.setattr(
        torch.cuda, "get_device_properties", lambda _rank: SimpleNamespace(uuid="b")
    )
    observer.start(model, optimizer, lambda: (ema.module, int(ema.n_averaged)))
    model(torch.ones(1, 2)).sum().backward()
    optimizer.step()
    ema.update_parameters(model)
    observer.snapshot()
    assert observer.state["optimizer_steps"] == 1
    assert observer.state["ema_updates"] == 1
    assert observer.state["initial_parameters"] != observer.state["parameters"]
    assert observer.state["finite"] is True
    targets = [{"image_id": torch.tensor(7), "labels": torch.tensor([0])}]
    batch = ([torch.zeros(3, 8, 8)], targets)
    observed = ObservedBatches([batch], observer, "train")
    assert len(observed) == 1
    assert next(iter(observed)) is batch
    assert observer.state["train_ids"] == [7]
    assert observer.state["train_labels"] == [0]
    monkeypatch.setattr(torch, "save", torch.save)
    observer.save_observer()
    torch.save(model.state_dict(), tmp_path / "best.pth")
    observer.finish()
    saved = json.loads((tmp_path / "native-rank-1.json").read_text())
    assert saved["checkpoints"] == [str(tmp_path / "best.pth")]
    assert state_digest({"a": torch.tensor(float("nan"))})[1] is False


@pytest.mark.parametrize("fault", ["crash", "oom"])
def test_cpu_fault_gate_waits_for_release_and_records_specific_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import torch

    from native_backend_ddp_worker import events_at

    observer = _observer(tmp_path, fault)
    observer.options["timeout"] = 0
    with pytest.raises(TimeoutError, match="gate was not released"):
        observer._fault_gate()
    assert events_at(tmp_path) == []
    (tmp_path / "release-fault").touch()
    if fault == "crash":

        def exit_process(code: int) -> None:
            raise SystemExit(code)

        monkeypatch.setattr("native_backend_ddp_observers.os._exit", exit_process)
        with pytest.raises(SystemExit) as caught:
            observer._fault_gate()
        assert caught.value.code == 73
    else:
        monkeypatch.setattr(
            torch.cuda, "get_device_properties", lambda _rank: SimpleNamespace(total_memory=100)
        )

        def allocation(size: int, **kwargs: Any) -> None:
            assert size == 200
            assert kwargs["device"] == "cuda:1"
            raise torch.cuda.OutOfMemoryError("CPU gate regression")

        monkeypatch.setattr(torch, "empty", allocation)
        with pytest.raises(torch.cuda.OutOfMemoryError):
            observer._fault_gate()
    assert [event["kind"] for event in events_at(tmp_path)] == [f"fault-{fault}"]


@pytest.mark.parametrize("world", [2, 3, 4])
def test_rfdetr_fixture_meets_native_minimum_without_repeated_samples(
    tmp_path: Path, world: int
) -> None:
    import torch

    native: Any = importlib.import_module("rfdetr.training.module_data")
    configuration: Any = importlib.import_module("rfdetr.config")
    # The harness deliberately targets the pinned 1.11.2 loader contract.
    assert native._MIN_TRAIN_BATCHES == 5
    request = request_document(
        GPUOptions(",".join(str(rank) for rank in range(world)), "native-tests", tmp_path),
        "rfdetr/nano",
        "none",
    )
    batch = request["global_batch"] // world
    accumulation = request["accumulation"]
    module = native.RFDETRDataModule(
        configuration.RFDETRNanoConfig(resolution=128, pretrain_weights=None, num_classes=1),
        configuration.TrainConfig(
            dataset_dir=str(tmp_path),
            batch_size=batch,
            grad_accum_steps=accumulation,
            num_workers=0,
        ),
    )
    module.trainer = SimpleNamespace(world_size=world, accumulate_grad_batches=accumulation)
    module._dataset_train = torch.utils.data.TensorDataset(torch.arange(request["train_count"]))
    loader = module.train_dataloader()
    assert len(loader.dataset) == request["train_count"], "Native loader repeated fixture samples"
    observed: list[int] = []
    for rank in range(world):
        sampler: torch.utils.data.DistributedSampler[Any] = torch.utils.data.DistributedSampler(
            loader.dataset,
            num_replicas=world,
            rank=rank,
            shuffle=False,
        )
        observed.extend(int(loader.dataset[index][0]) for index in sampler)
        assert len(sampler) // batch // accumulation == 5
    assert sorted(observed) == list(range(request["train_count"]))
