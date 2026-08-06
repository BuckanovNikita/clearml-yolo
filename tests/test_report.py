"""Locating dashboard workbooks: the new model's and a local baseline's, one way."""

from __future__ import annotations

from pathlib import Path

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.tasks.metrics import DASHBOARD_PREFIX
from clearml_yolo.tasks.report import BaselineConfig, build_reports, discover_dashboards


def _workbooks(directory: Path, splits: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for split in splits:
        (directory / f"{DASHBOARD_PREFIX}_{split}.xlsx").write_bytes(b"")


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
