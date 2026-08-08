"""Train a YOLO model with DDP and ClearML tracking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel

from clearml_yolo.clearml_session import ClearMLConfig, init_task
from clearml_yolo.gpu import AutoGpuConfig, DeviceSelection, remember_batch, resolve_devices
from clearml_yolo.ultralytics_params import fill_unset

# Where ultralytics puts a run's checkpoint. Named here because two other places have to
# predict this path without a trainer to ask: the standalone predict default, and the
# pipeline when training is skipped.
CHECKPOINT = "{project}/{name}/weights/best.pt"


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
    ultralytics: dict[str, Any],
    auto_gpu: AutoGpuConfig,
    clearml: ClearMLConfig,
) -> TrainResult:
    """Run training and return the best checkpoint with the device that produced it.

    ``ultralytics`` is the whole of ``conf/ultralytics/train.yaml``: every parameter
    ultralytics accepts for detection training, passed on as it stands. The keys left
    ``null`` there are the ones decided here — the batch and cards from ``auto_gpu``, AMP
    and ``torch.compile`` from whether this run is on a GPU at all, and the run's name
    from the ClearML experiment, so the run directory always matches the experiment.

    The checkpoint path is derived from project/name rather than from the return value
    of ``model.train()``: under DDP the parent process never runs a validator, so
    ultralytics returns no metrics there.
    """
    from ultralytics.models import YOLO

    # Only the task identity is ours. Ultralytics' own ClearML callback connects the
    # hyperparameters, logs losses and metrics, and uploads best.pt on its own.
    init_task(clearml, stage="train")
    architecture = ultralytics["model"]
    selection = resolve_devices(
        auto_gpu,
        ultralytics.get("device"),
        ultralytics.get("batch"),
        model=architecture,
        stage="train",
    )
    on_gpu = isinstance(selection.devices, list) and bool(selection.devices)

    settings = fill_unset(
        ultralytics,
        # Training's half precision is AMP, not the `quantize` flag inference takes: that
        # one casts the weights outright, which training cannot do.
        amp=on_gpu,
        # Unlike inference, training runs long enough to earn the one-off compilation back
        # many times over — it is paid once and amortised across every epoch.
        compile=on_gpu,
        name=clearml.task_name,
    )
    settings["batch"] = selection.batch
    settings["device"] = selection.devices
    # Relative projects are resolved against ultralytics' configured runs_dir, which is
    # rarely the working directory, so anchor it here instead.
    settings["project"] = str(Path(settings["project"]).resolve())
    # `model` names the weights YOLO() is built from. Left in as well, it would reach
    # train() as a keyword argument, which ultralytics lets win over the constructor —
    # two ways to say which model this is, and no rule for which of them means it.
    del settings["model"]

    logger.info(
        "Training {} on {} for {} epochs — devices={} batch={} (per GPU {})",
        architecture,
        settings["data"],
        settings["epochs"],
        selection.devices,
        selection.batch,
        selection.batch_per_gpu,
    )

    yolo = YOLO(architecture)
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
    remember_batch(auto_gpu, "train", architecture, selection)
    return TrainResult(weights=best, inference_device=_inference_device(selection))
