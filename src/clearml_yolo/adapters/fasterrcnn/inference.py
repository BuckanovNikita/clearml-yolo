"""Native tensor execution and canonical prediction rows at the Torchvision boundary."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import torch

from clearml_yolo.adapters.fasterrcnn.data import image_tensor
from clearml_yolo.adapters.fasterrcnn.model import build_model, checkpoint_state
from clearml_yolo.adapters.fasterrcnn.transform import canvas_size
from clearml_yolo.adapters.observability.progress import image_progress
from clearml_yolo.application.contracts import PREDICTION_COLUMNS
from clearml_yolo.core.models import CheckpointMetadata, Device, PredictSettings


def execution_device(value: Device) -> torch.device:
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError("Faster R-CNN multi-device execution is unsupported")
        value = value[0]
    if value in (None, -1, "-1"):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if isinstance(value, int) or value.isdecimal():
        return torch.device(f"cuda:{value}")
    return torch.device(value)


def predict_native(
    descriptor: CheckpointMetadata,
    weights: Path,
    image_paths: Sequence[str],
    settings: PredictSettings,
) -> pd.DataFrame:
    device = execution_device(settings.device)
    if settings.half and device.type != "cuda":
        raise ValueError("Faster R-CNN half inference requires CUDA")
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
                    if not 1 <= label <= len(descriptor.class_names):
                        raise ValueError("Faster R-CNN emitted an unknown foreground label")
                    rows.append(
                        {
                            "image_name": path,
                            "instance_label": descriptor.class_names[label - 1],
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
            "backend": "fasterrcnn",
            "preset": descriptor.preset,
            "model": str(weights),
            "device": str(device),
            "imgsz": list(canvas_size(size)),
            "resize": "letterbox",
            "padding": "top_left_normalized_zero",
        },
    )
    return frame
