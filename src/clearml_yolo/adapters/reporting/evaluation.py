"""Render neutral evaluation values with the public digital-metrics reporter."""

from collections.abc import Mapping
from pathlib import Path
from textwrap import wrap

import numpy as np
import pandas as pd
from digital_metrics import summarize_metrics
from digital_metrics.reporting import get_dashboards, plot_confidence_intervals
from digital_metrics.types import Metrics

from clearml_yolo.adapters.reporting.workbook_identity import annotate_workbook
from clearml_yolo.core.artifact_names import PLOT_METRICS, split_component
from clearml_yolo.core.evaluation.models import (
    ComputedEvaluation,
    DetectionMetrics,
    EvaluationArtifacts,
)
from clearml_yolo.core.identity import ModelIdentity


def render_evaluation(
    computed: ComputedEvaluation,
    *,
    output_dir: Path,
    suffix: str,
    dashboard_classes: set[str] | None = None,
) -> EvaluationArtifacts:
    """Write the original dashboards and plots without repeating matching/scoring."""
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
            (output_dir / f"{metric_name}_confidence_intervals{plot_suffix}.png").unlink(
                missing_ok=True
            )
    dashboard, dtrk_dashboard = get_dashboards(
        visible_metrics,
        computed.ground_truth,
        np.asarray(computed.confusion_matrix.counts),
        computed.confusion_matrix.labels,
        suffix=suffix,
        save_to_excel=True,
        path=str(output_dir),
    )
    dashboard_path = output_dir / f"full_dashboard_{suffix}.xlsx"
    dtrk_path = output_dir / f"метрики_дтрк_{suffix}.xlsx"
    plot_paths: dict[str, Path] = {}
    for metric_name in PLOT_METRICS:
        generated = output_dir / f"{metric_name}_confidence_intervals.png"
        preserved = output_dir / f"{metric_name}_confidence_intervals_{suffix}.png"
        if not preserved.is_file():
            if not generated.is_file():
                raise FileNotFoundError(
                    f"Required confidence interval plot is missing: {preserved}"
                )
            generated.replace(preserved)
        plot_paths[metric_name] = preserved
    confusion_matrix_path = output_dir / f"matrix_{suffix}.xlsx"
    _annotate_outputs(
        visible_metrics,
        plot_paths,
        (dashboard_path, dtrk_path, confusion_matrix_path),
        computed.model_identity,
    )
    return EvaluationArtifacts(
        dashboard=dashboard,
        dtrk_dashboard=dtrk_dashboard,
        dashboard_path=dashboard_path,
        dtrk_dashboard_path=dtrk_path,
        plot_paths=plot_paths,
        confusion_matrix_path=confusion_matrix_path,
    )


def _annotate_outputs(
    metrics: dict[str, object],
    plot_paths: dict[str, Path],
    workbooks: tuple[Path, ...],
    identity: ModelIdentity | None,
) -> None:
    if identity is None:
        return
    for metric_name, path in plot_paths.items():
        _write_identity_plot(metrics, metric_name, path, identity)
    for workbook in workbooks:
        annotate_workbook(workbook, {"model": identity})


def _write_identity_plot(
    metrics: dict[str, object],
    metric_name: str,
    path: Path,
    identity: ModelIdentity,
) -> None:
    """Annotate a public producer figure before the final local PNG export.

    The upstream save_path API returns a closed Figure, which remains editable
    and exportable. Passing save_path avoids its interactive show branch.
    """
    figure, _ = plot_confidence_intervals(
        metrics=metrics,
        metric=metric_name,
        confidence_level=0.95,
        save_path=str(path),
        figsize=(12, 8),
    )
    if figure is None:
        raise ValueError(f"No figure was produced for {metric_name!r}")
    caption = (
        f"Model: {identity.model_name}\nTraining task: {identity.training_task_id or 'unavailable'}"
    )
    wrapped_caption = "\n".join(
        line for value in caption.splitlines() for line in wrap(value, width=100)
    )
    figure.suptitle(wrapped_caption, y=1.03, va="bottom", fontsize=10, parse_math=False)
    figure.savefig(path, bbox_inches="tight", dpi=300, metadata={"Model identity": caption})


def summarize_evaluation(
    metrics: Mapping[str, DetectionMetrics],
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Retain the dependency's exact headline aggregation over neutral values."""
    frame, summary = summarize_metrics(dict(metrics))
    return frame, summary
