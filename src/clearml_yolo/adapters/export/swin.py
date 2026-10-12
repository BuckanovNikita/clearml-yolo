"""Export-only Swin blocks with tensor-derived shifted-window masks."""

import importlib
from typing import Any, cast, override

import torch
from torch import Tensor, nn
from torch.nn import functional


def _partition(values: Tensor, window: tuple[int, int]) -> Tensor:
    batch, height, width, channels = values.shape
    values = values.reshape(
        batch, height // window[0], window[0], width // window[1], window[1], channels
    )
    return values.permute(0, 1, 3, 2, 4, 5).contiguous().reshape(-1, window[0], window[1], channels)


def shifted_window_mask(
    padded: Tensor, window: tuple[int, int], shift: tuple[int, int]
) -> Tensor | None:
    """Native nine-region mask on an already padded NHWC grid, without math.ceil."""
    if not any(shift):
        return None
    regions = []
    for size, length, displacement in zip(padded.shape[1:3], window, shift, strict=True):
        coordinates = torch.arange(size, device=padded.device)
        if displacement:
            regions.append(
                (coordinates >= size - length).to(torch.int64)
                + (coordinates >= size - displacement).to(torch.int64)
            )
        else:
            # Native's final slice (0,None) overwrites that entire zero-shift axis.
            regions.append(torch.full_like(coordinates, 2))
    labels = regions[0][:, None] * 3 + regions[1][None, :]
    windows = _partition(labels[None, :, :, None], window).reshape(-1, window[0] * window[1])
    difference = windows[:, :, None] != windows[:, None, :]
    return torch.where(difference, padded.new_tensor(-100.0), padded.new_tensor(0.0))


class ExportSwinBlock(nn.Module):
    """Retain source attention/normalization/MLP; replace only mask construction."""

    def __init__(self, source: Any) -> None:
        super().__init__()
        self.source = source

    def _attention(self, values: Tensor) -> Tensor:
        source = self.source
        batch, height, width, channels = values.shape
        window = tuple(source.window_size)
        shift = tuple(source.shift_size)
        if any(shift):
            values = torch.roll(values, shifts=(-shift[0], -shift[1]), dims=(1, 2))
        values = functional.pad(
            values,
            (
                0,
                0,
                0,
                (window[1] - width % window[1]) % window[1],
                0,
                (window[0] - height % window[0]) % window[0],
            ),
        )
        padded_height, padded_width = values.shape[1:3]
        windows = _partition(values, window).reshape(-1, source.window_area, channels)
        # SDK-native relative bias, Q/K/V, attention and projection remain intact.
        attended = source.attn(windows, mask=shifted_window_mask(values, window, shift))
        attended = (
            attended.reshape(
                batch,
                padded_height // window[0],
                padded_width // window[1],
                window[0],
                window[1],
                channels,
            )
            .permute(0, 1, 3, 2, 4, 5)
            .contiguous()
        )
        attended = attended.reshape(batch, padded_height, padded_width, channels)
        attended = attended[:, :height, :width, :].contiguous()
        if any(shift):
            attended = torch.roll(attended, shifts=shift, dims=(1, 2))
        return cast(Tensor, attended)

    @override
    def forward(self, values: Tensor) -> Tensor:
        source = self.source
        batch, height, width, channels = values.shape
        values = values + source.drop_path1(self._attention(source.norm1(values)))
        values = values.reshape(batch, -1, channels)
        values = values + source.drop_path2(source.mlp(source.norm2(values)))
        return values.reshape(batch, height, width, channels)


def adapt_swin_blocks(body: nn.Module) -> None:
    """Replace blocks in the caller-owned model copy; never mutate installed SDK code."""
    native_type = importlib.import_module("timm.models.swin_transformer").SwinTransformerBlock
    replaced = 0
    for path, module in list(body.named_modules()):
        if isinstance(module, native_type):
            parent_path, _, name = path.rpartition(".")
            parent = body.get_submodule(parent_path)
            setattr(parent, name, ExportSwinBlock(module))
            replaced += 1
    if not replaced:
        raise ValueError("Swin export found no supported native transformer blocks")
