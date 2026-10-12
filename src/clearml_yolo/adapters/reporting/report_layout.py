"""Compatibility adapter for compacting existing freshly generated reports."""

from collections.abc import Mapping
from pathlib import Path

from report_generator.v2 import compact_report_counts as compact_counts


def compact_report_counts(
    path: Path,
    sheet_names: tuple[str, ...],
    *,
    translations: Mapping[str, str] | None = None,
) -> None:
    """Move aggregate availability below tables without recalculating metrics."""
    compact_counts(path, sheet_names, translations=translations)
