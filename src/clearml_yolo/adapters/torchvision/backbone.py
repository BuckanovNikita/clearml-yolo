"""Pretrained hierarchical and patch-token backbones with explicit detector pyramids."""

import importlib
from collections import OrderedDict
from pathlib import Path
from typing import Any, Literal, cast, override

from torch import Tensor, nn
from torch.nn import functional

from clearml_yolo.adapters.torchvision.assets import TIMM_MODELS
from clearml_yolo.adapters.torchvision.checkpoint import checkpoint_state

_STRIDES = (4, 8, 16, 32)
_P2 = 2
_P3 = 3


class FeaturePyramid(nn.Module):
    """Stride-aligned P2-P6 or P3-P7 features, each with 256 channels."""

    out_channels = 256

    def __init__(
        self,
        preset: str,
        *,
        pretrained: bool,
        weights: Path | None,
        first_level: Literal[2, 3] = 2,
    ) -> None:
        super().__init__()
        timm = importlib.import_module("timm")
        self.preset = preset
        self.strides = _STRIDES if first_level == _P2 else _STRIDES[1:]
        self.intermediate_indices = [2, 5, 8, 11] if first_level == _P2 else [5, 8, 11]
        self.patch_features = preset.startswith("dino")
        options: dict[str, Any] = {}
        if self.patch_features:
            options.update(dynamic_img_size=True, dynamic_img_pad=True)
        else:
            options.update(
                features_only=True,
                out_indices=(0, 1, 2, 3) if first_level == _P2 else (1, 2, 3),
            )
            if preset == "swin_tiny":
                options["strict_img_size"] = False
        if pretrained and weights is None:
            raise ValueError("Prepare the pretrained backbone asset before native construction")
        if weights is not None:
            options["pretrained_cfg_overlay"] = {"file": str(weights.absolute())}
        # A native file override retains checkpoint filtering, key remapping and
        # positional interpolation before timm wraps the feature extractor.
        self.body = timm.create_model(
            TIMM_MODELS[preset], pretrained=weights is not None, **options
        )
        channels = (
            [int(self.body.num_features)] * len(self.strides)
            if self.patch_features
            else self.body.feature_info.channels()
        )
        pyramid = importlib.import_module("torchvision.ops.feature_pyramid_network")
        self.fpn = pyramid.FeaturePyramidNetwork(
            channels,
            self.out_channels,
            extra_blocks=(
                pyramid.LastLevelMaxPool()
                if first_level == _P2
                else pyramid.LastLevelP6P7(self.out_channels, self.out_channels)
            ),
        )

    @override
    def forward(self, images: Tensor) -> OrderedDict[str, Tensor]:
        if self.patch_features:
            features = self.body.forward_intermediates(
                images,
                indices=self.intermediate_indices,
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
                for feature, stride in zip(features, self.strides, strict=True)
            ]
        else:
            features = self.body(images)
            if self.preset == "swin_tiny":
                features = [feature.permute(0, 3, 1, 2) for feature in features]
        ordered = OrderedDict((str(index), feature) for index, feature in enumerate(features))
        return cast(OrderedDict[str, Tensor], self.fpn(ordered))


def _resnet_backbone(
    preset: str,
    *,
    pretrained: bool,
    weights: Path | None,
    first_level: Literal[2, 3] = 2,
) -> Any:
    utilities = importlib.import_module("torchvision.models.detection.backbone_utils")
    name = preset.removesuffix("_fpn")
    if pretrained and weights is None:
        raise ValueError("Prepare the pretrained backbone asset before native construction")
    options: dict[str, Any] = {}
    if first_level == _P3:
        pyramid = importlib.import_module("torchvision.ops.feature_pyramid_network")
        options.update(returned_layers=[2, 3, 4], extra_blocks=pyramid.LastLevelP6P7(256, 256))
    backbone = utilities.resnet_fpn_backbone(
        backbone_name=name,
        weights=None,
        trainable_layers=5,
        **options,
    )
    if weights is not None:
        state = {
            key: tensor
            for key, tensor in checkpoint_state(weights).items()
            if not key.startswith("fc.")
        }
        backbone.body.load_state_dict(state, strict=True)
    return backbone
