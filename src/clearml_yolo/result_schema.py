"""Tracking-neutral evaluation payloads shared by producers and renderers."""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class ResultContext(BaseModel):
    """One model's evaluation of one split within an invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    model_id: str
    split: str


class ConfusionMatrixPayload(BaseModel):
    """Exact post-threshold counts; true labels are rows, predictions columns."""

    model_config = ConfigDict(extra="forbid")

    labels: list[str]
    counts: list[list[int]]

    @model_validator(mode="after")
    def validate_matrix(self) -> Self:
        size = len(self.labels)
        if len(self.counts) != size or any(len(row) != size for row in self.counts):
            raise ValueError("Confusion matrix must be square and match its labels")
        if len(set(self.labels)) != size:
            raise ValueError("Confusion matrix labels must be unique")
        if any(value < 0 for row in self.counts for value in row):
            raise ValueError("Confusion matrix counts must be nonnegative")
        return self


class PRCurve(BaseModel):
    """Confidence-ordered PR observations reconstructed at IoU 0.50."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    class_name: str
    recall: list[float]
    precision: list[float]
    confidence: list[float]
    tp: list[int]
    fp: list[int]
    gt_count: int
    ap50: float | None
    integration_method: str

    @model_validator(mode="after")
    def validate_points(self) -> Self:
        lengths = {len(values) for values in (
            self.recall, self.precision, self.confidence, self.tp, self.fp,
        )}
        if len(lengths) != 1:
            raise ValueError("PR curve point arrays must have equal lengths")
        if self.gt_count < 0 or any(value < 0 for value in [*self.tp, *self.fp]):
            raise ValueError("PR curve counts must be nonnegative")
        if any(not 0 <= value <= 1 for value in [*self.recall, *self.precision]):
            raise ValueError("PR curve axes must lie within [0, 1]")
        return self
