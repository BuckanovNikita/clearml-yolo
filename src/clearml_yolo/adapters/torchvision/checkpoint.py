"""Strict tensor checkpoint loading shared by Torchvision detector families."""

from pathlib import Path
from typing import cast

import torch
from torch import Tensor


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
