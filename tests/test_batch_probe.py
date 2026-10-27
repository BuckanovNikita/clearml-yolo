"""Supervised probe receipts preserve failures and exercise native YOLO optimizer semantics."""

from collections.abc import Callable, Sequence
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, override
from uuid import uuid4

import pytest

from clearml_yolo.adapters.integrations import batch_probe as adapter
from clearml_yolo.adapters.integrations import probe_worker
from clearml_yolo.adapters.runtime import gpu_inventory
from clearml_yolo.adapters.runtime.workers import WorkerCommand, WorkerOutcome
from clearml_yolo.adapters.yolo import batch_probe as yolo
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult
from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    GPUHardware,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    TrialStatus,
    select_models,
)
from clearml_yolo.core.models import ModelConfig
from test_batch_estimate_workflow import sample_profile
from test_batch_profiles import sample_devices


def _profile(selection: str = "yolo11n") -> TrainingProfile:
    return sample_profile().model_copy(
        update={
            "model": select_models((selection,))[0],
            "nominal_size": (32, 32),
            "effective_size": (32, 32),
            "compilation": False,
            "gpus": tuple(
                GPUHardware(name=d.name, uuid=d.uuid, total_memory_bytes=d.total_memory_bytes)
                for d in sample_devices()[:1]
            ),
            "optimizers": ("AdamW", "MuSGD") if selection.startswith("yolo") else ("AdamW",),
        }
    )


def _request(tmp_path: Path) -> BatchProbeRequest:
    return BatchProbeRequest(
        token=uuid4().hex,
        profile=_profile(),
        workload=SyntheticWorkload(classes=3, objects_per_image=2),
        settings=SearchSettings(),
        global_batch=4,
        optimizer="AdamW",
        output=tmp_path,
    )


class _Workers:
    def __init__(
        self,
        *,
        status: Literal["success", "crash", "timeout"] = "success",
        receipts: tuple[TrialStatus | None, ...] = ("success",),
        wrong_identity: bool = False,
        allocator_peak: int = 200,
        non_allocator: int = 0,
    ) -> None:
        self.status, self.receipts, self.wrong_identity = status, receipts, wrong_identity
        self.allocator_peak, self.non_allocator = allocator_peak, non_allocator
        self.requests: list[BatchProbeRequest] = []
        self.commands: list[Sequence[WorkerCommand]] = []

    def run(
        self,
        commands: Sequence[WorkerCommand],
        *,
        timeout_seconds: float,
        monitor: Callable[[Callable[[], tuple[int, ...]]], None],
    ) -> WorkerOutcome:
        request = BatchProbeRequest.model_validate_json(
            Path(commands[0].argv[-1]).read_text(encoding="utf-8")
        )
        self.requests.append(request)
        self.commands.append(commands)
        monitor(lambda: (101, 102))
        for rank, status in enumerate(self.receipts):
            if status is None:
                continue
            record = ProbeRankResult(
                token=uuid4().hex if self.wrong_identity else request.token,
                rank=rank,
                status=status,
                actual_global_batch=request.global_batch,
                peak_memory_bytes=self.allocator_peak + rank * 100,
                non_allocator_memory_bytes=self.non_allocator,
                warmup_steps=5,
                measured_steps=10,
                validation_steps=1,
                diagnostic="confirmed worker outcome",
            )
            (request.output / f"rank-{rank}.json").write_text(record.model_dump_json())
        return WorkerOutcome(
            status=self.status, exit_codes=(0, 0) if self.status == "success" else (1, -15)
        )


