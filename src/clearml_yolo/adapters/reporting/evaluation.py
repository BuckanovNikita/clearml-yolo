"""Render neutral evaluation values with the public digital-metrics reporter."""

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd
from digital_metrics import summarize_metrics
from digital_metrics.reporting import render_evaluation as render_shared_evaluation
from digital_metrics.types import Metrics

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.reporting.workbook_identity import annotate_workbook
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.core.artifact_names import PLOT_METRICS, split_component
from clearml_yolo.core.evaluation.models import (
    ComputedEvaluation,
    DetectionMetrics,
    EvaluationArtifacts,
)


@trace_operation("report.evaluation.render")
def render_evaluation(
    computed: ComputedEvaluation,
    *,
    output_dir: Path,
    suffix: str,
    dashboard_classes: set[str] | None = None,
) -> EvaluationArtifacts:
    """Write the original dashboards and plots without repeating matching/scoring."""
    output_dir = write_path(output_dir)
    metrics = {
        name: Metrics(
            counts_observed=value.counts_observed,
            tp=value.tp,
            fp=value.fp,
            fn=value.fn,
            confidence=value.confidence,
            ap50=value.ap50,
            ap75=value.ap75,
            ap50_95=value.ap50_95,
            cohen_kappa=value.cohen_kappa,
        )
        for name, value in computed.metrics.items()
    }
    visible_metrics = (
        metrics
        if dashboard_classes is None
        else {name: metric for name, metric in metrics.items() if name in dashboard_classes}
    )
    if not visible_metrics:
        raise ValueError(
            f"Split {computed.split!r} has no classes that can be written to a dashboard"
        )
    suffix = split_component(suffix)
    output_dir.mkdir(parents=True, exist_ok=True)
    # These API-owned outputs must come from this evaluation under either producer convention.
    for metric_name in PLOT_METRICS:
        for plot_suffix in ("", f"_{suffix}"):
            write_path(output_dir / f"{metric_name}_confidence_intervals{plot_suffix}.png").unlink(
                missing_ok=True
            )
    dashboard_path = output_dir / f"full_dashboard_{suffix}.xlsx"
    dtrk_path = output_dir / f"метрики_дтрк_{suffix}.xlsx"
    confusion_matrix_path = output_dir / f"matrix_{suffix}.xlsx"
    plot_paths = {
        name: output_dir / f"{name}_confidence_intervals_{suffix}.png" for name in PLOT_METRICS
    }
    for artifact in (dashboard_path, dtrk_path, confusion_matrix_path, *plot_paths.values()):
        write_path(artifact)
    identity = computed.model_identity
    caption = (
        None
        if identity is None
        else (
            f"Model: {identity.model_name}\n"
            f"Training task: {identity.training_task_id or 'unavailable'}"
        )
    )
    with trace_operation(
        "report.dashboards.render",
        context={
            "split": computed.split,
            "classes": len(visible_metrics),
            "destination": str(output_dir),
        },
    ):
        rendered = render_shared_evaluation(
            visible_metrics,
            computed.ground_truth,
            np.asarray(computed.confusion_matrix.counts),
            computed.confusion_matrix.labels,
            suffix=suffix,
            save_to_excel=True,
            path=str(output_dir),
            artifact_paths={
                "dashboard": dashboard_path,
                "dtrk_dashboard": dtrk_path,
                "confusion_matrix": confusion_matrix_path,
                **plot_paths,
            },
            caption=caption,
        )
    for path in plot_paths.values():
        if not path.is_file():
            raise FileNotFoundError(f"Required confidence interval plot is missing: {path}")
    if identity is not None:
        for workbook in (dashboard_path, dtrk_path, confusion_matrix_path):
            annotate_workbook(workbook, {"model": identity})
    return EvaluationArtifacts(
        dashboard=rendered.dashboard,
        dtrk_dashboard=rendered.dtrk_dashboard,
        dashboard_path=dashboard_path,
        dtrk_dashboard_path=dtrk_path,
        plot_paths=plot_paths,
        confusion_matrix_path=confusion_matrix_path,
    )


def summarize_evaluation(
    metrics: Mapping[str, DetectionMetrics],
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Retain the dependency's exact headline aggregation over neutral values."""
    frame, summary = summarize_metrics(dict(metrics))
    return frame, summary
