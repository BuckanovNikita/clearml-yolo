"""Complete source-row exports with explicit prepared-index match lineage."""

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol

import numpy as np
import pandas as pd

_BOX_COLUMNS = ["bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br"]
RowType = Literal["ground_truth", "prediction"]
Relationships = dict[tuple[RowType, str], list[dict[str, Any]]]


class ExportMatch(Protocol):
    """The public dependency match fields needed by neutral CSV evidence."""

    type: str
    gt_index: int
    pred_index: int
    gt_label: str
    pred_label: str
    confidence: float
    iou: float | None


def assign_source_ids(frame: pd.DataFrame, *, row_type: RowType) -> pd.DataFrame:
    """Assign positional IDs once, before filtering or index reset.

    IDs identify source occurrences rather than coordinates or DataFrame labels.
    Existing IDs are authoritative and must remain unique and nonmissing.
    """
    result = frame.copy()
    if "source_row_id" in result:
        ids = result["source_row_id"]
        if ids.isna().any() or ids.astype(str).duplicated().any():
            raise ValueError("source_row_id must be unique and nonmissing")
        result["source_row_id"] = ids.astype(str)
    else:
        prefix = "gt" if row_type == "ground_truth" else "pred"
        result["source_row_id"] = [f"{prefix}:{position}" for position in range(len(result))]
    if "object_id" not in result:
        result["object_id"] = result["source_row_id"]
    return result


def _source_rows(frame: pd.DataFrame, row_type: RowType) -> pd.DataFrame:
    result = assign_source_ids(frame, row_type=row_type)
    result["row_type"] = "gt" if row_type == "ground_truth" else "predict"
    result["evaluation_status"] = "not_evaluated"
    for column in (
        "exclusion_reason", "confidence_threshold", "is_below_threshold", "prepared_index",
    ):
        result[column] = pd.Series([None] * len(result), index=result.index, dtype=object)
    result["matches_pre_threshold"] = "[]"
    result["matches_post_threshold"] = "[]"
    return result


def build_ground_truth_rows(source_ground_truth: pd.DataFrame) -> pd.DataFrame:
    """Retain all effective GT fields and source objects for canonical publication."""
    return _source_rows(source_ground_truth, "ground_truth")


def build_prediction_rows(
    source_predictions: pd.DataFrame, *, split: str | None = None,
) -> pd.DataFrame:
    """Retain unevaluated prediction source rows without inventing matches."""
    rows = _source_rows(source_predictions, "prediction")
    if split is not None:
        rows["split"] = split
    return rows


def _geometry_reason(row: pd.Series) -> str | None:
    boxes = [row[column] for column in _BOX_COLUMNS]
    if any(pd.isna(value) for value in boxes):
        return "missing"
    try:
        coordinates = [float(value) for value in boxes]
    except (TypeError, ValueError):
        return "nonnumeric"
    if not all(math.isfinite(value) for value in coordinates):
        return "nonfinite"
    if coordinates[2] < coordinates[0] or coordinates[3] < coordinates[1]:
        return "reversed_corners"
    if coordinates[2] == coordinates[0] or coordinates[3] == coordinates[1]:
        return "zero_area"
    return None


def prepared_source_mapping(prepared: pd.DataFrame, source: pd.DataFrame) -> dict[int, str]:
    """Join dependency indices through preserved IDs, never through box coordinates."""
    if "source_row_id" not in prepared:
        raise ValueError("Prepared rows require explicit source_row_id lineage")
    if not prepared.index.is_unique or (prepared.index == -1).any():
        raise ValueError("Prepared row indices must be unique and distinct from -1")
    ids = prepared["source_row_id"]
    if ids.isna().any() or ids.astype(str).duplicated().any():
        raise ValueError("Prepared source_row_id must be unique and nonmissing")
    mapping: dict[int, str] = {}
    for index, source_id in ids.items():
        if not isinstance(index, (int, np.integer)):
            raise TypeError("Prepared row indices must be integers")
        mapping[int(index)] = str(source_id)
    unknown = set(mapping.values()) - set(source["source_row_id"])
    if unknown:
        raise ValueError(
            f"Prepared source_row_id is absent from the source frame: {sorted(unknown)}"
        )
    return mapping


