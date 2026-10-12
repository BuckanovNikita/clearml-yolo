"""Convert authoritative dependency PR observations into application records."""

import pandas as pd
from digital_metrics.scoring.ap import build_pr_observations

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.core.evaluation.schema import PRCurve


@trace_operation("evaluation.pr.curves")
def build_pr_curves(
    ground_truth: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    classes: list[str],
    image_names: list[str],
    matching_strategy: str,
    ap_method: str,
) -> list[PRCurve]:
    """Return AP-population curves, without a fixed-threshold operating point."""
    return [
        PRCurve(
            class_name=curve.class_name,
            recall=curve.recall,
            precision=curve.precision,
            confidence=curve.confidence,
            tp=curve.tp,
            fp=curve.fp,
            gt_count=curve.gt_count,
            ap50=curve.ap50,
            integration_method=curve.integration_method,
        )
        for curve in build_pr_observations(
            ground_truth,
            predictions,
            classes=classes,
            image_names=image_names,
            matching_strategy=matching_strategy,
            ap_method=ap_method,
        )
    ]
