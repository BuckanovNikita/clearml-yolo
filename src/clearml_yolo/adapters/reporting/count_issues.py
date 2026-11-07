"""Separate unavailable count rows from report populations and retain their evidence."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook  # type: ignore[import-untyped]
from openpyxl.comments import Comment  # type: ignore[import-untyped]
from report_generator.v2 import MetricsTable

from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.core.report_counts import TrainingCountIssue, training_count

TRAIN_COLUMN = "Количество примеров train"
UNKNOWN_SHEET = "Unknown training count"
ISSUES_SHEET = "Report issues"
_IMPACT = "Excluded from training-count-filtered aggregates and comparison deltas."


def apply_training_counts(frame: pd.DataFrame, path: Path, counts: Mapping[str, int] | None) -> None:
    """Replace evaluation-population counts with checkpoint-owned training evidence."""
    frame[TRAIN_COLUMN] = [
        training_count(counts.get(str(label), 0)) if counts is not None else None for label in frame.index
    ]
    workbook = load_workbook(path)
    try:
        sheet = workbook.worksheets[0]
        headers = [cell.value for cell in sheet[1]]
        column = headers.index(TRAIN_COLUMN) + 1 if TRAIN_COLUMN in headers else len(headers) + 1
        sheet.cell(1, column, TRAIN_COLUMN)
        for row in range(2, sheet.max_row + 1):
            label = sheet.cell(row, 1).value
            if label in frame.index:
                value = frame.loc[label, TRAIN_COLUMN]
                cell = sheet.cell(row, column)
                cell.value = _cell_value(value)
                if isinstance(cell.value, str):
                    cell.data_type = "s"
        workbook.save(write_path(path))
    finally:
        workbook.close()
    table_frame = frame.rename_axis("Класс").reset_index()
    partition = partition_counts(MetricsTable(table_frame, path.name, path), "model")
    annotate_count_issues(path, (partition,))


@dataclass(frozen=True)
class CountPartition:
    # report-generator is an opaque third-party boundary under the mypy configuration.
    table: Any
    unknown: pd.DataFrame
    issues: tuple[TrainingCountIssue, ...]


def partition_counts(table: Any, model: str) -> CountPartition:
    """Keep only count-valid rows for the strict dependency; never invent counts."""
    frame = table.frame.copy(deep=True)
    columns = [column for column in frame.columns if "train" in str(column).lower() and "пример" in str(column).lower()]
    if len(columns) > 1:
        raise ValueError(f"Multiple training count columns in {table.source_name}: {columns}")
    column = columns[0] if columns else TRAIN_COLUMN
    if not columns:
        frame[column] = None
    counts = [training_count(value) for value in frame[column]]
    valid = pd.Series([value is not None for value in counts], index=frame.index, dtype=bool)
    unknown = frame.loc[~valid].copy()
    unknown[column] = "NA"
    unknown.insert(0, "Model", model)
    issues = tuple(
        TrainingCountIssue(
            model=model,
            class_name=str(label),
            field=str(column),
            reason=("Missing training count" if not columns else "Unavailable or invalid training count"),
        )
        for label in unknown["Класс"]
    )
    eligible = frame.loc[valid].copy()
    eligible[column] = [value for value in counts if value is not None]
    return CountPartition(MetricsTable(eligible, table.source_name, table.source_path), unknown, issues)


def _cell_value(value: Any) -> Any:
    # Workbook scalar values come from pandas and may be numpy scalar wrappers.
    if pd.isna(value):
        return "NA"
    return value.item() if hasattr(value, "item") else value


def _append(sheet: Any, values: list[Any]) -> None:
    sheet.append([_cell_value(value) for value in values])
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def annotate_count_issues(path: Path, partitions: tuple[CountPartition, ...]) -> None:
    """Append visible warning evidence without changing original metric cells."""
    issues = tuple(issue for partition in partitions for issue in partition.issues)
    if not issues:
        return
    workbook = load_workbook(path)
    try:
        for title in (UNKNOWN_SHEET, ISSUES_SHEET):
            if title in workbook.sheetnames:
                raise ValueError(f"Reserved count diagnostics worksheet already exists: {title}")
        unknown_sheet = workbook.create_sheet(UNKNOWN_SHEET)
        frames = [partition.unknown for partition in partitions if partition.issues]
        unknown = pd.concat(frames, ignore_index=True, sort=False)
        _append(unknown_sheet, list(unknown.columns))
        for row in unknown.itertuples(index=False, name=None):
            _append(unknown_sheet, list(row))
        issue_sheet = workbook.create_sheet(ISSUES_SHEET)
        _append(issue_sheet, ["Model", "Class", "Field", "Reason", "Aggregate impact"])
        for issue in issues:
            _append(
                issue_sheet,
                [issue.model, issue.class_name, issue.field, issue.reason, _IMPACT],
            )
        workbook.active = workbook.index(issue_sheet)
        for sheet in workbook:
            if sheet in (unknown_sheet, issue_sheet):
                sheet.freeze_panes = "A2"
                sheet.auto_filter.ref = sheet.dimensions
                sheet.column_dimensions["A"].width = 28
                sheet.column_dimensions["B"].width = 30
            else:
                warning = (
                    f"WARNING: {len(issues)} unavailable training counts. "
                    f"See '{ISSUES_SHEET}' and '{UNKNOWN_SHEET}'. {_IMPACT}"
                )
                if all(partition.table.frame.empty for partition in partitions):
                    warning += " No eligible classes; aggregate metrics are unavailable."
                # Dashboards are also machine inputs: diagnostic text must never become a class row.
                sheet.cell(1, 1).comment = Comment(warning, "clearml-yolo")
                sheet.sheet_properties.tabColor = "FFEB9C"
        workbook.save(write_path(path))
    finally:
        workbook.close()
