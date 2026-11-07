"""Unavailable training evidence is visible without aborting real report builders."""

from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook  # type: ignore[import-untyped]
from report_generator.config import Config
from report_generator.v2 import MetricsTable

from clearml_yolo.adapters.reporting.count_issues import (
    TRAIN_COLUMN,
    apply_training_counts,
    partition_counts,
)
from clearml_yolo.adapters.reporting.reports import build_reports
from clearml_yolo.core.report_counts import training_count


@pytest.mark.parametrize("value", [None, "NA", "-", -1, 1.5, float("inf"), True])
def test_invalid_count_is_unavailable(value: object) -> None:
    assert training_count(value) is None


@pytest.mark.parametrize("value", [0, "0", 30, "30", 30.0])
def test_valid_counts_remain_exact(value: object) -> None:
    assert training_count(value) == int(value)  # type: ignore[call-overload]


@pytest.mark.parametrize("all_unknown", [False, True])
def test_real_reports_preserve_unknown_rows_without_counting_them(tmp_path: Path, all_unknown: bool) -> None:
    source = tmp_path / "dashboard.xlsx"
    pd.DataFrame(
        {
            "Класс": ["valid", "unknown", "zero"],
            TRAIN_COLUMN: [None if all_unknown else 30, "NA", 0],
            "ap50": [0.8, 0.1, 0.9],
            "f1_score": [0.8, 0.1, 0.9],
            "perebrak": [0.1, 0.2, 0.3],
            "nedobrak": [0.1, 0.2, 0.3],
        }
    ).to_excel(source, index=False)
    original = source.read_bytes()
    dev, business = tmp_path / "dev.xlsx", tmp_path / "business.xlsx"
    issues = build_reports(source, source, dev, business, None)
    assert len(issues) == (4 if all_unknown else 2)
    assert source.read_bytes() == original
    config = Config.load()
    for path in (dev, business):
        workbook = load_workbook(path)
        assert "Report issues" in workbook.sheetnames
        sheet = workbook["Unknown training count"]
        rows = list(sheet.values)
        assert rows[1][0] == "candidate"
        assert any("unknown" in row and 0.1 in row for row in rows)
        assert not any("zero" in row for row in rows)
        metrics = workbook[config.sheet_names.model1]
        assert not any(cell.value == "unknown" for cell in metrics["A"])
        summary = next(row for row in metrics.iter_rows(values_only=True) if row[0] == "AP50-valid-class-count")
        assert summary[1] == ("0/0" if all_unknown else "1/1")
        workbook.close()


@pytest.mark.parametrize("counts", [None, {"known": 7}])
def test_producer_counts_come_only_from_training_evidence(tmp_path: Path, counts: dict[str, int] | None) -> None:
    frame = pd.DataFrame({TRAIN_COLUMN: [999, 888], "ap50": [0.3, 0.4]}, index=["known", "absent"])
    path = tmp_path / "dashboard.xlsx"
    frame.to_excel(path)
    apply_training_counts(frame, path, counts)
    readback = pd.read_excel(path, index_col=0)
    if counts is None:
        assert frame[TRAIN_COLUMN].isna().all()
        assert readback[TRAIN_COLUMN].isna().all()
    else:
        assert frame[TRAIN_COLUMN].tolist() == [7, 0]
        assert readback[TRAIN_COLUMN].tolist() == [7, 0]


def test_legacy_missing_count_column_has_no_eligible_rows() -> None:
    frame = pd.DataFrame({"Класс": ["legacy"], "ap50": [0.7]})
    partition = partition_counts(MetricsTable(frame, "legacy.xlsx"), "baseline")
    assert partition.table.frame.empty
    assert partition.unknown["ap50"].tolist() == [0.7]
    assert partition.issues[0].reason == "Missing training count"
    assert TRAIN_COLUMN not in frame


def test_partition_excludes_every_malformed_count_but_preserves_valid_zero() -> None:
    values = [None, "NA", -1, 1.5, float("inf"), True, "bad", 0, "30"]
    frame = pd.DataFrame({"Класс": [str(index) for index in range(len(values))], TRAIN_COLUMN: values})
    partition = partition_counts(MetricsTable(frame, "counts.xlsx"), "candidate")
    assert partition.table.frame[TRAIN_COLUMN].tolist() == [0, 30]
    assert len(partition.issues) == 7


def test_statistical_summary_is_not_accepted_as_a_dashboard(tmp_path: Path) -> None:
    source = tmp_path / "compare_workbook_test.xlsx"
    pd.DataFrame({"Metric": ["f1_score"], "p_value": [0.1]}).to_excel(source, index=False)
    with pytest.raises(ValueError, match="not a per-model metrics dashboard"):
        build_reports(source, source, tmp_path / "dev.xlsx", tmp_path / "business.xlsx", None)


def test_generated_unknown_dashboard_roundtrips_without_synthetic_classes(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {TRAIN_COLUMN: [999], "ap50": [0.3], "f1_score": [0.4], "perebrak": [0.1], "nedobrak": [0.2]},
        index=["cat"],
    )
    source = tmp_path / "dashboard.xlsx"
    frame.to_excel(source)
    apply_training_counts(frame, source, None)
    issues = build_reports(source, source, tmp_path / "dev.xlsx", tmp_path / "biz.xlsx", None)
    assert len(issues) == 2
    assert {issue.class_name for issue in issues} == {"cat"}
    assert pd.read_excel(source).iloc[:, 0].tolist() == ["cat"]
