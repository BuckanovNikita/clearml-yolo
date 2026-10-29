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

    pipeline: dict[str, JsonValue] = Field(
        description=(
            "Сгенерированное сериализованное содержимое Albumentations pipeline; "
            "проверяется по sha256."
        ),
        examples=[
            {
                "__version__": "2.0.8",
                "transform": {"__class_fullname__": "Compose", "transforms": []},
            }
        ],
        json_schema_extra={
            "shapes": "dict[str, JsonValue]",
            "applicability": "TransformSnapshot",
            "source": "clearml_yolo.core.transforms.TransformSnapshot.pipeline",
            "classification": "generated",
        },
    )
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] = Field(
        description=(
            "Сгенерированный SHA-256 канонического JSON pipeline, ровно 64 "
            "шестнадцатеричных символа."
        ),
        examples=["0000000000000000000000000000000000000000000000000000000000000000"],
        json_schema_extra={
            "shapes": "Annotated[str, Field(pattern='^[0-9a-f]{64}$')]",
            "applicability": "TransformSnapshot",
            "source": "clearml_yolo.core.transforms.TransformSnapshot.sha256",
            "classification": "generated",
        },
    )
    source: Annotated[str, Field(min_length=1)] = Field(
        description=(
            "Сохранённое непустое имя источника pipeline; служит происхождением при replay."
        ),
        examples=["augmentations.yaml"],
        json_schema_extra={
            "shapes": "Annotated[str, Field(min_length=1)]",
            "applicability": "TransformSnapshot",
            "source": "clearml_yolo.core.transforms.TransformSnapshot.source",
            "classification": "generated",
        },
    )

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

    mode: Literal["native", "albumentations"] = Field(
        default="native",
        description=(
            "Режим аугментации: native оставляет нативный trainer, albumentations"
            " использует общий сериализованный pipeline."
        ),
        examples=["native"],
        json_schema_extra={
            "shapes": "Literal['native', 'albumentations']",
            "applicability": "TransformConfig",
            "source": "clearml_yolo.core.transforms.TransformConfig.mode",
            "classification": "input",
        },
    )
    pipeline_file: Path | None = Field(
        default=None,
        description=(
            "Путь к YAML/JSON Albumentations; допустим только в режиме "
            "albumentations. Читается при запуске, но не при preview."
        ),
        examples=["augmentations.yaml"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "TransformConfig",
            "source": "clearml_yolo.core.transforms.TransformConfig.pipeline_file",
            "classification": "input",
        },
    )
    snapshot: TransformSnapshot | None = Field(
        default=None,
        description=(
            "Сгенерированный снимок pipeline, хеша и происхождения для "
            "воспроизведения. Пользователь выбирает pipeline_file; снимок создаёт"
            " владелец конфигурации."
        ),
        examples=[None],
        json_schema_extra={
            "shapes": "TransformSnapshot | None",
            "applicability": "TransformConfig",
            "source": "clearml_yolo.core.transforms.TransformConfig.snapshot",
            "classification": "generated",
        },
    )

    @model_validator(mode="after")
    def selected_source(self) -> Self:
        if self.mode == "native" and (self.pipeline_file is not None or self.snapshot is not None):
            raise ValueError("Select transforms=albumentations before providing a pipeline")
        if self.mode == "albumentations" and self.pipeline_file is None and self.snapshot is None:
            raise ValueError("Albumentations requires pipeline_file or a resolved snapshot")
        return self
