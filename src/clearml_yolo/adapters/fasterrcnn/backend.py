"""Lazy native Faster R-CNN operations; heavy model libraries load only on execution."""

from collections.abc import Callable, Sequence
from pathlib import Path

import pandas as pd

from clearml_yolo.adapters.fasterrcnn.configuration import validate_preprocessing
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.models import (
    BackendTrainResult,
    CheckpointMetadata,
    Device,
    ModelConfig,
    PredictSettings,
)


def validate_device(value: Device) -> None:
    if (isinstance(value, list) and len(value) != 1) or (isinstance(value, str) and "," in value):
        raise ValueError("Faster R-CNN multi-device execution is not supported by this adapter")


def train(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
) -> BackendTrainResult:
    if config.backend != "fasterrcnn":
        raise ValueError("Faster R-CNN training requires its own model configuration")
    validate_device(config.train.device)
    from clearml_yolo.adapters.fasterrcnn.training import train_native

    return train_native(config, prepared, output, report)


def predict(
    config: ModelConfig,
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
) -> pd.DataFrame:
    if (config.backend, config.preset) != (descriptor.backend, descriptor.preset):
        raise ValueError("Faster R-CNN model selection disagrees with checkpoint metadata")
    validate_preprocessing(descriptor.preprocessing)
    validate_device(settings.device)
    from clearml_yolo.adapters.fasterrcnn.inference import predict_native

    return predict_native(descriptor, weights, image_paths, settings)
