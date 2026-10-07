"""Publish readable current-model plots and comparison headline values to ClearML.

Detailed comparisons remain downloadable reports. Every entry point is a no-op for
workers (task=None); rendering never recomputes evaluation observations.
"""

from collections.abc import Mapping, Sequence
from html import escape
from numbers import Real
from textwrap import wrap
from typing import Any, NamedTuple

import pandas as pd
from loguru import logger

from clearml_yolo.clearml_session import Task
from clearml_yolo.model_identity import ModelIdentity
from clearml_yolo.result_schema import ConfusionMatrixPayload, PRCurve, ResultContext

ITERATION = 0


def _display_label(context: ResultContext, display_label: str | None) -> str:
    if display_label is not None:
        return display_label
    name = context.model_identity.model_name if context.model_identity else "Current model"
    return f"{name} · {context.split}"


def _caption_annotation(caption: str) -> dict[str, Any]:
    # ClearML report_plotly replaces layout.title with series; annotations survive.
    return {
        "text": caption,
        "xref": "paper",
        "yref": "paper",
        "x": 0.5,
        "y": 1.02,
        "yanchor": "bottom",
        "font": {"size": 11},
        "showarrow": False,
    }


def _confusion_trace(matrix: ConfusionMatrixPayload, normalization: str) -> dict[str, Any]:
    counts = matrix.counts
    row_totals = [sum(row) for row in counts]
    column_totals = [sum(row[index] for row in counts) for index in range(len(counts))]
    total = sum(row_totals)
    values: list[list[int | float]] = []
    hover: list[list[list[int | str]]] = []
    for row_index, row in enumerate(counts):
        value_row: list[int | float] = []
        hover_row: list[list[int | str]] = []
        for column_index, count in enumerate(row):
            denominator = {
                "raw": total,
                "row": row_totals[row_index],
                "column": column_totals[column_index],
                "global": total,
            }[normalization]
            value_row.append(
                count
                if normalization == "raw"
                else (100 * count / denominator if denominator else 0)
            )
            hover_row.append([count, denominator, "observed" if denominator else "no observations"])
        values.append(value_row)
        hover.append(hover_row)
    trace: dict[str, Any] = {
        "type": "heatmap",
        "x": list(range(len(counts))),
        "y": list(range(len(counts))),
        "z": values,
        "customdata": hover,
        "text": [
            [
                f"True: {escape(true)}<br>Predicted: {escape(predicted)}"
                for predicted in matrix.labels
            ]
            for true in matrix.labels
        ],
        "colorscale": "Blues",
        "hovertemplate": "%{text}<br>Count: %{customdata[0]}<br>Denominator: %{customdata[1]}"
        "<br>%{customdata[2]}<br>Value: %{z}<extra></extra>",
    }
    if normalization != "raw":
        trace.update(zmin=0, zmax=100, colorbar={"title": "Percent", "ticksuffix": "%"})
    return trace


def report_confusion_matrices(
    task: Task,
    context: ResultContext,
    matrix: ConfusionMatrixPayload,
    *,
    display_label: str | None = None,
) -> None:
    """Publish one heatmap with selectable normalizations of the exact same counts."""
    if task is None:
        return
    axis = {
        "tickmode": "array",
        "tickvals": list(range(len(matrix.labels))),
        "ticktext": [escape(label) for label in matrix.labels],
    }
    modes = (("raw", "Counts"), ("row", "Row %"), ("column", "Column %"),
             ("global", "Overall %"))
    label = _display_label(context, display_label)
    caption = escape(label)
    data = [
        {**_confusion_trace(matrix, mode), "visible": index == 0, "name": name}
        for index, (mode, name) in enumerate(modes)
    ]
    figure = {
        "data": data,
        "layout": {
            "title": caption,
            "annotations": [_caption_annotation(caption)],
            "margin": {"t": 120},
            "xaxis": {**axis, "title": "Predicted class"},
            "yaxis": {**axis, "title": "True class", "autorange": "reversed"},
            "updatemenus": [{
                "type": "dropdown", "active": 0, "x": 0, "y": 1.18,
                "buttons": [
                    {"label": name, "method": "restyle",
                     "args": [{"visible": [i == index for i in range(len(modes))]}]}
                    for index, (_, name) in enumerate(modes)
                ],
            }],
        },
    }
    task.get_logger().report_plotly(
        title="Confusion matrix", series=label, iteration=ITERATION, figure=figure,
    )


