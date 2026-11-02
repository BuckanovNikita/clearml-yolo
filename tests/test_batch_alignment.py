"""Automatic search uses an aligned grid without relabelling historical evidence."""

import pytest

from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    EstimateCase,
    SearchSettings,
    SyntheticWorkload,
    compatibility_issues,
    estimate_key,
    select_recommendation,
)
from test_batch_estimation import _case, _profile, _trial

ALIGNED = "memory_guided_aligned_v1"


def _aligned(capacity: int, *, count: int = 1, ceiling: int = 128) -> BatchSearch:
    search = BatchSearch.start(_profile(count), SearchSettings(max_global_batch=ceiling))
    for _ in range(100):
        if search.next_batch is None:
            return search
        status = "success" if search.next_batch <= capacity else "oom"
        search = search.observe(_trial(search, status))
    pytest.fail("Aligned search did not terminate")


def test_default_search_starts_at_eight_per_gpu() -> None:
    search = BatchSearch.start(_profile(), SearchSettings())
    assert search.next_batch == 8
    assert search.settings.search_strategy == ALIGNED


@pytest.mark.parametrize("count", [1, 2, 3, 4])
@pytest.mark.parametrize("capacity", [0, 7, 8, 11, 15, 16, 23, 24, 31, 64, 127, 256])
@pytest.mark.parametrize("ceiling", [32, 99, 128])
def test_all_trials_and_confirmed_capacity_follow_the_per_gpu_grid(
    count: int,
    capacity: int,
    ceiling: int,
) -> None:
    search = _aligned(capacity, count=count, ceiling=ceiling)
    quantum = 8 * count
    expected = min(capacity, ceiling) // quantum * quantum
    assert all(trial.global_batch % quantum == 0 for trial in search.trials)
    assert all(trial.global_batch <= ceiling for trial in search.trials)
    if expected == 0:
        assert search.status == "no_capacity"
        assert search.global_batch is None
    else:
        assert search.global_batch == expected
        assert search.per_gpu_batch == expected // count
        assert search.status == (
            "ceiling_limited" if expected == ceiling // quantum * quantum else "validated"
        )
        assert search.trials[-1].global_batch == expected
        assert any(
            trial.global_batch == expected and trial.status == "success"
            for trial in search.trials[:-1]
        )
        assert len({trial.trial_id for trial in search.trials}) == len(search.trials)
        case = _case(search)
        assert EstimateCase.model_validate_json(case.model_dump_json()) == case


@pytest.mark.parametrize(("count", "ceiling"), [(1, 7), (2, 15), (3, 23)])
def test_ceiling_must_cover_eight_per_gpu(count: int, ceiling: int) -> None:
    with pytest.raises(ValueError, match=r"eight|8"):
        BatchSearch.start(_profile(count), SearchSettings(max_global_batch=ceiling))


def test_guided_prediction_and_binary_refinement_stay_aligned() -> None:
    search = BatchSearch.start(_profile(), SearchSettings(max_global_batch=99))
    for peak in (200, 300):
        search = search.observe(_trial(search, peak_memory_bytes=(peak,)))
    assert search.next_batch == 64
    search = search.observe(_trial(search, "oom"))
    assert search.next_batch == 40
    search = search.observe(_trial(search, "oom"))
    assert search.next_batch == 24
    search = search.observe(_trial(search))
    assert search.next_batch == 32
    search = search.observe(_trial(search, "oom"))
    assert search.confirming
    assert search.next_batch == 24
    search = search.observe(_trial(search))
    assert search.global_batch == 24
    assert search.status == "validated"


def test_numerical_failure_confirms_only_prior_aligned_success() -> None:
    search = BatchSearch.start(_profile(), SearchSettings())
    search = search.observe(_trial(search))
    search = search.observe(_trial(search, "nonfinite"))
    assert search.confirming
    assert search.next_batch == 8
    search = search.observe(_trial(search))
    assert search.status == "numerically_limited"
    assert search.global_batch == 8
    assert _case(search).usable


@pytest.mark.parametrize("failure", ["oom", "memory_limit", "nonfinite", "timeout"])
def test_failed_aligned_confirmation_remains_unusable(failure: str) -> None:
    search = BatchSearch.start(_profile(), SearchSettings(max_global_batch=8))
    search = search.observe(_trial(search))
    search = search.observe(_trial(search, failure))
    assert search.status == "failed"
    assert search.global_batch is None


@pytest.mark.parametrize("strategy", ["exponential_binary_v1", "memory_guided_v1"])
def test_unaligned_history_replays_but_cannot_supply_automatic_lookup(strategy: str) -> None:
    settings = SearchSettings.model_validate({"search_strategy": strategy, "max_global_batch": 11})
    search = BatchSearch.start(_profile(), settings)
    while search.next_batch is not None:
        search = search.observe(_trial(search))
    case = _case(search)
    raw, key = case.model_dump_json(), estimate_key(case.profile, case.workload, case.settings)
    assert EstimateCase.model_validate_json(raw) == case
    assert case.global_batch == 11
    assert case.usable
    assert any(
        "eight" in issue or "8" in issue
        for issue in compatibility_issues(case, case.profile, SyntheticWorkload())
    )
    with pytest.raises(ValueError, match="cy-batch-estimate"):
        select_recommendation((case,), case.profile, SyntheticWorkload())
    assert case.model_dump_json() == raw
    assert estimate_key(case.profile, case.workload, case.settings) == key
