"""Bounded native RF-DETR optimization at the recipe's largest training shape.

Lightning and RF-DETR remain opaque SDK objects at this adapter boundary. The
native module owns loss, AdamW, AMP, clipping, accumulation and EMA; only the
synthetic input source, spatial envelope and stopping counters differ from fit.
"""

import importlib
import math
import os
from typing import Any, override

import torch
from torch import Tensor
from torch.utils.data import Dataset

from clearml_yolo.adapters.rfdetr.backend import trainer_devices, training_configuration
from clearml_yolo.adapters.runtime.distributed import global_batch_per_rank
from clearml_yolo.adapters.runtime.gpu_memory import GPUMemory
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult
from clearml_yolo.core.batch_estimation import TrialStatus
from clearml_yolo.core.models import ModelConfig


class SyntheticDataset(Dataset[tuple[Tensor, dict[str, Tensor]]]):
    """Native normalized CHW images and zero-based, normalized cxcywh targets."""

    def __init__(self, request: BatchProbeRequest, count: int) -> None:
        self.request = request
        self.count = count

    def __len__(self) -> int:
        return self.count

    @override
    def __getitem__(self, index: int) -> tuple[Tensor, dict[str, Tensor]]:
        height, width = self.request.profile.effective_size
        generator = torch.Generator().manual_seed(index)
        image = torch.rand((3, height, width), generator=generator)
        image.sub_(torch.tensor([0.485, 0.456, 0.406])[:, None, None])
        image.div_(torch.tensor([0.229, 0.224, 0.225])[:, None, None])
        objects = self.request.workload.objects_per_image
        positions = torch.arange(objects)
        grid = math.ceil(math.sqrt(objects))
        cx = (positions % grid + 0.5) / grid
        cy = (positions // grid + 0.5) / grid
        extent = torch.full((objects,), 0.8 / grid)
        return image, {
            "boxes": torch.stack((cx, cy, extent, extent), dim=1),
            "labels": positions % self.request.workload.classes,
            "image_id": torch.tensor(index, dtype=torch.int64),
            "orig_size": torch.tensor([height, width]),
            "size": torch.tensor([height, width]),
            "area": extent.square() * height * width,
            "iscrowd": torch.zeros(objects, dtype=torch.int64),
        }


class _SyntheticData:
    def setup(self, stage: str | None = None) -> None:
        """Datasets are already installed; native collation and device transfer remain."""
        del stage


class _MaximumShape:
    def on_train_batch_start(self, _batch: Any, _batch_idx: int) -> None:
        """Keep the maximum native scale instead of randomly choosing a smaller one."""


class _ProbeProgress:
    """Count native optimizer updates without counting scaler-skipped attempts."""

    def __init__(
        self, per_rank_batch: int, shape: tuple[int, int], *, memory: GPUMemory | None = None
    ) -> None:
        self.per_rank_batch = per_rank_batch
        self.shape = shape
        self.optimizer_steps = 0
        self.validation_steps = 0
        self.target_steps: int | None = None
        self._hooks: list[Any] = []
        self.memory = memory

    def _observe_memory(self) -> None:
        if self.memory is not None:
            self.memory.observe()

    def _stepped(self, _optimizer: Any, _args: Any, _kwargs: Any) -> None:
        self.optimizer_steps += 1
        self._observe_memory()

    def on_train_start(self, trainer: Any, _module: Any) -> None:
        if len(trainer.optimizers) != 1:
            raise ValueError("RF-DETR probe requires one native AdamW optimizer")
        self._hooks.append(trainer.optimizers[0].register_step_post_hook(self._stepped))
        self._observe_memory()

    def on_train_batch_start(
        self, _trainer: Any, _module: Any, batch: Any, _batch_idx: int
    ) -> None:
        samples, targets = batch
        if len(targets) != self.per_rank_batch or tuple(samples.tensors.shape[-2:]) != self.shape:
            raise ValueError(
                "Native probe batch disagrees with its recorded batch or effective shape"
            )

    def on_before_optimizer_step(self, trainer: Any, _module: Any, optimizer: Any) -> None:
        # Lightning unscales before this hook, then lets GradScaler skip overflow
        # and reduce its scale. A first overflow is not a failed training recipe.
        if trainer.scaler is not None and trainer.scaler.is_enabled():
            return
        for group in optimizer.param_groups:
            for parameter in group["params"]:
                if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                    raise FloatingPointError("RF-DETR probe produced nonfinite gradients")

    def on_train_batch_end(
        self, trainer: Any, _module: Any, outputs: Any, _batch: Any, _batch_idx: int
    ) -> None:
        loss = outputs["loss"] if isinstance(outputs, dict) else outputs
        if not isinstance(loss, Tensor) or not torch.isfinite(loss).all():
            raise FloatingPointError("RF-DETR probe produced a nonfinite loss")
        scaler = trainer.scaler
        if scaler is not None and scaler.is_enabled() and scaler.get_scale() < 1:
            raise FloatingPointError(
                "RF-DETR probe gradients remain nonfinite after AMP scale reduction"
            )
        if self.target_steps is not None and self.optimizer_steps >= self.target_steps:
            # The pinned Lightning loop checks should_stop after this hook and
            # runs validation before leaving fit. Enable it only now, preserving
            # optimizer/EMA residency and avoiding validation after skipped steps.
            trainer.limit_val_batches = 1
            trainer.should_stop = True
        self._observe_memory()

    def on_validation_batch_end(
        self,
        _trainer: Any,
        _module: Any,
        outputs: Any,
        _batch: Any,
        _batch_idx: int,
        _dataloader_idx: int = 0,
    ) -> None:
        if len(outputs["targets"]) != self.per_rank_batch:
            raise ValueError("RF-DETR probe validation did not execute the requested batch")
        for prediction in outputs["results"]:
            if any(not torch.isfinite(prediction[key]).all() for key in ("boxes", "scores")):
                raise FloatingPointError("RF-DETR probe produced nonfinite validation predictions")
        self.validation_steps += 1
        self._observe_memory()

    def on_validation_end(self, trainer: Any, _module: Any) -> None:
        for name, value in trainer.callback_metrics.items():
            if str(name).startswith("val/") and not torch.isfinite(value).all():
                raise FloatingPointError("RF-DETR probe produced a nonfinite validation loss")
        self._observe_memory()

    def on_train_end(self, _trainer: Any, _module: Any) -> None:
        # Lightning tears CUDA resources down before fit returns (and on_fit_end).
        self._observe_memory()

    def teardown(self, _trainer: Any, _module: Any, stage: str) -> None:
        del stage
        for hook in self._hooks:
            hook.remove()
        self._hooks.clear()


def _config(request: BatchProbeRequest) -> ModelConfig:
    config = request.config
    if config is None or config.backend != "rfdetr":
        raise ValueError("RF-DETR probe requires an owner-prepared RF-DETR configuration")
    if (config.backend, config.preset) != (
        request.profile.model.backend,
        request.profile.model.preset,
    ):
        raise ValueError("RF-DETR probe profile disagrees with model selection")
    if request.optimizer != "AdamW" or request.profile.compilation is not False:
        raise ValueError("RF-DETR probes require their native uncompiled AdamW recipe")
    if request.profile.nominal_size != (config.train.imgsz, config.train.imgsz):
        raise ValueError("RF-DETR probe nominal resolution disagrees with its model")
    precision = "native-auto" if config.train.amp else "fp32"
    if (
        request.profile.precision != precision
        or request.profile.accumulation != f"fixed:{config.train.grad_accum_steps}"
        or request.profile.ema != config.train.use_ema
    ):
        raise ValueError("RF-DETR probe precision, accumulation or EMA disagrees with its profile")
    result = config.model_copy(deep=True)
    result.train.batch = request.global_batch
    result.train.device = int(os.environ.get("LOCAL_RANK", "0"))
    return result


def _attempt_steps(steps: int, scaler: Any) -> int:
    """Allow native AMP backoff without an infinite scheduler training horizon."""
    if scaler is None or not scaler.is_enabled():
        return steps
    # The native scheduler requires finite estimated_stepping_batches. Bound the
    # possible skipped updates before scale < 1, allowing scale growth after every
    # successful interval. The callback stops earlier at the actual-update target;
    # one further backoff produces the explicit persistent-nonfinite failure.
    growths = (steps - 1) // int(scaler.get_growth_interval())
    log_scale = math.log(float(scaler.get_scale())) + growths * math.log(
        float(scaler.get_growth_factor())
    )
    skipped = max(0, math.ceil(log_scale / -math.log(float(scaler.get_backoff_factor())))) + 1
    return steps + skipped


def _fit(request: BatchProbeRequest, config: ModelConfig, progress: _ProbeProgress) -> None:
    training = importlib.import_module("rfdetr.training")
    callbacks = importlib.import_module("rfdetr.training.callbacks")
    scales = importlib.import_module("rfdetr.datasets.coco")
    lightning = importlib.import_module("pytorch_lightning")
    lightning.seed_everything(config.train.seed, workers=True)
    device = f"cuda:{config.train.device}"
    names = tuple(str(index) for index in range(request.workload.classes))
    mc, tc = training_configuration(config, names, device, request.output, request.output)
    maximum = max(
        scales.compute_multi_scale_scales(
            mc.resolution, tc.expanded_scales, mc.patch_size, mc.num_windows
        )
    )
    if request.profile.effective_size != (maximum, maximum):
        raise ValueError("RF-DETR probe profile disagrees with the native maximum training scale")
    if mc.compile or bool(tc.use_ema) != request.profile.ema:
        raise ValueError("RF-DETR native compilation or EMA disagrees with the recorded profile")
    module_type = type("MaximumShapeRFDETR", (_MaximumShape, training.RFDETRModelModule), {})
    module = module_type(mc, tc)
    data_type = type("SyntheticRFDETRData", (_SyntheticData, training.RFDETRDataModule), {})
    data = data_type(mc, tc)
    steps = request.settings.warmup_steps + request.settings.measured_steps
    progress.target_steps = steps
    # The pinned DataModule has no public dataset injection hook. Preserve its
    # native loaders and packed-target transfer at this explicit SDK seam.
    data._dataset_val = SyntheticDataset(request, request.global_batch)  # noqa: SLF001
    native_callbacks: list[Any] = []
    if tc.use_ema:
        native_callbacks.append(
            callbacks.RFDETREMACallback(
                decay=tc.ema_decay, tau=tc.ema_tau, update_interval_steps=tc.ema_update_interval
            )
        )
    if tc.drop_path > 0:
        native_callbacks.append(callbacks.DropPathCallback(drop_path=tc.drop_path))
    native_callbacks.append(progress)
    trainer = training.build_trainer(
        tc,
        mc,
        include_training_callbacks=False,
        **trainer_devices(device),
        callbacks=native_callbacks,
        logger=False,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        max_steps=-1,
        max_epochs=1,
        min_steps=0,
        min_epochs=0,
        limit_train_batches=1.0,
        limit_val_batches=0,
        val_check_interval=1.0,
        check_val_every_n_epoch=1,
        num_sanity_val_steps=0,
    )
    microsteps = _attempt_steps(steps, trainer.scaler) * config.train.grad_accum_steps
    data._dataset_train = SyntheticDataset(request, microsteps * request.global_batch)  # noqa: SLF001
    trainer.fit(module, data)
    if progress.optimizer_steps != steps or progress.validation_steps != 1:
        raise RuntimeError("RF-DETR probe did not complete its optimizer and validation workload")


def probe(request: BatchProbeRequest) -> ProbeRankResult:
    config = _config(request)
    world = int(os.environ.get("WORLD_SIZE", "1"))
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    if world != request.profile.world_size:
        raise ValueError("RF-DETR probe world size disagrees with its recorded GPU profile")
    per_rank = global_batch_per_rank(request.global_batch, world)
    if not torch.cuda.is_available():
        raise ValueError("Batch capacity estimation requires CUDA")
    torch.cuda.set_device(local_rank)
    torch.cuda.reset_peak_memory_stats(local_rank)
    memory = GPUMemory(local_rank)
    lightning = importlib.import_module("pytorch_lightning")
    callback_type = type("ProbeProgress", (_ProbeProgress, lightning.Callback), {})
    progress = callback_type(per_rank, request.profile.effective_size, memory=memory)
    status: TrialStatus = "success"
    diagnostic = ""
    try:
        _fit(request, config, progress)
    except torch.cuda.OutOfMemoryError as exc:
        status, diagnostic = "oom", str(exc)
    except FloatingPointError as exc:
        status, diagnostic = "nonfinite", str(exc)
    except FileNotFoundError as exc:
        status, diagnostic = "missing_asset", str(exc)
    return ProbeRankResult(
        token=request.token,
        rank=rank,
        status=status,
        actual_global_batch=request.global_batch if status == "success" else None,
        peak_memory_bytes=memory.peak_memory_bytes,
        non_allocator_memory_bytes=memory.non_allocator_memory_bytes,
        warmup_steps=min(progress.optimizer_steps, request.settings.warmup_steps),
        measured_steps=max(0, progress.optimizer_steps - request.settings.warmup_steps),
        validation_steps=progress.validation_steps,
        diagnostic=diagnostic,
    )
