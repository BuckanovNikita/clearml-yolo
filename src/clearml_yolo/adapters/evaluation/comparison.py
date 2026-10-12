"""Bridge shared paired statistics into the application's comparison policy."""

from collections.abc import Callable, Sequence

from digital_metrics.comparison import adjust_benjamini_hochberg, compare_paired

from clearml_yolo.core.comparison.assemble import (
    ComparisonTables,
    build_comparison_rows_with_statistics,
)
from clearml_yolo.core.comparison.significance import TestResult
from clearml_yolo.core.evaluation.models import SplitOutcome


class _Statistics:
    def test_pair(
        self,
        baseline: SplitOutcome,
        candidate: SplitOutcome,
        class_name: str | None,
        images: Sequence[str],
        *,
        iterations: int,
        seed: int,
        diagnostic: Callable[[str], None] | None,
    ) -> tuple[TestResult, TestResult, TestResult]:
        baseline_gt, baseline_preds = baseline.gt_status, baseline.pred_status
        candidate_gt, candidate_preds = candidate.gt_status, candidate.pred_status
        if class_name is not None:
            baseline_gt = baseline_gt[baseline_gt["instance_label"] == class_name]
            baseline_preds = baseline_preds[baseline_preds["instance_label"] == class_name]
            candidate_gt = candidate_gt[candidate_gt["instance_label"] == class_name]
            candidate_preds = candidate_preds[candidate_preds["instance_label"] == class_name]
        result = compare_paired(
            baseline_gt,
            baseline_preds,
            candidate_gt,
            candidate_preds,
            images,
            iterations=iterations,
            seed=seed,
            diagnostic=diagnostic,
        ).pooled
        return (
            TestResult.model_validate(result.precision.model_dump()),
            TestResult.model_validate(result.recall_interval.model_dump()),
            TestResult.model_validate(result.recall.model_dump()),
        )

    def adjust(self, p_values: Sequence[float], q: float) -> list[float]:
        return list(adjust_benjamini_hochberg(p_values, q).adjusted_p_values)


def compare_outcomes(
    baseline: SplitOutcome,
    candidate: SplitOutcome,
    *,
    thresholds_baseline: dict[str, float],
    thresholds_candidate: dict[str, float],
    images: Sequence[str],
    baseline_classes: set[str] | None = None,
    candidate_classes: set[str] | None = None,
    q: float = 0.05,
    iterations: int = 10_000,
    seed: int = 0,
    observe_class: Callable[[str | None], None] | None = None,
    diagnostic: Callable[[str], None] | None = None,
    summary: Callable[[str], None] | None = None,
) -> ComparisonTables:
    """Keep eligibility, family and pooled policy local; compute tests upstream."""
    return build_comparison_rows_with_statistics(
        baseline,
        candidate,
        statistics=_Statistics(),
        thresholds_baseline=thresholds_baseline,
        thresholds_candidate=thresholds_candidate,
        images=images,
        baseline_classes=baseline_classes,
        candidate_classes=candidate_classes,
        q=q,
        iterations=iterations,
        seed=seed,
        observe_class=observe_class,
        diagnostic=diagnostic,
        summary=summary,
    )
