"""Tensor primitives reproducing PyTorch antialiased bicubic position resizing."""

from typing import Any, cast, override

import torch
from torch import Tensor, nn

_CUBIC_SUPPORT = 2


def _weights(size: int, source: int, reference: Tensor) -> Tensor:
    scale = reference.new_tensor(float(source)) / size
    filter_scale = torch.maximum(scale, reference.new_tensor(1.0))
    coordinate = torch.arange(size, device=reference.device, dtype=reference.dtype) + 0.5
    coordinate = coordinate * scale - 0.5
    source_coordinate = torch.arange(source, device=reference.device, dtype=reference.dtype)
    distance = (source_coordinate[None, :] - coordinate[:, None]).abs() / filter_scale
    # PyTorch's antialiased bicubic kernel uses Pillow's a=-0.5 coefficient.
    first = (1.5 * distance - 2.5) * distance * distance + 1
    second = ((-0.5 * distance + 2.5) * distance - 4) * distance + 2
    weights = torch.where(
        distance < 1,
        first,
        torch.where(distance < _CUBIC_SUPPORT, second, torch.zeros_like(distance)),
    )
    # Discard samples outside the source grid and renormalize the remaining weights.
    return weights / weights.sum(-1, keepdim=True)


def resize_bicubic_antialiased(values: Tensor, size: tuple[int, int]) -> Tensor:
    """Resize NCHW positions with separable MatMul instead of ONNX cubic Resize.

    This includes widened filters when downsampling and normalized border kernels.
    The dimensions remain tensor-derived during ONNX tracing.
    """
    height_weights = _weights(size[0], values.shape[-2], values)
    width_weights = _weights(size[1], values.shape[-1], values)
    horizontal = values @ width_weights.t()
    return (horizontal.transpose(-2, -1) @ height_weights.t()).transpose(-2, -1)


class ExportViTIntermediates(nn.Module):
    """Export-only DINOv2 adapter retaining the source's blocks and normalization.

    The timm object is an opaque SDK boundary; no installed timm code is modified.
    DINOv3 has rotary positions and keeps its own native intermediate implementation.
    """

    def __init__(self, source: Any) -> None:
        super().__init__()
        self.source = source

    def forward_intermediates(self, images: Tensor, **options: Any) -> list[Tensor]:
        if options != {
            "indices": [2, 5, 8, 11],
            "norm": True,
            "output_fmt": "NCHW",
            "intermediates_only": True,
        }:
            raise ValueError("Unsupported DINO intermediate export configuration")
        return self.forward(images)

    @override
    def forward(self, images: Tensor) -> list[Tensor]:
        source = self.source
        embedded = source.patch_embed(images)
        batch, height, width, channels = embedded.shape
        prefix_count = 0 if source.no_embed_class else source.num_prefix_tokens
        positions = source.pos_embed[:, prefix_count:]
        old_height, old_width = source.patch_embed.grid_size
        positions = positions.reshape(1, old_height, old_width, channels).permute(0, 3, 1, 2)
        positions = resize_bicubic_antialiased(positions.float(), (height, width))
        positions = positions.permute(0, 2, 3, 1).reshape(1, -1, channels)
        positions = positions.to(embedded.dtype)
        if prefix_count:
            positions = torch.cat((source.pos_embed[:, :prefix_count], positions), dim=1)
        tokens = embedded.reshape(batch, -1, channels)
        prefix = []
        if source.cls_token is not None:
            prefix.append(source.cls_token.expand(batch, -1, -1))
        if source.reg_token is not None:
            prefix.append(source.reg_token.expand(batch, -1, -1))
        if source.no_embed_class:
            tokens = tokens + positions
        tokens = torch.cat([*prefix, tokens], dim=1)
        if not source.no_embed_class:
            tokens = tokens + positions
        tokens = source.norm_pre(source.patch_drop(source.pos_drop(tokens)))
        results: list[Tensor] = []
        for index, block in enumerate(source.blocks):
            tokens = block(tokens)
            if index in {2, 5, 8, 11}:
                normalized = source.norm(tokens)[:, source.num_prefix_tokens :]
                feature = normalized.reshape(batch, height, width, channels)
                results.append(cast(Tensor, feature.permute(0, 3, 1, 2).contiguous()))
        return results


class ExportDinoRotary(nn.Module):
    """Keep rotary normalization denominators dynamic instead of Python floats."""

    def __init__(self, source: Any) -> None:
        super().__init__()
        self.source = source

    def get_embed(self, shape: tuple[int, int]) -> Tensor:
        height, width = shape
        source = self.source
        if source.normalize_coords != "separate" or source.grid_indexing != "ij":
            raise ValueError("Unsupported DINOv3 rotary coordinate configuration")
        coords_h = (torch.arange(height, dtype=torch.float32) + 0.5 + source.grid_offset) / height
        coords_w = (torch.arange(width, dtype=torch.float32) + 0.5 + source.grid_offset) / width
        coords = torch.stack(torch.meshgrid(coords_h, coords_w, indexing="ij"), dim=-1)
        coords = 2 * coords.flatten(0, 1) - 1
        # Preserve the native periods, rotation layout, sin and cos calculation.
        sin, cos = source._get_pos_embed_from_coords(coords)  # noqa: SLF001
        return torch.cat((sin, cos), dim=-1)
