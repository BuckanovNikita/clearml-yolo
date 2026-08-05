"""Significance tests checked against synthetic data with known answers."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd
import pytest

from clearml_yolo.comparison.significance import (
    adjust_benjamini_hochberg,
    bootstrap_precision_delta,
    mcnemar_recall,
)


def detection_series(
    baseline_only: int, candidate_only: int, both: int, neither: int
) -> tuple[pd.Series, pd.Series]:
    """Two paired detected/missed vectors with an exactly known discordance."""
    shared = [True] * both + [False] * neither
    baseline = [True] * baseline_only + [False] * candidate_only + shared
    candidate = [False] * baseline_only + [True] * candidate_only + shared
    index = pd.Index(range(len(baseline)), name="gt_index")
    return pd.Series(baseline, index=index), pd.Series(candidate, index=index)


def prediction_frame(image_true_positives: dict[str, Sequence[bool]]) -> pd.DataFrame:
    rows = [
        {
            "pred_index": f"{image}-{position}",
            "image_name": image,
            "instance_label": "car",
            "is_tp": is_tp,
        }
        for image, flags in image_true_positives.items()
        for position, is_tp in enumerate(flags)
    ]
    return pd.DataFrame(rows, columns=["pred_index", "image_name", "instance_label", "is_tp"])


def test_mcnemar_matches_hand_computed_exact_binomial() -> None:
    baseline, candidate = detection_series(baseline_only=2, candidate_only=8, both=5, neither=5)

    result = mcnemar_recall(baseline, candidate)

    # binomtest(2, 10, 0.5) two-sided = 2 * (1 + 10 + 45) / 1024
    assert result.p_value == pytest.approx(112 / 1024)
    assert result.delta == pytest.approx(0.65 - 0.35)
    assert result.n_baseline == 20
    assert result.n_candidate == 20
    assert result.ci_lower is None
    assert result.ci_upper is None


def test_mcnemar_is_two_sided_so_a_lost_box_weighs_as_much_as_a_gained_one() -> None:
    improved = mcnemar_recall(*detection_series(2, 8, both=5, neither=5))
    degraded = mcnemar_recall(*detection_series(8, 2, both=5, neither=5))

    assert degraded.p_value == pytest.approx(improved.p_value)
    assert degraded.delta == pytest.approx(-improved.delta)
    assert improved.delta > 0
    assert degraded.delta < 0


def test_mcnemar_without_discordant_pairs_reports_no_evidence() -> None:
    baseline, candidate = detection_series(baseline_only=0, candidate_only=0, both=7, neither=3)

    result = mcnemar_recall(baseline, candidate)

    assert result.p_value == 1.0
    assert result.delta == 0.0
    assert result.n_baseline == 10


def test_mcnemar_scores_only_the_shared_boxes() -> None:
    baseline = pd.Series([True, True, False, True], index=[0, 1, 2, 3])
    candidate = pd.Series([False, True, True, True], index=[2, 3, 4, 5])

    result = mcnemar_recall(baseline, candidate)

    assert result.n_baseline == 2
    assert result.delta == pytest.approx(0.0)
    assert result.p_value == 1.0


def test_mcnemar_refuses_missing_detection_flags() -> None:
    baseline = pd.Series([True, float("nan"), False], index=[0, 1, 2])
    candidate = pd.Series([True, True, False], index=[0, 1, 2])

    with pytest.raises(ValueError, match="missing values"):
        mcnemar_recall(baseline, candidate)


def test_mcnemar_without_shared_boxes_is_undefined() -> None:
    baseline = pd.Series([True], index=[0])
    candidate = pd.Series([True], index=[1])

    result = mcnemar_recall(baseline, candidate)

    assert math.isnan(result.p_value)
    assert math.isnan(result.delta)
    assert result.n_baseline == 0


def planted_difference_frames() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    images = [f"img{index}" for index in range(60)]
    baseline = prediction_frame(
        {image: [index % 3 == 0, index % 5 == 0, False] for index, image in enumerate(images)}
    )
    candidate = prediction_frame(
        {image: [True, True, index % 7 != 0] for index, image in enumerate(images)}
    )
    return baseline, candidate, images


def test_bootstrap_detects_a_planted_precision_gap() -> None:
    baseline, candidate, images = planted_difference_frames()

    result = bootstrap_precision_delta(baseline, candidate, images, iterations=500, seed=0)

    expected = candidate["is_tp"].sum() / len(candidate) - baseline["is_tp"].sum() / len(baseline)
    assert result.delta == pytest.approx(expected)
    assert result.n_baseline == len(baseline)
    assert result.n_candidate == len(candidate)
    assert result.ci_lower is not None
    assert result.ci_upper is not None
    assert result.ci_lower > 0.0
    assert result.p_value == pytest.approx(1 / 500)


def modest_difference_frames() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """A gap small enough that the p-value lands off its 1 / iterations floor."""
    rng = np.random.default_rng(19)
    images = [f"img{index}" for index in range(60)]
    baseline = prediction_frame({image: rng.random(3) < 0.5 for image in images})
    candidate = prediction_frame({image: rng.random(3) < 0.6 for image in images})
    return baseline, candidate, images


def test_bootstrap_flags_a_planted_precision_drop_just_as_loudly() -> None:
    weaker, stronger, images = modest_difference_frames()

    improved = bootstrap_precision_delta(weaker, stronger, images, iterations=500, seed=5)
    degraded = bootstrap_precision_delta(stronger, weaker, images, iterations=500, seed=5)

    # A floored p-value would compare equal whatever the tails did, so stay off the floor.
    assert improved.p_value > 1 / 500
    assert improved.p_value < 0.5
    assert degraded.p_value == pytest.approx(improved.p_value)
    assert degraded.delta == pytest.approx(-improved.delta)
    assert improved.ci_lower is not None
    assert degraded.ci_upper is not None
    assert improved.ci_lower > 0.0
    assert degraded.ci_upper < 0.0


def test_bootstrap_on_identical_inputs_finds_nothing() -> None:
    images = [f"img{index}" for index in range(40)]
    frame = prediction_frame({image: [index % 2 == 0, True] for index, image in enumerate(images)})

    result = bootstrap_precision_delta(frame, frame.copy(), images, iterations=200, seed=3)

    assert result.delta == pytest.approx(0.0)
    assert result.p_value > 0.5
    assert result.ci_lower is not None
    assert result.ci_upper is not None
    assert result.ci_lower <= 0.0 <= result.ci_upper


def test_bootstrap_finds_nothing_between_two_equally_good_models() -> None:
    """The null case that is not true by construction: different rows, one shared rate."""
    rng = np.random.default_rng(8)
    images = [f"img{index}" for index in range(60)]
    baseline = prediction_frame({image: rng.random(3) < 0.55 for image in images})
    candidate = prediction_frame({image: rng.random(3) < 0.55 for image in images})

    result = bootstrap_precision_delta(baseline, candidate, images, iterations=500, seed=2)

    assert result.delta != 0.0
    assert result.p_value > 0.2
    assert result.ci_lower is not None
    assert result.ci_upper is not None
    assert result.ci_lower < 0.0 < result.ci_upper


def test_bootstrap_is_reproducible_for_one_seed() -> None:
    baseline, candidate, images = planted_difference_frames()

    first = bootstrap_precision_delta(baseline, candidate, images, iterations=300, seed=11)
    second = bootstrap_precision_delta(baseline, candidate, images, iterations=300, seed=11)
    other_seed = bootstrap_precision_delta(baseline, candidate, images, iterations=300, seed=12)

    assert first == second
    assert first != other_seed


def test_bootstrap_skips_draws_where_a_model_predicts_nothing() -> None:
    images = [f"img{index}" for index in range(5)]
    baseline = prediction_frame({"img0": [True, False]})
    candidate = prediction_frame({image: [True, True] for image in images})

    result = bootstrap_precision_delta(baseline, candidate, images, iterations=400, seed=7)

    assert result.delta == pytest.approx(0.5)
    assert result.ci_lower is not None
    assert result.ci_upper is not None
    assert math.isfinite(result.ci_lower)
    assert math.isfinite(result.p_value)
    assert result.p_value >= 1 / 400


def test_bootstrap_without_baseline_predictions_is_undefined() -> None:
    images = [f"img{index}" for index in range(4)]
    empty = prediction_frame({})
    candidate = prediction_frame({image: [True] for image in images})

    result = bootstrap_precision_delta(empty, candidate, images, iterations=50, seed=0)

    assert math.isnan(result.delta)
    assert math.isnan(result.p_value)
    assert result.ci_lower is None
    assert result.n_baseline == 0
    assert result.n_candidate == 4


def test_bootstrap_rejects_degenerate_arguments() -> None:
    baseline, candidate, images = planted_difference_frames()

    with pytest.raises(ValueError, match="images"):
        bootstrap_precision_delta(baseline, candidate, [], iterations=10)
    with pytest.raises(ValueError, match="iterations"):
        bootstrap_precision_delta(baseline, candidate, images, iterations=0)


def test_benjamini_hochberg_matches_a_hand_checked_family() -> None:
    result = adjust_benjamini_hochberg([0.001, 0.01, 0.3, 0.4, 0.5])

    assert result.adjusted_p_values == pytest.approx([0.005, 0.025, 0.5, 0.5, 0.5])
    assert result.rejected == [True, True, False, False, False]
    assert result.q == 0.05


def test_benjamini_hochberg_keeps_the_input_order() -> None:
    shuffled = adjust_benjamini_hochberg([0.3, 0.001, 0.5, 0.01, 0.4])

    assert shuffled.adjusted_p_values == pytest.approx([0.5, 0.005, 0.5, 0.025, 0.5])
    assert shuffled.rejected == [False, True, False, True, False]


def test_benjamini_hochberg_excludes_undefined_tests_from_the_family() -> None:
    without_nan = adjust_benjamini_hochberg([0.001, 0.01, 0.3, 0.4, 0.5])
    with_nan = adjust_benjamini_hochberg([0.001, 0.01, float("nan"), 0.3, 0.4, 0.5])

    assert math.isnan(with_nan.adjusted_p_values[2])
    assert with_nan.rejected[2] is False
    kept = [*with_nan.adjusted_p_values[:2], *with_nan.adjusted_p_values[3:]]
    assert kept == pytest.approx(without_nan.adjusted_p_values)


def test_benjamini_hochberg_selects_on_p_value_not_on_the_size_or_sign_of_the_delta() -> None:
    deltas = [-0.4, 0.01, 0.3, -0.2, 0.5]
    p_values = [0.001, 0.01, 0.3, 0.4, 0.5]

    result = adjust_benjamini_hochberg(p_values)

    rejected_deltas = [delta for delta, keep in zip(deltas, result.rejected, strict=True) if keep]
    assert rejected_deltas == [-0.4, 0.01]
    assert max(deltas) not in rejected_deltas


def test_benjamini_hochberg_never_lowers_a_p_value() -> None:
    raw = list(np.linspace(0.001, 0.9, 25))

    adjusted = adjust_benjamini_hochberg(raw).adjusted_p_values

    assert all(after >= before - 1e-12 for before, after in zip(raw, adjusted, strict=True))


def test_benjamini_hochberg_handles_an_all_undefined_family() -> None:
    result = adjust_benjamini_hochberg([float("nan"), float("nan")], q=0.1)

    assert all(math.isnan(value) for value in result.adjusted_p_values)
    assert result.rejected == [False, False]
