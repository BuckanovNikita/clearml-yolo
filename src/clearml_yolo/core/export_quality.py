"""Class-aware numerical agreement and independent export accuracy acceptance."""

import math
from typing import Annotated, Any, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field
from scipy.optimize import linear_sum_assignment

Metric = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
DetectionArray = NDArray[np.floating[Any]]
_COLUMNS = 6
_DIMENSIONS = 2
_SCORE_TIE_WEIGHT = 1e-9


class QualityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mAP: Metric  # noqa: N815 -- public COCO metric spelling
    map50: Metric
    recall: Metric
    per_class_recall: dict[str, Metric]


class DetectionAgreement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    matched: Annotated[int, Field(strict=True, ge=0)]
    unmatched_reference: Annotated[int, Field(strict=True, ge=0)]
    unmatched_exported: Annotated[int, Field(strict=True, ge=0)]
    max_box_error: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None
    max_score_error: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None


def validate_detections(values: DetectionArray) -> NDArray[np.float64]:
    """Validate real Nx6 xyxy/confidence/zero-based integer-class rows."""
    if values.ndim != _DIMENSIONS or values.shape[1] != _COLUMNS:
        raise ValueError("Detections must have shape Nx6")
    if not np.issubdtype(values.dtype, np.number) or np.iscomplexobj(values):
        raise ValueError("Detection rows must contain real numeric values")
    rows = np.asarray(values, dtype=np.float64)
    if not np.isfinite(rows).all():
        raise ValueError("Detection rows must contain finite values")
    if np.any(rows[:, 2:4] <= rows[:, :2]):
        raise ValueError("Detection box width and height must be positive")
    if np.any((rows[:, 4] < 0) | (rows[:, 4] > 1)):
        raise ValueError("Detection confidence must be between zero and one")
    labels = rows[:, 5]
    if np.any(labels < 0) or np.any(labels != np.floor(labels)):
        raise ValueError("Detection labels must be zero-based nonnegative integers")
    return rows


def _pair_iou(reference: NDArray[np.float64], exported: NDArray[np.float64]) -> NDArray[np.float64]:
    lower = np.maximum(reference[:, None, :2], exported[None, :, :2])
    upper = np.minimum(reference[:, None, 2:4], exported[None, :, 2:4])
    intersection = np.prod(np.maximum(upper - lower, 0), axis=2)
    reference_area = np.prod(reference[:, 2:4] - reference[:, :2], axis=1)
    exported_area = np.prod(exported[:, 2:4] - exported[:, :2], axis=1)
    return np.asarray(
        intersection / (reference_area[:, None] + exported_area[None, :] - intersection),
        dtype=np.float64,
    )


def match_detections(
    reference: DetectionArray,
    exported: DetectionArray,
    *,
    min_iou: float = 0.99,
) -> DetectionAgreement:
    """Maximize valid one-to-one class/IoU matches, then favor higher IoU.

    Hungarian costs prioritize match cardinality, then higher IoU. Numerical errors
    describe only matched rows; unmatched populations remain explicit evidence.
    """
    if not math.isfinite(min_iou) or not 0 < min_iou <= 1:
        raise ValueError("min_iou must be finite and between zero (exclusive) and one")
    native = validate_detections(reference)
    served = validate_detections(exported)
    native_indices = np.empty(0, dtype=np.int64)
    served_indices = np.empty(0, dtype=np.int64)
    if len(native) and len(served):
        overlap = _pair_iou(native, served)
        valid = (native[:, None, 5] == served[None, :, 5]) & (overlap >= min_iou)
        # One invalid assignment costs more than the sum of all valid assignment costs.
        penalty = max(len(native), len(served)) + 1
        # Scores break geometric ties so duplicate boxes remain permutation invariant.
        score_tie = np.abs(native[:, None, 4] - served[None, :, 4]) * _SCORE_TIE_WEIGHT
        costs = np.where(valid, 1 - overlap + score_tie, penalty)
        assigned_native, assigned_served = linear_sum_assignment(costs)
        selected = valid[assigned_native, assigned_served]
        native_indices = assigned_native[selected]
        served_indices = assigned_served[selected]
    count = len(native_indices)
    difference = np.abs(native[native_indices, :5] - served[served_indices, :5])
    return DetectionAgreement(
        matched=count,
        unmatched_reference=len(native) - count,
        unmatched_exported=len(served) - count,
        max_box_error=float(difference[:, :4].max()) if count else None,
        max_score_error=float(difference[:, 4].max()) if count else None,
    )


def _valid_metrics(metrics: QualityMetrics) -> bool:
    values = (metrics.mAP, metrics.map50, metrics.recall, *metrics.per_class_recall.values())
    return all(math.isfinite(value) and 0 <= value <= 1 for value in values)


def quality_gate(
    native: QualityMetrics,
    exported: QualityMetrics,
    *,
    precision: Literal["fp32", "fp16"],
    reference_detection_count: int,
) -> bool:
    """Accept only a meaningful finite native baseline and a bounded absolute mAP loss.

    An accuracy improvement passes; numerical drift is assessed independently by
    match_detections. COCO undefined/all-empty results cannot establish acceptance.
    """
    if precision not in {"fp32", "fp16"}:
        raise ValueError("Quality gate precision must be fp32 or fp16")
    if reference_detection_count <= 0 or not _valid_metrics(native) or not _valid_metrics(exported):
        return False
    if native.mAP <= 0:
        return False
    if not any(
        (exported.mAP, exported.map50, exported.recall, *exported.per_class_recall.values())
    ):
        return False
    tolerance = 0.001 if precision == "fp32" else 0.005
    loss = native.mAP - exported.mAP
    return loss <= tolerance or math.isclose(loss, tolerance, rel_tol=0, abs_tol=1e-12)
