"""DEIM synthetic probes execute real CPU optimizer updates and exact rank shards."""

import multiprocessing
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, override
from uuid import uuid4

import pytest

from clearml_yolo.adapters.deim.probe import (
    _coco_annotations,
    synthetic_batch,
    target_bound,
    training_steps,
)
from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
from clearml_yolo.application.training_workers import BatchProbeRequest
from clearml_yolo.core.batch_estimation import SearchSettings, SyntheticWorkload, select_models
from clearml_yolo.core.models import ModelConfig, TrainSettings
from test_batch_estimate_workflow import sample_profile


def _request(tmp_path: Path) -> BatchProbeRequest:
    profile = sample_profile().model_copy(
        update={
            "model": select_models(("deimv2/s",))[0],
            "nominal_size": (128, 128),
            "effective_size": (160, 160),
            "optimizers": ("AdamW",),
            "compilation": False,
        }
    )
    return BatchProbeRequest(
        token=uuid4().hex,
        profile=profile,
        workload=SyntheticWorkload(classes=3, objects_per_image=5),
        settings=SearchSettings(),
        global_batch=2,
        optimizer="AdamW",
        output=tmp_path,
        config=ModelConfig(
            backend="deimv2",
            preset="s",
            train=TrainSettings(batch=2, imgsz=128, pretrained=False, device="cpu"),
        ),
    )


class _EMA:
    def __init__(self, model: Any) -> None:
        self.module = deepcopy(model)
        self.updates = 0

    def update(self, model: Any) -> None:
        self.updates += 1
        self.module.load_state_dict(model.state_dict())


def _solver() -> Any:
    import torch

    class Model(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(0.5))

        @override
        def forward(self, images: torch.Tensor, **kwargs: Any) -> torch.Tensor:
            return images.mean() * self.weight

    class Criterion(torch.nn.Module):
        @override
        def forward(
            self, outputs: torch.Tensor, *args: Any, **kwargs: Any
        ) -> dict[str, torch.Tensor]:
            return {"loss": (outputs - 1).square()}

    model = Model()
    return SimpleNamespace(
        model=model,
        criterion=Criterion(),
        optimizer=torch.optim.AdamW(model.parameters()),
        device=torch.device("cpu"),
        scaler=None,
        cfg=SimpleNamespace(clip_max_norm=0.1),
        ema=_EMA(model),
        lr_warmup_scheduler=None,
    )


@pytest.mark.parametrize(
    ("mosaic", "mixup", "copyblend", "expected"),
    [
        (False, False, False, 300),
        (True, False, False, 1200),
        (True, True, False, 2400),
        (True, False, True, 1203),
    ],
)
def test_probe_bounds_native_augmentation_target_growth(
    mosaic: bool,
    mixup: bool,
    copyblend: bool,
    expected: int,
) -> None:
    configuration = {
        "train_dataloader": {
            "dataset": {"transforms": {"ops": [{"type": "Mosaic", "probability": int(mosaic)}]}},
            "collate_fn": {"mixup_prob": int(mixup), "copyblend_prob": int(copyblend)},
        }
    }
    assert target_bound(configuration, 300) == expected


def test_synthetic_targets_preserve_zero_class_and_valid_box_geometry() -> None:
    import torch

    images, targets = synthetic_batch(2, (128, 160), 300, 150, torch.device("cpu"), rank=1)
    assert tuple(images.shape) == (2, 3, 128, 160)
    assert [target["image_id"].item() for target in targets] == [2, 3]
    assert all(target["labels"].min() == 0 and target["labels"].max() == 149 for target in targets)
    boxes = targets[0]["boxes"]
    assert torch.all(boxes[:, :2] - boxes[:, 2:] / 2 >= 0)
    assert torch.all(boxes[:, :2] + boxes[:, 2:] / 2 <= 1)
    assert targets[0]["orig_size"].tolist() == [160, 128]


def test_probe_counts_real_optimizer_updates_and_ema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solver = _solver()
    observations: list[int] = []
    memory = GPUMemory()
    monkeypatch.setattr(memory, "observe", lambda: observations.append(solver.ema.updates))
    count = training_steps(solver, _request(tmp_path), 2, 5, memory=memory)
    assert count == 15
    assert solver.ema.updates == 15
    assert all(state["step"].item() == 15 for state in solver.optimizer.state.values())
    assert not solver.optimizer._optimizer_step_post_hooks
    assert observations == list(range(1, 16))


