"""Workbook identity footers preserve source data and identify every printed page."""

import io
import json
import math
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook  # type: ignore[import-untyped]
from openpyxl.styles import Font  # type: ignore[import-untyped]
from openpyxl.worksheet.pagebreak import Break  # type: ignore[import-untyped]
from openpyxl.worksheet.table import Table  # type: ignore[import-untyped]

from clearml_yolo.adapters.reporting.workbook_identity import (
    annotate_workbook,
    deannotated_workbook,
    read_dashboard,
    workbook_identities,
)
from clearml_yolo.core.identity import IdentityLinks, ModelIdentity


def _complex_workbook(path: Path) -> None:
    workbook = Workbook()
    main = workbook.active
    main.title = "Main sheet"
    main.append(["Class", "Value"])
    main.append(["cat", 2])
    main.append(["total", "=SUM($B$2:B2)"])
    main["A1"].font = Font(bold=True, color="FF0000")
    main.merge_cells("D2:E2")
    main.add_table(Table(displayName="Results", ref="A1:B2"))
    main.freeze_panes = "B2"
    main.print_title_rows = "1:1"
    main.print_title_cols = "A:A"
    main.print_area = "A1:E3"
    main.row_breaks.append(Break(id=2))
    other = workbook.create_sheet("Other")
    other["A1"] = "='Main sheet'!$B$2+1"
    other.print_title_rows = "1:2"
    workbook.save(path)


def _footer(sheet: Any) -> list[str]:
    """Visible lines after the one empty row that ends original content."""
    values = [sheet.cell(row, 1).value for row in range(1, sheet.max_row + 1)]
    start = max(index for index, value in enumerate(values) if value is None) + 1
    return [str(value) for value in values[start:]]


def test_identity_footer_keeps_every_original_coordinate_on_all_sheets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("CY_HOME", str(workspace))
    path = workspace / "workbook.xlsx"
    _complex_workbook(path)
    original = path.read_bytes()
    identity = ModelIdentity(model_name="=Unicode 模型 " + "long name " * 40, training_task_id="full-training-task-id")
    annotate_workbook(path, {"Candidate": identity})
    annotated = load_workbook(path)
    main, other = annotated["Main sheet"], annotated["Other"]
    # Headers stay in row 1 and references, styles and print setup keep their cells.
    assert main["A1"].value == "Class"
    assert main["A1"].font.color.rgb == "00FF0000"
    assert main["B3"].value == "=SUM($B$2:B2)"
    assert other["A1"].value == "='Main sheet'!$B$2+1"
    assert "D2:E2" in main.merged_cells
    assert main.tables["Results"].ref == "A1:B2"
    assert main.freeze_panes == "B2"
    assert main.row_breaks.brk[0].id == 2
    assert main.print_title_rows == "$1:$1"
    assert main.print_title_cols == "$A:$A"
    assert other.print_title_rows == "$1:$2"
    expected = [f"Candidate: {identity.model_name}", "Training source: recorded"]
    for sheet, last_original_row in ((main, 3), (other, 1)):
        assert sheet.cell(last_original_row + 1, 1).value is None
        assert [sheet.cell(last_original_row + 2 + offset, 1).value for offset in range(2)] == expected
        assert sheet.cell(last_original_row + 2, 1).data_type == "s"
        assert sheet.cell(last_original_row + 2, 1).hyperlink is None
        footer = sheet.oddFooter.left.text
        assert footer.startswith("Candidate: =Unicode 模型")
        assert len(footer) <= 253
        assert "full-training-task-id" not in footer
        visible = [str(cell.value) for row in sheet for cell in row if cell.value is not None]
        assert all("full-training-task-id" not in value for value in visible)
    assert main.print_area == "'Main sheet'!$A$1:$H$6"  # widened for the merged A:H footer
    assert workbook_identities(path) == {"Candidate": identity}
    with deannotated_workbook(path) as restored:
        assert restored.is_relative_to(tmp_path / "workspace/.tmp")
        assert restored.read_bytes() == original
    assert not restored.exists()
    assert path.read_bytes() != original
    first = path.read_bytes()
    annotate_workbook(path, {"Candidate": identity})
    assert workbook_identities(path) == {"Candidate": identity}
    with deannotated_workbook(path) as restored:
        assert restored.read_bytes() == original
    with ZipFile(path) as current, ZipFile(io.BytesIO(first)) as previous:
        assert current.read("xl/worksheets/sheet1.xml") == previous.read("xl/worksheets/sheet1.xml")