def test_completed_receipts_fence_telemetry_during_cuda_context_teardown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workers = _Workers()
    _install_workers(monkeypatch, tmp_path, workers)
    monkeypatch.setattr(adapter, "_TELEMETRY_INTERVAL_SECONDS", 0)
    observations: list[tuple[int, ...]] = []

    def telemetry(devices: Any, owned_pids: Callable[[], tuple[int, ...]]) -> tuple[int, ...]:
        pids = owned_pids()
        observations.append(pids)
        if not pids:
            pytest.fail("Retired CUDA contexts cannot contaminate already completed measurements")
        return (500,)

    def run(
        commands: Sequence[WorkerCommand],
        *,
        timeout_seconds: float,
        monitor: Callable[[Callable[[], tuple[int, ...]]], None],
    ) -> WorkerOutcome:
        result = workers.run(commands, timeout_seconds=timeout_seconds, monitor=monitor)
        monitor(lambda: ())
        return result

    monkeypatch.setattr(adapter, "monitor_devices", telemetry)
    monkeypatch.setattr(adapter, "run_workers", run)
    result = adapter.NativeBatchProbe().run(_profile(), SyntheticWorkload(), SearchSettings(), 4)
    assert result.status == "success"
    assert observations == [(101, 102), (101, 102)]


def _install_workers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, workers: _Workers) -> None:
    monkeypatch.setattr(adapter, "discover_gpus", sample_devices)
    monkeypatch.setattr(adapter, "require_idle", lambda devices: tuple(10 for _ in devices))
    monkeypatch.setattr(adapter, "temporary_root", lambda: tmp_path)
    monkeypatch.setattr(adapter, "_port", lambda: "12345")
    monkeypatch.setattr(adapter, "monitor_devices", lambda devices, pids: (500,))
    monkeypatch.setattr(adapter, "run_workers", workers.run)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "GPU-physical-a,GPU-physical-b")


def test_both_yolo_optimizer_paths_use_fresh_workers_and_maximum_whole_gpu_peaks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workers = _Workers()
    _install_workers(monkeypatch, tmp_path, workers)
    result = adapter.NativeBatchProbe().run(_profile(), SyntheticWorkload(), SearchSettings(), 4)
    assert result.status == "success"
    assert result.optimizer_paths == ("AdamW", "MuSGD")
    assert [request.optimizer for request in workers.requests] == ["AdamW", "MuSGD"]
    assert workers.requests[0].output != workers.requests[1].output
    assert result.peak_memory_bytes == (500,)
    assert result.actual_global_batch == 4
    assert (result.warmup_steps, result.measured_steps, result.validation_steps) == (5, 10, 1)
    for commands in workers.commands:
        assert [command.environment["LOCAL_RANK"] for command in commands] == ["0"]
        assert all(command.environment["WORLD_SIZE"] == "1" for command in commands)
        assert all(
            command.environment["CUDA_VISIBLE_DEVICES"] == "GPU-physical-a" for command in commands
        )


@pytest.mark.parametrize(
    ("allocator", "non_allocator", "polled", "expected"),
    [(850, 100, 700, 950), (700, 100, 750, 800), (700, 150, 750, 850), (700, 50, 950, 950)],
)
def test_budget_peak_combines_disjoint_memory_without_adding_the_baseline_twice(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    allocator: int,
    non_allocator: int,
    polled: int,
    expected: int,
) -> None:
    workers = _Workers(receipts=("success",), allocator_peak=allocator, non_allocator=non_allocator)
    _install_workers(monkeypatch, tmp_path, workers)
    monkeypatch.setattr(adapter, "require_idle", lambda _: (100,))
    monkeypatch.setattr(adapter, "monitor_devices", lambda *_: (polled,))
    profile = _profile().model_copy(update={"gpus": _profile().gpus[:1], "optimizers": ("AdamW",)})
    settings = SearchSettings(memory_fraction=0.9)
    result = adapter.NativeBatchProbe().run(profile, SyntheticWorkload(), settings, 1)
    assert result.peak_memory_bytes == (expected,)
    state = BatchSearch.start(profile, settings).observe(result)
    assert state.status == ("no_capacity" if expected > 900 else "searching")
    # Owner accounting never rewrites the raw allocator/non-allocator receipt.
    receipt = ProbeRankResult.model_validate_json(
        (workers.requests[0].output / "rank-0.json").read_text(encoding="utf-8")
    )
    assert receipt.peak_memory_bytes == allocator
    assert receipt.non_allocator_memory_bytes == non_allocator


