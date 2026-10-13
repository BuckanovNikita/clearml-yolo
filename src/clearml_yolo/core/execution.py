"""Validated switches and SDK-free phase records for command-boundary scheduling."""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

DEFAULT_MAX_USED_MEMORY_GIB = 2.0


class ExecutionControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool = True


class AutoGPUControl(ExecutionControl):
    """Project availability policy; GiB denotes 1024**3 bytes of total used memory."""

    force: StrictBool = False

    max_used_memory_gib: float = Field(
        default=DEFAULT_MAX_USED_MEMORY_GIB, strict=True, gt=0, allow_inf_nan=False
    )


class ExecutionPhase(BaseModel):
    """A native setting location and its unmodified device selection before admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["train", "predict", "export"]
    settings_path: str
    # Preserve raw Hydra selectors, including malformed values, until the enabled
    # phase's device validator handles them without coercing booleans into ordinals.
    device: object = None


def concrete_device_selector(value: object) -> tuple[int, ...] | str:
    """Validate exact native ordinals without discovery; retain their configured order."""
    message = "Device selection requires unique exact nonnegative GPU ordinals or CPU/MPS"
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"cpu", "mps"} or (text.startswith("mps:") and text[4:].isdigit()):
            return text
        text = text.removeprefix("cuda:").strip()
        parts = text.split(",")
        if any(not part.strip().isascii() or not part.strip().isdigit() for part in parts):
            raise ValueError(message)
        values = tuple(int(part.strip()) for part in parts)
    elif type(value) is int:
        values = (value,)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if any(type(item) is not int for item in value):
            raise ValueError(message)
        values = tuple(int(item) for item in value)
    else:
        raise ValueError(message)
    if not values or any(item < 0 for item in values) or len(set(values)) != len(values):
        raise ValueError(message)
    return values


def validate_concrete_phases(phases: Sequence[ExecutionPhase]) -> dict[str, tuple[int, ...] | str]:
    """Require one inference ordinal and concrete selectors for every enabled phase."""
    result: dict[str, tuple[int, ...] | str] = {}
    for phase in phases:
        selection = concrete_device_selector(phase.device)
        if phase.kind != "train" and isinstance(selection, tuple) and len(selection) > 1:
            raise ValueError("Inference requires one exact GPU ordinal")
        result[phase.settings_path] = selection
    return result
