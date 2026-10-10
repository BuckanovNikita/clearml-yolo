"""Concrete workflow operations behind application ports."""

from pathlib import Path
from typing import Any

from loguru import logger

from clearml_yolo.adapters.clearml.native import finalize_native_model
from clearml_yolo.adapters.clearml.session import record_run_configuration
from clearml_yolo.adapters.integrations.native_ddp import native_ddp_relay
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import model_weights_path
from clearml_yolo.adapters.yolo.config import requested_settings, write_native_yaml
from clearml_yolo.application.contracts import PreparedDataset, TrainResult


def execute_training(
    task: object, architecture: str | Path, settings: dict[str, Any], prepared: PreparedDataset
) -> TrainResult:
    with trace_operation("native.import.yolo"):
        from ultralytics.models import YOLO

    with trace_operation("training.model.load", context={"path": str(architecture)}):
        model = YOLO(model_weights_path(architecture))
    if model.task != "detect":
        raise ValueError(f"Training requires a detection model; loaded task={model.task!r}")
    requested = requested_settings(settings, "train") | {"model": str(architecture)}
    write_native_yaml(
        Path(settings["project"]) / ".configs" / settings["name"] / "ultralytics_requested.yaml",
        requested,
        "train",
    )
    with native_ddp_relay(task, model) as relay:
        with trace_operation("training.native.train", context={"stage": "train"}):
            model.train(**settings)
        trainer: Any = model.trainer
        relay.replay(trainer)
        directory = Path(trainer.save_dir)
        best = directory / "weights" / "best.pt"
        if not best.is_file():
            raise FileNotFoundError(f"Training finished without required checkpoint {best}")
        effective = dict(vars(trainer.args))
        write_native_yaml(directory / "ultralytics.yaml", requested | effective, "train")
        differences = {
            key: {"requested": requested.get(key), "effective": value}
            for key, value in effective.items()
            if requested.get(key) != value
        }
        record_run_configuration(task, {"training_normalization": differences})
        with trace_operation("training.model.finalize", context={"path": str(architecture)}):
            finalize_native_model(task, model, trainer, architecture)
        logger.info("Training checkpoint: {}", best)
        return TrainResult(
            weights=best,
            save_dir=directory,
            effective_args=effective,
            cleaned_ground_truth=prepared.ground_truth,
            dataset_reference=prepared.data,
        )
