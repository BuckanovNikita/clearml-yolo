"""Faster R-CNN inference with its background-slot label contract."""

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from clearml_yolo.adapters.fasterrcnn.model import build_model
from clearml_yolo.adapters.torchvision.distributed import execution_device
from clearml_yolo.adapters.torchvision.inference import predict_native as predict_torchvision
from clearml_yolo.core.models import CheckpointMetadata, PredictSettings

__all__ = ["execution_device", "predict_native"]


def predict_native(
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
) -> pd.DataFrame:
    return predict_torchvision(
        descriptor, weights, image_paths, settings, build_model=build_model, label_offset=1
    )