def test_identity_footer_links_sources_by_role_without_visible_identifiers(tmp_path: Path) -> None:
    path = tmp_path / "comparison.xlsx"
    _complex_workbook(path)
    identities = {
        "baseline": ModelIdentity(model_name="old-detector", training_task_id="b" * 32, model_id="m" * 32),
        "candidate": ModelIdentity(model_name="train-brave-willow", training_task_id="c" * 32),
    }
    links = {
        "baseline": IdentityLinks(
            model_url=f"https://app.example/projects/*/models/{'m' * 32}",
            task_url=f"https://app.example/projects/*/tasks/{'b' * 32}/output/log",
        ),
        "candidate": IdentityLinks(),
    }
    annotate_workbook(path, identities, links=links)
    workbook = load_workbook(path)
    main = workbook["Main sheet"]
    assert _footer(main) == [
        "baseline: old-detector",
        "Training task: open in ClearML",
        "candidate: train-brave-willow",
        "Training source: recorded",
    ]
    targets = {cell.value: cell.hyperlink.target if cell.hyperlink else None for cell in main["A"][4:8]}
    assert targets == {
        "baseline: old-detector": links["baseline"].model_url,
        "Training task: open in ClearML": links["baseline"].task_url,
        "candidate: train-brave-willow": None,
        "Training source: recorded": None,
    }
    assert main.oddFooter.left.text == (
        "baseline: old-detector · Training source: recorded | candidate: train-brave-willow · Training source: recorded"
    )
    visible = [str(cell.value) for sheet in workbook for row in sheet for cell in row if cell.value is not None]
    assert not any(token * 32 in value for value in visible for token in "bcm")
    workbook.close()
    assert workbook_identities(path) == identities


def test_model_link_requires_recorded_model_identifier(tmp_path: Path) -> None:
    path = tmp_path / "book.xlsx"
    _complex_workbook(path)
    identity = ModelIdentity(model_name="custom")
    annotate_workbook(
        path, {"model": identity}, links={"model": IdentityLinks(model_url="https://app.example/projects/*/models/x")}
    )
    main = load_workbook(path)["Main sheet"]
    assert _footer(main) == ["model: custom", "Training source: unavailable"]
    assert all(cell.hyperlink is None for cell in main["A"])


def test_historical_top_banner_workbook_recovers_and_moves_to_footer(tmp_path: Path) -> None:
    from report_generator.v2 import annotate_workbook as annotate_package

    from clearml_yolo.adapters.reporting import workbook_identity

    path = tmp_path / "historical.xlsx"
    _complex_workbook(path)
    original = path.read_bytes()
    identity = ModelIdentity(model_name="legacy", training_task_id="task")
    annotate_package(
        path,
        banner_lines=["Model: legacy", "Training task: task"],
        metadata_texts={"models": json.dumps({"model": identity.model_dump()})},
        format=workbook_identity._FORMAT,
        validate=workbook_identity._model_metadata,
    )
    assert load_workbook(path)["Main sheet"]["A3"].value == "Class"
    assert workbook_identities(path) == {"model": identity}
    with deannotated_workbook(path) as restored:
        assert restored.read_bytes() == original
    annotate_workbook(path, workbook_identities(path))
    main = load_workbook(path)["Main sheet"]
    assert main["A1"].value == "Class"
    assert _footer(main) == ["model: legacy", "Training source: recorded"]


def test_real_dependency_dashboards_are_readable_annotated_and_historical(tmp_path: Path) -> None:
    from digital_metrics.reporting.dashboard import get_dashboards
    from digital_metrics.types import Metrics

    get_dashboards(
        {"cat": Metrics(tp=4, fp=1, fn=2, confidence=0.377)},
        pd.DataFrame({"instance_label": ["cat"], "split": ["test"]}),
        None,
        ["cat"],
        path=str(tmp_path),
    )
    for path in tmp_path.glob("*.xlsx"):
        before = pd.read_excel(path, index_col=0)
        assert workbook_identities(path) == {}
        pd.testing.assert_frame_equal(read_dashboard(path, index_col=0), before)
        annotate_workbook(path, {"Model": ModelIdentity(model_name="+safe", training_task_id="task")})
        pd.testing.assert_frame_equal(read_dashboard(path, index_col=0), before)
        with ZipFile(path) as archive:
            assert b"+safe" in archive.read("xl/worksheets/sheet1.xml")


