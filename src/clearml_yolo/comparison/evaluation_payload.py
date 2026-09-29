"""Neutral, versioned records for exact fixed-threshold evaluation results."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

EvaluationBoxStatus = Literal["TP", "FP", "FN", "filtered"]
EvaluationMatchStatus = Literal["TP", "FP", "FN"]


class EvaluationBox(BaseModel):
    """One evaluated ground-truth or prepared prediction box."""

    model_config = ConfigDict(extra="forbid")

    index: int
    image_name: str
    label: str
    box: tuple[float, float, float, float]
    confidence: float | None = None
    status: EvaluationBoxStatus


class EvaluationMatch(BaseModel):
    """One exact fixed-threshold match record."""

    model_config = ConfigDict(extra="forbid")

    gt_index: int | None
    pred_index: int | None
    gt_label: str
    pred_label: str
    confidence: float
    iou: float | None
    status: EvaluationMatchStatus


class EvaluationPayload(BaseModel):
    """Portable evidence for one evaluated split."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    split: str
    image_names: list[str]
    thresholds: dict[str, float]
    ground_truth: list[EvaluationBox]
    predictions: list[EvaluationBox]
    matches: list[EvaluationMatch]
    methodology: dict[str, JsonValue] = Field(default_factory=dict)
