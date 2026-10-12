"""Torchvision detector components with explicit hierarchical and patch-token pyramids.

Torchvision and timm construction/feature records are opaque SDK boundaries. Their
objects stay in this module; public recipe and checkpoint records remain typed.
"""

import importlib
from collections import OrderedDict
from pathlib import Path
from typing import Any, cast, override

import torch
from torch import Tensor, nn
from torch.nn import functional

from clearml_yolo.adapters.fasterrcnn.transform import LetterboxTransform
from clearml_yolo.core.models import ImageSize

_TIMM_MODELS = {
    "convnext_tiny": "convnext_tiny.fb_in22k_ft_in1k",
    "swin_tiny": "swin_tiny_patch4_window7_224.ms_in1k",
    "dinov2_small": "vit_small_patch14_dinov2.lvd142m",
    "dinov3_small": "vit_small_patch16_dinov3.lvd1689m",
}
_STRIDES = (4, 8, 16, 32)


def checkpoint_state(path: Path) -> dict[str, Tensor]:
    """Read only tensor archives, retaining strict shape checks at model loading."""
    if not path.is_file():
        raise FileNotFoundError(path)
    loaded = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(loaded, dict) and "state_dict" in loaded:
        loaded = loaded["state_dict"]
    if not isinstance(loaded, dict) or not all(
        isinstance(key, str) and isinstance(value, Tensor) for key, value in loaded.items()
    ):
        raise ValueError(f"Checkpoint is not a tensor state dictionary: {path}")
    return cast(dict[str, Tensor], loaded)


class FeaturePyramid(nn.Module):
    """Four stride-aligned levels and pooled P6, each with 256 channels."""

    out_channels = 256

    def __init__(self, preset: str, *, pretrained: bool, weights: Path | None) -> None:
        super().__init__()
        timm = importlib.import_module("timm")
        self.preset = preset
        self.patch_features = preset.startswith("dino")
        options: dict[str, Any] = {}
        if self.patch_features:
            options.update(dynamic_img_size=True, dynamic_img_pad=True)
        else:
            options.update(features_only=True, out_indices=(0, 1, 2, 3))
            if preset == "swin_tiny":
                options["strict_img_size"] = False
        self.body = timm.create_model(
            _TIMM_MODELS[preset], pretrained=pretrained and weights is None, **options
        )
        if weights is not None:
            self.body.load_state_dict(checkpoint_state(weights), strict=True)
        channels = (
            [int(self.body.num_features)] * 4
            if self.patch_features
            else self.body.feature_info.channels()
        )
        pyramid = importlib.import_module("torchvision.ops.feature_pyramid_network")
        self.fpn = pyramid.FeaturePyramidNetwork(
            channels, self.out_channels, extra_blocks=pyramid.LastLevelMaxPool()
        )

    @override
    def forward(self, images: Tensor) -> OrderedDict[str, Tensor]:
        if self.patch_features:
            features = self.body.forward_intermediates(
                images,
                indices=[2, 5, 8, 11],
                norm=True,
                output_fmt="NCHW",
                intermediates_only=True,
            )
            features = [
                functional.interpolate(
                    feature,
                    size=(images.shape[-2] // stride, images.shape[-1] // stride),
                    mode="bilinear",
                    align_corners=False,
                )
                for feature, stride in zip(features, _STRIDES, strict=True)
            ]
        else:
            features = self.body(images)
            if self.preset == "swin_tiny":
                features = [feature.permute(0, 3, 1, 2) for feature in features]
        ordered = OrderedDict((str(index), feature) for index, feature in enumerate(features))
        return cast(OrderedDict[str, Tensor], self.fpn(ordered))


def _resnet_backbone(preset: str, *, pretrained: bool, weights: Path | None) -> Any:
    models = importlib.import_module("torchvision.models")
    utilities = importlib.import_module("torchvision.models.detection.backbone_utils")
    name = preset.removesuffix("_fpn")
    native_weights = (
        models.ResNet50_Weights.DEFAULT if name == "resnet50" else models.ResNet101_Weights.DEFAULT
    )
    backbone = utilities.resnet_fpn_backbone(
        backbone_name=name,
        weights=native_weights if pretrained and weights is None else None,
        trainable_layers=5,
    )
    if weights is not None:
        state = {
            key: tensor
            for key, tensor in checkpoint_state(weights).items()
            if not key.startswith("fc.")
        }
        backbone.body.load_state_dict(state, strict=True)
    return backbone


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
    elif preset in _TIMM_MODELS:
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
