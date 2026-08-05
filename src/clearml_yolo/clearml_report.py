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

POOLED_COLUMN = "is_pooled"
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
    adjusted_p_column: str
    verdict_column: str


# Every class contributes one hypothesis per metric to the BH family, so the adjusted
# p-value is per (class, metric) rather than per class.
COMPARED_METRICS = (
    ComparedMetric("precision", "precision_delta", "precision_p_bh", "precision_verdict"),
    ComparedMetric("recall", "recall_delta", "recall_p_bh", "recall_verdict"),
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


def _tested_hypotheses(per_class: pd.DataFrame) -> pd.DataFrame:
    """Which (class, metric) hypotheses carry a BH-adjusted p-value, one column per metric.

    A class can be tested on one metric and not the other: a class with ground truth but no
    predictions from either model has a defined recall test and an undefined precision one.
    """
    tested: dict[str, pd.Series[Any]] = {}
    for metric in COMPARED_METRICS:
        if metric.adjusted_p_column in per_class.columns:
            adjusted = pd.to_numeric(per_class[metric.adjusted_p_column], errors="coerce")
            tested[metric.name] = adjusted.notna()
        else:
            logger.warning(
                "Comparison rows have no {!r} column; the {} hypotheses are not counted",
                metric.adjusted_p_column,
                metric.name,
            )
    return pd.DataFrame(tested, index=per_class.index)


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
    per_class: pd.DataFrame,
    pooled: pd.DataFrame,
    verdicts: Mapping[str, pd.Series[Any]],
    tested_hypotheses: pd.DataFrame,
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

    if not tested_hypotheses.columns.empty:
        # A class counts as tested once either of its two hypotheses entered the family.
        tested = float(tested_hypotheses.any(axis=1).sum())
        values[TESTED_VALUE_NAME] = tested
        values[EXCLUDED_VALUE_NAME] = float(len(per_class)) - tested

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

    ``rows`` is the per-class comparison frame — one row per class plus the pooled row,
    which is the one flagged by ``is_pooled``; ``methodology`` records how the comparison
    was decided (tests used, BH family size, q, seed, threshold and weights sources,
    counts). Three tables are published — the full comparison, the classes that
    significantly degraded, and the methodology — alongside the headline single values.
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

    if POOLED_COLUMN not in rows.columns:
        logger.warning(
            "Comparison rows have no {!r} column, so the pooled row cannot be told apart "
            "from the per-class ones; skipping the headline values",
            POOLED_COLUMN,
        )
        return

    is_pooled = rows[POOLED_COLUMN].eq(True).fillna(False).astype(bool)
    per_class = rows[~is_pooled]
    pooled = rows[is_pooled]
    if pooled.empty:
        logger.warning(
            "No comparison row for split {!r} is flagged {!r}; the pooled deltas are not reported",
            split,
            POOLED_COLUMN,
        )
    verdicts = _verdicts(per_class)

    degraded = _degraded_classes(per_class, verdicts)
    report_table(task, DEGRADED_TABLE_TITLE, split, degraded)
    if not degraded.empty:
        logger.warning("Split {!r}: {} class(es) significantly degraded", split, len(degraded))

    tested_hypotheses = _tested_hypotheses(per_class)
    headline = _headline_values(per_class, pooled, verdicts, tested_hypotheses)

    # The BH family is the set of hypotheses, two per class, so the declared family size is
    # compared against the adjusted p-values themselves rather than against a class count.
    # Real covers numpy's scalars too, which a count computed upstream easily is.
    declared_family_size = methodology.get(FAMILY_SIZE_KEY)
    hypotheses = float(tested_hypotheses.to_numpy().sum())
    if (
        isinstance(declared_family_size, Real)
        and not tested_hypotheses.columns.empty
        and float(declared_family_size) != hypotheses
    ):
        logger.warning(
            "Methodology declares a BH family size of {} but the comparison rows carry "
            "{:.0f} adjusted p-value(s)",
            declared_family_size,
            hypotheses,
        )

    task_logger = task.get_logger()
    for name, value in headline.items():
        task_logger.report_single_value(name=f"{split}/{name}", value=value)
    logger.info("Split {!r}: reported {} headline single values to ClearML", split, len(headline))
