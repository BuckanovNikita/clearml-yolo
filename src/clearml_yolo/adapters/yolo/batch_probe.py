"""Bounded real YOLO loss/optimizer/EMA probes without trainer AutoBatch fallback."""

import math
import os
from collections.abc import Iterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
from clearml_yolo.adapters.yolo.config import native_defaults
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult


def _batch(
    request: BatchProbeRequest, count: int, device: Any, *, validation: bool = False
) -> dict[str, Any]:
    import torch

    stride = 64 if request.profile.model.architecture.endswith("6u.pt") else 32
    height, width = (
        tuple(math.ceil(size / stride) * stride for size in request.profile.nominal_size)
        if validation
        else request.profile.effective_size
    )
    # Mosaic can retain four input target populations. Use its upper bound rather
    # than a randomly sparse augmentation draw when allocating target/loss tensors.
    objects = request.workload.objects_per_image * (1 if validation else 4)
    xy = torch.rand((count * objects, 2), device=device) * 0.8 + 0.1
    wh = torch.rand((count * objects, 2), device=device) * 0.08 + 0.01
    result: dict[str, Any] = {
        "img": (
            torch.randint(0, 256, (count, 3, height, width), dtype=torch.uint8, device=device)
            if validation
            else torch.rand((count, 3, height, width), device=device)
        ),
        "batch_idx": torch.arange(count, device=device).repeat_interleave(objects),
        "cls": (torch.arange(count * objects, device=device) % request.workload.classes)
        .float()
        .unsqueeze(1),
        "bboxes": torch.cat((xy, wh), dim=1),
    }
    if validation:
        rank = int(os.environ.get("LOCAL_RANK", "0"))
        result.update(
            ori_shape=[(height, width)] * count,
            ratio_pad=[((1.0, 1.0), (0.0, 0.0))] * count,
            im_file=[
                str(request.output / f"rank-{rank}-image-{index}.png") for index in range(count)
            ],
        )
    return result


def _amp_decision(model: Any, device: Any, world_size: int, requested: bool | str) -> bool:
    """Match the native rank-zero AMP check and its collective precision decision."""
    import torch
    import torch.distributed as dist
    from ultralytics.utils import callbacks
    from ultralytics.utils.checks import check_amp

    if world_size > 1 and (not dist.is_initialized() or dist.get_world_size() != world_size):
        raise RuntimeError("YOLO AMP selection requires the initialized worker process group")
    rank = dist.get_rank() if world_size > 1 else 0
    decision = torch.tensor(requested not in {False, "fp32"}, dtype=torch.int32, device=device)
    if rank == 0 and bool(decision) and requested != "bf16":
        saved_callbacks = callbacks.default_callbacks.copy()
        try:
            decision.fill_(bool(check_amp(model)))  # type: ignore[no-untyped-call]
        finally:
            callbacks.default_callbacks = saved_callbacks
    if world_size > 1:
        dist.broadcast(decision, src=0)
    return bool(decision)


def probe(request: BatchProbeRequest) -> ProbeRankResult:
    import torch
    from torch.nn.parallel import DistributedDataParallel
    from ultralytics.models import YOLO
    from ultralytics.models.yolo.detect import DetectionTrainer
    from ultralytics.nn.tasks import DetectionModel
    from ultralytics.utils.torch_utils import ModelEMA, attempt_compile

    rank = int(os.environ["LOCAL_RANK"])
    world_size = request.profile.world_size
    batch = request.global_batch // world_size
    device = torch.device("cuda", rank)
    torch.manual_seed(0)
    torch.cuda.reset_peak_memory_stats(device)
    memory = GPUMemory(rank)
    weights: Any = YOLO(request.profile.model.architecture).model
    # Pinned native constructors and optimizer hooks have no complete typed signatures.
    model: Any = DetectionModel(  # type: ignore[no-untyped-call]
        weights.yaml, nc=request.workload.classes, verbose=False
    )
    model.load(weights)
    del weights
    values = native_defaults() | {"imgsz": request.profile.effective_size[0]}
    model.args = SimpleNamespace(**values)
    model.names = {index: str(index) for index in range(request.workload.classes)}
    model.nc = request.workload.classes
    model.to(device=device, memory_format=torch.channels_last)
    amp = _amp_decision(model, device, world_size, values["amp"])
    model = attempt_compile(model, device=device, mode=request.profile.compilation)
    for name, parameter in model.named_parameters():
        if ".dfl" in name:
            parameter.requires_grad_(False)
    if world_size > 1:
        model = DistributedDataParallel(
            model,
            device_ids=[rank],
            static_graph=bool(request.profile.compilation),
            find_unused_parameters=not bool(request.profile.compilation),
            forward_sync_buffers=False,
        )
    accumulation = max(round(int(values["nbs"]) / request.global_batch), 1)
    # Use the installed native optimizer resolver, including both auto paths.
    trainer: Any = SimpleNamespace(
        args=SimpleNamespace(**values), data={"nc": request.workload.classes}
    )
    optimizer = DetectionTrainer.build_optimizer(  # type: ignore[no-untyped-call]
        trainer,
        model,
        name="auto",
        lr=values["lr0"],
        momentum=values["momentum"],
        decay=values["weight_decay"] * request.global_batch * accumulation / values["nbs"],
        iterations=10001 if request.optimizer == "MuSGD" else 1,
    )
    if trainer.args.optimizer != request.optimizer:
        raise ValueError("Installed YOLO auto optimizer differs from the recorded profile")
    ema = ModelEMA(model)  # type: ignore[no-untyped-call]
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    trainer.model, trainer.optimizer, trainer.scaler, trainer.ema = model, optimizer, scaler, ema
    trainer.device = device
    memory.observe()
    _optimize(request, trainer, accumulation, amp, memory=memory)
    _validate(
        request,
        ema.ema,
        batch,
        device,
        values,
        amp,
        loss_items=trainer.loss_items,
        memory=memory,
    )
    memory.observe()
    return ProbeRankResult(
        token=request.token,
        rank=rank,
        status="success",
        actual_global_batch=request.global_batch,
        peak_memory_bytes=memory.peak_memory_bytes,
        non_allocator_memory_bytes=memory.non_allocator_memory_bytes,
        warmup_steps=request.settings.warmup_steps,
        measured_steps=request.settings.measured_steps,
        validation_steps=1,
    )


