"""Real workbook builders retain metrics across changing model vocabularies."""

from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook  # type: ignore[import-untyped]
from report_generator.config import Config

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.tasks.compare import MANIFEST_NAME, ComparisonManifest
from clearml_yolo.tasks.report import report


@pytest.mark.parametrize("shared", [True, False])
def test_report_preserves_one_sided_metrics_with_real_builders(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shared: bool,
) -> None:
    monkeypatch.setattr("clearml_yolo.tasks.report.init_task", lambda *_a, **_kw: None)
    comparison = tmp_path / "comparison"
    comparison.mkdir()
    for model, unique, values in (
        ("candidate", "new", [0.8, 0.0]),
        ("baseline", "deleted", [0.6, 0.4]),
    ):
        labels = ["shared", unique] if shared else [unique]
        metrics = values if shared else values[1:]
        pd.DataFrame(
            {
                "Класс": labels,
                "Количество примеров train": [30] * len(labels),
                "f1_score": metrics,
                "perebrak": [0.1] * len(labels),
                "nedobrak": [0.1] * len(labels),
            }
        ).to_excel(comparison / f"{model}.xlsx", index=False)
    manifest = ComparisonManifest(
        split="test",
        candidate_dashboard="candidate.xlsx",
        baseline_dashboard="baseline.xlsx",
        candidate_predictions="candidate.csv",
        baseline_predictions="baseline.csv",
        statistical_workbook="comparison.xlsx",
    )
    (comparison / MANIFEST_NAME).write_text(manifest.model_dump_json(), encoding="utf-8")
    result = report(comparison, tmp_path / "reports", ClearMLConfig())
    config = Config.load()
    for business, path in (
        (False, result.dev_reports["test"]),
        (True, result.business_reports["test"]),
    ):
        workbook = load_workbook(path)
        metric = (
            config.business.column_translations.get("f1_score", "f1_score")
            if business
            else "f1_score"
        )
        for sheet_name, available, absent, expected, mean in (
            (config.sheet_names.model1, "new", "deleted", 0.0, 0.4 if shared else 0.0),
            (config.sheet_names.model2, "deleted", "new", 0.4, 0.5 if shared else 0.4),
        ):
            sheet = workbook[sheet_name]
            headers = [cell.value for cell in sheet[2]]
            column = headers.index(metric) + 1
            rows = {sheet.cell(row, 1).value: row for row in range(3, sheet.max_row + 1)}
            assert {"new", "deleted"} <= rows.keys()
            assert sheet.cell(rows[available], column).value == pytest.approx(expected)
            assert sheet.cell(rows[absent], column).value == "NA"
            assert sheet.cell(rows["Среднее"], column).value == pytest.approx(mean)
        sheet = workbook[config.sheet_names.comparison]
        headers = [cell.value for cell in sheet[2]]
        column = headers.index(metric) + 1
        rows = {sheet.cell(row, 1).value: row for row in range(3, sheet.max_row + 1)}
        for label in ("new", "deleted"):
            cell = sheet.cell(rows[label], column)
            assert cell.value == "NA"
            assert cell.fill.patternType is None
