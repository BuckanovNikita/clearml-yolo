"""Native Torchvision loss optimization, optional EMA and validation-selected checkpoints."""

import csv
import importlib.metadata
import math
from collections.abc import Callable
from contextlib import ExitStack, nullcontext
from pathlib import Path
from typing import Any, Literal

import torch
from torch import Tensor, distributed
from torch.nn.parallel import DistributedDataParallel
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from torch.utils.data import DataLoader, DistributedSampler

from clearml_yolo.adapters.storage.filesystem import validate_output_tree, write_path
from clearml_yolo.adapters.torchvision.checkpoint import checkpoint_state
from clearml_yolo.adapters.torchvision.configuration import DetectorBuilder
from clearml_yolo.adapters.torchvision.data import collate_detection, prepared_datasets
from clearml_yolo.adapters.torchvision.distributed import (
    DistributedEvaluationSampler,
    synchronize_buffers,
    training_context,
    unwrap_model,
    wrap_model,
)
from clearml_yolo.adapters.torchvision.evaluation import evaluate_coco
from clearml_yolo.adapters.torchvision.transform import canvas_size
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.models import (
    BackendTrainResult,
    CheckpointMetadata,
    ModelConfig,
    Preprocessing,
    TrainSettings,
)
from clearml_yolo.core.transforms import TransformConfig


def _training_epoch(
    model: Any,
    loader: DataLoader[tuple[Tensor, dict[str, Tensor]]],
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    settings: TrainSettings,
    device: torch.device,
    ema: AveragedModel | None,
    *,
    on_optimizer_step: Callable[[], None] | None = None,
) -> float:
    model.train()
    optimizer.zero_grad(set_to_none=True)
    total = 0.0
    for index, (images, targets) in enumerate(loader):
        device_images = [image.to(device) for image in images]
        device_targets = [
            {key: value.to(device) for key, value in target.items()} for target in targets
        ]
        start = (index // settings.grad_accum_steps) * settings.grad_accum_steps
        window = min(settings.grad_accum_steps, len(loader) - start)
        update = (index + 1) % settings.grad_accum_steps == 0 or index + 1 == len(loader)
        synchronization = (
            model.no_sync()
            if isinstance(model, DistributedDataParallel) and not update
            else nullcontext()
        )
        # DDP requires no_sync around forward as well as backward. Every rank's
        # training sampler yields the same number of microbatches/windows.
        with synchronization:
            with torch.autocast(device_type=device.type, enabled=scaler.is_enabled()):
                losses = model(device_images, device_targets)
                loss = torch.stack(list(losses.values())).sum()
            value = float(loss.detach())
            if not math.isfinite(value):
                raise FloatingPointError("Torchvision training produced a nonfinite loss")
            total += value
            # Torch's Tensor.backward implementation lacks a complete typed signature.
            scaler.scale(loss / window).backward()  # type: ignore[no-untyped-call]
        if update:
            scale = scaler.get_scale()
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
            synchronize_buffers(model)
            if ema is not None and scaler.get_scale() >= scale:
                ema.update_parameters(unwrap_model(model))
            if on_optimizer_step is not None and scaler.get_scale() >= scale:
                on_optimizer_step()
    population = torch.tensor([total, len(loader)], dtype=torch.float64, device=device)
    if distributed.is_available() and distributed.is_initialized():
        distributed.all_reduce(population)
    return float(population[0] / population[1])


def _checkpoint(
    model: Any, path: Path, epoch: int, score: float, metadata: CheckpointMetadata
) -> None:
    path = write_path(path)
    torch.save(
        {
            "state_dict": unwrap_model(model).state_dict(),
            "epoch": epoch,
            "selection_metric": score,
            "class_names": list(metadata.class_names),
            "preprocessing": metadata.preprocessing.model_dump(mode="json"),
        },
        path,
    )


class _TrainingRun:
    """Own model/optimizer/loaders for one externally supervised rank."""

    def __init__(
        self,
        config: ModelConfig,
        prepared: PreparedDataset,
        *,
        build_model: DetectorBuilder,
        label_offset: Literal[0, 1],
        transforms: TransformConfig | None,
    ) -> None:
        self.settings = config.train
        self.context = training_context(self.settings.device, self.settings.batch)
        self.train_data, self.validation_data, names = prepared_datasets(
            prepared, transforms=transforms, seed=self.settings.seed, label_offset=label_offset
        )
        torch.manual_seed(self.settings.seed)
        model = build_model(
            config.preset,
            len(names),
            pretrained=self.settings.pretrained and self.settings.weights is None,
            backbone_weights=self.settings.backbone_weights,
            image_size=self.settings.imgsz,
        )
        if self.settings.weights is not None:
            model.load_state_dict(checkpoint_state(self.settings.weights), strict=True)
        model.to(self.context.device)
        self.model = wrap_model(model, self.context)
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=self.settings.lr, weight_decay=self.settings.weight_decay
        )
        self.scaler = torch.amp.GradScaler(
            "cuda", enabled=self.settings.amp and self.context.device.type == "cuda"
        )
        self.ema = (
            AveragedModel(
                unwrap_model(self.model),
                multi_avg_fn=get_ema_multi_avg_fn(0.999),  # type: ignore[no-untyped-call]
                use_buffers=True,
            )
            if self.settings.use_ema
            else None
        )
        self.train_loader, self.val_loader = self._loaders()
        self.metadata = CheckpointMetadata(
            backend=config.backend,
            preset=config.preset,
            class_names=names,
            preprocessing=Preprocessing(resize="letterbox", size=canvas_size(self.settings.imgsz)),
            dependencies={
                name: importlib.metadata.version(name)
                for name in ("torch", "torchvision", "timm", "pycocotools")
            },
        )

    def _loaders(
        self,
    ) -> tuple[
        DataLoader[tuple[Tensor, dict[str, Tensor]]], DataLoader[tuple[Tensor, dict[str, Tensor]]]
    ]:
        context = self.context
        sampler: DistributedSampler[tuple[Tensor, dict[str, Tensor]]] | None = (
            DistributedSampler(
                self.train_data,
                num_replicas=context.world_size,
                rank=context.rank,
                shuffle=True,
                seed=self.settings.seed,
            )
            if context.world_size > 1
            else None
        )
        train = DataLoader(
            self.train_data,
            batch_size=context.per_rank_batch,
            shuffle=sampler is None,
            sampler=sampler,
            num_workers=self.settings.workers,
            collate_fn=collate_detection,
        )
        validation = DataLoader(
            self.validation_data,
            batch_size=context.per_rank_batch,
            sampler=DistributedEvaluationSampler(
                len(self.validation_data), context.rank, context.world_size
            ),
            num_workers=self.settings.workers,
            collate_fn=collate_detection,
        )
        return train, validation

    def epoch(self, epoch: int) -> tuple[Any, dict[str, float]]:
        if isinstance(self.train_loader.sampler, DistributedSampler):
            self.train_loader.sampler.set_epoch(epoch)
        loss = _training_epoch(
            self.model,
            self.train_loader,
            self.optimizer,
            self.scaler,
            self.settings,
            self.context.device,
            self.ema,
        )
        evaluated = self.ema.module if self.ema is not None else unwrap_model(self.model)
        synchronize_buffers(evaluated)
        metrics = {
            "train/loss": loss,
            **evaluate_coco(
                evaluated, self.validation_data, iter(self.val_loader), self.context.device
            ),
        }
        return evaluated, metrics