def _optimize(
    request: BatchProbeRequest,
    trainer: Any,
    accumulation: int,
    amp: bool,
    *,
    memory: GPUMemory | None = None,
) -> None:
    import torch
    from ultralytics.models.yolo.detect import DetectionTrainer
    from ultralytics.utils.torch_utils import unwrap_model

    model, optimizer, scaler = trainer.model, trainer.optimizer, trainer.scaler
    world_size, device = request.profile.world_size, trainer.device
    batch = request.global_batch // world_size
    model.train()
    completed = 0
    while completed < request.settings.warmup_steps + request.settings.measured_steps:
        optimizer.zero_grad(set_to_none=True)
        for _microstep in range(accumulation):
            data = _batch(request, batch, device)
            with torch.autocast("cuda", enabled=amp):
                if request.profile.compilation:
                    # Match native training: compile inference, leave target assignment
                    # and loss outside the compiled graph (including its int8 scatter).
                    predictions = model(data["img"])
                    native_model: Any = unwrap_model(model)
                    losses, trainer.loss_items = native_model.loss(data, predictions)
                    del predictions
                else:
                    losses, trainer.loss_items = model(data)
                loss = losses.sum() * world_size
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("YOLO probe produced nonfinite loss")
            scaler.scale(loss).backward()
            del data, losses, loss
        scale = scaler.get_scale()
        DetectionTrainer.optimizer_step(trainer)  # type: ignore[no-untyped-call]
        if memory is not None:
            memory.observe()
        if scaler.get_scale() >= scale:
            completed += 1
        elif scaler.get_scale() < 1:
            raise FloatingPointError("YOLO gradients remain nonfinite after AMP scale reduction")


@dataclass(frozen=True)
class _ValidationLoader:
    batch: dict[str, Any]
    global_images: int

    @property
    def dataset(self) -> range:
        return range(self.global_images)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        yield self.batch

    def __len__(self) -> int:
        return 1


class _BoundedValidation:
    def gather_stats(self) -> None:
        import torch.distributed as dist

        # Private single-rank workers set RANK=0 but need no process group.
        if dist.is_initialized():
            cast(Any, super()).gather_stats()


def _finite_validation_loss(validator: Any) -> None:
    import torch

    if any(not bool(torch.isfinite(value).all()) for value in validator.loss.values()):
        raise FloatingPointError("YOLO probe produced nonfinite validation loss")


def _validate(
    request: BatchProbeRequest,
    model: Any,
    batch: int,
    device: Any,
    values: dict[str, Any],
    amp: bool,
    *,
    loss_items: dict[str, Any],
    memory: GPUMemory | None = None,
) -> None:
    from ultralytics.models.yolo.detect import DetectionValidator

    # Use the native training-validator entrypoint so assignment loss, matching,
    # aggregate metrics, and distributed metric/loss gathers are all measured.
    loader = _ValidationLoader(
        _batch(request, batch * 2, device, validation=True), request.global_batch * 2
    )
    validator_type: Any = type("CYBoundedValidator", (_BoundedValidation, DetectionValidator), {})

    def observe_validation(validator: Any) -> None:
        _finite_validation_loss(validator)
        if memory is not None:
            memory.observe()

    validator = validator_type(
        dataloader=loader,
        save_dir=request.output,
        args=values
        | {
            "imgsz": loader.batch["img"].shape[-1],
            "save": False,
            "plots": False,
            "save_txt": False,
            "save_json": False,
        },
        _callbacks={"on_val_batch_end": [observe_validation]},
    )
    trainer = SimpleNamespace(
        ema=SimpleNamespace(ema=model),
        device=device,
        data={"nc": request.workload.classes, "val": "synthetic"},
        amp=amp,
        loss_items=loss_items,
        stopper=SimpleNamespace(possible_stop=False),
        epoch=0,
        epochs=1,
        world_size=request.profile.world_size,
        label_loss_items=lambda values, prefix: {
            f"{prefix}/{key}": value for key, value in values.items()
        },
    )
    results = validator(trainer=trainer)
    if results is not None and any(not math.isfinite(value) for value in results.values()):
        raise FloatingPointError("YOLO probe produced nonfinite validation metrics")