def test_amp_skips_do_not_count_as_optimizer_updates(tmp_path: Path) -> None:
    class Scaler:
        def __init__(self) -> None:
            self.calls = 0

        def scale(self, loss: Any) -> Any:
            return loss

        def unscale_(self, optimizer: Any) -> None:
            pass

        def step(self, optimizer: Any) -> None:
            self.calls += 1
            if self.calls > 2:
                optimizer.step()

        def update(self) -> None:
            pass

    solver = _solver()
    solver.scaler = Scaler()
    assert training_steps(solver, _request(tmp_path), 2, 5) == 15
    assert solver.scaler.calls == 17
    assert solver.ema.updates == 17


def test_nonfinite_loss_stops_before_optimizer_state_is_allocated(tmp_path: Path) -> None:
    solver = _solver()
    solver.model.weight.data.fill_(float("nan"))
    with pytest.raises(FloatingPointError, match="Nonfinite DEIM"):
        training_steps(solver, _request(tmp_path), 2, 5)
    assert not solver.optimizer.state
    assert not solver.optimizer._optimizer_step_post_hooks


def test_validation_annotations_cover_global_samples_and_use_xywh(tmp_path: Path) -> None:
    import torch

    request = _request(tmp_path)
    _, targets = synthetic_batch(2, (128, 128), 5, 3, torch.device("cpu"))
    annotations = _coco_annotations(request, targets[0])
    assert len(annotations["images"]) == 2
    assert len(annotations["annotations"]) == 10
    assert {row["category_id"] for row in annotations["annotations"]} == {0, 1, 2}
    assert all(row["bbox"][2] > 0 and row["bbox"][3] > 0 for row in annotations["annotations"])


def _distributed_cpu_worker(rank: int, rendezvous: str, result: Any) -> None:
    import torch
    import torch.distributed as dist

    from clearml_yolo.adapters.deim.backend import _DistributedSolver

    torch.set_num_threads(1)
    dist.init_process_group(
        "gloo", init_method=rendezvous, rank=rank, world_size=2, timeout=timedelta(seconds=15)
    )
    try:

        class Native:
            def train(self) -> None:
                model = torch.nn.Sequential(torch.nn.BatchNorm1d(2), torch.nn.Linear(2, 1))
                self.model = torch.nn.parallel.DistributedDataParallel(model)
                self.optimizer = torch.optim.AdamW(self.model.parameters())
                self.val_dataloader = torch.utils.data.DataLoader(
                    torch.utils.data.TensorDataset(torch.arange(5)), batch_size=1
                )
                self.ema = None

        solver: Any = type("TestSolver", (_DistributedSolver, Native), {})()
        solver.train()
        solver.model(torch.tensor([[rank + 1.0, 2.0], [rank + 2.0, 3.0]])).sum().backward()
        solver.optimizer.step()
        solver.model.eval()
        samples = []
        with torch.no_grad():
            for item in solver.val_dataloader:
                samples.extend(item[0].tolist())
                solver.model(torch.ones(1, 2))
        result.put(
            {
                "rank": rank,
                "samples": samples,
                "buffer": solver.model.module[0].running_mean.tolist(),
                "ddp": type(solver.model) is torch.nn.parallel.DistributedDataParallel,
            }
        )
    finally:
        dist.destroy_process_group()


def test_real_cpu_ranks_finish_unequal_validation_and_synchronize_buffers(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    result = context.Queue()
    rendezvous = (tmp_path / "gloo-store").as_uri()
    processes = [
        context.Process(target=_distributed_cpu_worker, args=(rank, rendezvous, result))
        for rank in range(2)
    ]
    try:
        for process in processes:
            process.start()
        records = [result.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=10)
            assert process.exitcode == 0
        records.sort(key=lambda record: record["rank"])
        assert records[0]["samples"] == [0, 2, 4]
        assert records[1]["samples"] == [1, 3]
        assert records[0]["buffer"] == records[1]["buffer"]
        assert all(record["ddp"] for record in records)
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)
        result.close()
        result.join_thread()
