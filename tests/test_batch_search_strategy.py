"""Guided candidates retain measured boundaries and historical replay identities."""

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clearml_yolo.adapters.storage.batch_estimates import FileBatchEstimateStore
from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    EstimateCase,
    EstimateCatalogue,
    GPUHardware,
    SearchSettings,
    estimate_key,
)
from test_batch_estimation import _case, _profile, _trial

LEGACY = "exponential_binary_v1"
GUIDED = "memory_guided_v1"
FIXTURES = Path(__file__).parent / "fixtures" / "batch-estimates"
LEGACY_KEYS = {
    1: (
        "5e562005da701de463ae0a52787f8cd77dd2a6c03faab5d943f95a06844e7ff6",
        "8bbcbd17bab9f4b5462a8185a1027f7d07e689214e5ead86d05cdfce34e4388f",
    ),
    2: ("5ea7ab3e9bc4ddec8d8c7682639f2f65103eb627db3b3f479197fdba2572eccd",),
}


def _start(*, budget: int = 900, ceiling: int = 1024, strategy: str = GUIDED) -> BatchSearch:
    profile = _profile().model_copy(
        update={"gpus": (GPUHardware(name="Test GPU", total_memory_bytes=budget),)}
    )
    settings = SearchSettings.model_validate(
        {"memory_fraction": 1, "max_global_batch": ceiling, "search_strategy": strategy}
    )
    return BatchSearch.start(profile, settings)


def _run_curve(
    memory: Callable[[int], int], *, budget: int, ceiling: int = 1024, strategy: str = GUIDED
) -> BatchSearch:
    search = _start(budget=budget, ceiling=ceiling, strategy=strategy)
    for _ in range(ceiling + 2):
        candidate = search.next_batch
        if candidate is None:
            return search
        search = search.observe(_trial(search, peak_memory_bytes=(memory(candidate),)))
    pytest.fail("Search did not terminate within its finite candidate range")


def test_new_calls_default_to_guided_search_and_schema_three() -> None:
    assert SearchSettings().search_strategy == GUIDED
    assert EstimateCatalogue().schema_version == 3


@pytest.mark.parametrize("capacity", [1, 2, 3, 11, 24, 96, 1024])
def test_affine_memory_uses_fewer_full_trials_with_same_confirmed_capacity(capacity: int) -> None:
    def memory(batch: int) -> int:
        return 100 + 10 * batch

    guided = _run_curve(memory, budget=memory(capacity))
    legacy = _run_curve(memory, budget=memory(capacity), strategy=LEGACY)
    assert guided.global_batch == legacy.global_batch == capacity
    assert guided.status == legacy.status
    assert len(guided.trials) <= len(legacy.trials)
    if capacity >= 11:
        assert len(guided.trials) < len(legacy.trials)
    assert [trial.global_batch for trial in guided.trials[:2]] == [1, 2]
    assert guided.trials[-1].global_batch == capacity
    assert any(trial.global_batch == capacity for trial in guided.trials[:-1])
    assert len({trial.trial_id for trial in guided.trials}) == len(guided.trials)
    assert all(trial.warmup_steps == 5 and trial.measured_steps == 10 for trial in guided.trials)
    assert all(trial.validation_steps and trial.optimizer_paths == guided.profile.optimizers
               for trial in guided.trials)
    assert EstimateCase.model_validate_json(_case(guided).model_dump_json()) == _case(guided)


@pytest.mark.parametrize(
    ("memory", "budget"),
    [
        (lambda batch: 100 + batch**2, 1000),
        (lambda batch: 100 + batch * 17 + batch % 3 * 2, 600),
        (lambda batch: 100 + 5 * batch if batch < 16 else 200 + 20 * batch, 900),
    ],
    ids=["quadratic", "rounded", "allocation-step"],
)
def test_nonlinear_memory_still_finds_the_observed_boundary(
    memory: Callable[[int], int], budget: int
) -> None:
    expected = max(batch for batch in range(1, 129) if memory(batch) <= budget)
    result = _run_curve(memory, budget=budget, ceiling=128)
    assert result.global_batch == expected
    assert result.status == "validated"
    assert any(trial.global_batch == expected + 1 for trial in result.trials)
    assert _case(result).usable


