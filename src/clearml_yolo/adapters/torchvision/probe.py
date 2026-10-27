"""Real Torchvision training-capacity trials using the production optimization loop."""

import math
from typing import Literal, override

import torch
from torch import Tensor
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from torch.utils.data import DataLoader, Dataset

from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
from clearml_yolo.adapters.torchvision.checkpoint import checkpoint_state
from clearml_yolo.adapters.torchvision.configuration import DetectorBuilder
from clearml_yolo.adapters.torchvision.data import collate_detection
from clearml_yolo.adapters.torchvision.distributed import (
    TrainingContext,
    synchronize_buffers,
    training_context,
    unwrap_model,
    wrap_model,
)
from clearml_yolo.adapters.torchvision.training import _training_epoch
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult
from clearml_yolo.core.batch_estimation import TrialStatus
from clearml_yolo.core.models import ModelConfig


class SyntheticDataset(Dataset[tuple[Tensor, dict[str, Tensor]]]):
    """Generate fixed-density targets lazily so the search never preallocates a corpus."""

    def __init__(self, request: BatchProbeRequest, count: int, label_offset: Literal[0, 1]) -> None:
        self.request = request
        self.count = count
        self.label_offset = label_offset

    def __len__(self) -> int:
        return self.count

    @override
    def __getitem__(self, index: int) -> tuple[Tensor, dict[str, Tensor]]:
        height, width = self.request.profile.effective_size
        objects = self.request.workload.objects_per_image
        generator = torch.Generator().manual_seed(index)
        image = torch.rand((3, height, width), generator=generator)
        grid = math.ceil(math.sqrt(objects))
        positions = torch.arange(objects)
        left = (positions % grid).float() * (width / grid)
        top = (positions // grid).float() * (height / grid)
        boxes = torch.stack(
            (left, top, left + width / grid * 0.8, top + height / grid * 0.8), dim=1
        )
        labels = positions % self.request.workload.classes + self.label_offset
        return image, {
            "boxes": boxes,
            "labels": labels,
            "image_id": torch.tensor(index, dtype=torch.int64),
            "area": (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]),
            "iscrowd": torch.zeros(objects, dtype=torch.int64),
        }


class _ProbeRun:
    def __init__(
        self,
        request: BatchProbeRequest,
        config: ModelConfig,
        context: TrainingContext,
        build_model: DetectorBuilder,
        label_offset: Literal[0, 1],
        *,
        memory: GPUMemory | None = None,
    ) -> None:
        self.request = request
        self.settings = config.train
        self.context = context
        self.label_offset = label_offset
        self.memory = memory
        torch.manual_seed(self.settings.seed)
        model = build_model(
            config.preset,
            request.workload.classes,
            pretrained=self.settings.pretrained and self.settings.weights is None,
            backbone_weights=self.settings.backbone_weights,
            image_size=request.profile.effective_size,
        )
        if self.settings.weights is not None:
            model.load_state_dict(checkpoint_state(self.settings.weights), strict=True)
        model.to(context.device)
        self.model = wrap_model(model, context)
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=self.settings.lr, weight_decay=self.settings.weight_decay
        )
        self.scaler = torch.amp.GradScaler(
            "cuda", enabled=self.settings.amp and context.device.type == "cuda"
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
        self.completed_steps = 0
        if self.memory is not None:
            self.memory.observe()

    def _optimizer_step(self) -> None:
        self.completed_steps += 1
        if self.memory is not None:
            self.memory.observe()

    def train(self, steps: int) -> int:
        before = self.completed_steps
        while self.completed_steps - before < steps:
            remaining = steps - (self.completed_steps - before)
            self._train_attempts(remaining)
            if self.scaler.is_enabled() and self.scaler.get_scale() < 1:
                raise FloatingPointError(
                    "Probe gradients remain nonfinite after AMP scale reduction"
                )
        return self.completed_steps - before

    def _train_attempts(self, steps: int) -> None:
        dataset = SyntheticDataset(
            self.request,
            steps * self.context.per_rank_batch * self.settings.grad_accum_steps,
            self.label_offset,
        )
        loader = DataLoader(
            dataset,
            batch_size=self.context.per_rank_batch,
            num_workers=self.settings.workers,
            collate_fn=collate_detection,
        )
        _training_epoch(
            self.model,
            loader,
            self.optimizer,
            self.scaler,
            self.settings,
            self.context.device,
            self.ema,
            on_optimizer_step=self._optimizer_step,
        )

    def validate(self) -> int:
        dataset = SyntheticDataset(self.request, self.context.per_rank_batch, self.label_offset)
        images, _ = collate_detection([dataset[index] for index in range(len(dataset))])
        model = self.ema.module if self.ema is not None else unwrap_model(self.model)
        synchronize_buffers(model)
        model.eval()
        with torch.inference_mode():
            predictions = model([image.to(self.context.device) for image in images])
        for prediction in predictions:
            if any(not torch.isfinite(prediction[key]).all() for key in ("boxes", "scores")):
                raise FloatingPointError("Probe validation produced nonfinite predictions")
            labels = prediction["labels"] - self.label_offset
            if ((labels < 0) | (labels >= self.request.workload.classes)).any():
                raise ValueError("Probe validation emitted an unknown foreground label")
        if self.memory is not None:
            self.memory.observe()
        return 1


def _config(request: BatchProbeRequest) -> ModelConfig:
    config = request.config
    if config is None:
        raise ValueError("Torchvision probe requires an owner-prepared model configuration")
    if config.backend not in {"fasterrcnn", "fcos"}:
        raise ValueError("Torchvision probe requires a Torchvision detector configuration")
    if (config.backend, config.preset) != (
        request.profile.model.backend,
        request.profile.model.preset,
    ):
        raise ValueError("Probe profile disagrees with model selection")
    if request.optimizer != "AdamW" or request.profile.compilation is not False:
        raise ValueError("Torchvision probes require their native uncompiled AdamW recipe")
    return config


def probe(
    request: BatchProbeRequest, *, build_model: DetectorBuilder, label_offset: Literal[0, 1]
) -> ProbeRankResult:
    config = _config(request)
    context = training_context(config.train.device, request.global_batch)
    if context.device.type != "cuda":
        raise ValueError("Batch capacity estimation requires a CUDA device")
    if context.world_size != request.profile.world_size:
        raise ValueError("Probe world size disagrees with its recorded GPU profile")
    torch.cuda.reset_peak_memory_stats(context.device)
    memory = GPUMemory(context.device.index)
    status: TrialStatus = "success"
    diagnostic = ""
    warmup_steps = measured_steps = validation_steps = 0
    actual_global_batch = None
    try:
        run = _ProbeRun(request, config, context, build_model, label_offset, memory=memory)
        warmup_steps = run.train(request.settings.warmup_steps)
        measured_steps = run.train(request.settings.measured_steps)
        validation_steps = run.validate()
        memory.observe()
        actual_global_batch = context.per_rank_batch * context.world_size
    except torch.cuda.OutOfMemoryError as error:
        status, diagnostic = "oom", str(error)
    except FloatingPointError as error:
        status, diagnostic = "nonfinite", str(error)
    except FileNotFoundError as error:
        status, diagnostic = "missing_asset", str(error)
    return ProbeRankResult(
        token=request.token,
        rank=context.rank,
        status=status,
        diagnostic=diagnostic,
        actual_global_batch=actual_global_batch,
        warmup_steps=warmup_steps,
        measured_steps=measured_steps,
        validation_steps=validation_steps,
        peak_memory_bytes=memory.peak_memory_bytes,
        non_allocator_memory_bytes=memory.non_allocator_memory_bytes,
    )
