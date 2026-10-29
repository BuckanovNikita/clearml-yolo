"""Backend-neutral publication inputs and outcomes."""

from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue


class FiftyOneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Публиковать результаты в FiftyOne. false отключает эту операцию.",
        examples=[True],
        json_schema_extra={
            "shapes": "bool",
            "applicability": "FiftyOneConfig",
            "source": "clearml_yolo.core.publication.FiftyOneConfig.enabled",
            "classification": "input",
        },
    )
    preflight_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        allow_inf_nan=False,
        description="Положительный конечный таймаут предварительной проверки FiftyOne в секундах.",
        examples=[60.0],
        json_schema_extra={
            "shapes": "float",
            "applicability": "FiftyOneConfig",
            "source": "clearml_yolo.core.publication.FiftyOneConfig.preflight_timeout_seconds",
            "classification": "input",
        },
    )
    publish_timeout_seconds: float = Field(
        default=900.0,
        gt=0,
        allow_inf_nan=False,
        description="Положительный конечный таймаут публикации FiftyOne в секундах.",
        examples=[900.0],
        json_schema_extra={
            "shapes": "float",
            "applicability": "FiftyOneConfig",
            "source": "clearml_yolo.core.publication.FiftyOneConfig.publish_timeout_seconds",
            "classification": "input",
        },
    )
    lock_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        allow_inf_nan=False,
        description=(
            "Положительный конечный таймаут ожидания блокировки набора FiftyOne в секундах."
        ),
        examples=[30.0],
        json_schema_extra={
            "shapes": "float",
            "applicability": "FiftyOneConfig",
            "source": "clearml_yolo.core.publication.FiftyOneConfig.lock_timeout_seconds",
            "classification": "input",
        },
    )
    dataset_prefix: str = Field(
        default="clearml-yolo",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$",
        description=(
            "Префикс имени набора: латинские буквы, цифры, дефис и подчёркивание;"
            " первый символ — буква или цифра."
        ),
        examples=["clearml-yolo"],
        json_schema_extra={
            "shapes": "str",
            "applicability": "FiftyOneConfig",
            "source": "clearml_yolo.core.publication.FiftyOneConfig.dataset_prefix",
            "classification": "input",
        },
    )


class PublicationRequest(BaseModel):
    """Paths to durable producer outputs; no backend or tracking objects cross here."""

    task_id: str = Field(min_length=1)
    ground_truth: Path
    source_ground_truth: Path | None = None
    predictions: Path | None = None
    prediction_splits: list[str] | None = None
    prediction_image_name: Literal["name", "stem", "path"] = "name"
    evaluations: dict[str, Path] = Field(default_factory=dict)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class PublicationReceipt(BaseModel):
    dataset_name: str
    task_id: str
    run_key: str
    ground_truth_sha256: str
    source_ground_truth_sha256: str
    dataset_reused: bool
    sample_count: int
    fields: dict[str, str]
    evaluation_keys: dict[str, str] = Field(default_factory=dict)
    dataset_complete: bool
    run_complete: bool
    payload_paths: dict[str, Path]
    published_at: AwareDatetime
