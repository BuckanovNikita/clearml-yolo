"""Train a YOLO model with DDP and ClearML tracking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.gpu import AutoGpuConfig, DeviceSelection, remember_batch, resolve_devices


class TrainResult(BaseModel):
    """The checkpoint plus the device it was produced on.

    The device travels with the result so a stage that follows training in the same
    process can reuse it instead of surveying again: training still holds the card's
    memory at that point, so a fresh survey would wait for a device this very run owns.
    """

    weights: Path
    inference_device: str | None = None


def _inference_device(selection: DeviceSelection) -> str | None:
    """Name training's device the way inference expects it, or None for CPU."""
    if isinstance(selection.devices, list) and selection.devices:
        return str(selection.devices[0])
    return None


def train(
    model: str,
    data: str,
    epochs: int,
    imgsz: int,
    batch: int | None,
    project: str,
    name: str,
    auto_gpu: AutoGpuConfig,
    clearml: ClearMLConfig,
    device: list[int] | int | str | None = None,
    train_kwargs: dict[str, Any] | None = None,
) -> TrainResult:
    """Run training and return the best checkpoint with the device that produced it.

    The checkpoint path is derived from project/name rather than from the return value
    of ``model.train()``: under DDP the parent process never runs a validator, so
    ultralytics returns no metrics there.

    ``batch`` left unset hands the decision to ``auto_gpu``, which sizes it to the model
    and the cards this run was given; a number set here is used as it stands.
    """
    from ultralytics.models import YOLO

    # Only the task identity is ours. Ultralytics' own ClearML callback connects the
    # hyperparameters, logs losses and metrics, and uploads best.pt on its own.
    init_task(clearml, stage="train")
    selection = resolve_devices(auto_gpu, device, batch, model=model, stage="train")

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
    on_gpu = isinstance(selection.devices, list) and bool(selection.devices)
    settings: dict[str, Any] = {
        "data": data,
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": selection.batch,
        "device": selection.devices,
        # Training's half precision is AMP, not the `quantize` flag inference takes: that
        # one casts the weights outright, which training cannot do. Ultralytics already
        # defaults amp=True, but a run's numeric precision is not something to leave to a
        # dependency's default.
        "amp": on_gpu,
        # Unlike inference, training runs long enough to earn the one-off compilation back
        # many times over — it is paid once and amortised across every epoch.
        "compile": on_gpu,
        # Relative projects are resolved against ultralytics' configured runs_dir, which
        # is rarely the working directory, so anchor it here instead.
        "project": str(Path(project).resolve()),
        "name": name,
        "exist_ok": True,
        # Last, so a run reproducing older numbers can turn either of the two above back
        # off — as keyword arguments they would collide instead.
        **(train_kwargs or {}),
    }
    yolo.train(**settings)

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
    # Only now is this batch known to fit: it survived every epoch, including the
    # validation pass, which is where a batch that trains but does not validate fails.
    remember_batch(auto_gpu, "train", model, selection)
    return TrainResult(weights=best, inference_device=_inference_device(selection))
