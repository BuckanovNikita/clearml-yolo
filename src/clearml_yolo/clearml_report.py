"""Publish the model comparison to ClearML in a form a reviewer can read in place.

Uploading spreadsheets is not reporting: a reviewer should be able to answer "did this
model get better?" from the ClearML scalar panel, and audit *how* that was decided from
the methodology table next to it, without downloading anything.

Regressions lead. The significance tests are two-sided, so degradation is in the data;
the degraded counts are reported before the improved ones and the degraded classes get
their own table, because a model that improves twelve classes while breaking three must
never read as an unqualified win.

Every entry point is a no-op when ``task`` is ``None`` (ClearML tracking is switchable
off), and a missing column is a warning rather than an exception — a reporting layer must
never fail a run that already produced valid results.

The constants below are the integration seam with the comparison frame: they name the
columns this module reads out of it.
"""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any, NamedTuple

import pandas as pd
from loguru import logger

from clearml_yolo.clearml_session import Task

COMPARISON_TABLE_TITLE = "comparison"
DEGRADED_TABLE_TITLE = "comparison_degraded"
METHODOLOGY_TABLE_TITLE = "comparison_methodology"
ITERATION = 0

CLASS_COLUMN = "class"
POOLED_CLASS_LABEL = "Итого"
ADJUSTED_P_COLUMN = "p_adjusted"
FAMILY_SIZE_KEY = "family_size"
TESTED_VALUE_NAME = "classes_tested"
EXCLUDED_VALUE_NAME = "classes_excluded"

# The verdict columns already encode BH significance *and* direction, so the sign of the
# delta is never re-derived here.
DEGRADED_VERDICT = "degraded"
IMPROVED_VERDICT = "improved"


class ComparedMetric(NamedTuple):
    """Where one tested metric's change lives in the comparison frame."""

    name: str
    delta_column: str
    verdict_column: str


COMPARED_METRICS = (
    ComparedMetric("precision", "delta_precision", "precision_verdict"),
    ComparedMetric("recall", "delta_recall", "recall_verdict"),
)


def report_table(task: Task, title: str, series: str, frame: pd.DataFrame) -> None:
    """Publish a DataFrame as a ClearML table plot, tolerating disabled tracking."""
    if task is None:
        return
    task.get_logger().report_table(
        title=title, series=series, iteration=ITERATION, table_plot=frame
    )
    logger.debug("Reported table {}/{} ({} rows)", title, series, len(frame))


def report_scalars(task: Task, title: str, values: Mapping[str, float]) -> None:
    """Publish named values as one ClearML scalar plot, one series per name."""
    if task is None:
        return
    task_logger = task.get_logger()
    for series, value in values.items():
        task_logger.report_scalar(
            title=title, series=series, value=float(value), iteration=ITERATION
        )
    logger.debug("Reported {} scalars under {}", len(values), title)


def _class_labels(rows: pd.DataFrame) -> pd.Series[Any] | None:
    """Per-row class labels, whether they live in a column or in the index."""
    if CLASS_COLUMN in rows.columns:
        return rows[CLASS_COLUMN]
    if POOLED_CLASS_LABEL in rows.index:
        return rows.index.to_series()
    return None


def _verdicts(per_class: pd.DataFrame) -> dict[str, pd.Series[Any]]:
    """The verdict column of every compared metric the frame actually carries."""
    found: dict[str, pd.Series[Any]] = {}
    for metric in COMPARED_METRICS:
        if metric.verdict_column in per_class.columns:
            found[metric.name] = per_class[metric.verdict_column]
        else:
            logger.warning(
                "Comparison rows have no {!r} column; skipping the {} verdict counts",
                metric.verdict_column,
                metric.name,
            )
    return found


def _degraded_classes(
    per_class: pd.DataFrame, verdicts: Mapping[str, pd.Series[Any]]
) -> pd.DataFrame:
    """The per-class rows that got significantly worse on at least one metric."""
    if not verdicts:
        return per_class.iloc[:0]
    is_degraded = pd.Series(False, index=per_class.index)
    for verdict in verdicts.values():
        is_degraded |= verdict.eq(DEGRADED_VERDICT).fillna(False).astype(bool)
    return per_class[is_degraded]


