"""Pandera contracts preserve lexical input, stage geometry and row lineage.

Checks may interpret numeric cells, as the existing CSV readers and scientific
dependency do, but never assign converted values back to the caller's frame.
Raw geometry remains evidence until an explicit preparation policy filters it.
"""

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

BOX_COLUMNS = ("bbox_x_tl", "bbox_y_tl", "bbox_x_br", "bbox_y_br")


class ValidationStage(StrEnum):
    RAW_GROUND_TRUTH = "raw_ground_truth"
    TRAINING_GROUND_TRUTH = "training_ground_truth"
    PREPARED_GROUND_TRUTH = "prepared_ground_truth"
    RAW_PREDICTIONS = "raw_predictions"
    EVALUATION_PREDICTIONS = "evaluation_predictions"
    PUBLICATION_GROUND_TRUTH = "publication_ground_truth"
    PUBLICATION_PREDICTIONS = "publication_predictions"
    RESULTS = "results"


@dataclass(frozen=True)
class ValidationFinding:
    """A fatal schema finding referring to the original dataframe row label."""

    stage: ValidationStage
    column: str | None
    row: object
    check: str
    failure: object


class DataFrameValidationError(ValueError):
    """Structured dataframe failures; adapters retain their lexical diagnostics."""

    def __init__(self, stage: ValidationStage, findings: tuple[ValidationFinding, ...]) -> None:
        self.stage = stage
        self.findings = findings
        detail = "; ".join(
            f"{finding.column or 'dataframe'} at {finding.row!r}: {finding.check}"
            for finding in findings
        )
        super().__init__(f"Invalid {stage.value} dataframe: {detail}")


def _empty(value: object) -> bool:
    return (value is None or (isinstance(value, str) and value == "")
            or bool(np.asarray(pd.isna(np.asarray(value))).all()))


def _nonempty(value: object) -> bool:
    return not _empty(value)


def _confidence(value: object) -> bool:
    try:
        number = float(cast(str | float, value))
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and 0 <= number <= 1


