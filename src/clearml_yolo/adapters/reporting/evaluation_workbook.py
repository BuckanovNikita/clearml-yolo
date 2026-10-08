"""Concrete workflow operations behind application ports."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from clearml_yolo.adapters.reporting.evaluation import summarize_evaluation as summarize_metrics
from clearml_yolo.adapters.reporting.workbook_identity import (
    annotate_workbook,
    read_dashboard,
)
from clearml_yolo.core.evaluation.models import EvaluatedSplit


def write_candidate_workbook(
    path: Path, per_class: pd.DataFrame, summary: dict[str, float]
) -> None:
    """Retain candidate diagnostics when no automatic baseline is available."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        per_class.to_excel(writer, sheet_name="Classes")
        pd.DataFrame([summary]).to_excel(writer, sheet_name="Summary", index=False)


def write_evaluation_workbook(
    path: Path, evaluated: EvaluatedSplit, *, methodology: dict[str, Any]
) -> dict[str, Path]:
    """Write metric tables to Excel and row-level evidence/metadata to CSV."""
    required_diagnostics = [
        evaluated.dashboard_path,
        evaluated.dtrk_dashboard_path,
        evaluated.confusion_matrix_path,
        *evaluated.plot_paths.values(),
    ]
    missing = [str(item) for item in required_diagnostics if not item.is_file()]
    if missing:
        raise FileNotFoundError(f"Required local evaluation diagnostics are missing: {missing}")
    expected_plots = {"recall", "precision", "perebrak", "nedobrak"}
    if set(evaluated.plot_paths) != expected_plots:
        raise ValueError(
            f"Evaluation plot inventory mismatch: expected={sorted(expected_plots)}, "
            f"actual={sorted(evaluated.plot_paths)}"
        )
    per_class, summary = summarize_metrics(evaluated.metrics)
    confusion = read_dashboard(evaluated.confusion_matrix_path, index_col=0)
    thresholds = pd.DataFrame(
        sorted(evaluated.thresholds.items()), columns=["class_name", "confidence"]
    )
    summary_frame = pd.DataFrame([summary])
    per_class_frame = per_class.rename_axis("class_name").reset_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_frame.to_excel(writer, sheet_name="summary", index=False)
        per_class_frame.to_excel(writer, sheet_name="per_class", index=False)
        confusion.to_excel(writer, sheet_name="confusion_matrix")
    if evaluated.model_identity is not None:
        annotate_workbook(path, {"model": evaluated.model_identity})
    tables: dict[str, Path] = {}
    for title, frame in {
        "ground_truth_matches": evaluated.gt_matches,
        "prediction_matches": evaluated.pred_matches,
        "thresholds": thresholds,
        "methodology": _methodology_frame(methodology),
    }.items():
        table_path = path.with_name(f"{path.stem}_{title}.csv")
        frame.to_csv(table_path, index=False, float_format="%.17g")
        tables[table_path.stem] = table_path
    return tables


def _methodology_frame(values: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "parameter": list(values),
            "value": [
                json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values.values()
            ],
        }
    )
