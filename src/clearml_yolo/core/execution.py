"""Validated switches and SDK-free phase records for command-boundary scheduling."""

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
