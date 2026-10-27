"""Real CPU ranks verify accumulation, EMA, unique validation and checkpoint ownership."""

import importlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import pytest
import torch
from torch import Tensor, distributed, nn
from torch._C._distributed_c10d import GradBucket

from clearml_yolo.adapters.torchvision.distributed import (
    DistributedEvaluationSampler,
    training_context,
)
from clearml_yolo.application.training_workers import BatchProbeRequest
from clearml_yolo.core.models import ModelConfig
from test_fasterrcnn_backend import _prepared


@pytest.mark.parametrize(("size", "world"), [(0, 3), (1, 3), (7, 2), (12, 4)])
def test_validation_sampler_never_pads_or_loses_images(size: int, world: int) -> None:
    partitions = [list(DistributedEvaluationSampler(size, rank, world)) for rank in range(world)]
    assert sorted(item for partition in partitions for item in partition) == list(range(size))
    for rank, partition in enumerate(partitions):
        assert len(DistributedEvaluationSampler(size, rank, world)) == len(partition)


@pytest.mark.parametrize("batch", [None, 0, -1])
def test_unresolved_or_invalid_global_batch_is_rejected(batch: int | None) -> None:
    with pytest.raises(ValueError, match="batch"):
        training_context("cpu", batch)


def test_global_batch_must_divide_world_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(distributed, "is_initialized", lambda: True)
    monkeypatch.setattr(distributed, "get_world_size", lambda: 2)
    monkeypatch.setattr(distributed, "get_rank", lambda: 0)
    with pytest.raises(ValueError, match="divisible"):
        training_context("cpu", 3)


class _ToyDetector(nn.Module):
    running: Tensor

    def __init__(self, rank: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.tensor(0.1))
        self.register_buffer("running", torch.zeros(1))
        self.rank = rank

    @override
    def forward(self, images: list[Tensor], targets: list[dict[str, Tensor]] | None = None) -> Any:
        if targets is not None:
            self.running.add_(self.rank + 1)
            # Different rank-local gradients must still produce identical
            # optimizer/EMA parameters through DDP's averaged communication.
            desired = torch.stack([image.mean() for image in images]).mean() + self.rank * 0.1
            return {"loss": (self.weight - desired).square()}
        return [
            {
                "boxes": torch.tensor([[20.0, 10.0, 60.0, 42.0]]),
                "scores": torch.tensor([0.9]),
                "labels": torch.tensor([1]),
            }
            for _ in images
        ]


def _rank_training(rank: int, directory: str) -> None:
    from torch.distributed.algorithms.ddp_comm_hooks.default_hooks import allreduce_hook

    from clearml_yolo.adapters.torchvision import training
    from clearml_yolo.application.contracts import PreparedDataset

    torch.set_num_threads(1)
    root = Path(directory)
    distributed.init_process_group(
        "gloo",
        init_method=(root / "rendezvous").as_uri(),
        rank=rank,
        world_size=2,
        timeout=timedelta(seconds=45),
    )
    try:
        prepared = PreparedDataset.model_validate_json((root / "prepared.json").read_text())
        config = ModelConfig.model_validate(
            {
                "backend": "fasterrcnn",
                "preset": "resnet50_fpn",
                "train": {
                    "device": "cpu",
                    "epochs": 1,
                    "batch": 2,
                    "workers": 0,
                    "pretrained": False,
                    "amp": False,
                    "use_ema": True,
                    "grad_accum_steps": 3,
                },
            }
        )
        emitted: list[str] = []
        captured: list[dict[str, Tensor]] = []
        writes: list[str] = []
        synchronizations: list[int] = []
        original_checkpoint = training._checkpoint
        original_epoch = training._training_epoch

        def checkpoint(*args: Any, **kwargs: Any) -> None:
            writes.append(str(args[1]))
            original_checkpoint(*args, **kwargs)

        def epoch(*args: Any, **kwargs: Any) -> float:
            def communicate(state: Any, bucket: GradBucket) -> torch.futures.Future[Tensor]:
                synchronizations.append(1)
                return allreduce_hook(state, bucket)

            args[0].register_comm_hook(None, communicate)
            result = original_epoch(*args, **kwargs)
            captured.append(
                {key: value.clone() for key, value in args[6].module.state_dict().items()}
            )
            return result

        # These process-local spies observe the actual shared training loop and
        # rank-owned writes without replacing distributed/model behavior.
        training._checkpoint = checkpoint
        training._training_epoch = epoch
        model = _ToyDetector(rank)

        def build_model(*args: Any, **kwargs: Any) -> Any:
            return model

        def report(name: str, _value: float, _step: int) -> None:
            emitted.append(name)

        result = training.train_native(
            config, prepared, root / "run", report, build_model=build_model, label_offset=1
        )
        torch.save(captured[0], root / f"ema-{rank}.pth")
        (root / f"rank-{rank}.json").write_text(
            json.dumps(
                {
                    "metrics": result.metrics,
                    "emitted": emitted,
                    "writes": writes,
                    "effective": result.effective_args,
                    "synchronizations": len(synchronizations),
                }
            )
        )
    finally:
        distributed.destroy_process_group()