@pytest.mark.parametrize("with_identity", [False, True])
def test_readable_workbook_classes_keep_exact_original_and_distinct_aliases(
    tmp_path: Path,
    with_identity: bool,
) -> None:
    from clearml_yolo.adapters.reporting.workbook_identity import humanize_workbook

    names = ["0123456789abcdef" * 2, "fedcba9876543210" * 2]
    path = tmp_path / "classes.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Class", "Value"])
    sheet.append([names[0], 0.125])
    sheet.append([names[1], 0.25])
    sheet.append(["[task]", "=SUM(B2:B3)"])
    workbook.save(path)
    original = path.read_bytes()
    humanize_workbook(path)
    humanize_workbook(path)
    if with_identity:
        identity = ModelIdentity(model_name="Detector", training_task_id=names[0])
        annotate_workbook(path, {"model": identity})
        annotate_workbook(path, {"model": identity})
        assert workbook_identities(path) == {"model": identity}
    visible = load_workbook(path)
    labels = [row[0].value for row in visible.active if row[1].value in (0.125, 0.25)]
    assert len(set(labels)) == 2
    assert "[task]" not in labels
    assert all(name not in str(cell.value) for sheet in visible for row in sheet for cell in row for name in names)
    visible.close()
    with deannotated_workbook(path) as source:
        assert source.read_bytes() == original
    assert read_dashboard(path)["Class"].tolist() == [*names, "[task]"]


def test_readable_workbook_rejects_visible_edits_before_recovering_original(tmp_path: Path) -> None:
    from clearml_yolo.adapters.reporting.workbook_identity import humanize_workbook

    path = tmp_path / "classes.xlsx"
    workbook = Workbook()
    workbook.active.append(["0123456789abcdef" * 2, 0.125])
    workbook.save(path)
    humanize_workbook(path)
    with ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    entries["xl/worksheets/sheet1.xml"] = entries["xl/worksheets/sheet1.xml"].replace(
        b">0.125<",
        b">10<",
    )
    with ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    with pytest.raises(ValueError, match="changed after"), deannotated_workbook(path):
        pass


def test_real_report_workbooks_keep_every_original_sheet_and_cell(tmp_path: Path) -> None:
    from digital_metrics.reporting.dashboard import get_dashboards
    from digital_metrics.types import Metrics
    from report_generator.config import Config
    from report_generator.core.reader import MetricsReader
    from report_generator.reports.business.builder import BusinessReportBuilder
    from report_generator.reports.dev.builder import DevReportBuilder

    get_dashboards(
        {"cat": Metrics(tp=4, fp=1, fn=2, confidence=0.37)},
        pd.DataFrame({"instance_label": ["cat"], "split": ["test"]}),
        None,
        ["cat"],
        path=str(tmp_path),
    )
    dashboard = tmp_path / "full_dashboard_default.xlsx"
    baseline = ModelIdentity(model_name="Old model", training_task_id="old-task")
    candidate = ModelIdentity(model_name="新模型", training_task_id="new-task")
    reader = MetricsReader(dashboard)
    expected = reader.read()
    annotate_workbook(dashboard, {"Candidate": candidate})
    with deannotated_workbook(dashboard) as clean:
        adapted = MetricsReader(clean)
        pd.testing.assert_frame_equal(adapted.read(), expected)
        dev = tmp_path / "dev.xlsx"
        business = tmp_path / "business.xlsx"
        DevReportBuilder(adapted, adapted, Config.load()).build(dev)
        BusinessReportBuilder(adapted, adapted, Config.load()).build(business)
    for path in (dev, business):
        before = load_workbook(path)
        annotate_workbook(path, {"Baseline": baseline, "Candidate": candidate})
        after = load_workbook(path)
        assert before.sheetnames == after.sheetnames
        for old, new in zip(before, after, strict=True):
            for row in old:
                for cell in row:
                    assert new.cell(cell.row, cell.column).value == cell.value
            footer = _footer(new)
            assert footer[0] == "Baseline: Old model"
            assert footer[2] == "Candidate: 新模型"
            assert new.oddFooter.left.text.startswith("Baseline: Old model · Training source: recorded")
            assert new.print_title_rows == old.print_title_rows


def test_chart_validation_and_filter_ranges_follow_original_body(tmp_path: Path) -> None:
    from openpyxl.chart import BarChart, Reference  # type: ignore[import-untyped]
    from openpyxl.worksheet.datavalidation import DataValidation  # type: ignore[import-untyped]

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Values, original"
    sheet.append(["Class", "Value"])
    sheet.append(["cat", 4])
    sheet.auto_filter.ref = "A1:B2"
    validation = DataValidation(type="whole", formula1="B2", formula2="10")
    validation.add("B2")
    sheet.add_data_validation(validation)
    chart = BarChart()
    chart.add_data(Reference(sheet, min_col=2, min_row=1, max_row=2), titles_from_data=True)
    sheet.add_chart(chart, "D2")
    sheet.print_title_rows = "1:1"
    sheet.print_title_cols = "A:A"
    sheet.page_setup.fitToHeight = 2
    path = tmp_path / "chart.xlsx"
    workbook.save(path)
    annotate_workbook(path, {"Model": ModelIdentity(model_name="model", training_task_id="task")})
    with ZipFile(path) as archive:
        drawing = archive.read("xl/drawings/drawing1.xml")
        chart_xml = archive.read("xl/charts/chart1.xml")
    after = load_workbook(path)["Values, original"]
    assert after.auto_filter.ref == "A1:B2"
    assert after.data_validations.dataValidation[0].sqref == "B2"
    assert after.data_validations.dataValidation[0].formula1 == "B2"
    assert after.print_title_rows == "$1:$1"
    assert after.print_title_cols == "$A:$A"
    assert after.page_setup.fitToHeight == 2
    assert b"'Values, original'!$B$2" in chart_xml
    # openpyxl anchors the default 7.5 cm chart at D2 (zero-based row 1); the footer starts below it.
    chart_rows = 1 + math.ceil(7.5 / 2.54 * 72 * 12700 / (15 * 12700))
    footer_start = next(row for row in range(3, after.max_row + 1) if after.cell(row, 1).value)
    assert footer_start == chart_rows + 2
    assert b"<xdr:row>1</xdr:row>" in drawing or b">1</" in drawing


