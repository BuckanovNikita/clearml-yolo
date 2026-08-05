"""Train a YOLO model with DDP and ClearML tracking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.gpu import AutoGpuConfig, resolve_devices


def train(
    model: str,
    data: str,
    epochs: int,
    imgsz: int,
    batch: int,
    project: str,
    name: str,
    auto_gpu: AutoGpuConfig,
    clearml: ClearMLConfig,
    device: list[int] | int | str | None = None,
    train_kwargs: dict[str, Any] | None = None,
) -> Path:
    """Run training and return the path to the best checkpoint.

    The checkpoint path is derived from project/name rather than from the return value
    of ``model.train()``: under DDP the parent process never runs a validator, so
    ultralytics returns no metrics there.
    """
    from ultralytics.models import YOLO

    # Only the task identity is ours. Ultralytics' own ClearML callback connects the
    # hyperparameters, logs losses and metrics, and uploads best.pt on its own.
    init_task(clearml, stage="train")
    selection = resolve_devices(auto_gpu, device, batch)

    logger.info(
        "Training {} on {} for {} epochs — devices={} batch={} (per GPU {})",
        model,
        data,
        epochs,
        selection.devices,
        selection.batch,
        selection.batch_per_gpu,
    )

    yolo = YOLO(model)
    yolo.train(
        data=data,
        epochs=epochs,
        imgsz=imgsz,
        batch=selection.batch,
        device=selection.devices,
        # Relative projects are resolved against ultralytics' configured runs_dir, which
        # is rarely the working directory, so anchor it here instead.
        project=str(Path(project).resolve()),
        name=name,
        exist_ok=True,
        **(train_kwargs or {}),
    )

    # Read the run directory from the trainer rather than rebuilding it: ultralytics
    # may deduplicate the name, and only it knows where the checkpoint actually went.
    # The attribute is declared optional upstream but is always set once train() returns.
    trainer: Any = yolo.trainer
    save_dir = Path(trainer.save_dir)
    best = save_dir / "weights" / "best.pt"
    if not best.is_file():
        raise FileNotFoundError(
            f"Training finished but {best} does not exist. Check the run directory {save_dir}."
        )
    logger.info("Best checkpoint: {}", best)
    return best
