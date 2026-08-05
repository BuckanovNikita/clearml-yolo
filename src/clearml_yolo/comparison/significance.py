"""Significance tests for per-class metric deltas between a baseline and a candidate model.

Every delta is ``candidate - baseline``, so a positive delta is an improvement and a
negative one a degradation. Both tests are two-sided: the p-value answers "did this
class change at all", the sign of ``delta`` answers "in which direction". Benjamini-
Hochberg then controls the false discovery rate over that two-sided family, and the
direction of each surviving change is still read off the sign of its delta.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from loguru import logger
from pydantic import BaseModel
from scipy.stats import binomtest, false_discovery_control


class TestResult(BaseModel):
    """One hypothesis test: the observed delta, its p-value and its sample sizes.

    ``ci_lower``/``ci_upper`` are ``None`` when the test does not produce an interval
    (McNemar) or when no resample was usable. ``n_baseline``/``n_candidate`` count
    aligned ground-truth boxes for the recall test and prediction rows for the
    precision test.
    """

    delta: float
    p_value: float
    ci_lower: float | None = None
    ci_upper: float | None = None
    n_baseline: int
    n_candidate: int


class BHResult(BaseModel):
    """Benjamini-Hochberg output, aligned element-wise to the input p-values."""

    adjusted_p_values: list[float]
    rejected: list[bool]
    q: float = 0.05


def mcnemar_recall(baseline_detected: pd.Series, candidate_detected: pd.Series) -> TestResult:
    """Exact two-sided McNemar test on the boxes both models were scored against.

    Recall is paired at the ground-truth-box level, so each box contributes one
    detected/missed outcome per model. The exact binomial test is used instead of the
    chi-square approximation because per-class discordant counts are small, and its
    ``alternative`` is pinned so a lost recall is flagged as loudly as a gained one.
    """
    shared = baseline_detected.index.intersection(candidate_detected.index)
    if len(shared) == 0:
        logger.warning("McNemar test got no overlapping ground-truth boxes")
        return TestResult(delta=float("nan"), p_value=float("nan"), n_baseline=0, n_candidate=0)

    baseline = baseline_detected.loc[shared].astype(bool)
    candidate = candidate_detected.loc[shared].astype(bool)
    baseline_only = int((baseline & ~candidate).sum())
    candidate_only = int((~baseline & candidate).sum())
    discordant = baseline_only + candidate_only

    # No discordant pair carries no evidence in either direction.
    if discordant == 0:
        p_value = 1.0
    else:
        p_value = float(binomtest(baseline_only, discordant, 0.5, alternative="two-sided").pvalue)
    return TestResult(
        delta=float(candidate.mean() - baseline.mean()),
        p_value=p_value,
        n_baseline=len(shared),
        n_candidate=len(shared),
    )


def _per_image_counts(
    pred_status: pd.DataFrame, images: Sequence[str], model: str
) -> tuple[np.ndarray, np.ndarray]:
    """True-positive and prediction counts per image, in the order of ``images``."""
    split_images = pd.Index(images)
    grouped = pred_status.groupby("image_name")["is_tp"]
    true_positives = grouped.sum().reindex(split_images, fill_value=0).to_numpy(dtype=float)
    totals = grouped.size().reindex(split_images, fill_value=0).to_numpy(dtype=float)
    dropped = len(pred_status) - int(totals.sum())
    if dropped:
        logger.warning(
            "{} predictions of the {} model reference images outside the split and were dropped",
            dropped,
            model,
        )
    return true_positives, totals


def bootstrap_precision_delta(
    baseline_pred_status: pd.DataFrame,
    candidate_pred_status: pd.DataFrame,
    images: Sequence[str],
    *,
    iterations: int = 10_000,
    seed: int = 0,
) -> TestResult:
    """Bootstrap the candidate-minus-baseline precision delta by resampling images.

    Precision cannot be paired at box level because the two models emit different
    numbers of predictions. Images are resampled rather than predictions because boxes
    cluster within images and resampling boxes would understate the variance. A draw in
    which either model emits no prediction leaves precision undefined and is skipped;
    the p-value averages over the usable draws only, but its floor stays ``1 /
    iterations`` because that is the resolution the bootstrap was asked for.

    The p-value compares absolute deviations against the H0-centred distribution, which
    makes it two-sided - a precision drop is as significant as an equal-sized gain. Do
    not narrow that comparison to one tail.
    """
    if iterations <= 0:
        raise ValueError(f"iterations must be positive, got {iterations}")
    if len(images) == 0:
        raise ValueError("images must not be empty")

    baseline_tp, baseline_totals = _per_image_counts(baseline_pred_status, images, "baseline")
    candidate_tp, candidate_totals = _per_image_counts(candidate_pred_status, images, "candidate")
    n_baseline = int(baseline_totals.sum())
    n_candidate = int(candidate_totals.sum())
    if n_baseline == 0 or n_candidate == 0:
        logger.warning(
            "Precision bootstrap needs predictions from both models, got {} and {}",
            n_baseline,
            n_candidate,
        )
        return TestResult(
            delta=float("nan"),
            p_value=float("nan"),
            n_baseline=n_baseline,
            n_candidate=n_candidate,
        )

    observed = candidate_tp.sum() / n_candidate - baseline_tp.sum() / n_baseline

    rng = np.random.default_rng(seed)
    image_count = len(images)
    resampled = np.empty(iterations, dtype=float)
    for iteration in range(iterations):
        sampled = rng.integers(0, image_count, image_count)
        baseline_predictions = baseline_totals[sampled].sum()
        candidate_predictions = candidate_totals[sampled].sum()
        if baseline_predictions == 0 or candidate_predictions == 0:
            resampled[iteration] = np.nan
            continue
        resampled[iteration] = (
            candidate_tp[sampled].sum() / candidate_predictions
            - baseline_tp[sampled].sum() / baseline_predictions
        )

    usable = resampled[np.isfinite(resampled)]
    if usable.size == 0:
        logger.warning("Every precision bootstrap draw was degenerate; p-value is undefined")
        return TestResult(
            delta=float(observed),
            p_value=float("nan"),
            n_baseline=n_baseline,
            n_candidate=n_candidate,
        )

    ci_lower, ci_upper = np.percentile(usable, [2.5, 97.5])
    # The interval comes from the uncentred draws, the p-value from the H0-centred ones.
    centred = usable - observed
    exceedance = float(np.mean(np.abs(centred) >= abs(observed)))
    return TestResult(
        delta=float(observed),
        p_value=max(exceedance, 1.0 / iterations),
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        n_baseline=n_baseline,
        n_candidate=n_candidate,
    )


def adjust_benjamini_hochberg(p_values: Sequence[float], q: float = 0.05) -> BHResult:
    """Control the false discovery rate across every class-by-metric test in a split.

    Undefined tests arrive as NaN and are held out of the family entirely - leaving them
    in would inflate its size and distort the ranking - then mapped back as NaN so the
    output stays aligned to the input order.
    """
    raw = np.asarray(p_values, dtype=float)
    defined = np.isfinite(raw)
    adjusted = np.full(raw.shape, np.nan)
    if defined.any():
        adjusted[defined] = false_discovery_control(raw[defined], method="bh")
    return BHResult(
        adjusted_p_values=[float(value) for value in adjusted],
        rejected=[bool(value <= q) for value in adjusted],
        q=q,
    )
