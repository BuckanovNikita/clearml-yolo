"""Compatibility exports for shared Torchvision assets machinery."""

from clearml_yolo.adapters.torchvision.assets import (
    TIMM_MODELS,
    pretrained_asset,
)

__all__ = ["TIMM_MODELS", "pretrained_asset"]