def test_real_cpu_ranks_share_ema_and_write_one_checkpoint(tmp_path: Path) -> None:
    prepared = _prepared(tmp_path)
    for split in ("train", "valid"):
        annotation = prepared.data.parent / split / "_annotations.coco.json"
        payload = json.loads(annotation.read_text())
        payload["images"] = [dict(payload["images"][0], id=index) for index in range(1, 8)]
        payload["annotations"] = [
            dict(payload["annotations"][0], id=index, image_id=index) for index in range(1, 8)
        ]
        annotation.write_text(json.dumps(payload))
    (tmp_path / "prepared.json").write_text(prepared.model_dump_json())
    multiprocessing = importlib.import_module("torch.multiprocessing")
    multiprocessing.spawn(_rank_training, args=(str(tmp_path),), nprocs=2, join=True)
    ranks = [json.loads((tmp_path / f"rank-{rank}.json").read_text()) for rank in range(2)]
    assert len(ranks[0]["writes"]) == 1
    assert ranks[1]["writes"] == []
    assert ranks[0]["emitted"]
    assert ranks[1]["emitted"] == []
    assert ranks[0]["metrics"] == ranks[1]["metrics"]
    assert [rank["synchronizations"] for rank in ranks] == [2, 2]
    assert ranks[0]["metrics"]["val/map50"] == pytest.approx(1.0)
    assert ranks[0]["effective"]["per_rank_batch"] == 1
    assert ranks[0]["effective"]["effective_optimizer_batch"] == 6
    states = [torch.load(tmp_path / f"ema-{rank}.pth", weights_only=True) for rank in range(2)]
    assert set(states[0]) == {"weight", "running"}
    for key, tensor in states[0].items():
        torch.testing.assert_close(tensor, states[1][key], rtol=0, atol=0)
    assert float(states[0]["weight"]) > 0.1
    assert float(states[0]["running"]) == pytest.approx(3.001)
    checkpoint = torch.load(tmp_path / "run" / "best.pth", weights_only=True)
    assert set(checkpoint["state_dict"]) == {"weight", "running"}


def _probe_request(tmp_path: Path) -> BatchProbeRequest:
    from clearml_yolo.core.batch_estimation import (
        GPUHardware,
        ModelVariant,
        SearchSettings,
        SyntheticWorkload,
        TrainingProfile,
    )

    return BatchProbeRequest(
        token=uuid4().hex,
        profile=TrainingProfile(
            model=ModelVariant(
                selection="fasterrcnn/resnet50_fpn",
                backend="fasterrcnn",
                preset="resnet50_fpn",
                architecture="fasterrcnn/resnet50_fpn",
            ),
            nominal_size=(128, 128),
            effective_size=(128, 128),
            gpus=(GPUHardware(name="synthetic", total_memory_bytes=1024),),
            dependencies={"torch": "test"},
            precision="fp32",
            compilation=False,
            optimizers=("AdamW",),
            accumulation="fixed:2",
            ema=True,
            augmentation="native",
            implementation_revision="test",
        ),
        workload=SyntheticWorkload(),
        settings=SearchSettings(),
        global_batch=2,
        optimizer="AdamW",
        output=tmp_path,
        config=ModelConfig.model_validate(
            {
                "backend": "fasterrcnn",
                "preset": "resnet50_fpn",
                "train": {
                    "device": "cpu",
                    "batch": 2,
                    "workers": 0,
                    "pretrained": False,
                    "amp": False,
                    "grad_accum_steps": 2,
                    "use_ema": True,
                },
            }
        ),
    )


def test_probe_uses_dense_targets_actual_optimizer_updates_and_ema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
    from clearml_yolo.adapters.torchvision.distributed import TrainingContext
    from clearml_yolo.adapters.torchvision.probe import SyntheticDataset, _ProbeRun

    request = _probe_request(tmp_path)
    dataset = SyntheticDataset(request, 1, 0)
    image, targets = dataset[0]
    assert image.shape == (3, 128, 128)
    assert targets["labels"].tolist() == list(range(150)) * 2
    assert targets["boxes"].shape == (300, 4)
    assert torch.all(targets["boxes"][:, 2:] > targets["boxes"][:, :2])
    model = _ToyDetector(0)

    def build_model(*args: Any, **kwargs: Any) -> Any:
        return model

    context = TrainingContext(0, 1, torch.device("cpu"), 2)
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    memory = GPUMemory()
    observations: list[None] = []
    monkeypatch.setattr(memory, "observe", lambda: observations.append(None))
    try:
        assert request.config is not None
        run = _ProbeRun(request, request.config, context, build_model, 1, memory=memory)
        assert run.train(request.settings.warmup_steps) == 5
        assert run.train(request.settings.measured_steps) == 10
        assert run.completed_steps == 15
        assert run.ema is not None
        assert int(run.ema.n_averaged) == 15
        assert run.validate() == 1
        assert len(observations) == 17
        assert float(model.weight.detach()) > 0.1
    finally:
        torch.set_num_threads(previous)


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (torch.cuda.OutOfMemoryError("allocation failed"), "oom"),
        (FloatingPointError("bad loss"), "nonfinite"),
        (FileNotFoundError("weights absent"), "missing_asset"),
    ],
)
def test_probe_classifies_native_failures_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception, status: str
) -> None:
    from clearml_yolo.adapters.torchvision import probe
    from clearml_yolo.adapters.torchvision.distributed import TrainingContext

    monkeypatch.setattr(
        probe, "training_context", lambda *_: TrainingContext(0, 1, torch.device("cuda", 0), 2)
    )
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda *_: None)

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise failure

    monkeypatch.setattr(probe, "_ProbeRun", fail)
    result = probe.probe(_probe_request(tmp_path), build_model=fail, label_offset=1)
    assert result.status == status
    assert result.peak_memory_bytes == 0
    assert result.non_allocator_memory_bytes == 0
    assert result.actual_global_batch is None
    assert result.measured_steps == 0


def test_probe_refuses_cpu_capacity_claims(tmp_path: Path) -> None:
    from clearml_yolo.adapters.torchvision.probe import probe

    def unused(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("CPU estimation must stop before model construction")

    with pytest.raises(ValueError, match="CUDA"):
        probe(_probe_request(tmp_path), build_model=unused, label_offset=1)
