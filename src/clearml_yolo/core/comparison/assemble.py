"""Turn two scored splits into the one comparison frame the reports agree on.

Scoring yields per-class tallies, significance yields tests, and the workbook and the
ClearML report both consume a single wide frame — one row per class plus a pooled row —
that neither of them builds. This is that frame.

Two decisions are pinned here because getting them wrong silently changes the verdict.
The Benjamini-Hochberg family spans every (class, metric) hypothesis of the split, not
each metric separately, because that is what the false-discovery rate is being
controlled over. And the pooled row stays outside the family: it is a summary of the
same data, so folding it in would count the evidence twice.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pandas as pd

from clearml_yolo.core.comparison.significance import (
    TestResult,
    adjust_benjamini_hochberg,
    bootstrap_precision_delta,
    bootstrap_recall_delta,
    mcnemar_recall,
    validate_q,
)
from clearml_yolo.core.evaluation.models import ClassCounts, SplitOutcome

POOLED_FLAG = "is_pooled"
IMPROVED = "improved"
DEGRADED = "degraded"
NOT_SIGNIFICANT = "not_significant"
UNAVAILABLE = "unavailable"

NO_GROUND_TRUTH = "Нет разметки в сплите"
NO_PREDICTIONS = "Ни одна модель не предсказала класс"
UNKNOWN_TO_BASELINE = "Только в новой модели"
UNKNOWN_TO_CANDIDATE = "Только в прод модели"
UNKNOWN_TO_BOTH = "Нет ни в одной модели"


@dataclass(frozen=True)
class ComparisonTables:
    """Everything one split's comparison produces, ready for both report writers."""

    rows: pd.DataFrame
    excluded: pd.DataFrame
    methodology: dict[str, object]


def _rate(numerator: int, denominator: int) -> float:
    """A rate whose denominator can legitimately be zero, e.g. precision with no predictions."""
    return numerator / denominator if denominator else math.nan


def _precision(counts: ClassCounts) -> float:
    return _rate(counts.tp, counts.tp + counts.fp)


def _recall(counts: ClassCounts) -> float:
    return _rate(counts.tp, counts.tp + counts.fn)