def _json_relationships(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        relationships = json.loads(value)
    except (ValueError, TypeError):
        return False
    return isinstance(relationships, list) and all(
        isinstance(relationship, dict) for relationship in relationships
    )


def _geometry(frame: pd.DataFrame, *, backgrounds: bool, collapsed: bool) -> pd.Series:
    validity: list[bool] = []
    for label, *cells in frame[["instance_label", *BOX_COLUMNS]].itertuples(
        index=False, name=None
    ):
        if backgrounds and _empty(label) and all(_empty(value) for value in cells):
            validity.append(True)
            continue
        try:
            x1, y1, x2, y2 = (float(value) for value in cells)
        except (TypeError, ValueError):
            validity.append(False)
            continue
        ordered = x2 >= x1 and y2 >= y1 if collapsed else x2 > x1 and y2 > y1
        validity.append(
            (collapsed or _nonempty(label))
            and all(math.isfinite(value) for value in (x1, y1, x2, y2))
            and ordered
        )
    return pd.Series(validity, index=frame.index, dtype=bool)


def _positive_ground_truth(frame: pd.DataFrame) -> pd.Series:
    return _geometry(frame, backgrounds=True, collapsed=False)


def _image_bounds(frame: pd.DataFrame) -> pd.Series:
    background = frame["instance_label"].map(_empty)
    return background | (
        (frame["bbox_x_tl"] >= 0) & (frame["bbox_y_tl"] >= 0)
        & (frame["bbox_x_br"] <= frame["width"])
        & (frame["bbox_y_br"] <= frame["height"])
    )


def _unique_training_rows(frame: pd.DataFrame) -> pd.Series:
    return ~frame.duplicated(subset=["image_name", "instance_label", *BOX_COLUMNS], keep=False)


def _positive_predictions(frame: pd.DataFrame) -> pd.Series:
    return _geometry(frame, backgrounds=False, collapsed=False)


def _publication_predictions(frame: pd.DataFrame) -> pd.Series:
    return _geometry(frame, backgrounds=False, collapsed=True)


def _row_indices(frame: pd.DataFrame) -> bool:
    return frame.index.is_unique and all(
        index != -1 and not bool(np.asarray(pd.isna(index)).any()) for index in frame.index
    )


def _split_ownership(frame: pd.DataFrame) -> bool:
    if "split" not in frame:
        return True
    return not frame[["image_name", "split"]].drop_duplicates()["image_name"].duplicated().any()


def _source_ids(series: pd.Series) -> bool:
    return not series.isna().any() and not series.map(str).duplicated().any()


def _column(*, required: bool = True, nonempty: bool = False) -> pa.Column:
    checks = pa.Check(_nonempty, element_wise=True, ignore_na=False) if nonempty else None
    return pa.Column(checks=checks, required=required, nullable=not nonempty, coerce=False)


def _ground_truth_identity_columns(stage: ValidationStage) -> dict[str, pa.Column]:
    if stage not in {
        ValidationStage.RAW_GROUND_TRUTH, ValidationStage.PREPARED_GROUND_TRUTH,
        ValidationStage.TRAINING_GROUND_TRUTH, ValidationStage.PUBLICATION_GROUND_TRUTH,
    }:
        return {}
    required = stage == ValidationStage.PUBLICATION_GROUND_TRUTH
    return {name: _column(required=required, nonempty=True)
            for name in ("image_path", "split")}


def schema_for(stage: ValidationStage | str) -> pa.DataFrameSchema:
    """Create a stage schema without importing SDKs or touching external state."""
    selected = ValidationStage(stage)
    prediction = selected in {
        ValidationStage.RAW_PREDICTIONS, ValidationStage.EVALUATION_PREDICTIONS,
        ValidationStage.PUBLICATION_PREDICTIONS,
    }
    publication = selected in {
        ValidationStage.PUBLICATION_GROUND_TRUTH, ValidationStage.PUBLICATION_PREDICTIONS,
    }
    results = selected == ValidationStage.RESULTS
    columns = {
        "image_name": _column(nonempty=True),
        "instance_label": pa.Column(nullable=not prediction, coerce=False),
        **{column: _column() for column in BOX_COLUMNS},
    }
    if prediction:
        columns["confidence"] = pa.Column(
            checks=pa.Check(_confidence, element_wise=True, ignore_na=False),
            nullable=False, coerce=False,
        )
    columns.update(_ground_truth_identity_columns(selected))
    columns["source_row_id"] = pa.Column(
        checks=None if publication or results else pa.Check(_source_ids),
        required=results, nullable=False, coerce=False,
    )
    checks: list[pa.Check] = []
    if selected in {
        ValidationStage.PREPARED_GROUND_TRUTH, ValidationStage.TRAINING_GROUND_TRUTH,
    }:
        checks.extend([
            pa.Check(_positive_ground_truth, name="positive_or_background_geometry",
                     ignore_na=False),
            pa.Check(_split_ownership, name="image_split_ownership"),
        ])
        if selected == ValidationStage.TRAINING_GROUND_TRUTH:
            columns.update(width=_column(), height=_column())
            checks.extend([
                pa.Check(_image_bounds, name="image_bounds", ignore_na=False),
                pa.Check(_unique_training_rows, name="unique_training_boxes_or_backgrounds",
                         ignore_na=False),
            ])
    elif selected == ValidationStage.EVALUATION_PREDICTIONS:
        checks.append(pa.Check(_positive_predictions, name="positive_prediction_geometry",
                               ignore_na=False))
    elif selected == ValidationStage.PUBLICATION_GROUND_TRUTH:
        checks.append(pa.Check(_positive_ground_truth, name="positive_or_background_geometry",
                               ignore_na=False))
    elif selected == ValidationStage.PUBLICATION_PREDICTIONS:
        checks.append(pa.Check(_publication_predictions, name="ordered_prediction_geometry",
                               ignore_na=False))
    if not publication and not results:
        checks.append(pa.Check(_row_indices, name="unique_nonmissing_row_indices"))
    if selected in {
        ValidationStage.PREPARED_GROUND_TRUTH, ValidationStage.RAW_PREDICTIONS,
        ValidationStage.EVALUATION_PREDICTIONS,
    }:
        columns["instance_label"].checks.append(
            pa.Check(lambda labels: labels != "background", name="reserved_background_label")
        )
    if results:
        columns.update({
            "row_type": pa.Column(checks=pa.Check.isin(["gt", "predict"]), nullable=False),
            "evaluation_status": pa.Column(checks=pa.Check.isin([
                "not_evaluated", "background", "excluded", "TP", "FP", "FN", "filtered",
            ]), nullable=False),
            **{name: pa.Column(checks=pa.Check(_json_relationships, element_wise=True),
                              nullable=False) for name in (
                "matches_pre_threshold", "matches_post_threshold",
            )},
        })
    return pa.DataFrameSchema(columns=columns, checks=checks, coerce=False, strict=False,
                              drop_invalid_rows=False, unique_column_names=True,
                              name=selected.value)


def validate_dataframe(frame: pd.DataFrame, stage: ValidationStage | str) -> pd.DataFrame:
    """Validate a copy; never silently repair, filter or renumber caller rows."""
    selected = ValidationStage(stage)
    try:
        validated = schema_for(selected).validate(frame, lazy=True, inplace=False)
    except SchemaErrors as error:
        findings: list[ValidationFinding] = []
        for record in error.failure_cases.to_dict("records"):
            column = record.get("column")
            # Missing-column errors store the absent name in failure_case.
            if record.get("check") == "column_in_dataframe":
                column = record.get("failure_case")
            findings.append(ValidationFinding(
                stage=selected, column=None if _empty(column) else str(column),
                row=record.get("index"), check=str(record.get("check")),
                failure=record.get("failure_case"),
            ))
        raise DataFrameValidationError(selected, tuple(findings)) from error
    return validated
