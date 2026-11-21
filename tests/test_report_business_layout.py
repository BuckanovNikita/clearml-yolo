"""The business workbook from real report builders has the fixed-column layout."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from openpyxl import load_workbook  # type: ignore[import-untyped]
from report_generator.config import Config

from clearml_yolo.adapters.clearml.session import ClearMLConfig
from clearml_yolo.adapters.reporting.reports import build_reports
from clearml_yolo.adapters.reporting.workbook_identity import workbook_identities
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.compare import MANIFEST_NAME, ComparisonManifest
from clearml_yolo.application.use_cases.report import report
from clearml_yolo.core.identity import ModelIdentity
from workflow_dependencies import patch_workflow
from workflow_dependencies import workflow_dependencies as workflow_dependencies  # noqa: PLC0414

HEADERS = [
    "Класс",
    "tp",
    "fp",
    "fn",
    "Порог",
    "precision",
    "recall",
    "f1_score",
    "Перебраковка, %",
    "Недобраковка, %",
    # The four goal headers come from report-generator's bundled configuration.
    *Config.load().business.goal_cols,
    "Число примеров test",
    "Число примеров train",
    "Число примеров val",
]
COUNTS = HEADERS[14:]
NOTE = [
    "Средние и вердикт: собственный набор допустимых классов каждой модели (новая: 3, прод: 3);",
    "среднее разниц: общих классов 2.",
    "Наборы могут различаться;",
    "NA — отсутствующие или отфильтрованные данные.",
    "Причины отсутствия сравнения приведены на листе исключений.",
]
LEGEND = [
    "Легенда:",
    "Улучшение",
    "Ухудшение: доли > 0.05; перебраковка/недобраковка > 5.0 п.п.",
    "Незначительное изменение",
    "NA — разница недоступна; цветовая оценка не применяется",
]
# Rows are (class, tp, fp, fn, threshold, test count, train count, val count).
CANDIDATE: list[tuple[Any, ...]] = [
    ("shared", 8, 2, 2, 0.5, 10, 40, 12),
    ("weak", 5, 5, 15, 0.3, 20, 30, 8),
    ("new", 9, 1, 1, 0.7, 10, 25, 5),
]
BASELINE: list[tuple[Any, ...]] = [
    ("shared", 6, 4, 4, 0.4, 10, 40, 12),
    ("weak", 10, 10, 10, 0.2, 20, 50, 8),
    ("deleted", 4, 1, 6, 0.6, 10, 60, 9),
]


def _dashboard(rows: list[tuple[Any, ...]]) -> pd.DataFrame:
    """Every column of a full digital-metrics dashboard, indexed by class.

    Ratios follow from the counts, so the expected cells can be worked out by hand.
    """
    frame = pd.DataFrame(rows, columns=["class", "tp", "fp", "fn", "confidence", "test", "train", "val"])
    frame = frame.set_index("class").rename_axis(None)
    precision = frame["tp"] / (frame["tp"] + frame["fp"])
    recall = frame["tp"] / (frame["tp"] + frame["fn"])
    columns: dict[str, Any] = {
        "counts_observed": True,
        "tp": frame["tp"],
        "fp": frame["fp"],
        "fn": frame["fn"],
        "confidence": frame["confidence"],
        "ap50": 0.5,
        "ap75": 0.4,
        "ap50_95": 0.3,
        "cohen_kappa": 0.2,
        "precision": precision,
        "recall": recall,
        "f1_score": 2 * precision * recall / (precision + recall),
        "perebrak": 1 - precision,
        "nedobrak": 1 - recall,
    }
    for metric in ("precision", "recall", "perebrak", "nedobrak"):
        columns[f"{metric}_ci_lower"] = 0.1
        columns[f"{metric}_ci_upper"] = 0.9
    columns["Количество примеров test"] = frame["test"]
    columns["Количество примеров train"] = frame["train"]
    columns["Количество примеров val"] = frame["val"]
    return pd.DataFrame(columns, index=frame.index)


def _comparison(directory: Path, candidate: pd.DataFrame, baseline: pd.DataFrame) -> Path:
    comparison = directory / "comparison"
    comparison.mkdir()
    candidate.to_excel(comparison / "candidate.xlsx")
    baseline.to_excel(comparison / "baseline.xlsx")
    manifest = ComparisonManifest(
        split="test",
        candidate_dashboard="candidate.xlsx",
        baseline_dashboard="baseline.xlsx",
        candidate_predictions="candidate.csv",
        baseline_predictions="baseline.csv",
        statistical_workbook="comparison.xlsx",
    )
    (comparison / MANIFEST_NAME).write_text(manifest.model_dump_json(), encoding="utf-8")
    return comparison


@pytest.fixture
def offline_report(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> WorkflowDependencies:
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.report.init_task",
        lambda *_a, **_kw: None,
    )
    return workflow_dependencies


def _column_a(sheet: Any) -> list[Any]:
    return [sheet.cell(row, 1).value for row in range(1, sheet.max_row + 1)]


def _table(sheet: Any) -> dict[Any, dict[Any, Any]]:
    headers = [cell.value for cell in sheet[2]]
    rows = {}
    for row in sheet.iter_rows(min_row=3):
        if row[0].value is None:
            break
        rows[row[0].value] = dict(zip(headers, row, strict=False))
    return rows


def _values(row: dict[Any, Any], names: list[str]) -> list[Any]:
    return [row[name].value for name in names]


def _assert_fixed_layout(workbook: Any, config: Any) -> None:
    """Assert the cells worked out by hand from CANDIDATE and BASELINE."""
    names = config.sheet_names
    candidate, baseline, comparison = (
        workbook[names.model1],
        workbook[names.model2],
        workbook[names.comparison],
    )
    for sheet in (candidate, baseline, comparison):
        assert [cell.value for cell in sheet[2]] == HEADERS
        assert list(_table(sheet)) == ["deleted", "new", "shared", "weak", "Среднее"]
    mean = _table(candidate)["Среднее"]
    assert _values(mean, ["tp", "fp", "fn", "Порог"]) == ["NA"] * 4
    # Candidate precision 0.8, 0.5, 0.9; recall 0.8, 0.25, 0.9.
    assert mean["precision"].value == pytest.approx(2.2 / 3)
    assert mean["Недобраковка, %"].value == pytest.approx(35)
    assert _values(mean, COUNTS) == [40, 95, 25]
    assert _values(_table(baseline)["Среднее"], COUNTS) == [40, 150, 29]
    assert _table(candidate)["deleted"]["tp"].value == "NA"
    differences = _table(comparison)
    assert _values(differences["shared"], ["tp", "fp", "fn"]) == [2, -2, -2]
    assert differences["shared"]["Порог"].value == pytest.approx(0.1)
    assert differences["shared"]["Перебраковка, %"].value == pytest.approx(-20)
    assert _values(differences["shared"], HEADERS[10:14]) == [1, 1, 0, 0]
    assert differences["weak"]["Число примеров train"].value == -20
    assert differences["new"]["tp"].value == "NA"
    # Recall differences over the shared classes are 0.2 and -0.25.
    assert differences["Среднее"]["recall"].value == pytest.approx(-0.025)
    assert _values(differences["Среднее"], ["tp", "fp", "fn", "Порог"]) == ["NA"] * 4
    assert _values(differences["Среднее"], COUNTS) == [0, -20, 0]
    # Title, header, four classes and the mean row end at row 7.
    assert _column_a(candidate)[7:13] == [None, *NOTE]
    assert _column_a(baseline)[7:13] == [None, *NOTE]
    assert _column_a(comparison)[7:19] == [None, *LEGEND, None, *NOTE]
    assert all(cell.value is None for row in comparison.iter_rows(min_row=9, max_row=19) for cell in row[1:])
    assert _column_a(workbook[names.verdict])[11:17] == [None, *NOTE]
    # The issue sheets appended by clearml-yolo keep every source column as evidence.
    report_sheets = [names.model1, names.model2, names.comparison, names.verdict, names.excluded]
    text = " ".join(str(cell.value) for title in report_sheets for row in workbook[title] for cell in row if cell.value)
    for absent in ("coverage", "Valid class counts", "valid-class-count", "ap50", "cohen_kappa", "_ci_"):
        assert absent not in text


def test_business_workbook_has_the_fixed_columns_notes_legend_and_footer(
    tmp_path: Path, offline_report: WorkflowDependencies
) -> None:
    candidate = _dashboard([*CANDIDATE, ("unknown", 3, 1, 1, 0.5, 10, "NA", 5)])
    comparison = _comparison(tmp_path, candidate, _dashboard(BASELINE))
    result = report(
        comparison,
        tmp_path / "reports",
        ClearMLConfig(),
        baseline_label="fixture baseline",
        candidate_label="fixture candidate",
        deps=offline_report,
    )
    config = Config.load()
    workbook = load_workbook(result.business_reports["test"])
    names = config.sheet_names
    assert workbook.sheetnames == [
        names.model1,
        names.model2,
        names.comparison,
        names.verdict,
        names.excluded,
        "Unknown training count",
        "Report issues",
    ]
    _assert_fixed_layout(workbook, config)
    footer = ["baseline: fixture baseline", "Training source: unavailable"]
    for title, last_content in [
        (names.model1, NOTE[-1]),
        (names.model2, NOTE[-1]),
        (names.comparison, NOTE[-1]),
        (names.verdict, NOTE[-1]),
    ]:
        values = _column_a(workbook[title])
        start = values.index(footer[0])
        # The identity footer starts one empty row below the last note row.
        assert values[start - 2 : start + 2] == [last_content, None, *footer], title
    for sheet in workbook:
        values = _column_a(sheet)
        start = values.index(footer[0])
        assert values[start - 1] is None, sheet.title
        assert values[start - 2] is not None, sheet.title
        assert "candidate: fixture candidate" in values[start:]
    unknown = list(workbook["Unknown training count"].iter_rows(min_row=2, values_only=True))
    assert any(row[0] == "candidate" and "unknown" in row for row in unknown)
    workbook.close()


def test_business_workbook_from_dashboards_with_the_historical_top_identity_block(
    tmp_path: Path, offline_report: WorkflowDependencies
) -> None:
    from report_generator.v2 import annotate_workbook as annotate_package

    from clearml_yolo.adapters.reporting import workbook_identity

    comparison = _comparison(tmp_path, _dashboard(CANDIDATE), _dashboard(BASELINE))
    identities = {}
    for role in ("candidate", "baseline"):
        identity = ModelIdentity(model_name=f"historical {role}", training_task_id="a" * 32)
        identities[role] = identity
        path = comparison / f"{role}.xlsx"
        # Dashboards written before the footer placement carry the identity above the header.
        annotate_package(
            path,
            banner_lines=[f"model: {identity.model_name}", f"Training task: {identity.training_task_id}"],
            metadata_texts={"models": json.dumps({"model": identity.model_dump()})},
            format=workbook_identity._FORMAT,
            validate=workbook_identity._model_metadata,
        )
        sheet = load_workbook(path).worksheets[0]
        assert sheet["A1"].value == f"model: historical {role}"
        assert sheet["B3"].value == "counts_observed"
    result = report(comparison, tmp_path / "reports", ClearMLConfig(), deps=offline_report)
    business = result.business_reports["test"]
    assert workbook_identities(business) == identities
    workbook = load_workbook(business)
    _assert_fixed_layout(workbook, Config.load())
    workbook.close()


def test_business_workbook_follows_a_custom_report_configuration(tmp_path: Path) -> None:
    candidate, baseline = tmp_path / "candidate.xlsx", tmp_path / "baseline.xlsx"
    _dashboard(CANDIDATE).to_excel(candidate)
    _dashboard(BASELINE).to_excel(baseline)
    settings = tmp_path / "report.yaml"
    settings.write_text(
        "colors:\n  header: AABBCC\n"
        "sheet_names:\n  model1: Candidate\n  model2: Baseline\n"
        "  comparison: Difference\n  excluded: Excluded\n  verdict: Verdict\n"
        "business:\n  target_perebrak: 0.45\n  target_nedobrak: 0.15\n"
        "  column_translations:\n    f1_score: F1 custom\n    ap50: AP custom\n",
        encoding="utf-8",
    )
    business = tmp_path / "business.xlsx"
    build_reports(candidate, baseline, tmp_path / "dev.xlsx", business, settings)
    workbook = load_workbook(business)
    assert workbook.sheetnames == ["Candidate", "Baseline", "Difference", "Verdict", "Excluded"]
    expected = [header if header != "f1_score" else "F1 custom" for header in HEADERS]
    for title in ("Candidate", "Baseline", "Difference"):
        sheet = workbook[title]
        assert [cell.value for cell in sheet[2]] == expected
        assert sheet["A2"].fill.fgColor.rgb.endswith("AABBCC")
    goals = HEADERS[10:14]  # perebrak goal, nedobrak goal, perebrak gross, nedobrak gross
    # shared: candidate perebrak 0.2 and nedobrak 0.2, baseline 0.4 and 0.4.
    # The bundled targets 0.3 and 0.2 would give 1, 1, 0, 0 and 0, 0, 0, 0.
    assert _values(_table(workbook["Candidate"])["shared"], goals) == [1, 0, 0, 0]
    assert _values(_table(workbook["Baseline"])["shared"], goals) == [1, 0, 0, 1]
    assert _values(_table(workbook["Difference"])["shared"], goals) == [0, 0, 0, -1]
    assert _table(workbook["Difference"])["shared"]["F1 custom"].value == pytest.approx(0.2)
    workbook.close()