def _pr_trace(curve: PRCurve) -> dict[str, Any]:
    no_gt = curve.gt_count == 0
    ap50 = None if no_gt else (curve.ap50 if curve.recall else 0.0)
    ap_caption = "unavailable" if ap50 is None else f"{ap50:.6g}"
    name = f"{escape(curve.class_name)} · AP50={ap_caption} ({escape(curve.integration_method)})"
    if no_gt:
        name += " · No ground truth: recall unavailable"
    elif not curve.recall:
        name += " · No predictions"
    return {
        "type": "scatter", "mode": "lines+markers", "name": name,
        # A null gap keeps the legend visible in Plotly without plotting a point.
        "x": [None] if no_gt or not curve.recall else curve.recall,
        "y": [None] if no_gt or not curve.precision else curve.precision,
        "customdata": [] if no_gt else [
            list(point) for point in zip(curve.confidence, curve.tp, curve.fp, strict=True)
        ],
        "meta": [escape(curve.class_name), ap50, escape(curve.integration_method)],
        "hovertemplate": "Class: %{meta[0]}<br>AP50: %{meta[1]}<br>Method: %{meta[2]}"
        "<br>Recall: %{x}<br>Precision: %{y}<br>Confidence: %{customdata[0]}"
        "<br>Cumulative TP: %{customdata[1]}<br>Cumulative FP: %{customdata[2]}<extra></extra>",
    }


def report_pr_curves(
    task: Task, context: ResultContext, curves: Sequence[PRCurve],
    *, display_label: str | None = None,
) -> None:
    """Group current test PR classes; empty populations never invent operating points."""
    if task is None or context.split != "test":
        return
    label = _display_label(context, display_label)
    caption = f"{escape(label)} · IoU 0.50"
    annotations = [_caption_annotation(caption)]
    if not curves:
        annotations.append({
            "text": "No classes available", "xref": "paper", "yref": "paper",
            "x": 0.5, "y": 0.5, "showarrow": False,
        })
    figure = {
        "data": [_pr_trace(curve) for curve in curves],
        "layout": {
            "title": caption, "annotations": annotations,
            "margin": {"t": 90, "b": 80},
            "xaxis": {"title": "Recall", "range": [0, 1]},
            "yaxis": {"title": "Precision", "range": [0, 1]},
            "showlegend": True,
            "legend": {"title": {"text": "Class · AP50 (method)"}},
        },
    }
    task.get_logger().report_plotly(
        title="Precision-recall", series=label, iteration=ITERATION, figure=figure,
    )


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


def report_table(
    task: Task, title: str, series: str, frame: pd.DataFrame,
    *, identities: Mapping[str, ModelIdentity] | None = None,
) -> None:
    """Publish a DataFrame as a ClearML table plot, skipping distributed workers."""
    if task is None:
        return
    display_frame = frame.copy() if identities else frame
    for role, identity in (identities or {}).items():
        display_frame[f"{role}_model_name"] = identity.model_name
        display_frame[f"{role}_training_task_id"] = identity.training_task_id or "unavailable"
    options: dict[str, Any] = {}
    if identities:
        caption = "<br>".join(
            escape(line)
            for role, identity in identities.items()
            for line in wrap(f"{role}: {identity.model_name}", width=100)
        )
        options["extra_layout"] = {
            "annotations": [_caption_annotation(caption)],
            "margin": {"t": max(120, 24 * (caption.count("<br>") + 1) + 20)},
        }
    task.get_logger().report_table(
        title=title, series=series, iteration=ITERATION, table_plot=display_frame, **options,
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


def _verdicts(per_class: pd.DataFrame) -> dict[str, "pd.Series[Any]"]:
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
    per_class: pd.DataFrame, verdicts: Mapping[str, "pd.Series[Any]"]
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
    verdicts: Mapping[str, "pd.Series[Any]"],
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
            # Missing comparisons have no numeric headline; preserve them in the table.
            pooled_delta = pd.to_numeric(pooled[compared.delta_column], errors="coerce").iloc[0]
            if not pd.isna(pooled_delta):
                values[f"pooled_delta_{compared.name}"] = float(pooled_delta)

    return values


def report_comparison(
    task: Task, split: str, rows: pd.DataFrame, methodology: Mapping[str, object],
) -> None:
    """Publish comparison headline values outside Plots; detailed reports stay artifacts."""
    if task is None:
        return

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