def _headline_values(
    per_class: pd.DataFrame, pooled: pd.DataFrame, verdicts: Mapping[str, pd.Series[Any]]
) -> dict[str, float]:
    """Reduce the comparison to the handful of numbers that answer "did it get better?".

    Degradation goes first: a reviewer skimming the ClearML scalar panel must hit the bad
    news before the good news. The names lead with the direction rather than the metric so
    that holds whether the panel keeps the reporting order or sorts by name.
    """
    values: dict[str, float] = {}

    for metric, verdict in verdicts.items():
        values[f"degraded_{metric}"] = float(verdict.eq(DEGRADED_VERDICT).fillna(False).sum())
    for metric, verdict in verdicts.items():
        values[f"improved_{metric}"] = float(verdict.eq(IMPROVED_VERDICT).fillna(False).sum())

    if ADJUSTED_P_COLUMN in per_class.columns:
        tested = float(pd.to_numeric(per_class[ADJUSTED_P_COLUMN], errors="coerce").notna().sum())
        values[TESTED_VALUE_NAME] = tested
        values[EXCLUDED_VALUE_NAME] = float(len(per_class)) - tested
    else:
        logger.warning(
            "Comparison rows have no {!r} column; the tested/excluded class counts are "
            "not reported",
            ADJUSTED_P_COLUMN,
        )

    for compared in COMPARED_METRICS:
        if compared.delta_column not in per_class.columns:
            logger.warning(
                "Comparison rows have no {!r} column; skipping the pooled {} delta",
                compared.delta_column,
                compared.name,
            )
        elif not pooled.empty:
            # A nullable dtype yields pd.NA here, which float() refuses; the headline is
            # reported as NaN rather than taking the whole report down with it.
            pooled_delta = pd.to_numeric(pooled[compared.delta_column], errors="coerce").iloc[0]
            values[f"pooled_delta_{compared.name}"] = (
                float("nan") if pd.isna(pooled_delta) else float(pooled_delta)
            )

    return values


def report_comparison(
    task: Task, split: str, rows: pd.DataFrame, methodology: Mapping[str, object]
) -> None:
    """Publish one split's comparison: the tables, the headline numbers and the method.

    ``rows`` is the per-class comparison frame (one row per class plus the pooled
    ``Итого`` row); ``methodology`` records how the comparison was decided (tests used,
    BH family size, q, seed, threshold and weights sources, counts). Three tables are
    published — the full comparison, the classes that significantly degraded, and the
    methodology — alongside the headline single values.
    """
    if task is None:
        return

    report_table(task, COMPARISON_TABLE_TITLE, split, rows)
    report_table(
        task,
        METHODOLOGY_TABLE_TITLE,
        split,
        pd.DataFrame(
            {
                "parameter": [str(key) for key in methodology],
                "value": [str(value) for value in methodology.values()],
            }
        ),
    )

    labels = _class_labels(rows)
    if labels is None:
        logger.warning(
            "Comparison rows have no {!r} column and no pooled {!r} index entry; "
            "skipping the headline values",
            CLASS_COLUMN,
            POOLED_CLASS_LABEL,
        )
        return

    is_pooled = labels == POOLED_CLASS_LABEL
    per_class = rows[~is_pooled]
    pooled = rows[is_pooled]
    if pooled.empty:
        logger.warning(
            "Comparison rows for split {!r} have no pooled {!r} row; the pooled deltas are "
            "not reported",
            split,
            POOLED_CLASS_LABEL,
        )
    verdicts = _verdicts(per_class)

    degraded = _degraded_classes(per_class, verdicts)
    report_table(task, DEGRADED_TABLE_TITLE, split, degraded)
    if not degraded.empty:
        logger.warning("Split {!r}: {} class(es) significantly degraded", split, len(degraded))

    headline = _headline_values(per_class, pooled, verdicts)

    # Real covers numpy's scalars too, which a count computed upstream easily is.
    declared_family_size = methodology.get(FAMILY_SIZE_KEY)
    tested = headline.get(TESTED_VALUE_NAME)
    if (
        isinstance(declared_family_size, Real)
        and tested is not None
        and float(declared_family_size) != tested
    ):
        logger.warning(
            "Methodology declares a family size of {} but {:.0f} classes carry an adjusted "
            "p-value in the comparison rows",
            declared_family_size,
            tested,
        )

    task_logger = task.get_logger()
    for name, value in headline.items():
        task_logger.report_single_value(name=f"{split}/{name}", value=value)
    logger.info("Split {!r}: reported {} headline single values to ClearML", split, len(headline))
