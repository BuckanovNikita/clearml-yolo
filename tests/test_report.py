"""Developer/business reports consume paired current-test comparison dashboards."""

import sys
import types
from pathlib import Path

import pandas as pd
import pytest

from clearml_yolo.adapters.clearml.session import ClearMLConfig
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.compare import MANIFEST_NAME, ComparisonManifest
from clearml_yolo.application.use_cases.report import build_reports, report
from workflow_dependencies import patch_workflow
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)


@pytest.fixture
def report_generator(
    monkeypatch: pytest.MonkeyPatch, workflow_dependencies: WorkflowDependencies
) -> list[tuple[Path, Path]]:
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
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.report.init_task",
        lambda *_args, **_kwargs: None,
    )
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
    return (directory, candidate, baseline)


def test_report_builds_both_formats_from_manifest_pair(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
    workflow_dependencies: WorkflowDependencies,
) -> None:
    comparison, candidate, baseline = _comparison_dir(tmp_path)
    result = report(
        comparison,
        tmp_path / "reports",
        ClearMLConfig(),
        baseline_label="fixture baseline",
        candidate_label="fixture candidate",
        deps=workflow_dependencies,
    )
    assert result.dev_reports["test"].is_file()
    assert result.business_reports["test"].is_file()
    assert report_generator == [(candidate, baseline), (candidate, baseline)]


def test_missing_comparison_manifest_fails_explicitly(
    tmp_path: Path, workflow_dependencies: WorkflowDependencies
) -> None:
    with pytest.raises(FileNotFoundError, match=MANIFEST_NAME):
        report(
            tmp_path / "comparison",
            tmp_path / "reports",
            ClearMLConfig(),
            baseline_label="fixture baseline",
            candidate_label="fixture candidate",
            deps=workflow_dependencies,
        )


def test_missing_paired_dashboard_fails_explicitly(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
    workflow_dependencies: WorkflowDependencies,
) -> None:
    comparison, _, baseline = _comparison_dir(tmp_path)
    baseline.unlink()
    with pytest.raises(FileNotFoundError, match="baseline dashboard"):
        report(
            comparison,
            tmp_path / "reports",
            ClearMLConfig(),
            baseline_label="fixture baseline",
            candidate_label="fixture candidate",
            deps=workflow_dependencies,
        )


def test_build_reports_preserves_candidate_minus_baseline_order(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
    workflow_dependencies: WorkflowDependencies,
) -> None:
    _, candidate, baseline = _comparison_dir(tmp_path)
    build_reports(
        candidate,
        baseline,
        tmp_path / "reports",
        ClearMLConfig(),
        split="test",
        baseline_label="fixture baseline",
        candidate_label="fixture candidate",
        deps=workflow_dependencies,
    )
    assert report_generator == [(candidate, baseline), (candidate, baseline)]


def test_standalone_report_publishes_only_final_workbooks_and_report_configuration(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
    monkeypatch: pytest.MonkeyPatch,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    comparison, _, _ = _comparison_dir(tmp_path)
    config = tmp_path / "report.yaml"
    config.write_text("title: audit\n", encoding="utf-8")
    expected: list[str] = []
    uploads: dict[str, object] = {}
    connected: list[tuple[str, Path]] = []

    class FakeTask:
        pass

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.report.init_task",
        lambda *_args, **_kwargs: FakeTask(),
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.report.expect_artifacts",
        lambda _task, names: expected.extend(names),
    )
    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.report.upload_artifact",
        lambda _task, name, value: uploads.setdefault(name, value),
    )

    def connect(_task: object, name: str, path: Path) -> Path:
        connected.append((name, path))
        return path

    patch_workflow(
        monkeypatch,
        workflow_dependencies,
        "clearml_yolo.application.use_cases.report.connect_config_file",
        connect,
    )
    report(
        comparison,
        tmp_path / "reports",
        ClearMLConfig(),
        config,
        baseline_label="fixture baseline",
        candidate_label="fixture candidate",
        deps=workflow_dependencies,
    )
    assert connected == [("report", config)]
    assert set(expected) == {"report_dev_test", "report_business_test"}
    assert set(uploads) == set(expected)


def test_report_encodes_split_without_changing_logical_identity(
    tmp_path: Path,
    report_generator: list[tuple[Path, Path]],
    workflow_dependencies: WorkflowDependencies,
) -> None:
    comparison, candidate, baseline = _comparison_dir(tmp_path)
    manifest_path = comparison / MANIFEST_NAME
    manifest = ComparisonManifest.model_validate_json(manifest_path.read_text())
    split = "../../../escape/actual"
    manifest.split = split
    manifest_path.write_text(manifest.model_dump_json())
    destination = tmp_path / "reports"
    result = report(
        comparison,
        destination,
        ClearMLConfig(),
        baseline_label="fixture baseline",
        candidate_label="fixture candidate",
        deps=workflow_dependencies,
    )
    assert result.dev_reports[split].parent == destination
    assert result.business_reports[split].parent == destination
    assert result.dev_reports[split].is_file()
    assert report_generator == [(candidate, baseline), (candidate, baseline)]