def test_each_optimizer_path_refreshes_its_baseline_after_asset_setup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workers = _Workers(allocator_peak=850, non_allocator=100)
    _install_workers(monkeypatch, tmp_path, workers)
    baselines = iter([(10,), (100,), (200,)])
    sampled: list[tuple[int, ...]] = []

    def idle(_: Any) -> tuple[int, ...]:
        baseline = next(baselines)
        sampled.append(baseline)
        return baseline

    monkeypatch.setattr(adapter, "require_idle", idle)
    result = adapter.NativeBatchProbe().run(_profile(), SyntheticWorkload(), SearchSettings(), 4)
    assert sampled == [(10,), (100,), (200,)]
    assert result.peak_memory_bytes == (1050,)


@pytest.mark.parametrize(
    ("outcome", "receipts", "expected"),
    [
        ("crash", (None,), "crash"),
        ("timeout", (None,), "timeout"),
        ("crash", ("oom",), "oom"),
        ("crash", ("nonfinite",), "nonfinite"),
        ("crash", ("missing_asset",), "missing_asset"),
        ("crash", ("success",), "crash"),
        ("timeout", ("success",), "timeout"),
    ],
)
def test_failed_groups_never_become_capacity_without_confirmed_oom(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    outcome: Literal["success", "crash", "timeout"],
    receipts: tuple[TrialStatus | None, ...],
    expected: TrialStatus,
) -> None:
    workers = _Workers(status=outcome, receipts=receipts)
    _install_workers(monkeypatch, tmp_path, workers)
    result = adapter.NativeBatchProbe().run(_profile(), SyntheticWorkload(), SearchSettings(), 4)
    assert result.status == expected
    assert len(workers.requests) == 1
    assert result.actual_global_batch is None
    assert result.optimizer_paths == ()


def test_forged_receipt_identity_is_not_a_success_or_capacity_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workers = _Workers(wrong_identity=True)
    _install_workers(monkeypatch, tmp_path, workers)
    result = adapter.NativeBatchProbe().run(_profile(), SyntheticWorkload(), SearchSettings(), 4)
    assert result.status == "error"
    assert "identity" in result.diagnostic


@pytest.mark.parametrize("failure", ["missing", "changed", "busy"])
def test_changed_or_busy_hardware_stops_before_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    workers = _Workers()
    _install_workers(monkeypatch, tmp_path, workers)
    devices = sample_devices()
    if failure == "missing":
        monkeypatch.setattr(adapter, "discover_gpus", lambda: devices[1:])
    elif failure == "changed":
        changed = devices[0].model_copy(update={"total_memory_bytes": 2000})
        monkeypatch.setattr(adapter, "discover_gpus", lambda: (changed, devices[1]))
    else:

        def busy(_: Any) -> None:
            raise RuntimeError("GPU 0 is busy")

        monkeypatch.setattr(adapter, "require_idle", busy)
    result = adapter.NativeBatchProbe().run(_profile(), SyntheticWorkload(), SearchSettings(), 4)
    assert result.status == "contaminated"
    assert not workers.requests


def test_malformed_telemetry_aborts_search_without_becoming_capacity_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workers = _Workers()
    _install_workers(monkeypatch, tmp_path, workers)
    queries = iter(
        [
            [["GPU-a", "[Generic operating system error]", "75"]],
            [["GPU-a", "101"]],
        ]
    )
    monkeypatch.setattr(gpu_inventory, "_query", lambda _: next(queries))
    monkeypatch.setattr(adapter, "monitor_devices", gpu_inventory.monitor_devices)
    profile, settings = _profile(), SearchSettings()
    state = BatchSearch.start(profile, settings)
    assert state.next_batch is not None
    result = adapter.NativeBatchProbe().run(
        profile, SyntheticWorkload(), settings, state.next_batch
    )
    assert result.status == "contaminated"
    assert "GPU telemetry unavailable" in result.diagnostic
    assert "memory.used" in result.diagnostic
    assert result.peak_memory_bytes == ()
    assert state.observe(result).status == "failed"
    assert len(workers.requests) == 1


