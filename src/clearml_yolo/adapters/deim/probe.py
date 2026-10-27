"""Real DEIM optimizer/EMA capacity trials using its approved native recipe."""

import importlib
import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from clearml_yolo.adapters.deim.backend import (
    _native_writer,
    synchronize_buffers,
    training_configuration,
    training_world,
)
from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult

if TYPE_CHECKING:
    import torch


def target_bound(configuration: dict[str, Any], objects_per_image: int) -> int:
    """Bound target amplification from the enabled native mosaic/mixup recipe."""
    loader = configuration["train_dataloader"]
    operations = loader["dataset"]["transforms"]["ops"]
    mosaic = any(
        operation["type"] == "Mosaic" and operation.get("probability", 1) > 0
        for operation in operations
    )
    count = objects_per_image * (4 if mosaic else 1)
    collate = loader["collate_fn"]
    mixed = count * (2 if collate.get("mixup_prob", 0) > 0 else 1)
    copied = count + (collate.get("num_objects", 3) if collate.get("copyblend_prob", 0) > 0 else 0)
    return int(max(mixed, copied))


def synthetic_batch(
    batch: int,
    shape: tuple[int, int],
    objects: int,
    classes: int,
    device: "torch.device",
    *,
    rank: int = 0,
) -> tuple["torch.Tensor", list[dict[str, "torch.Tensor"]]]:
    import torch

    height, width = shape
    images = torch.rand((batch, 3, height, width), device=device).mul_(4).sub_(2)
    sequence = torch.arange(objects, device=device)
    grid = math.ceil(math.sqrt(objects))
    boxes = torch.stack(
        (
            (sequence.remainder(grid) + 0.5) / grid,
            (sequence.div(grid, rounding_mode="floor") + 0.5) / grid,
            torch.full((objects,), 0.5 / grid, device=device),
            torch.full((objects,), 0.5 / grid, device=device),
        ),
        dim=1,
    )
    labels = sequence.remainder(classes)
    targets = [
        {
            "boxes": boxes.clone(),
            "labels": labels.clone(),
            "area": boxes[:, 2] * boxes[:, 3] * height * width,
            "iscrowd": torch.zeros(objects, dtype=torch.int64, device=device),
            "image_id": torch.tensor([rank * batch + index], device=device),
            "orig_size": torch.tensor([width, height], device=device),
            "size": torch.tensor([width, height], device=device),
            "mixup": torch.ones(objects, device=device),
        }
        for index in range(batch)
    ]
    return images, targets


@dataclass
class _OptimizerUpdates:
    completed: int = 0

    def count(self, _optimizer: Any, _args: Any, _kwargs: Any) -> None:
        self.completed += 1


def training_steps(
    solver: Any,
    request: BatchProbeRequest,
    per_rank: int,
    objects: int,
    *,
    memory: GPUMemory | None = None,
) -> int:
    """Count real optimizer calls, including AMP skips, with finite-loss checks."""
    import torch

    total = request.settings.warmup_steps + request.settings.measured_steps
    updates = _OptimizerUpdates()
    handle = solver.optimizer.register_step_post_hook(updates.count)
    solver.model.train()
    solver.criterion.train()
    attempts = 0
    try:
        while updates.completed < total:
            if attempts >= total * 4:
                raise FloatingPointError("DEIM scaler repeatedly skipped optimizer updates")
            images, targets = synthetic_batch(
                per_rank,
                request.profile.effective_size,
                objects,
                request.workload.classes,
                solver.device,
            )
            solver.optimizer.zero_grad(set_to_none=True)
            with torch.autocast(solver.device.type, enabled=solver.scaler is not None):
                outputs = solver.model(images, targets=targets)
            with torch.autocast(solver.device.type, enabled=False):
                losses = solver.criterion(
                    outputs,
                    targets,
                    epoch=0,
                    step=attempts,
                    global_step=attempts,
                    epoch_step=total,
                )
                loss = sum(losses.values())
            if not torch.isfinite(loss).all():
                raise FloatingPointError("Nonfinite DEIM synthetic training loss")
            if solver.scaler is not None:
                solver.scaler.scale(loss).backward()
                solver.scaler.unscale_(solver.optimizer)
            else:
                loss.backward()
            if solver.cfg.clip_max_norm > 0:
                torch.nn.utils.clip_grad_norm_(solver.model.parameters(), solver.cfg.clip_max_norm)
            if solver.scaler is not None:
                solver.scaler.step(solver.optimizer)
                solver.scaler.update()
            else:
                solver.optimizer.step()
            synchronize_buffers(solver.model)
            if solver.ema is not None:
                solver.ema.update(solver.model)
            if solver.lr_warmup_scheduler is not None:
                solver.lr_warmup_scheduler.step()
            if memory is not None:
                memory.observe()
            attempts += 1
    finally:
        handle.remove()
    return updates.completed