def _relationship_lists(
    matches: Mapping[str, Sequence[ExportMatch]],
    *, phase: str, gt_mapping: dict[int, str], pred_mapping: dict[int, str],
) -> Relationships:
    relationships: Relationships = {}
    for number, match in enumerate(match for records in matches.values() for match in records):
        gt_id = None if match.gt_index == -1 else gt_mapping[match.gt_index]
        pred_id = None if match.pred_index == -1 else pred_mapping[match.pred_index]
        relationship = {
            "match_id": f"{phase}:{number}", "phase": phase, "status": match.type,
            "gt_source_row_id": gt_id, "pred_source_row_id": pred_id,
            "gt_index": None if match.gt_index == -1 else int(match.gt_index),
            "pred_index": None if match.pred_index == -1 else int(match.pred_index),
            "gt_label": str(match.gt_label), "pred_label": str(match.pred_label),
            "confidence": float(match.confidence), "iou": match.iou,
        }
        if gt_id is not None:
            relationships.setdefault(("ground_truth", gt_id), []).append(relationship)
        if pred_id is not None:
            relationships.setdefault(("prediction", pred_id), []).append(relationship)
    return relationships


def _row_status(
    row: pd.Series, row_type: RowType, prepared_indices: dict[str, int],
    post_relationships: Relationships,
) -> tuple[str, str | None]:
    if row_type == "ground_truth" and pd.isna(row["instance_label"]):
        return "background", None
    reason = _geometry_reason(row)
    if reason is not None:
        return "excluded", f"invalid_geometry:{reason}"
    source_id = str(row["source_row_id"])
    if source_id not in prepared_indices:
        reason = (
            "duplicate_ground_truth" if row_type == "ground_truth" else "prediction_preprocessing"
        )
        return "excluded", reason
    statuses = {
        relationship["status"]
        for relationship in post_relationships.get((row_type, source_id), [])
    }
    if row_type == "ground_truth":
        return ("TP" if "TP" in statuses else "FN"), None
    if statuses:
        return ("TP" if "TP" in statuses else "FP"), None
    return "filtered", "confidence_threshold"


def _enrich_rows(
    rows: pd.DataFrame, row_type: RowType, *, prepared_mapping: dict[int, str],
    thresholds: Mapping[str, float], before: Relationships, after: Relationships,
) -> pd.DataFrame:
    prepared_indices = {source_id: index for index, source_id in prepared_mapping.items()}
    records: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        source_id = str(row["source_row_id"])
        record = {str(key): value for key, value in row.to_dict().items()}
        status, reason = _row_status(row, row_type, prepared_indices, after)
        record.update(evaluation_status=status, exclusion_reason=reason,
                      prepared_index=prepared_indices.get(source_id))
        for phase, relationships in (("pre", before), ("post", after)):
            record[f"matches_{phase}_threshold"] = json.dumps(
                relationships.get((row_type, source_id), []), ensure_ascii=False, allow_nan=False,
                separators=(",", ":"),
            )
        if row_type == "prediction":
            threshold = thresholds.get(str(row["instance_label"]))
            record["confidence_threshold"] = threshold
            record["is_below_threshold"] = (
                None if threshold is None else float(row["confidence"]) < threshold
            )
            if threshold is None and status == "filtered":
                record.update(evaluation_status="excluded", exclusion_reason="class_not_evaluated")
        records.append(record)
    return pd.DataFrame(records, columns=rows.columns)


def build_result_rows(
    source_ground_truth: pd.DataFrame,
    source_predictions: pd.DataFrame,
    *,
    prepared_ground_truth: pd.DataFrame,
    prepared_predictions: pd.DataFrame,
    split: str,
    thresholds: Mapping[str, float],
    matches_pre_threshold: Mapping[str, Sequence[ExportMatch]],
    matches_post_threshold: Mapping[str, Sequence[ExportMatch]],
) -> pd.DataFrame:
    """Export scoped source populations and every fixed-matching relationship."""
    gt = build_ground_truth_rows(source_ground_truth)
    preds = build_prediction_rows(source_predictions)
    gt = gt[gt["split"] == split].copy()
    image_names = set(gt["image_name"].map(str))
    preds = preds[preds["image_name"].map(str).isin(image_names)].copy()
    gt_mapping = prepared_source_mapping(prepared_ground_truth, gt)
    pred_mapping = prepared_source_mapping(
        prepared_predictions[prepared_predictions["image_name"].map(str).isin(image_names)], preds,
    )
    before = _relationship_lists(matches_pre_threshold, phase="pre_threshold",
                                 gt_mapping=gt_mapping, pred_mapping=pred_mapping)
    after = _relationship_lists(matches_post_threshold, phase="post_threshold",
                                gt_mapping=gt_mapping, pred_mapping=pred_mapping)
    enriched = [
        _enrich_rows(gt, "ground_truth", prepared_mapping=gt_mapping, thresholds=thresholds,
                     before=before, after=after),
        _enrich_rows(preds, "prediction", prepared_mapping=pred_mapping, thresholds=thresholds,
                     before=before, after=after),
    ]
    result = pd.concat(enriched, ignore_index=True)
    result["split"] = split
    return result