@pytest.mark.parametrize("ceiling", [1, 2, 5])
def test_small_ceilings_are_fully_confirmed(ceiling: int) -> None:
    search = _run_curve(lambda batch: 100 + batch, budget=1000, ceiling=ceiling)
    assert search.status == "ceiling_limited"
    assert search.global_batch == ceiling
    assert all(trial.global_batch <= ceiling for trial in search.trials)
    assert search.trials[-1].global_batch == search.trials[-2].global_batch == ceiling


@pytest.mark.parametrize("second_peak", [100, 99])
def test_flat_or_decreasing_memory_growth_falls_back_to_doubling(second_peak: int) -> None:
    search = _start()
    search = search.observe(_trial(search, peak_memory_bytes=(100,)))
    assert search.next_batch == 2
    search = search.observe(_trial(search, peak_memory_bytes=(second_peak,)))
    assert search.next_batch == 4


def test_growth_is_clamped_and_uses_latest_successful_observations() -> None:
    search = _start()
    search = search.observe(_trial(search, peak_memory_bytes=(100,)))
    search = search.observe(_trial(search, peak_memory_bytes=(101,)))
    assert search.next_batch == 8
    search = search.observe(_trial(search, peak_memory_bytes=(701,)))
    assert search.next_batch == 9


def test_exact_budget_prediction_advances_to_observe_an_upper_bound() -> None:
    search = _start()
    search = search.observe(_trial(search, peak_memory_bytes=(899,)))
    search = search.observe(_trial(search, peak_memory_bytes=(900,)))
    assert search.next_batch == 3
    assert search.upper is None
    assert not search.confirming
    search = search.observe(_trial(search, peak_memory_bytes=(901,)))
    assert search.confirming
    assert search.next_batch == 2


@pytest.mark.parametrize("failure", ["oom", "memory_limit"])
def test_capacity_failure_switches_to_exact_binary_refinement(failure: str) -> None:
    search = _start()
    for peak in (200, 300):
        search = search.observe(_trial(search, peak_memory_bytes=(peak,)))
    assert search.next_batch == 8
    search = search.observe(_trial(search, failure))
    assert (search.lower, search.upper, search.next_batch) == (2, 8, 5)
    search = search.observe(_trial(search, peak_memory_bytes=(350,)))
    assert search.next_batch == 6
    search = search.observe(_trial(search, peak_memory_bytes=(351,)))
    assert search.next_batch == 7
    search = search.observe(_trial(search, failure))
    assert search.confirming
    assert search.next_batch == 6
    search = search.observe(_trial(search, peak_memory_bytes=(351,)))
    assert search.status == "validated"
    assert search.global_batch == 6


def test_guided_nonfinite_jump_confirms_only_the_last_success() -> None:
    search = _start()
    for peak in (100, 101):
        search = search.observe(_trial(search, peak_memory_bytes=(peak,)))
    assert search.next_batch == 8
    search = search.observe(_trial(search, "nonfinite", diagnostic="nonfinite validation loss"))
    assert search.next_batch == 2
    assert search.upper is None
    search = search.observe(_trial(search, peak_memory_bytes=(101,)))
    assert search.global_batch == 2
    assert search.status == "numerically_limited"
    assert "batch 8" in search.diagnostic
    assert _case(search).usable


@pytest.mark.parametrize("failure", ["oom", "nonfinite", "timeout"])
def test_guided_confirmation_failure_never_returns_a_recommendation(failure: str) -> None:
    search = _start(ceiling=8)
    for peak in (100, 101, 107):
        search = search.observe(_trial(search, peak_memory_bytes=(peak,)))
    assert search.confirming
    search = search.observe(_trial(search, failure))
    assert search.status == "failed"
    assert search.global_batch is None
    assert not _case(search).usable


