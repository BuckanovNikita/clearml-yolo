"""Lazy FCOS operations; only the invocation owner handles publication."""

from collections.abc import Callable, Sequence
from pathlib import Path

import pandas as pd

from clearml_yolo.adapters.torchvision.configuration import validate_preprocessing
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.application.training_workers import BatchProbeRequest, ProbeRankResult
from clearml_yolo.core.models import (
    BackendTrainResult,
    CheckpointMetadata,
    ModelConfig,
    PredictSettings,
)
from clearml_yolo.core.transforms import TransformConfig


def train(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
    *,
    transforms: TransformConfig | None = None,
) -> BackendTrainResult:
    if config.backend != "fcos":
        raise ValueError("FCOS training requires its own model configuration")
    from clearml_yolo.adapters.fcos.model import build_model
    from clearml_yolo.adapters.torchvision.training import train_native

    return train_native(
        config,
        prepared,
        output,
        report,
        build_model=build_model,
        label_offset=0,
        transforms=transforms,
    )


def predict(
    config: ModelConfig,
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
) -> pd.DataFrame:
    if config.backend != "fcos" or descriptor.backend != "fcos":
        raise ValueError("FCOS prediction requires its own model and checkpoint")
    if (config.backend, config.preset) != (descriptor.backend, descriptor.preset):
        raise ValueError("FCOS model selection disagrees with checkpoint metadata")
    validate_preprocessing(descriptor.preprocessing)
    from clearml_yolo.adapters.fcos.model import build_model
    from clearml_yolo.adapters.torchvision.inference import predict_native

    return predict_native(
        descriptor, weights, image_paths, settings, build_model=build_model, label_offset=0
    )


def probe(request: BatchProbeRequest) -> ProbeRankResult:
    from clearml_yolo.adapters.fcos.model import build_model
    from clearml_yolo.adapters.torchvision.probe import probe as probe_torchvision

    return probe_torchvision(request, build_model=build_model, label_offset=0)
