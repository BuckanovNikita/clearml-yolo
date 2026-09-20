"""Developer/business reports consume paired current-test comparison dashboards."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd
import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.tasks.compare import MANIFEST_NAME, ComparisonManifest
from clearml_yolo.tasks.report import build_reports, report


@pytest.fixture
def report_generator(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []

    class FakeReader:
        def __init__(self, path: str | Path) -> None:
            self.file_path = Path(path)

        def read(self) -> pd.DataFrame:
            return pd.read_excel(self.file_path, index_col=0)

    class FakeBuilder:
        def __init__(self, candidate: FakeReader, baseline: FakeReader, *_: object) -> None:
            self.candidate = candidate
            self.baseline = baseline

        def build(self, path: str | Path) -> None:
            pairs.append((self.candidate.file_path, self.baseline.file_path))
            pd.DataFrame({"metric": ["f1"]}).to_excel(path, index=False)

    class FakeConfig:
        @staticmethod
        def load(*_: object) -> dict[str, object]:
            return {}

    def install(name: str, attribute: str, value: object) -> None:
        module = types.ModuleType(name)
        setattr(module, attribute, value)
        monkeypatch.setitem(sys.modules, name, module)

    install("report_generator.config", "Config", FakeConfig)
    install("report_generator.core.reader", "MetricsReader", FakeReader)
    install("report_generator.reports.dev.builder", "DevReportBuilder", FakeBuilder)
    install("report_generator.reports.business.builder", "BusinessReportBuilder", FakeBuilder)
    monkeypatch.setattr("clearml_yolo.tasks.report.init_task", lambda *_args, **_kwargs: None)
    return pairs


def _comparison_dir(tmp_path: Path) -> tuple[Path, Path, Path]:
    directory = tmp_path / "comparison"
    directory.mkdir()
    baseline = directory / "full_dashboard_baseline_test.xlsx"
    candidate = directory / "full_dashboard_candidate_test.xlsx"
    pd.DataFrame({"tp": [1]}, index=["cat"]).to_excel(baseline)
    pd.DataFrame({"tp": [2]}, index=["cat"]).to_excel(candidate)
    (directory / MANIFEST_NAME).write_text(
        ComparisonManifest(
            split="test",
            baseline_dashboard=baseline.name,
            candidate_dashboard=candidate.name,
            baseline_predictions="baseline.csv",
            candidate_predictions="candidate.csv",
            statistical_workbook="comparison.xlsx",
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    return directory, candidate, baseline


def test_report_builds_both_formats_from_manifest_pair(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
) -> None:
    comparison, candidate, baseline = _comparison_dir(tmp_path)

    result = report(comparison, tmp_path / "reports", ClearMLConfig())

    assert result.dev_reports["test"].is_file()
    assert result.business_reports["test"].is_file()
    assert report_generator == [(candidate, baseline), (candidate, baseline)]


def test_missing_comparison_manifest_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=MANIFEST_NAME):
        report(tmp_path / "comparison", tmp_path / "reports", ClearMLConfig())


def test_missing_paired_dashboard_fails_explicitly(
    tmp_path: Path, report_generator: list[tuple[Path, Path]]
) -> None:
    comparison, _, baseline = _comparison_dir(tmp_path)
    baseline.unlink()

    with pytest.raises(FileNotFoundError, match="baseline dashboard"):
        report(comparison, tmp_path / "reports", ClearMLConfig())


def test_build_reports_preserves_candidate_minus_baseline_order(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
) -> None:
    _, candidate, baseline = _comparison_dir(tmp_path)

    build_reports(
        candidate,
        baseline,
        tmp_path / "reports",
        ClearMLConfig(),
        split="test",
    )

    assert report_generator == [(candidate, baseline), (candidate, baseline)]


def test_standalone_report_tracks_consumed_inputs_and_sanitized_config(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comparison, candidate, baseline = _comparison_dir(tmp_path)
    manifest = comparison / MANIFEST_NAME
    config = tmp_path / "report.yaml"
    config.write_text("title: audit\n", encoding="utf-8")
    expected: list[str] = []
    uploads: dict[str, object] = {}
    connected: list[tuple[str, Path]] = []

    class FakeTask:
        pass

    monkeypatch.setattr(
        "clearml_yolo.tasks.report.init_task", lambda *_args, **_kwargs: FakeTask()
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.report.expect_artifacts",
        lambda _task, names: expected.extend(names),
    )
    monkeypatch.setattr(
        "clearml_yolo.tasks.report.upload_artifact",
        lambda _task, name, value: uploads.setdefault(name, value),
    )
    monkeypatch.setattr("clearml_yolo.tasks.report.report_table", lambda *_args: None)

    def connect(_task: object, name: str, path: Path) -> Path:
        connected.append((name, path))
        return path

    monkeypatch.setattr("clearml_yolo.tasks.report.connect_config_file", connect)

    report(comparison, tmp_path / "reports", ClearMLConfig(), config)

    assert connected == [("source_report_configuration", config)]
    assert uploads["report_input_manifest_test"] == manifest
    assert uploads["report_input_dashboard_candidate_test"] == candidate
    assert uploads["report_input_dashboard_baseline_test"] == baseline
    assert set(expected) == set(uploads)
