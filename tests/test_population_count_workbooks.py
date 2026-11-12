"""Original split populations remain separate from current evaluation tables."""

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook  # type: ignore[import-untyped]

from clearml_yolo.adapters.reporting.population_counts import annotate_population_counts
from clearml_yolo.adapters.reporting.workbook_identity import annotate_workbook, read_dashboard
from clearml_yolo.core.identity import ModelIdentity


def test_original_populations_preserve_evaluation_counts_and_lexical_classes(tmp_path: Path) -> None:
    path = tmp_path / "comparison.xlsx"
    original = pd.DataFrame({"class_name": ["cat"], "evaluation_count": [999]})
    original.to_excel(path, index=False)
    baseline = ModelIdentity(model_name="=baseline", training_task_id="old-task")
    candidate = ModelIdentity(model_name="candidate", training_task_id="new-task")
    annotate_workbook(path, {"baseline": baseline, "candidate": candidate})
    annotate_population_counts(
        path,
        {
            "baseline": (baseline, {"train": {"0001": 12, "=cat": 3}, "val": {"NA": 2}, "holdout": {}}),
            "candidate": (candidate, {"train": {"0001": 7}, "test": {"0001": 4}}),
        },
    )
    with path.open("rb") as stream:
        workbook = load_workbook(stream)
        rows = list(workbook["Dataset counts"].values)
        assert ("baseline", "=baseline", "old-task", "train", "0001", 12) in rows
        assert ("candidate", "candidate", "new-task", "train", "0001", 7) in rows
        assert ("baseline", "=baseline", "old-task", "val", "0001", 0) in rows
        assert ("baseline", "=baseline", "old-task", "test", "NA", "NA") in rows
        assert ("baseline", "=baseline", "old-task", "holdout", "NA", 0) in rows
        assert all(
            cell.data_type == "s" for row in workbook["Dataset counts"] for cell in row if isinstance(cell.value, str)
        )
        workbook.close()
    annotate_workbook(path, {"baseline": baseline, "candidate": candidate})
    pd.testing.assert_frame_equal(read_dashboard(path), original)


def test_unavailable_population_is_not_zero_and_repeated_annotation_replaces_sheet(tmp_path: Path) -> None:
    path = tmp_path / "dashboard.xlsx"
    pd.DataFrame({"class_name": ["cat"], "ap50": [0.8]}).to_excel(path, index=False)
    for _ in range(2):
        annotate_population_counts(path, {"model": (None, None)})
    workbook = load_workbook(path)
    assert workbook.sheetnames.count("Dataset counts") == 1
    assert list(workbook["Dataset counts"].values)[1:] == [
        ("model", "NA", "NA", split, "NA", "NA") for split in ("train", "val", "test")
    ]
    workbook.close()
