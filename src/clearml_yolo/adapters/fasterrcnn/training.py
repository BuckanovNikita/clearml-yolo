"""Native Torchvision loss optimization, optional EMA and validation-selected checkpoints."""

import csv
import importlib.metadata
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import torch
from torch import Tensor
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn
from torch.utils.data import DataLoader

from clearml_yolo.adapters.fasterrcnn.data import collate_detection, prepared_datasets
from clearml_yolo.adapters.fasterrcnn.evaluation import evaluate_coco
from clearml_yolo.adapters.fasterrcnn.inference import execution_device
from clearml_yolo.adapters.fasterrcnn.model import build_model, checkpoint_state
from clearml_yolo.adapters.fasterrcnn.transform import canvas_size
from clearml_yolo.adapters.storage.filesystem import validate_output_tree, write_path
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.models import (
    BackendTrainResult,
    CheckpointMetadata,
    ModelConfig,
    Preprocessing,
    TrainSettings,
)


def _training_epoch(
    model: Any,
    loader: DataLoader[tuple[Tensor, dict[str, Tensor]]],
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    settings: TrainSettings,
    device: torch.device,
    ema: AveragedModel | None,
) -> float:
    model.train()
    optimizer.zero_grad(set_to_none=True)
    total = 0.0
    for index, (images, targets) in enumerate(loader):
        device_images = [image.to(device) for image in images]
        device_targets = [
            {key: value.to(device) for key, value in target.items()} for target in targets
        ]
        with torch.autocast(device_type=device.type, enabled=scaler.is_enabled()):
            losses = model(device_images, device_targets)
            loss = torch.stack(list(losses.values())).sum()
        value = float(loss.detach())
        if not math.isfinite(value):
            raise FloatingPointError("Faster R-CNN training produced a nonfinite loss")
        total += value
        start = (index // settings.grad_accum_steps) * settings.grad_accum_steps
        window = min(settings.grad_accum_steps, len(loader) - start)
        # Torch's Tensor.backward implementation lacks a complete typed signature.
        scaler.scale(loss / window).backward()  # type: ignore[no-untyped-call]
        if (index + 1) % settings.grad_accum_steps == 0 or index + 1 == len(loader):
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
            if ema is not None:
                ema.update_parameters(model)
    return total / len(loader)


def _checkpoint(
    model: Any, path: Path, epoch: int, score: float, metadata: CheckpointMetadata
) -> None:
    path = write_path(path)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "epoch": epoch,
            "selection_metric": score,
            "class_names": list(metadata.class_names),
            "preprocessing": metadata.preprocessing.model_dump(mode="json"),
        },
        path,
    )


def train_native(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
) -> BackendTrainResult:
    output = validate_output_tree(output)
    settings = config.train
    device = execution_device(settings.device)
    train_data, validation_data, names = prepared_datasets(prepared)
    torch.manual_seed(settings.seed)
    model = build_model(
        config.preset,
        len(names),
        pretrained=settings.pretrained and settings.weights is None,
        backbone_weights=settings.backbone_weights,
        image_size=settings.imgsz,
    )
    if settings.weights is not None:
        model.load_state_dict(checkpoint_state(settings.weights), strict=True)
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=settings.lr, weight_decay=settings.weight_decay
    )
    scaler = torch.amp.GradScaler("cuda", enabled=settings.amp and device.type == "cuda")
    ema = (
        # Torch exposes this averaging factory without annotations.
        AveragedModel(
            model,
            multi_avg_fn=get_ema_multi_avg_fn(0.999),  # type: ignore[no-untyped-call]
            use_buffers=True,
        )
        if settings.use_ema
        else None
    )
    train_loader = DataLoader(
        train_data,
        batch_size=settings.batch,
        shuffle=True,
        num_workers=settings.workers,
        collate_fn=collate_detection,
    )
    val_loader = DataLoader(
        validation_data,
        batch_size=settings.batch,
        shuffle=False,
        num_workers=settings.workers,
        collate_fn=collate_detection,
    )
    metadata = CheckpointMetadata(
        backend="fasterrcnn",
        preset=config.preset,
        class_names=names,
        preprocessing=Preprocessing(resize="letterbox", size=canvas_size(settings.imgsz)),
        dependencies={
            name: importlib.metadata.version(name)
            for name in ("torch", "torchvision", "timm", "pycocotools")
        },
    )
    output.mkdir(parents=True, exist_ok=True)
    best_path = write_path(output / "best.pth")
    metrics_path = write_path(output / "metrics.csv")
    best_score = -math.inf
    best_metrics: dict[str, float] = {}
    with write_path(metrics_path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "epoch",
                "train/loss",
                "val/map50_95",
                "val/map50",
                "val/recall",
            ],
        )
        writer.writeheader()
        for epoch in range(settings.epochs):
            loss = _training_epoch(model, train_loader, optimizer, scaler, settings, device, ema)
            evaluated = ema.module if ema is not None else model
            metrics = {
                "train/loss": loss,
                **evaluate_coco(evaluated, validation_data, iter(val_loader), device),
            }
            for name, value in metrics.items():
                report(name, value, epoch)
            writer.writerow({"epoch": epoch, **metrics})
            stream.flush()
            score = metrics["val/map50_95"]
            if score > best_score:
                best_score, best_metrics = score, metrics
                _checkpoint(evaluated, best_path, epoch, score, metadata)
    if not best_path.is_file():
        raise RuntimeError("Faster R-CNN did not produce a validation-selected checkpoint")
    return BackendTrainResult(
        weights=best_path,
        metadata=metadata,
        metrics=best_metrics,
        artifacts=[metrics_path],
        effective_args=settings.model_dump(mode="json")
        | {
            "backend": "fasterrcnn",
            "preset": config.preset,
            "device": str(device),
            "imgsz": list(canvas_size(settings.imgsz)),
            "amp": scaler.is_enabled(),
            "optimizer": "AdamW",
            "ema_decay": 0.999 if ema is not None else None,
            "selection_metric": "val/map50_95",
            "preprocessing": metadata.preprocessing.model_dump(),
        },
    )
