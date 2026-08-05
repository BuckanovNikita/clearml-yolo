"""ClearML-free tests for the comparison reporting layer.

A fake task records what the reporting layer asks of it, so the whole dispatch —
tables, scalars, single values and the warn-and-skip paths — is exercised without a
ClearML server or the SDK.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from typing import Any

import pandas as pd
import pytest
from loguru import logger

from clearml_yolo.clearml_report import (
    COMPARISON_TABLE_TITLE,
    DEGRADED_TABLE_TITLE,
    METHODOLOGY_TABLE_TITLE,
    report_comparison,
    report_scalars,
    report_table,
)


class _FakeLogger:
    def __init__(self) -> None:
        self.tables: list[dict[str, Any]] = []
        self.scalars: list[dict[str, Any]] = []
        self.single_values: dict[str, float] = {}

    def report_table(
        self, title: str, series: str, iteration: int, table_plot: pd.DataFrame
    ) -> None:
        self.tables.append({"title": title, "series": series, "frame": table_plot})

    def report_scalar(self, title: str, series: str, value: float, iteration: int) -> None:
        self.scalars.append({"title": title, "series": series, "value": value})

    def report_single_value(self, name: str, value: float) -> None:
        self.single_values[name] = value


class _FakeTask:
    def __init__(self) -> None:
        self._logger = _FakeLogger()

    def get_logger(self) -> _FakeLogger:
        return self._logger


@pytest.fixture
def warnings_log() -> Iterator[list[str]]:
    """Collect the loguru warnings emitted while the test runs."""
    messages: list[str] = []
    sink_id = logger.add(messages.append, level="WARNING", format="{message}")
    yield messages
    logger.remove(sink_id)


def _comparison_rows() -> pd.DataFrame:
    """Five classes plus the pooled row, covering every verdict and both test outcomes.

    'fish' is tested on recall only (a class with ground truth but no predictions has no
    defined precision test), 'worm' is excluded from the family entirely, and the pooled
    row is outside the family by design — so the seven adjusted p-values below are the BH
    family size, and four of the five classes count as tested.
    """
    return pd.DataFrame(
        {
            "class_name": ["cat", "dog", "bird", "fish", "worm", "Итого"],
            "is_pooled": [False, False, False, False, False, True],
            "precision_baseline": [0.80, 0.70, 0.70, 0.48, 0.60, 0.68],
            "precision_candidate": [0.90, 0.62, 0.75, 0.50, 0.60, 0.71],
            "precision_delta": [0.10, -0.08, 0.05, 0.02, 0.00, 0.03],
            "precision_p_bh": [0.01, 0.03, 0.40, None, None, None],
            "precision_verdict": [
                "improved",
                "degraded",
                "not_significant",
                "not_significant",
                "not_significant",
                "improved",
            ],
            "recall_delta": [-0.12, 0.04, 0.01, 0.00, 0.00, -0.02],
            "recall_p_bh": [0.02, 0.30, 0.55, 0.60, None, None],
            "recall_verdict": [
                "degraded",
                "not_significant",
                "not_significant",
                "not_significant",
                "not_significant",
                "degraded",
            ],
        }
    )


_METHODOLOGY: dict[str, object] = {
    "tests": ["mcnemar", "fisher"],
    "family_size": 7,
    "q": 0.05,
    "seed": 42,
    "threshold_source": "frozen/baseline",
    "weights_source": "clearml://task/abc",
    "images": 128,
}


def _missing_column_warnings(messages: list[str]) -> list[str]:
    return [message for message in messages if "column" in message]


def test_every_entry_point_is_a_noop_without_a_task() -> None:
    report_table(None, "t", "s", _comparison_rows())
    report_scalars(None, "t", {"a": 1.0})
    report_comparison(None, "test", _comparison_rows(), _METHODOLOGY)


def test_report_table_keeps_the_requested_title_and_series() -> None:
    task = _FakeTask()
    frame = _comparison_rows()

    report_table(task, "comparison", "test", frame)

    (reported,) = task.get_logger().tables
    assert reported["title"] == "comparison"
    assert reported["series"] == "test"
    assert reported["frame"] is frame


def test_report_scalars_reports_one_series_per_value() -> None:
    task = _FakeTask()

    report_scalars(task, "deltas", {"precision": 0.03, "recall": -0.02})

    assert task.get_logger().scalars == [
        {"title": "deltas", "series": "precision", "value": 0.03},
        {"title": "deltas", "series": "recall", "value": -0.02},
    ]


def test_report_comparison_publishes_the_table_and_the_methodology() -> None:
    task = _FakeTask()

    report_comparison(task, "test", _comparison_rows(), _METHODOLOGY)

    tables = {table["title"]: table for table in task.get_logger().tables}
    assert set(tables) == {COMPARISON_TABLE_TITLE, DEGRADED_TABLE_TITLE, METHODOLOGY_TABLE_TITLE}
    assert tables[COMPARISON_TABLE_TITLE]["series"] == "test"
    assert len(tables[COMPARISON_TABLE_TITLE]["frame"]) == 6

    methodology_frame = tables[METHODOLOGY_TABLE_TITLE]["frame"]
    assert list(methodology_frame.columns) == ["parameter", "value"]
    assert dict(zip(methodology_frame["parameter"], methodology_frame["value"], strict=True)) == {
        "tests": "['mcnemar', 'fisher']",
        "family_size": "7",
        "q": "0.05",
        "seed": "42",
        "threshold_source": "frozen/baseline",
        "weights_source": "clearml://task/abc",
        "images": "128",
    }


def test_degraded_classes_are_named_in_their_own_table() -> None:
    task = _FakeTask()

    report_comparison(task, "test", _comparison_rows(), _METHODOLOGY)

    (degraded,) = [
        table for table in task.get_logger().tables if table["title"] == DEGRADED_TABLE_TITLE
    ]
    assert degraded["series"] == "test"
    # 'cat' degraded on recall, 'dog' on precision; the pooled row is never listed.
    assert list(degraded["frame"]["class_name"]) == ["cat", "dog"]


def test_headline_values_count_verdicts_of_per_class_rows_only(warnings_log: list[str]) -> None:
    task = _FakeTask()

    report_comparison(task, "test", _comparison_rows(), _METHODOLOGY)

    # The pooled row carries verdicts too: counting it would make improved_precision 2
    # and degraded_recall 2.
    assert task.get_logger().single_values == {
        "test/degraded_precision": 1.0,
        "test/degraded_recall": 1.0,
        "test/improved_precision": 1.0,
        "test/improved_recall": 0.0,
        "test/classes_tested": 4.0,
        "test/classes_excluded": 1.0,
        "test/pooled_delta_precision": pytest.approx(0.03),
        "test/pooled_delta_recall": pytest.approx(-0.02),
    }
    assert not _missing_column_warnings(warnings_log)


def test_degradation_is_reported_before_improvement() -> None:
    task = _FakeTask()

    report_comparison(task, "test", _comparison_rows(), _METHODOLOGY)

    reported = list(task.get_logger().single_values)
    assert reported[:2] == ["test/degraded_precision", "test/degraded_recall"]
    assert reported.index("test/improved_precision") > reported.index("test/degraded_recall")


def test_the_family_size_check_is_silent_on_a_well_formed_frame(warnings_log: list[str]) -> None:
    # The BH family is hypotheses, not classes: five classes yield seven tests here. A
    # check that fires on every healthy run trains the reader to ignore it.
    task = _FakeTask()

    report_comparison(task, "test", _comparison_rows(), _METHODOLOGY)

    assert not [message for message in warnings_log if "family size" in message]


def test_family_size_disagreeing_with_the_hypotheses_is_warned_about(
    warnings_log: list[str],
) -> None:
    task = _FakeTask()
    methodology: dict[str, object] = {**_METHODOLOGY, "family_size": 10}

    report_comparison(task, "test", _comparison_rows(), methodology)

    assert "family size of 10" in "\n".join(warnings_log)
    assert "7 adjusted p-value(s)" in "\n".join(warnings_log)
    assert task.get_logger().single_values["test/classes_tested"] == 4.0


def test_missing_columns_are_warned_about_and_skipped(warnings_log: list[str]) -> None:
    task = _FakeTask()
    rows = _comparison_rows().drop(columns=["recall_delta", "recall_verdict", "recall_p_bh"])

    report_comparison(task, "test", rows, _METHODOLOGY)

    warnings = "\n".join(_missing_column_warnings(warnings_log))
    assert "'recall_verdict'" in warnings
    assert "'recall_delta'" in warnings
    assert "'recall_p_bh'" in warnings

    single_values = task.get_logger().single_values
    assert single_values["test/degraded_precision"] == 1.0
    assert not [name for name in single_values if "recall" in name]
    # Precision alone still answers how many classes were tested: 'fish' and 'worm' have
    # no precision hypothesis, so three of the five remain.
    assert single_values["test/classes_tested"] == 3.0
    assert single_values["test/classes_excluded"] == 2.0
    # The tables are still published: reporting never fails on a partial frame.
    assert len(task.get_logger().tables) == 3


def test_rows_without_any_verdict_column_still_publish_the_tables(
    warnings_log: list[str],
) -> None:
    task = _FakeTask()
    rows = _comparison_rows().drop(columns=["precision_verdict", "recall_verdict"])

    report_comparison(task, "test", rows, _METHODOLOGY)

    assert "'precision_verdict'" in "\n".join(_missing_column_warnings(warnings_log))
    (degraded,) = [
        table for table in task.get_logger().tables if table["title"] == DEGRADED_TABLE_TITLE
    ]
    assert degraded["frame"].empty
    assert task.get_logger().single_values["test/classes_tested"] == 4.0


def test_rows_without_the_pooled_flag_skip_the_headline_but_keep_the_tables(
    warnings_log: list[str],
) -> None:
    # Without is_pooled the pooled row cannot be told from a class, and counting it as one
    # would overstate both the improvements and the degradations.
    task = _FakeTask()
    rows = _comparison_rows().drop(columns=["is_pooled"])

    report_comparison(task, "test", rows, _METHODOLOGY)

    assert "'is_pooled'" in "\n".join(_missing_column_warnings(warnings_log))
    assert task.get_logger().single_values == {}
    assert len(task.get_logger().tables) == 2


def test_a_missing_pooled_delta_is_reported_as_nan() -> None:
    task = _FakeTask()
    rows = _comparison_rows()
    # A nullable dtype carries pd.NA rather than NaN, and float(pd.NA) raises.
    rows["precision_delta"] = pd.array([0.10, -0.08, 0.05, 0.02, 0.00, None], dtype="Float64")

    report_comparison(task, "test", rows, _METHODOLOGY)

    single_values = task.get_logger().single_values
    assert math.isnan(single_values["test/pooled_delta_precision"])
    assert single_values["test/pooled_delta_recall"] == pytest.approx(-0.02)


def test_rows_without_a_pooled_row_are_warned_about(warnings_log: list[str]) -> None:
    task = _FakeTask()
    rows = _comparison_rows()
    rows = rows[~rows["is_pooled"]]

    report_comparison(task, "test", rows, _METHODOLOGY)

    assert "'is_pooled'" in "\n".join(warnings_log)
    single_values = task.get_logger().single_values
    assert not [name for name in single_values if name.startswith("test/pooled_delta")]
    # The per-class headline is unaffected by the absent pooled row.
    assert single_values["test/degraded_precision"] == 1.0