def test_edited_annotated_parts_are_rejected_before_reading_original(tmp_path: Path) -> None:
    import io

    import pytest

    path = tmp_path / "edited.xlsx"
    pd.DataFrame({"class": ["cat"], "confidence": [0.37]}).to_excel(path, index=False)
    annotate_workbook(path, {"Model": ModelIdentity(model_name="model", training_task_id="task")})
    content = path.read_bytes()
    with ZipFile(io.BytesIO(content)) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    worksheet = "xl/worksheets/sheet1.xml"
    assert b">0.37<" in parts[worksheet]
    parts[worksheet] = parts[worksheet].replace(b">0.37<", b">0.91<")
    with ZipFile(path, "w") as archive:
        for name, part in parts.items():
            archive.writestr(name, part)
    with pytest.raises(ValueError, match="changed after model identity annotation"):
        workbook_identities(path)
    with pytest.raises(ValueError, match="changed after model identity annotation"):
        read_dashboard(path)
    with (
        pytest.raises(ValueError, match="changed after model identity annotation"),
        deannotated_workbook(path),
    ):
        pytest.fail("Edited workbook must not yield stale original content")


def test_malformed_model_metadata_is_rejected_by_all_read_adapters(tmp_path: Path) -> None:
    import io

    import pytest

    path = tmp_path / "malformed.xlsx"
    pd.DataFrame({"class": ["cat"], "confidence": [0.37]}).to_excel(path, index=False)
    annotate_workbook(path, {"Model": ModelIdentity(model_name="model", training_task_id="task")})
    with ZipFile(io.BytesIO(path.read_bytes())) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    metadata = "customXml/clearml-yolo-identity.xml"
    parts[metadata] = parts[metadata].replace(b'"model_name": "model"', b'"model_name": ""')
    with ZipFile(path, "w") as archive:
        for name, part in parts.items():
            archive.writestr(name, part)
    with pytest.raises(ValueError, match="Invalid workbook model identity metadata"):
        workbook_identities(path)
    with pytest.raises(ValueError, match="Invalid workbook model identity metadata"):
        read_dashboard(path)
    with (
        pytest.raises(ValueError, match="Invalid workbook model identity metadata"),
        deannotated_workbook(path),
    ):
        pytest.fail("Malformed identities must not yield original content")


@pytest.mark.parametrize("changed_part", ["identity", "original"])
def test_valid_metadata_edits_are_rejected(tmp_path: Path, changed_part: str) -> None:
    import base64
    import io

    path = tmp_path / "edited-metadata.xlsx"
    pd.DataFrame({"class": ["cat"], "confidence": [0.37]}).to_excel(path, index=False)
    original = path.read_bytes()
    annotate_workbook(path, {"Model": ModelIdentity(model_name="model", training_task_id="task")})
    with ZipFile(io.BytesIO(path.read_bytes())) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    metadata = "customXml/clearml-yolo-identity.xml"
    if changed_part == "identity":
        parts[metadata] = parts[metadata].replace(b'"training_task_id": "task"', b'"training_task_id": "other"')
    else:
        edited = io.BytesIO()
        with ZipFile(io.BytesIO(original)) as source, ZipFile(edited, "w") as destination:
            for name in source.namelist():
                content = source.read(name)
                if name == "xl/worksheets/sheet1.xml":
                    assert b">0.37<" in content
                    content = content.replace(b">0.37<", b">0.91<")
                destination.writestr(name, content)
        parts[metadata] = parts[metadata].replace(base64.b64encode(original), base64.b64encode(edited.getvalue()))
    with ZipFile(path, "w") as archive:
        for name, part in parts.items():
            archive.writestr(name, part)
    with pytest.raises(ValueError, match="changed after model identity annotation"):
        workbook_identities(path)
    with pytest.raises(ValueError, match="changed after model identity annotation"):
        read_dashboard(path)
