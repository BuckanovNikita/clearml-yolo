"""Validated switches and SDK-free phase records for command-boundary scheduling."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class ExecutionControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool = True


class ExecutionPhase(BaseModel):
    """A native setting location and its unmodified device selection before admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["train", "predict", "export"]
    settings_path: str
    # Preserve raw Hydra selectors, including malformed values, until the enabled
    # phase's device validator handles them without coercing booleans into ordinals.
    device: object = None