@dataclass(frozen=True)
class _ValidationBatch:
    images: "torch.Tensor"
    targets: list[dict[str, "torch.Tensor"]]

    def __iter__(self) -> Iterator[tuple["torch.Tensor", list[dict[str, "torch.Tensor"]]]]:
        yield self.images, self.targets

    def __len__(self) -> int:
        return 1


def _coco_annotations(
    request: BatchProbeRequest, template: dict[str, "torch.Tensor"]
) -> dict[str, Any]:
    height, width = request.profile.nominal_size
    boxes = template["boxes"].cpu().tolist()
    labels = template["labels"].cpu().tolist()
    annotations: list[dict[str, Any]] = []
    for image in range(request.global_batch):
        for box, label in zip(boxes, labels, strict=True):
            cx, cy, box_width, box_height = box
            annotations.append(
                {
                    "id": len(annotations) + 1,
                    "image_id": image,
                    "category_id": label,
                    "bbox": [
                        (cx - box_width / 2) * width,
                        (cy - box_height / 2) * height,
                        box_width * width,
                        box_height * height,
                    ],
                    "area": box_width * width * box_height * height,
                    "iscrowd": 0,
                }
            )
    return {
        "info": {},
        "images": [
            {"id": image, "width": width, "height": height} for image in range(request.global_batch)
        ],
        "categories": [
            {"id": label, "name": str(label)} for label in range(request.workload.classes)
        ],
        "annotations": annotations,
    }


def validate(
    solver: Any, module_name: str, request: BatchProbeRequest, per_rank: int, rank: int
) -> None:
    """Run the native bounded validation/evaluator while optimizer and EMA stay resident."""
    import torch

    engine = importlib.import_module(f"{module_name}.solver.det_engine")
    data = importlib.import_module(f"{module_name}.data")
    coco_module = importlib.import_module("faster_coco_eval")
    images, targets = synthetic_batch(
        per_rank,
        request.profile.nominal_size,
        request.workload.objects_per_image,
        request.workload.classes,
        solver.device,
        rank=rank,
    )
    coco = coco_module.COCO()
    coco.dataset = _coco_annotations(request, targets[0])
    coco.createIndex()
    evaluator = data.CocoEvaluator(coco, ["bbox"])
    module = solver.ema.module if solver.ema is not None else solver.cfg.model
    synchronize_buffers(module)
    with torch.no_grad():
        engine.evaluate(
            module,
            solver.criterion,
            solver.postprocessor,
            _ValidationBatch(images, targets),
            evaluator,
            solver.device,
        )


def probe(request: BatchProbeRequest) -> ProbeRankResult:
    import torch

    config = request.config
    if config is None or config.backend != "deimv2":
        raise ValueError("DEIM probe requires a prepared DEIM model configuration")
    if request.optimizer != "AdamW" or request.global_batch != config.train.batch:
        raise ValueError("DEIM probe request disagrees with the resolved native recipe")
    config = config.model_copy(deep=True)
    rank, world = training_world(config)
    if world != request.profile.world_size:
        raise ValueError("DEIM probe process group differs from recorded hardware count")
    config.train.device = torch.cuda.current_device()
    torch.cuda.reset_peak_memory_stats()
    memory = GPUMemory(torch.cuda.current_device())
    names = tuple(str(label) for label in range(request.workload.classes))
    cfg, solver_module = training_configuration(config, names, request.output)
    writer = _native_writer(lambda *_args: None)
    writer.enabled = False
    cfg.writer = writer
    solver = solver_module.TASKS["detection"](cfg)
    # The verified upstream separates model/loss/EMA construction from data loaders.
    # Invoke that setup seam to preserve native tuning and DDP without fake datasets.
    solver._setup()  # noqa: SLF001
    solver.optimizer = cfg.optimizer
    solver.lr_warmup_scheduler = cfg.lr_warmup_scheduler
    memory.observe()
    try:
        count = training_steps(
            solver,
            request,
            request.global_batch // world,
            target_bound(cfg.yaml_cfg, request.workload.objects_per_image),
            memory=memory,
        )
        module_name = solver_module.__package__.rsplit(".", 1)[0]
        validate(solver, module_name, request, request.global_batch // world, rank)
        memory.observe()
        return ProbeRankResult(
            token=request.token,
            rank=rank,
            status="success",
            actual_global_batch=request.global_batch,
            peak_memory_bytes=memory.peak_memory_bytes,
            non_allocator_memory_bytes=memory.non_allocator_memory_bytes,
            warmup_steps=request.settings.warmup_steps,
            measured_steps=count - request.settings.warmup_steps,
            validation_steps=1,
        )
    finally:
        writer.close()
