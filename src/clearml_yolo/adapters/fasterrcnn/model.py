"""Faster R-CNN head and ROI geometry on shared pretrained backbone machinery."""

import importlib
from pathlib import Path
from typing import Any

from clearml_yolo.adapters.torchvision.assets import TIMM_MODELS
from clearml_yolo.adapters.torchvision.backbone import FeaturePyramid, _resnet_backbone
from clearml_yolo.adapters.torchvision.checkpoint import checkpoint_state
from clearml_yolo.adapters.torchvision.transform import LetterboxTransform
from clearml_yolo.core.models import ImageSize

_STRIDES = (4, 8, 16, 32)

__all__ = ["FeaturePyramid", "_resnet_backbone", "build_model", "checkpoint_state"]


def build_model(
    preset: str,
    num_classes: int,
    *,
    pretrained: bool,
    backbone_weights: Path | None = None,
    image_size: ImageSize = 800,
    score_thresh: float = 0.001,
    nms_thresh: float = 0.7,
    detections_per_img: int = 300,
) -> Any:
    """Build a native detector; num_classes counts foreground classes only."""
    if num_classes < 1:
        raise ValueError("Faster R-CNN needs at least one foreground class")
    if backbone_weights is not None and not backbone_weights.is_file():
        raise FileNotFoundError(backbone_weights)
    if preset in {"resnet50_fpn", "resnet101_fpn"}:
        backbone = _resnet_backbone(preset, pretrained=pretrained, weights=backbone_weights)
    elif preset in TIMM_MODELS:
        backbone = FeaturePyramid(preset, pretrained=pretrained, weights=backbone_weights)
    else:
        raise ValueError(f"Unsupported Faster R-CNN preset: {preset}")
    detection = importlib.import_module("torchvision.models.detection")
    model = detection.FasterRCNN(
        backbone,
        num_classes=num_classes + 1,
        box_score_thresh=score_thresh,
        box_nms_thresh=nms_thresh,
        box_detections_per_img=detections_per_img,
    )
    model.transform = LetterboxTransform(image_size)
    # Valid image heights can be much smaller than the padded feature canvas.
    # Torchvision's inferred scales would then pool the wrong spatial locations.
    pooling = importlib.import_module("torchvision.ops.poolers")
    model.roi_heads.box_roi_pool.scales = [1.0 / stride for stride in _STRIDES]
    model.roi_heads.box_roi_pool.map_levels = pooling.LevelMapper(2, 5)
    return model
