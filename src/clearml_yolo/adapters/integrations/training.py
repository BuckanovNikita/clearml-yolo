"""Concrete workflow operations behind application ports."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from loguru import logger

from clearml_yolo.adapters.clearml.native import finalize_native_model
from clearml_yolo.adapters.clearml.session import (
    preserve_training_success,
    record_run_configuration,
    record_training_publication_failure,
    register_training_counts,
)
from clearml_yolo.adapters.integrations.native_ddp import native_ddp_relay
from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.file_io import read_detection_csv
from clearml_yolo.adapters.storage.filesystem import model_weights_path
from clearml_yolo.adapters.yolo.config import requested_settings, write_native_yaml
from clearml_yolo.application.contracts import PreparedDataset, TrainResult
from clearml_yolo.core.transforms import TransformConfig


def execute_training(
    task: object,
    architecture: str | Path,
    settings: dict[str, Any],
    prepared: PreparedDataset,
    *,
    transforms: TransformConfig | None = None,
) -> TrainResult:
    from clearml_yolo.adapters.integrations.batch_resolution import resolve_yolo_batch
    from clearml_yolo.adapters.integrations.native_trainer import trainer_with_transforms

    requested = requested_settings(settings, "train") | {"model": str(architecture)}
    settings, batch_estimate = resolve_yolo_batch(architecture, settings, prepared, transforms)
    if batch_estimate is not None:
        record_run_configuration(task, {"training_batch_estimate": batch_estimate})
    with trace_operation("native.import.yolo"):
        from ultralytics.models import YOLO

    with trace_operation("training.model.load", context={"path": str(architecture)}):
        model = YOLO(model_weights_path(architecture))
    if model.task != "detect":
        raise ValueError(f"Training requires a detection model; loaded task={model.task!r}")
    write_native_yaml(
        Path(settings["project"]) / ".configs" / settings["name"] / "ultralytics_requested.yaml",
        requested,
        "train",
    )
    result: TrainResult | None = None
    try:
        with native_ddp_relay(task, model) as relay:
            with trace_operation("training.native.train", context={"stage": "train"}):
                model.train(trainer=trainer_with_transforms(transforms), **settings)
            trainer: Any = model.trainer
            directory = Path(trainer.save_dir)
            best = directory / "weights" / "best.pt"
            if not best.is_file():
                raise FileNotFoundError(  # noqa: TRY301 - training boundary must remain strict
                    f"Training finished without required checkpoint {best}",
                )
            preserve_training_success(task, best, directory.parent.parent / "pipeline_outcome.json")
            effective = dict(vars(trainer.args))
            result = TrainResult(
                weights=best,
                save_dir=directory,
                effective_args=effective,
                cleaned_ground_truth=prepared.ground_truth,
                dataset_reference=prepared.data,
            )
            try:
                counts = training_population_counts(prepared.ground_truth)
                register_training_counts(task, best, counts)
                relay.replay(trainer)
                # Replay restores worker-normalized arguments into the owner trainer.
                effective = dict(vars(trainer.args))
                result = result.model_copy(update={"effective_args": effective})
                write_native_yaml(directory / "ultralytics.yaml", requested | effective, "train")
                differences = {
                    key: {"requested": requested.get(key), "effective": value}
                    for key, value in effective.items()
                    if requested.get(key) != value
                }
                record_run_configuration(task, {"training_normalization": differences})
                with trace_operation(
                    "training.model.finalize",
                    context={"path": str(architecture)},
                ):
                    finalize_native_model(task, model, trainer, architecture)
            except Exception as error:
                if not record_training_publication_failure(task, error):
                    raise
    except Exception as error:
        # The relay may rethrow a publication failure while exiting even after
        # replay was handled. Only a returned native run establishes this boundary.
        if result is None or not record_training_publication_failure(task, error):
            raise
    if result is None:
        raise RuntimeError("Native training returned no completed result")
    logger.info("Training checkpoint: {}", result.weights)
    return result


def training_population_counts(ground_truth: Path) -> dict[str, int] | None:
    """Count prepared training annotations, preserving exact lexical class identity."""
    frame = read_detection_csv(ground_truth)
    if "split" not in frame or "instance_label" not in frame:
        logger.warning("Prepared training population lacks split/class provenance; counts unavailable")
        return None
    training = frame.loc[frame["split"] == "train", "instance_label"].dropna()
    return {str(label): int(count) for label, count in training.value_counts().items()}


@contextmanager
def training_publication(task: object) -> Iterator[None]:
    """Keep failed post-training publication visible without discarding trained weights."""
    try:
        yield
    except Exception as error:
        if not record_training_publication_failure(task, error):
            raise