def _class_rows(outcome: SplitOutcome, class_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    gt_status = outcome.gt_status[outcome.gt_status["instance_label"] == class_name]
    pred_status = outcome.pred_status[outcome.pred_status["instance_label"] == class_name]
    return gt_status, pred_status


def _detection_flags(gt_status: pd.DataFrame) -> pd.Series:
    """Detected/missed per ground-truth box, keyed so both models' boxes line up."""
    return gt_status.set_index("gt_index")["detected"]


def _test_pair(
    baseline: SplitOutcome,
    candidate: SplitOutcome,
    class_name: str | None,
    images: Sequence[str],
    *,
    iterations: int,
    seed: int,
    diagnostic: Callable[[str], None] | None,
) -> tuple[TestResult, TestResult, TestResult]:
    """Run the three tests for one class, or for the whole split when ``class_name`` is None.

    Recall gets both an exact McNemar p-value and a bootstrap interval: McNemar is
    authoritative at the per-class counts this report hits, where a bootstrap p-value is
    not, so the bootstrap contributes only its interval.
    """
    if class_name is None:
        baseline_gt, baseline_preds = baseline.gt_status, baseline.pred_status
        candidate_gt, candidate_preds = candidate.gt_status, candidate.pred_status
    else:
        baseline_gt, baseline_preds = _class_rows(baseline, class_name)
        candidate_gt, candidate_preds = _class_rows(candidate, class_name)

    precision = bootstrap_precision_delta(
        baseline_preds,
        candidate_preds,
        images,
        iterations=iterations,
        seed=seed,
        diagnostic=diagnostic,
    )
    recall_interval = bootstrap_recall_delta(
        baseline_gt,
        candidate_gt,
        images,
        iterations=iterations,
        seed=seed,
        diagnostic=diagnostic,
    )
    recall_test = mcnemar_recall(
        _detection_flags(baseline_gt),
        _detection_flags(candidate_gt),
        diagnostic=diagnostic,
    )
    return precision, recall_interval, recall_test


def _verdict(delta: float, adjusted_p: float, q: float) -> str:
    """A change counts only once Benjamini-Hochberg has cleared it at the family level."""
    validate_q(q)
    if math.isnan(adjusted_p) or math.isnan(delta):
        return UNAVAILABLE
    if adjusted_p > q or delta == 0:
        return NOT_SIGNIFICANT
    return IMPROVED if delta > 0 else DEGRADED


def _exclusion_reason(
    class_name: str,
    baseline_counts: ClassCounts,
    candidate_counts: ClassCounts,
    baseline_classes: set[str],
    candidate_classes: set[str],
) -> str | None:
    """Why a class carries no usable comparison, or None when it does."""
    in_baseline = class_name in baseline_classes
    in_candidate = class_name in candidate_classes
    if not in_baseline and not in_candidate:
        # Neither model knows the class, which is a labelling gap rather than a
        # difference between the two — calling it "only in the new model" would send a
        # reader looking for a change that no model made.
        return UNKNOWN_TO_BOTH
    if not in_baseline:
        return UNKNOWN_TO_BASELINE
    if not in_candidate:
        return UNKNOWN_TO_CANDIDATE
    if not (baseline_counts.tp + baseline_counts.fn or candidate_counts.tp + candidate_counts.fn):
        return NO_GROUND_TRUTH
    if not (baseline_counts.tp + baseline_counts.fp or candidate_counts.tp + candidate_counts.fp):
        return NO_PREDICTIONS
    return None


def _row(
    class_name: str,
    baseline_counts: ClassCounts | None,
    candidate_counts: ClassCounts | None,
    thresholds_baseline: dict[str, float],
    thresholds_candidate: dict[str, float],
    precision: TestResult,
    recall_interval: TestResult,
    recall_test: TestResult,
    *,
    is_pooled: bool,
) -> dict[str, object]:
    return {
        "class_name": class_name,
        POOLED_FLAG: is_pooled,
        "threshold_baseline": thresholds_baseline.get(class_name, math.nan)
        if baseline_counts is not None
        else math.nan,
        "threshold_candidate": thresholds_candidate.get(class_name, math.nan)
        if candidate_counts is not None
        else math.nan,
        "tp_baseline": baseline_counts.tp if baseline_counts is not None else math.nan,
        "fp_baseline": baseline_counts.fp if baseline_counts is not None else math.nan,
        "fn_baseline": baseline_counts.fn if baseline_counts is not None else math.nan,
        "tp_candidate": candidate_counts.tp if candidate_counts is not None else math.nan,
        "fp_candidate": candidate_counts.fp if candidate_counts is not None else math.nan,
        "fn_candidate": candidate_counts.fn if candidate_counts is not None else math.nan,
        "precision_baseline": _precision(baseline_counts)
        if baseline_counts is not None
        else math.nan,
        "precision_candidate": _precision(candidate_counts)
        if candidate_counts is not None
        else math.nan,
        "precision_delta": precision.delta,
        "precision_ci_lower": precision.ci_lower,
        "precision_ci_upper": precision.ci_upper,
        "precision_p_value": precision.p_value,
        "precision_p_bh": math.nan,
        "precision_verdict": UNAVAILABLE,
        "recall_baseline": _recall(baseline_counts) if baseline_counts is not None else math.nan,
        "recall_candidate": _recall(candidate_counts) if candidate_counts is not None else math.nan,
        # The delta comes from McNemar's paired means, which is the test that decides the
        # verdict; the bootstrap supplies the interval around it.
        "recall_delta": recall_test.delta,
        "recall_ci_lower": recall_interval.ci_lower,
        "recall_ci_upper": recall_interval.ci_upper,
        "recall_p_value": recall_test.p_value,
        "recall_p_bh": math.nan,
        "recall_verdict": UNAVAILABLE,
    }


def _pooled_counts(counts: dict[str, ClassCounts], compared: Sequence[str]) -> ClassCounts:
    return ClassCounts(
        tp=sum(counts.get(name, ClassCounts()).tp for name in compared),
        fp=sum(counts.get(name, ClassCounts()).fp for name in compared),
        fn=sum(counts.get(name, ClassCounts()).fn for name in compared),
    )


def _restricted_outcome(outcome: SplitOutcome, classes: Sequence[str]) -> SplitOutcome:
    """Limit pooled counts and paired/bootstrap observations to the same classes."""
    return SplitOutcome(
        counts={name: outcome.counts.get(name, ClassCounts()) for name in classes},
        gt_status=outcome.gt_status[outcome.gt_status["instance_label"].isin(classes)],
        pred_status=outcome.pred_status[outcome.pred_status["instance_label"].isin(classes)],
    )


def build_comparison_rows(
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
    """Compare two scored outcomes of one split, class by class and then pooled.

    ``baseline_classes``/``candidate_classes`` are the checkpoints' own vocabularies. A
    class one model cannot predict retains the supporting model's metrics and missing
    values for the other model. Statistical tests and pooled statistics use only shared
    eligible classes; exclusions explain noncomparability rather than hide metrics.
    ``observe_class`` receives each class before computation and None after the
    class loop; diagnostics are warnings and the final summary is informational.
    """
    validate_q(q)
    compared: list[str] = []
    excluded_rows: list[dict[str, str]] = []
    known_to_baseline = baseline_classes if baseline_classes is not None else set(baseline.counts)
    known_to_candidate = (
        candidate_classes if candidate_classes is not None else set(candidate.counts)
    )

    display_classes = sorted(
        set(baseline.counts) | set(candidate.counts) | known_to_baseline | known_to_candidate
    )
    for class_name in display_classes:
        reason = _exclusion_reason(
            class_name,
            baseline.counts.get(class_name, ClassCounts()),
            candidate.counts.get(class_name, ClassCounts()),
            known_to_baseline,
            known_to_candidate,
        )
        if reason is None:
            compared.append(class_name)
        else:
            excluded_rows.append({"class_name": class_name, "reason": reason})

    unavailable_test = TestResult(delta=math.nan, p_value=math.nan, n_baseline=0, n_candidate=0)
    rows: list[dict[str, object]] = []
    for class_name in display_classes:
        if observe_class is not None:
            observe_class(class_name)
        precision, recall_interval, recall_test = (unavailable_test,) * 3
        if class_name in compared:
            precision, recall_interval, recall_test = _test_pair(
                baseline,
                candidate,
                class_name,
                images,
                iterations=iterations,
                seed=seed,
                diagnostic=diagnostic,
            )
        rows.append(
            _row(
                class_name,
                baseline.counts.get(class_name, ClassCounts())
                if class_name in known_to_baseline
                else None,
                candidate.counts.get(class_name, ClassCounts())
                if class_name in known_to_candidate
                else None,
                thresholds_baseline,
                thresholds_candidate,
                precision,
                recall_interval,
                recall_test,
                is_pooled=False,
            )
        )

    if observe_class is not None:
        observe_class(None)

    frame = pd.DataFrame(rows)
    family_size = _adjust_family(frame, q) if rows else 0

    pooled_precision, pooled_recall_interval, pooled_recall = (unavailable_test,) * 3
    if compared:
        # Counts and tests must summarize the same shared eligible class population.
        pooled_precision, pooled_recall_interval, pooled_recall = _test_pair(
            _restricted_outcome(baseline, compared),
            _restricted_outcome(candidate, compared),
            None,
            images,
            iterations=iterations,
            seed=seed,
            diagnostic=diagnostic,
        )
    pooled = _row(
        "pooled",
        _pooled_counts(baseline.counts, compared) if compared else None,
        _pooled_counts(candidate.counts, compared) if compared else None,
        {},
        {},
        pooled_precision,
        pooled_recall_interval,
        pooled_recall,
        is_pooled=True,
    )
    # Pooled hypotheses stay outside BH and are judged on their raw p-values.
    pooled["precision_verdict"] = _verdict(pooled_precision.delta, pooled_precision.p_value, q)
    pooled["recall_verdict"] = _verdict(pooled_recall.delta, pooled_recall.p_value, q)
    frame = pd.concat([frame, pd.DataFrame([pooled])], ignore_index=True)

    methodology: dict[str, object] = {
        "precision_test": "bootstrap по изображениям (доверительный интервал и p-value)",
        "recall_test": "точный тест Макнемара (p-value), bootstrap (интервал)",
        "multiple_testing": "Benjamini-Hochberg по всем гипотезам сплита",
        "family_size": family_size,
        "q": q,
        "bootstrap_iterations": iterations,
        "seed": seed,
        "images": len(images),
        "classes_compared": len(compared),
        "pooled_classes": list(compared),
        "display_population": "Union of model vocabularies and scored classes",
        "pooled_population": "Shared statistically eligible classes",
        "classes_excluded": len(excluded_rows),
    }
    if summary is not None:
        summary(
            f"Comparison assembled: {len(compared)} classes compared, "
            f"{len(excluded_rows)} excluded, BH family of {family_size}"
        )
    return ComparisonTables(
        rows=frame,
        excluded=pd.DataFrame(excluded_rows, columns=["class_name", "reason"]),
        methodology=methodology,
    )


def _adjust_family(frame: pd.DataFrame, q: float) -> int:
    """Correct every hypothesis of the split at once and write the verdicts back.

    Both metrics of every class enter one family: correcting precision and recall
    separately would control the false-discovery rate over half the tests actually run
    and let roughly twice as many spurious verdicts through.
    """
    p_values = [*frame["precision_p_value"], *frame["recall_p_value"]]
    adjusted = adjust_benjamini_hochberg(p_values, q=q).adjusted_p_values
    half = len(frame)
    frame["precision_p_bh"] = adjusted[:half]
    frame["recall_p_bh"] = adjusted[half:]
    for metric in ("precision", "recall"):
        frame[f"{metric}_verdict"] = [
            _verdict(delta, adjusted_p, q)
            for delta, adjusted_p in zip(
                frame[f"{metric}_delta"], frame[f"{metric}_p_bh"], strict=True
            )
        ]
    return int(sum(1 for value in adjusted if not math.isnan(value)))