@pytest.mark.parametrize("version", [1, 2])
def test_frozen_legacy_catalogues_preserve_keys_and_read_only_bytes(
    tmp_path: Path, version: int
) -> None:
    payload = (FIXTURES / f"legacy-v{version}.json").read_bytes()
    path = tmp_path / "estimates.json"
    path.write_bytes(payload)
    catalogue = FileBatchEstimateStore(path).read()
    assert path.read_bytes() == payload
    assert catalogue.schema_version == version
    assert all(case.settings.search_strategy == LEGACY for case in catalogue.cases)
    assert tuple(estimate_key(case.profile, case.workload, case.settings)
                 for case in catalogue.cases) == LEGACY_KEYS[version]
    if version == 1:
        assert catalogue.cases[1].profile.world_size == 2
        assert catalogue.cases[1].global_batch == 4
    else:
        assert catalogue.cases[0].status == "numerically_limited"


def test_mixed_schema_three_preserves_histories_and_explicit_strategies(tmp_path: Path) -> None:
    path = tmp_path / "estimates.json"
    path.write_bytes((FIXTURES / "legacy-v1.json").read_bytes())
    store = FileBatchEstimateStore(path)
    old = store.read().cases
    new = _case(_run_curve(lambda batch: 100 + batch, budget=200, ceiling=8))
    store.save(new)
    saved = store.read()
    assert saved.schema_version == 3
    assert saved.cases == (*old, new)
    raw = json.loads(path.read_text())
    assert [case["settings"]["search_strategy"] for case in raw["cases"]] == [
        LEGACY, LEGACY, GUIDED,
    ]
    assert tuple(estimate_key(case.profile, case.workload, case.settings)
                 for case in saved.cases[:-1]) == LEGACY_KEYS[1]


def test_legacy_inference_does_not_mutate_supplied_payload() -> None:
    raw = json.loads((FIXTURES / "legacy-v1.json").read_text())["cases"][0]
    before = deepcopy(raw)
    parsed = EstimateCase.model_validate(raw)
    assert parsed.settings.search_strategy == LEGACY
    assert raw == before
    assert SearchSettings.model_validate(raw["settings"]).search_strategy == GUIDED


@pytest.mark.parametrize("version", [1, 2])
def test_old_schema_cannot_claim_a_guided_strategy(version: int) -> None:
    case = _case(_run_curve(lambda batch: 100 + batch, budget=200, ceiling=8))
    with pytest.raises(ValidationError, match="schema 3"):
        EstimateCatalogue.model_validate({"schema_version": version, "cases": [case]})


def test_schema_three_requires_explicit_strategy_and_rejects_unknown_values() -> None:
    raw: dict[str, Any] = json.loads((FIXTURES / "legacy-v1.json").read_text())
    raw["schema_version"] = 3
    with pytest.raises(ValidationError, match="explicit search strategy"):
        EstimateCatalogue.model_validate(raw)
    raw["cases"][0]["settings"]["search_strategy"] = "unrecognized"
    with pytest.raises(ValidationError):
        EstimateCase.model_validate(raw["cases"][0])


def test_relabelled_history_and_fabricated_confirmation_are_rejected() -> None:
    case = _case(_run_curve(lambda batch: 100 + batch, budget=200, ceiling=8))
    raw = case.model_dump(mode="json")
    raw["settings"]["search_strategy"] = LEGACY
    with pytest.raises(ValidationError, match="pending search candidate"):
        EstimateCase.model_validate(raw)
    raw = case.model_dump(mode="json")
    raw["trials"] = raw["trials"][:-1]
    with pytest.raises(ValidationError, match="evidence"):
        EstimateCase.model_validate(raw)
