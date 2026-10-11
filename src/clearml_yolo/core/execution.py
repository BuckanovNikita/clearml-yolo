"""Validated switches for command-boundary scheduling and automatic GPU selection."""

from pydantic import BaseModel, ConfigDict, StrictBool


class ExecutionControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: StrictBool = True