def test_native_requests_preserve_default_recipe_while_binding_global_batch_and_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workers = _Workers()
    _install_workers(monkeypatch, tmp_path, workers)

    def prepare(config: ModelConfig, *, training: bool) -> tuple[ModelConfig, tuple[()]]:
        assert training
        copy = config.model_copy(deep=True)
        copy.train.backbone_weights = tmp_path / "backbone.pth"
        return copy, ()

    monkeypatch.setattr(adapter, "prepare_model_assets", prepare)
    profile = _profile("fcos/resnet50_fpn").model_copy(
        update={"nominal_size": (800, 800), "effective_size": (800, 800)}
    )
    result = adapter.NativeBatchProbe().run(profile, SyntheticWorkload(), SearchSettings(), 4)
    assert result.status == "success"
    config = workers.requests[0].config
    assert config is not None
    assert (config.train.batch, config.train.imgsz, config.train.workers) == (4, 800, 0)
    assert config.train.amp
    assert config.train.use_ema
    assert config.train.pretrained
    assert config.train.backbone_weights == tmp_path / "backbone.pth"


@pytest.mark.parametrize(
    ("error_type", "expected"),
    [
        (FileNotFoundError, "missing_asset"),
        (FloatingPointError, "nonfinite"),
        (RuntimeError, "error"),
    ],
)
def test_worker_classifies_typed_failures_without_matching_error_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_type: type[Exception],
    expected: TrialStatus,
) -> None:
    request = _request(tmp_path)
    path = tmp_path / "request.json"
    path.write_text(request.model_dump_json())
    monkeypatch.setenv("LOCAL_RANK", "0")
    monkeypatch.setattr(probe_worker, "native_rank", lambda **_: nullcontext())

    def fail(_: Any) -> Any:
        raise error_type("CUDA out of memory appears in arbitrary diagnostic text")

    monkeypatch.setattr(yolo, "probe", fail)
    assert probe_worker.run(path) == 1
    result = ProbeRankResult.model_validate_json((tmp_path / "rank-0.json").read_text())
    assert result.status == expected
    assert result.token == request.token


