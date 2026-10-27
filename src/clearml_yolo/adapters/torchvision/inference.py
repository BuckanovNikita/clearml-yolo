"""Native tensor execution and canonical prediction rows at the Torchvision boundary."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import torch

from clearml_yolo.adapters.observability.progress import image_progress
from clearml_yolo.adapters.torchvision.checkpoint import checkpoint_state
from clearml_yolo.adapters.torchvision.configuration import DetectorBuilder
from clearml_yolo.adapters.torchvision.data import image_tensor
from clearml_yolo.adapters.torchvision.distributed import execution_device
from clearml_yolo.adapters.torchvision.transform import canvas_size
from clearml_yolo.application.contracts import PREDICTION_COLUMNS
from clearml_yolo.core.models import CheckpointMetadata, PredictSettings


def predict_native(
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
    *,
    build_model: DetectorBuilder,
    label_offset: Literal[0, 1],
) -> pd.DataFrame:
    device = execution_device(settings.device)
    if settings.half and device.type != "cuda":
        raise ValueError("Torchvision half inference requires CUDA")
    size = settings.imgsz or descriptor.preprocessing.size
    model = build_model(
        descriptor.preset,
        len(descriptor.class_names),
        pretrained=False,
        image_size=size,
        score_thresh=settings.conf,
        nms_thresh=settings.iou,
        detections_per_img=settings.max_det,
    )
    model.load_state_dict(checkpoint_state(weights), strict=True)
    model.to(device).eval()
    rows: list[dict[str, Any]] = []
    with image_progress(len(image_paths)) as advance, torch.inference_mode():
        for offset in range(0, len(image_paths), settings.batch):
            paths = image_paths[offset : offset + settings.batch]
            images = [image_tensor(Path(path)).to(device) for path in paths]
            with torch.autocast(device_type=device.type, enabled=settings.half):
                predictions = model(images)
            for path, detection in zip(paths, predictions, strict=True):
                for box, score, label in zip(
                    detection["boxes"].cpu().tolist(),
                    detection["scores"].cpu().tolist(),
                    detection["labels"].cpu().tolist(),
                    strict=True,
                ):
                    if not label_offset <= label < len(descriptor.class_names) + label_offset:
                        raise ValueError("Torchvision detector emitted an unknown foreground label")
                    rows.append(
                        {
                            "image_name": path,
                            "instance_label": descriptor.class_names[label - label_offset],
                            "confidence": score,
                            "bbox_x_tl": box[0],
                            "bbox_y_tl": box[1],
                            "bbox_x_br": box[2],
                            "bbox_y_br": box[3],
                        }
                    )
            advance(len(paths))
    frame = pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
    frame.attrs.update(
        image_paths=list(image_paths),
        normalized_imgsz=list(canvas_size(size)),
        effective_args=settings.model_dump(mode="json")
        | {
            "backend": descriptor.backend,
            "preset": descriptor.preset,
            "model": str(weights),
            "device": str(device),
            "imgsz": list(canvas_size(size)),
            "resize": "letterbox",
            "padding": "top_left_normalized_zero",
        },
    )
    return frame
