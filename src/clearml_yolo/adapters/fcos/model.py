"""FCOS heads on pretrained P3-P7 backbones with zero-based foreground labels."""

import importlib
from pathlib import Path
from typing import Any

from clearml_yolo.adapters.torchvision.assets import TIMM_MODELS
from clearml_yolo.adapters.torchvision.backbone import FeaturePyramid, _resnet_backbone
from clearml_yolo.adapters.torchvision.transform import LetterboxTransform
from clearml_yolo.core.models import ImageSize


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
    if num_classes < 1:
        raise ValueError("FCOS needs at least one foreground class")
    if backbone_weights is not None and not backbone_weights.is_file():
        raise FileNotFoundError(backbone_weights)
    if preset in {"resnet50_fpn", "resnet101_fpn"}:
        backbone = _resnet_backbone(
            preset, pretrained=pretrained, weights=backbone_weights, first_level=3
        )
    elif preset in TIMM_MODELS:
        backbone = FeaturePyramid(
            preset, pretrained=pretrained, weights=backbone_weights, first_level=3
        )
    else:
        raise ValueError(f"Unsupported FCOS preset: {preset}")
    detection = importlib.import_module("torchvision.models.detection")
    anchors = importlib.import_module("torchvision.models.detection.anchor_utils")
    model = detection.FCOS(
        backbone,
        num_classes=num_classes,
        anchor_generator=anchors.AnchorGenerator(
            sizes=((8,), (16,), (32,), (64,), (128,)), aspect_ratios=((1.0,),) * 5
        ),
        score_thresh=score_thresh,
        nms_thresh=nms_thresh,
        detections_per_img=detections_per_img,
    )
    model.transform = LetterboxTransform(image_size)
    return model
