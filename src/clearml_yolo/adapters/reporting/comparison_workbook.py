"""Render the application's paired comparison using shared workbook mechanics."""

from pathlib import Path
from typing import cast

import pandas as pd
from loguru import logger
from report_generator.v2 import write_comparison_workbook as write_shared_workbook
from report_generator.v2.comparison import (
    COMPARISON_COLUMNS,
    COMPARISON_SHEET,
    DEGRADED,
    DISPLAY_DECIMALS,
    EXCLUDED_COLUMNS,
    IMPROVED,
    MISSING_VALUE,
    NOT_APPLICABLE,
    NOT_SIGNIFICANT,
    POOLED_FLAG,
    POOLED_LABEL,
    VERDICT_LABELS,
)

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import write_path

__all__ = [
    "COMPARISON_COLUMNS",
    "COMPARISON_SHEET",
    "DEGRADED",
    "DISPLAY_DECIMALS",
    "EXCLUDED_COLUMNS",
    "IMPROVED",
    "MISSING_VALUE",
    "NOT_APPLICABLE",
    "NOT_SIGNIFICANT",
    "POOLED_FLAG",
    "POOLED_LABEL",
    "VERDICT_LABELS",
    "write_comparison_workbook",
]


@trace_operation("report.comparison.workbook")
def write_comparison_workbook(
    rows: pd.DataFrame,
    excluded: pd.DataFrame,
    methodology: dict[str, object],
    path: Path,
) -> dict[str, Path]:
    """Write unchanged comparison Excel and exclusion/methodology CSV artifacts."""
    path = write_path(path)
    for title in ("excluded", "methodology"):
        write_path(path.with_name(f"{path.stem}_{title}.csv"))
    tables = cast(dict[str, Path], write_shared_workbook(rows, excluded, methodology, path))
    logger.info("Comparison workbook: {} ({} classes, {} excluded)", path, len(rows), len(excluded))
    return tables