def _fit(
    run: _TrainingRun, output: Path, report: Callable[[str, float, int], None]
) -> tuple[Path, Path, dict[str, float]]:
    output.mkdir(parents=True, exist_ok=True)
    best_path = write_path(output / "best.pth")
    metrics_path = write_path(output / "metrics.csv")
    best_score = -math.inf
    best_metrics: dict[str, float] = {}
    with ExitStack() as stack:
        stream = (
            stack.enter_context(metrics_path.open("w", newline="", encoding="utf-8"))
            if run.context.rank == 0
            else None
        )
        writer = (
            csv.DictWriter(
                stream,
                fieldnames=["epoch", "train/loss", "val/map50_95", "val/map50", "val/recall"],
            )
            if stream is not None
            else None
        )
        if writer is not None:
            writer.writeheader()
        for epoch in range(run.settings.epochs):
            evaluated, metrics = run.epoch(epoch)
            if writer is not None and stream is not None:
                for name, value in metrics.items():
                    report(name, value, epoch)
                writer.writerow({"epoch": epoch, **metrics})
                stream.flush()
            score = metrics["val/map50_95"]
            if score > best_score:
                best_score, best_metrics = score, metrics
                if run.context.rank == 0:
                    _checkpoint(evaluated, best_path, epoch, score, run.metadata)
    if run.context.world_size > 1:
        distributed.barrier()
    if not best_path.is_file():
        raise RuntimeError("Torchvision training did not produce a validation-selected checkpoint")
    return best_path, metrics_path, best_metrics


def train_native(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
    *,
    build_model: DetectorBuilder,
    label_offset: Literal[0, 1],
    transforms: TransformConfig | None = None,
) -> BackendTrainResult:
    output = validate_output_tree(output)
    run = _TrainingRun(
        config, prepared, build_model=build_model, label_offset=label_offset, transforms=transforms
    )
    weights, metrics_path, metrics = _fit(run, output, report)
    settings = run.settings
    global_batch = run.context.per_rank_batch * run.context.world_size
    return BackendTrainResult(
        weights=weights,
        metadata=run.metadata,
        metrics=metrics,
        artifacts=[metrics_path],
        effective_args=settings.model_dump(mode="json")
        | {
            "backend": config.backend,
            "preset": config.preset,
            "device": str(run.context.device),
            "imgsz": list(canvas_size(settings.imgsz)),
            "amp": run.scaler.is_enabled(),
            "optimizer": "AdamW",
            "ema_decay": 0.999 if run.ema is not None else None,
            "selection_metric": "val/map50_95",
            "global_batch": global_batch,
            "per_rank_batch": run.context.per_rank_batch,
            "world_size": run.context.world_size,
            "effective_optimizer_batch": global_batch * settings.grad_accum_steps,
            "preprocessing": run.metadata.preprocessing.model_dump(),
        },
    )
