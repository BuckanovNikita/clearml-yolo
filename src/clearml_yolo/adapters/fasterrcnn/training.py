"""Faster R-CNN training recipe on shared supervised Torchvision execution."""

from collections.abc import Callable
from pathlib import Path

from clearml_yolo.adapters.fasterrcnn.model import build_model
from clearml_yolo.adapters.torchvision.training import train_native as train_torchvision
from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.models import BackendTrainResult, ModelConfig
from clearml_yolo.core.transforms import TransformConfig


def train_native(
    config: ModelConfig,
    prepared: PreparedDataset,
    output: Path,
    report: Callable[[str, float, int], None],
    *,
    transforms: TransformConfig | None = None,
) -> BackendTrainResult:
    return train_torchvision(
        config,
        prepared,
        output,
        report,
        build_model=build_model,
        label_offset=1,
        transforms=transforms,
    )
