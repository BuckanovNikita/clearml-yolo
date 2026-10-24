"""Portable training augmentation selectors and content identity, without SDK effects."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    field_validator,
    model_validator,
)


def pipeline_digest(pipeline: Mapping[str, JsonValue]) -> str:
    """Hash canonical JSON rather than source whitespace or dictionary insertion order."""
    serialized = json.dumps(pipeline, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


class TransformSnapshot(BaseModel):
    """Detached content verified again at execution, including after JSON replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pipeline: dict[str, JsonValue]
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    source: Annotated[str, Field(min_length=1)]

    @field_validator("pipeline", mode="before")
    @classmethod
    def detached_json(cls, value: object) -> dict[str, JsonValue]:
        # A.to_dict can retain tuples; A.save writes the equivalent JSON arrays.
        return TypeAdapter(dict[str, JsonValue]).validate_json(json.dumps(value, allow_nan=False))

    @model_validator(mode="after")
    def matching_content(self) -> Self:
        if pipeline_digest(self.pipeline) != self.sha256:
            raise ValueError("Transform snapshot sha256 does not match its pipeline content")
        return self


class TransformConfig(BaseModel):
    """One public file selector; snapshots are populated by configuration resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["native", "albumentations"] = "native"
    pipeline_file: Path | None = None
    snapshot: TransformSnapshot | None = None

    @model_validator(mode="after")
    def selected_source(self) -> Self:
        if self.mode == "native" and (self.pipeline_file is not None or self.snapshot is not None):
            raise ValueError("Select transforms=albumentations before providing a pipeline")
        if self.mode == "albumentations" and self.pipeline_file is None and self.snapshot is None:
            raise ValueError("Albumentations requires pipeline_file or a resolved snapshot")
        return self
