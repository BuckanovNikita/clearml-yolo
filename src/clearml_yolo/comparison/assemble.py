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

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd
from loguru import logger

from clearml_yolo.comparison.scoring import ClassCounts, SplitOutcome
from clearml_yolo.comparison.significance import (
    TestResult,
    adjust_benjamini_hochberg,
    bootstrap_precision_delta,
    bootstrap_recall_delta,
    mcnemar_recall,
)

POOLED_FLAG = "is_pooled"
IMPROVED = "improved"
DEGRADED = "degraded"
NOT_SIGNIFICANT = "not_significant"

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
        baseline_preds, candidate_preds, images, iterations=iterations, seed=seed
    )
    recall_interval = bootstrap_recall_delta(
        baseline_gt, candidate_gt, images, iterations=iterations, seed=seed
    )
    recall_test = mcnemar_recall(_detection_flags(baseline_gt), _detection_flags(candidate_gt))
    return precision, recall_interval, recall_test


def _verdict(delta: float, adjusted_p: float, q: float) -> str:
    """A change counts only once Benjamini-Hochberg has cleared it at the family level."""
    if math.isnan(adjusted_p) or math.isnan(delta) or adjusted_p > q or delta == 0:
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
    baseline_counts: ClassCounts,
    candidate_counts: ClassCounts,
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
        "threshold_baseline": thresholds_baseline.get(class_name, math.nan),
        "threshold_candidate": thresholds_candidate.get(class_name, math.nan),
        "tp_baseline": baseline_counts.tp,
        "fp_baseline": baseline_counts.fp,
        "fn_baseline": baseline_counts.fn,
        "tp_candidate": candidate_counts.tp,
        "fp_candidate": candidate_counts.fp,
        "fn_candidate": candidate_counts.fn,
        "precision_baseline": _precision(baseline_counts),
        "precision_candidate": _precision(candidate_counts),
        "precision_delta": precision.delta,
        "precision_ci_lower": precision.ci_lower,
        "precision_ci_upper": precision.ci_upper,
        "precision_p_value": precision.p_value,
        "precision_p_bh": math.nan,
        "precision_verdict": NOT_SIGNIFICANT,
        "recall_baseline": _recall(baseline_counts),
        "recall_candidate": _recall(candidate_counts),
        # The delta comes from McNemar's paired means, which is the test that decides the
        # verdict; the bootstrap supplies the interval around it.
        "recall_delta": recall_test.delta,
        "recall_ci_lower": recall_interval.ci_lower,
        "recall_ci_upper": recall_interval.ci_upper,
        "recall_p_value": recall_test.p_value,
        "recall_p_bh": math.nan,
        "recall_verdict": NOT_SIGNIFICANT,
    }


def _pooled_counts(counts: dict[str, ClassCounts], compared: Sequence[str]) -> ClassCounts:
    return ClassCounts(
        tp=sum(counts[name].tp for name in compared),
        fp=sum(counts[name].fp for name in compared),
        fn=sum(counts[name].fn for name in compared),
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
) -> ComparisonTables:
    """Compare two scored outcomes of one split, class by class and then pooled.

    ``baseline_classes``/``candidate_classes`` are the checkpoints' own vocabularies. A
    class one model cannot predict is excluded rather than scored, because a model that
    never heard of a class does not have a recall of zero on it — it has no recall on it,
    and reporting the former turns a vocabulary difference into a fake regression.
    """
    compared: list[str] = []
    excluded_rows: list[dict[str, str]] = []
    known_to_baseline = baseline_classes if baseline_classes is not None else set(baseline.counts)
    known_to_candidate = (
        candidate_classes if candidate_classes is not None else set(candidate.counts)
    )

    for class_name in sorted(set(baseline.counts) | set(candidate.counts)):
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

    if not compared:
        raise ValueError(
            "No class can be compared: every one is missing from a model's vocabulary, has "
            f"no ground truth, or drew no predictions ({len(excluded_rows)} excluded)."
        )

    rows: list[dict[str, object]] = []
    for class_name in compared:
        precision, recall_interval, recall_test = _test_pair(
            baseline, candidate, class_name, images, iterations=iterations, seed=seed
        )
        rows.append(
            _row(
                class_name,
                baseline.counts.get(class_name, ClassCounts()),
                candidate.counts.get(class_name, ClassCounts()),
                thresholds_baseline,
                thresholds_candidate,
                precision,
                recall_interval,
                recall_test,
                is_pooled=False,
            )
        )

    frame = pd.DataFrame(rows)
    family_size = _adjust_family(frame, q)

    pooled_precision, pooled_recall_interval, pooled_recall = _test_pair(
        baseline, candidate, None, images, iterations=iterations, seed=seed
    )
    pooled = _row(
        "pooled",
        _pooled_counts(baseline.counts, compared),
        _pooled_counts(candidate.counts, compared),
        {},
        {},
        pooled_precision,
        pooled_recall_interval,
        pooled_recall,
        is_pooled=True,
    )
    # The pooled row is one hypothesis, not a family, so it is judged on its own raw
    # p-value. Leaving it at "not significant" because it has no adjusted p-value would
    # print that verdict beside a delta the per-class rows just called a degradation.
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
        "classes_excluded": len(excluded_rows),
    }
    logger.info(
        "Comparison assembled: {} classes compared, {} excluded, BH family of {}",
        len(compared),
        len(excluded_rows),
        family_size,
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