def test_worker_recognizes_actual_cuda_oom_exception_without_using_cuda(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import torch

    test_worker_classifies_typed_failures_without_matching_error_text(
        monkeypatch, tmp_path, torch.cuda.OutOfMemoryError, "oom"
    )


def _cpu_trainer() -> Any:
    import torch
    from ultralytics.utils.torch_utils import ModelEMA

    class Model(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(0.5))
            self.forwards = 0
            self.losses = 0
            self.dictionary_forwards = 0

        @override
        def forward(self, data: Any) -> Any:
            self.forwards += 1
            if isinstance(data, dict):
                self.dictionary_forwards += 1
                return self.loss(data, self.weight.square())
            return self.weight.square()

        def loss(self, data: Any, predictions: Any) -> Any:
            self.losses += 1
            return predictions, predictions.detach()

    model = Model()
    return SimpleNamespace(
        model=model,
        optimizer=torch.optim.AdamW(model.parameters()),
        scaler=torch.amp.GradScaler("cpu", enabled=False),
        ema=ModelEMA(model),  # type: ignore[no-untyped-call]
        device=torch.device("cpu"),
    )


@pytest.mark.parametrize("compiled", [False, True])
def test_yolo_real_cpu_optimizer_updates_and_ema_include_all_accumulated_microbatches(
    tmp_path: Path,
    compiled: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory

    request = _request(tmp_path)
    request = request.model_copy(
        update={"profile": request.profile.model_copy(update={"compilation": compiled})}
    )
    trainer = _cpu_trainer()
    memory = GPUMemory()
    observations: list[int] = []
    monkeypatch.setattr(memory, "observe", lambda: observations.append(trainer.ema.updates))
    yolo._optimize(request, trainer, accumulation=3, amp=False, memory=memory)
    assert trainer.model.forwards == 45
    assert trainer.model.losses == 45
    assert trainer.model.dictionary_forwards == (0 if compiled else 45)
    assert trainer.ema.updates == 15
    assert all(state["step"].item() == 15 for state in trainer.optimizer.state.values())
    assert observations == list(range(1, 16))


def test_yolo_nonfinite_loss_never_allocates_optimizer_state(tmp_path: Path) -> None:
    trainer = _cpu_trainer()
    trainer.model.weight.data.fill_(float("nan"))
    with pytest.raises(FloatingPointError, match="nonfinite loss"):
        yolo._optimize(_request(tmp_path), trainer, accumulation=1, amp=False)
    assert not trainer.optimizer.state
    assert trainer.ema.updates == 0


def test_yolo_amp_skips_do_not_count_toward_the_fifteen_real_updates(tmp_path: Path) -> None:
    class Scaler:
        def __init__(self) -> None:
            self.attempts = 0

        def scale(self, value: Any) -> Any:
            return value

        def unscale_(self, optimizer: Any) -> None:
            pass

        def get_scale(self) -> float:
            return float(8 // (2 ** min(self.attempts, 2)))

        def step(self, optimizer: Any) -> None:
            self.attempts += 1
            if self.attempts > 2:
                optimizer.step()

        def update(self) -> None:
            pass

    trainer = _cpu_trainer()
    trainer.scaler = Scaler()
    yolo._optimize(_request(tmp_path), trainer, accumulation=1, amp=False)
    assert trainer.scaler.attempts == 17
    assert trainer.ema.updates == 17
    assert all(state["step"].item() == 15 for state in trainer.optimizer.state.values())


def _validation_model(*, finite: bool = True) -> Any:
    import torch

    class Model(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.names = {0: "zero", 1: "one", 2: "two"}
            self.loss_calls = 0
            self.observed: dict[str, Any] = {}

        @override
        def forward(self, images: torch.Tensor, *, augment: bool = False) -> torch.Tensor:
            assert augment is False
            assert not self.training
            assert not torch.is_grad_enabled()
            self.observed["shape"] = tuple(images.shape)
            assert images.min() >= 0
            assert images.max() <= 1
            prediction = torch.zeros((images.shape[0], 7, 1), device=images.device)
            prediction[:, :4, 0] = torch.tensor([16, 16, 8, 8], device=images.device)
            prediction[:, 4, 0] = 0.9
            return prediction

        def loss(self, batch: dict[str, Any], predictions: Any) -> Any:
            self.loss_calls += 1
            self.observed["objects"] = batch["batch_idx"].bincount().tolist()
            value = torch.tensor(0.1 if finite else float("nan"))
            return value, {"box_loss": value}

    return Model()


def _validation_request(tmp_path: Path) -> BatchProbeRequest:
    request = _request(tmp_path)
    return request.model_copy(
        update={
            "global_batch": 2,
            "profile": request.profile.model_copy(
                update={"gpus": request.profile.gpus[:1], "effective_size": (64, 64)}
            ),
        }
    )


@pytest.mark.parametrize("native_rank", [-1, 0])
def test_yolo_validation_runs_real_loss_and_metrics_at_nominal_size_and_raw_density(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, native_rank: int
) -> None:
    import torch
    from ultralytics.engine import validator as native_base
    from ultralytics.models.yolo.detect import DetectionValidator
    from ultralytics.models.yolo.detect import val as native_validation
    from ultralytics.utils import callbacks

    model = _validation_model()
    reached: list[str] = []
    original_update: Any = DetectionValidator.update_metrics
    original_stats: Any = DetectionValidator.get_stats
    monkeypatch.setattr(native_validation, "RANK", native_rank)
    monkeypatch.setattr(native_base, "RANK", native_rank)

    def update(validator: Any, predictions: Any, batch: Any) -> Any:
        reached.append("update")
        return original_update(validator, predictions, batch)

    def stats(validator: Any) -> Any:
        reached.append("stats")
        assert validator.seen == 4
        return original_stats(validator)

    def forbidden(_: Any) -> None:
        pytest.fail("Probe validation must not invoke application or SDK callbacks")

    monkeypatch.setattr(DetectionValidator, "update_metrics", update)
    monkeypatch.setattr(DetectionValidator, "get_stats", stats)
    monkeypatch.setitem(callbacks.default_callbacks, "on_val_batch_end", [forbidden])
    yolo._validate(
        _validation_request(tmp_path),
        model,
        2,
        torch.device("cpu"),
        {},
        False,
        loss_items={"box_loss": torch.zeros(())},
    )
    assert reached == ["update", "stats"]
    assert model.loss_calls == 1
    assert model.observed == {"shape": (4, 3, 32, 32), "objects": [2, 2, 2, 2]}


def test_yolo_validation_nonfinite_loss_fails_before_a_success_receipt(tmp_path: Path) -> None:
    import torch

    with pytest.raises(FloatingPointError, match="nonfinite validation loss"):
        yolo._validate(
            _validation_request(tmp_path),
            _validation_model(finite=False),
            2,
            torch.device("cpu"),
            {},
            False,
            loss_items={"box_loss": torch.zeros(())},
        )


def test_yolo_validation_executes_installed_detection_loss_on_cpu(tmp_path: Path) -> None:
    import torch
    from ultralytics.nn.tasks import DetectionModel

    from clearml_yolo.adapters.yolo.config import native_defaults

    architecture = {
        "nc": 3,
        "backbone": [[-1, 1, "Conv", [8, 3, 2]]],
        "head": [[[-1], 1, "Detect", ["nc"]]],
    }
    model: Any = DetectionModel(architecture, nc=3, verbose=False)  # type: ignore[no-untyped-call]
    model.args = SimpleNamespace(**native_defaults())
    request = _validation_request(tmp_path)
    _, loss_items = model(yolo._batch(request, 2, torch.device("cpu")))
    assert loss_items
    assert all(torch.isfinite(value).all() for value in loss_items.values())
    yolo._validate(
        request, model, 2, torch.device("cpu"), native_defaults(), False, loss_items=loss_items
    )


@pytest.mark.parametrize("failure_stage", ["update_metrics", "get_stats"])
def test_yolo_validation_metric_failures_propagate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure_stage: str
) -> None:
    import torch
    from ultralytics.models.yolo.detect import DetectionValidator

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"failed {failure_stage}")

    monkeypatch.setattr(DetectionValidator, failure_stage, fail)
    with pytest.raises(RuntimeError, match=failure_stage):
        yolo._validate(
            _validation_request(tmp_path),
            _validation_model(),
            2,
            torch.device("cpu"),
            {},
            False,
            loss_items={"box_loss": torch.zeros(())},
        )


def test_yolo_validation_nonfinite_metrics_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import torch
    from ultralytics.models.yolo.detect import DetectionValidator

    original_stats: Any = DetectionValidator.get_stats

    def stats(validator: Any) -> Any:
        return original_stats(validator) | {"metric": float("nan")}

    monkeypatch.setattr(DetectionValidator, "get_stats", stats)
    with pytest.raises(FloatingPointError, match="nonfinite validation metrics"):
        yolo._validate(
            _validation_request(tmp_path),
            _validation_model(),
            2,
            torch.device("cpu"),
            {},
            False,
            loss_items={"box_loss": torch.zeros(())},
        )


@pytest.mark.parametrize(("rank", "owner_decision"), [(0, False), (0, True), (1, False), (1, True)])
def test_yolo_amp_uses_only_rank_zero_check_and_broadcasts_its_decision(
    monkeypatch: pytest.MonkeyPatch, rank: int, owner_decision: bool
) -> None:
    import torch
    import torch.distributed as dist
    from ultralytics.utils import callbacks, checks

    checks_seen: list[Any] = []
    broadcasts: list[int] = []
    original_callbacks = callbacks.default_callbacks.copy()
    monkeypatch.setattr(dist, "is_initialized", lambda: True)
    monkeypatch.setattr(dist, "get_world_size", lambda: 2)
    monkeypatch.setattr(dist, "get_rank", lambda: rank)

    def check(model: Any) -> bool:
        checks_seen.append(model)
        callbacks.default_callbacks = {}
        return owner_decision

    def broadcast(decision: Any, *, src: int) -> None:
        broadcasts.append(src)
        assert decision.dtype == torch.int32
        decision.fill_(owner_decision)

    monkeypatch.setattr(checks, "check_amp", check)
    monkeypatch.setattr(dist, "broadcast", broadcast)
    model = object()
    assert yolo._amp_decision(model, torch.device("cpu"), 2, True) == owner_decision
    assert checks_seen == ([model] if rank == 0 else [])
    assert broadcasts == [0]
    assert callbacks.default_callbacks == original_callbacks


def test_yolo_amp_refuses_missing_distributed_group(monkeypatch: pytest.MonkeyPatch) -> None:
    import torch
    import torch.distributed as dist

    monkeypatch.setattr(dist, "is_initialized", lambda: False)
    with pytest.raises(RuntimeError, match="initialized worker process group"):
        yolo._amp_decision(object(), torch.device("cpu"), 2, True)


def test_disabled_yolo_amp_does_not_probe_or_require_a_process_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import torch
    import torch.distributed as dist
    from ultralytics.utils import checks

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("Explicit FP32 must not run an AMP probe or a collective")

    monkeypatch.setattr(checks, "check_amp", forbidden)
    monkeypatch.setattr(dist, "broadcast", forbidden)
    assert not yolo._amp_decision(object(), torch.device("cpu"), 1, False)


@pytest.mark.parametrize(("selection", "expected"), [("yolo11n", 96), ("yolov5n6u", 128)])
def test_yolo_validation_batch_rounds_nominal_resolution_without_mosaic(
    tmp_path: Path, selection: str, expected: int
) -> None:
    import torch

    request = _request(tmp_path)
    request = request.model_copy(
        update={
            "profile": request.profile.model_copy(
                update={
                    "model": select_models((selection,))[0],
                    "nominal_size": (65, 65),
                    "effective_size": (160, 160),
                }
            )
        }
    )
    batch = yolo._batch(request, 2, torch.device("cpu"), validation=True)
    assert tuple(batch["img"].shape) == (2, 3, expected, expected)
    assert batch["img"].dtype == torch.uint8
    assert batch["batch_idx"].bincount().tolist() == [2, 2]
    assert batch["ori_shape"] == [(expected, expected), (expected, expected)]


def test_yolo_synthetic_density_classes_and_geometry_are_bounded(tmp_path: Path) -> None:
    import torch

    request = _request(tmp_path)
    batch = yolo._batch(request, 2, torch.device("cpu"))
    assert tuple(batch["img"].shape) == (2, 3, 32, 32)
    assert batch["batch_idx"].bincount().tolist() == [8, 8]
    assert batch["cls"].unique().tolist() == [0.0, 1.0, 2.0]
    boxes = batch["bboxes"]
    assert torch.all(boxes[:, :2] - boxes[:, 2:] / 2 >= 0)
    assert torch.all(boxes[:, :2] + boxes[:, 2:] / 2 <= 1)


@pytest.mark.parametrize(("iterations", "expected"), [(1, "AdamW"), (10001, "MuSGD")])
def test_recorded_yolo_optimizer_paths_match_installed_native_resolution(
    iterations: int, expected: str
) -> None:
    import torch
    from ultralytics.models.yolo.detect import DetectionTrainer

    model = torch.nn.Module()
    model.model = torch.nn.Sequential(torch.nn.Linear(2, 2))
    trainer: Any = SimpleNamespace(args=SimpleNamespace(lr0=0.01), data={"nc": 150})
    optimizer = DetectionTrainer.build_optimizer(  # type: ignore[no-untyped-call]
        trainer, model, name="auto", iterations=iterations
    )
    assert type(optimizer).__name__ == expected
    assert trainer.args.optimizer == expected
    assert trainer.args.warmup_bias_lr == 0


def test_native_estimator_rejects_multi_gpu_before_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter, "discover_gpus", lambda: pytest.fail("multi-GPU probe discovered GPUs")
    )
    with pytest.raises(ValueError, match="exactly one GPU"):
        adapter.NativeBatchProbe().run(sample_profile(2), SyntheticWorkload(), SearchSettings(), 4)
