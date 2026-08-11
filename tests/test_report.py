"""Locating dashboard workbooks: the new model's and a local baseline's, one way."""

from __future__ import annotations

from pathlib import Path

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.inference import ScoredResolution
from clearml_yolo.tasks import report as report_module
from clearml_yolo.tasks.metrics import DASHBOARD_PREFIX
from clearml_yolo.tasks.report import (
    RESOLUTION_SHEET,
    BaselineConfig,
    build_reports,
    discover_dashboards,
)


def _workbooks(directory: Path, splits: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for split in splits:
        (directory / f"{DASHBOARD_PREFIX}_{split}.xlsx").write_bytes(b"")


@pytest.fixture
def report_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for report-generator, whose builders read real dashboard workbooks.

    It is a released package this repo consumes rather than owns, so what is under test is
    only what happens to the file after it has written one.
    """
    import sys
    import types

    import pandas as pd

    class FakeBuilder:
        def __init__(self, *_: object) -> None:
            pass

        def build(self, path: Path) -> None:
            pd.DataFrame({"metric": ["f1"], "delta": [0.01]}).to_excel(path, index=False)

    class FakeReader:
        def __init__(self, *_: object) -> None:
            pass

        def read(self) -> pd.DataFrame:
            return pd.DataFrame({"metric": ["f1"]})

    class FakeConfig:
        @staticmethod
        def load(*_: object) -> dict[str, object]:
            return {}

    def _install(name: str, attribute: str, value: object) -> types.ModuleType:
        module = types.ModuleType(name)
        setattr(module, attribute, value)
        monkeypatch.setitem(sys.modules, name, module)
        return module

    _install("report_generator.config", "Config", FakeConfig)
    _install("report_generator.core.reader", "MetricsReader", FakeReader)
    _install("report_generator.reports.dev.builder", "DevReportBuilder", FakeBuilder)
    _install("report_generator.reports.business.builder", "BusinessReportBuilder", FakeBuilder)


def _built(tmp_path: Path, resolution: ScoredResolution | None) -> Path:
    """Run the report stage against a local baseline, returning the dev workbook."""
    _workbooks(tmp_path / "metrics", ["test"])
    _workbooks(tmp_path / "previous", ["test"])
    result = build_reports(
        {"test": tmp_path / "metrics" / f"{DASHBOARD_PREFIX}_test.xlsx"},
        tmp_path / "reports",
        ClearMLConfig(enabled=False),
        BaselineConfig(source="local", directory=tmp_path / "previous"),
        None,
        resolution,
    )
    return result.dev_reports["test"]


def test_the_dev_workbook_records_the_scale_its_numbers_were_measured_at(
    tmp_path: Path, report_generator: None
) -> None:
    """The workbook outlives the console log it was announced in, and is the artefact a
    reviewer opens months later to ask what these numbers mean."""
    import pandas as pd

    workbook = _built(tmp_path, ScoredResolution(trained_at=1280, scored_at=640))

    sheet = pd.read_excel(workbook, sheet_name=RESOLUTION_SHEET)
    assert dict(zip(sheet["parameter"], sheet["value"], strict=True)) == {
        "trained at imgsz": "1280",
        "scored at imgsz": "640",
        "same resolution?": "NO — scored at a scale this model was never shown",
    }


def test_a_report_that_did_not_run_the_inference_claims_no_resolution(
    tmp_path: Path, report_generator: None
) -> None:
    """A standalone `cy-report` reads dashboards off disk and has no way to know what
    produced them, and a wrong resolution in the workbook is worse than an absent one."""
    import pandas as pd

    workbook = _built(tmp_path, None)

    assert RESOLUTION_SHEET not in pd.ExcelFile(workbook).sheet_names


def test_clearml_stores_the_workbook_with_the_sheet_already_on_it(
    tmp_path: Path, report_generator: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Uploading before appending would leave the copy anyone actually reads without the
    sheet, which is the whole reason it is written — so the order is asserted, not assumed."""
    import pandas as pd

    uploaded: dict[str, list[str]] = {}

    class FakeTask:
        def upload_artifact(self, name: str, artifact_object: Path) -> None:
            uploaded[name] = [str(sheet) for sheet in pd.ExcelFile(artifact_object).sheet_names]

    monkeypatch.setattr(report_module, "init_task", lambda *_, **__: FakeTask())
    monkeypatch.setattr(report_module, "report_table", lambda *_, **__: None)

    _built(tmp_path, ScoredResolution(trained_at=1280, scored_at=640))

    dev = next(sheets for name, sheets in uploaded.items() if "dev" in name)
    assert RESOLUTION_SHEET in dev


def test_the_sheet_is_appended_rather_than_replacing_what_the_builder_wrote(
    tmp_path: Path, report_generator: None
) -> None:
    """`mode="a"` is what keeps the report a report; the resolution is context beside it."""
    import pandas as pd

    workbook = _built(tmp_path, ScoredResolution(trained_at=640, scored_at=640))

    assert len(pd.ExcelFile(workbook).sheet_names) > 1


def test_only_the_splits_that_have_a_workbook_are_returned(tmp_path: Path) -> None:
    _workbooks(tmp_path, ["train", "test"])

    found = discover_dashboards(tmp_path, ["train", "val", "test"])

    assert set(found) == {"train", "test"}
    assert found["train"] == tmp_path / f"{DASHBOARD_PREFIX}_train.xlsx"


def test_a_local_baseline_is_read_the_same_way_the_new_model_is(tmp_path: Path) -> None:
    """Both sides are the same files under the same naming convention, so a baseline
    directory is searched by the very function that finds the run's own dashboards."""
    baseline_dir = tmp_path / "previous"
    _workbooks(baseline_dir, ["test"])

    assert discover_dashboards(baseline_dir, ["test"]) == {
        "test": baseline_dir / f"{DASHBOARD_PREFIX}_test.xlsx"
    }


def test_a_local_baseline_without_a_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"baseline\.directory"):
        build_reports(
            {"test": tmp_path / f"{DASHBOARD_PREFIX}_test.xlsx"},
            tmp_path / "reports",
            ClearMLConfig(enabled=False),
            BaselineConfig(source="local"),
        )


def test_a_disabled_baseline_skips_every_split_instead_of_failing(tmp_path: Path) -> None:
    result = build_reports(
        {"test": tmp_path / f"{DASHBOARD_PREFIX}_test.xlsx"},
        tmp_path / "reports",
        ClearMLConfig(enabled=False),
        BaselineConfig(source="none"),
    )

    assert result.skipped_splits == ["test"]
    assert not result.dev_reports
