"""Capacity policy accepts measured, repeatable results rather than optimistic guesses."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    EstimateCase,
    EstimateCatalogue,
    GPUHardware,
    ResolvedRecommendation,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    TrialResult,
    compatibility_issues,
    estimate_key,
    model_catalogue,
    select_estimate,
    select_models,
    select_recommendation,
)
from clearml_yolo.core.models import PRESETS


def _profile(count: int = 1) -> TrainingProfile:
    return TrainingProfile(
        model=select_models(("yolo11n.pt",))[0],
        nominal_size=(960, 960),
        effective_size=(960, 960),
        gpus=tuple(
            GPUHardware(name="Test GPU", total_memory_bytes=1000, uuid=f"GPU-{index}")
            for index in range(count)
        ),
        dependencies={"torch": "2.13", "ultralytics": "8.4.184"},
        precision="fp16",
        compilation=True,
        optimizers=("AdamW", "MuSGD"),
        accumulation="max(round(64/global_batch),1)",
        ema=True,
        augmentation="native-v1",
        implementation_revision="probe-v1",
    )


def _trial(search: BatchSearch, status: str = "success", **updates: Any) -> TrialResult:
    batch = search.next_batch
    assert batch is not None
    values = {
        "global_batch": batch,
        "actual_global_batch": batch,
        "status": status,
        "trial_id": f"group-{len(search.trials)}",
        "peak_memory_bytes": (800,) * search.profile.world_size,
        "warmup_steps": 5,
        "measured_steps": 10,
        "validation_steps": 1,
        "optimizer_paths": search.profile.optimizers,
        "diagnostic": "observed trial",
    }
    return TrialResult.model_validate(values | updates)


def _search(
    capacity: int,
    *,
    count: int = 1,
    ceiling: int = 32,
    profile: TrainingProfile | None = None,
    observe: Callable[[BatchSearch], TrialResult] | None = None,
) -> BatchSearch:
    search = BatchSearch.start(profile or _profile(count), SearchSettings(max_global_batch=ceiling))
    while search.next_batch is not None:
        trial = (
            observe(search)
            if observe is not None
            else _trial(search, "success" if search.next_batch <= capacity else "oom")
        )
        search = search.observe(trial)
    return search


def _case(search: BatchSearch) -> EstimateCase:
    return EstimateCase(
        profile=search.profile,
        workload=SyntheticWorkload(),
        settings=search.settings,
        status=search.status,
        global_batch=search.global_batch,
        per_gpu_batch=search.per_gpu_batch,
        trials=search.trials,
        created_at="2026-10-26T10:00:00Z",
        diagnostic=search.diagnostic,
    )


def test_catalogue_has_standard_yolo_and_every_native_preset() -> None:
    variants = model_catalogue()
    yolo = [variant for variant in variants if variant.backend == "ultralytics"]
    assert len(yolo) == 44
    assert len({variant.selection for variant in variants}) == len(variants)
    assert {variant.architecture for variant in yolo} >= {
        "yolov3-sppu.pt",
        "yolov5x6u.pt",
        "yolov9e.pt",
        "yolov10b.pt",
        "yolo26x.pt",
    }
    assert {variant.selection for variant in variants if variant.backend != "ultralytics"} == {
        f"{backend}/{preset}"
        for backend, presets in PRESETS.items()
        if backend != "ultralytics"
        for preset in presets
    }
    assert select_models(("yolo11n",)) == select_models(("ultralytics/yolo11n",))
    assert select_models(None) == variants


@pytest.mark.parametrize("selection", [("missing",), (), ("yolo11n", "yolo11n.pt")])
def test_invalid_or_repeated_selections_fail(selection: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match=r"Unknown|empty|duplicate"):
        select_models(selection)


@pytest.mark.parametrize("count", [1, 2, 3, 4])
@pytest.mark.parametrize("capacity", [0, 1, 3, 5, 11, 16, 31, 32, 99])
def test_search_finds_divisible_capacity_and_independently_confirms(
    count: int, capacity: int
) -> None:
    search = _search(capacity, count=count)
    expected = min(capacity, 32) // count * count
    assert all(trial.global_batch % count == 0 for trial in search.trials)
    if expected == 0:
        assert search.status == "no_capacity"
        assert search.global_batch is None
    else:
        assert search.global_batch == expected
        assert search.per_gpu_batch == expected // count
        assert search.status == (
            "ceiling_limited" if expected == 32 // count * count else "validated"
        )
        assert search.trials[-1].global_batch == search.trials[-2].global_batch or any(
            trial.status == "success" and trial.global_batch == expected
            for trial in search.trials[:-1]
        )
        assert search.trials[-1].trial_id not in {trial.trial_id for trial in search.trials[:-1]}
        assert _case(search).usable


@pytest.mark.parametrize(
    "failure",
    ["timeout", "crash", "missing_asset", "contaminated", "cancelled", "error"],
)
def test_noncapacity_failures_do_not_become_capacity_bounds(failure: str) -> None:
    search = BatchSearch.start(_profile(), SearchSettings())
    search = search.observe(_trial(search))
    search = search.observe(_trial(search, failure))
    assert search.status == "failed"
    assert search.next_batch is None
    assert search.global_batch is None
    assert not _case(search).usable


@pytest.mark.parametrize("failure", ["oom", "memory_limit", "timeout", "nonfinite"])
def test_failed_fresh_repeat_invalidates_entire_estimate(failure: str) -> None:
    search = _search(
        2,
        observe=lambda state: _trial(
            state,
            failure if state.confirming else "success" if (state.next_batch or 0) <= 2 else "oom",
        ),
    )
    assert search.status == "failed"
    assert search.global_batch is None


@pytest.mark.parametrize(
    "updates",
    [
        {"actual_global_batch": 1},
        {"actual_global_batch": None},
        {"warmup_steps": 4},
        {"measured_steps": 9},
        {"validation_steps": 0},
        {"optimizer_paths": ("AdamW",)},
        {"peak_memory_bytes": (800,)},
        {"peak_memory_bytes": (800, 0)},
    ],
)
def test_incomplete_success_evidence_fails(updates: dict[str, Any]) -> None:
    search = BatchSearch.start(_profile(2), SearchSettings())
    search = search.observe(_trial(search, **updates))
    assert search.status == "failed"


def test_memory_budget_is_per_rank_and_inclusive() -> None:
    search = BatchSearch.start(_profile(2), SearchSettings())
    search = search.observe(_trial(search, peak_memory_bytes=(900, 900)))
    assert search.next_batch == 4
    search = search.observe(_trial(search, peak_memory_bytes=(901, 800)))
    assert search.confirming
    assert search.next_batch == 2


def test_exponential_growth_refines_the_boundary_before_repeating() -> None:
    search = _search(11)
    assert [trial.global_batch for trial in search.trials] == [1, 2, 4, 8, 16, 12, 10, 11, 11]


def test_heterogeneous_memory_and_order_are_checked_per_rank() -> None:
    profile = _profile(2).model_copy(
        update={
            "gpus": (
                GPUHardware(name="Large", total_memory_bytes=2000),
                GPUHardware(name="Small", total_memory_bytes=1000),
            )
        }
    )
    search = BatchSearch.start(profile, SearchSettings(max_global_batch=2))
    search = search.observe(_trial(search, peak_memory_bytes=(1800, 900)))
    search = search.observe(_trial(search, peak_memory_bytes=(1800, 900)))
    case = _case(search)
    swapped = profile.model_copy(update={"gpus": tuple(reversed(profile.gpus))})
    assert compatibility_issues(case, swapped, SyntheticWorkload())
    over = BatchSearch.start(profile, SearchSettings())
    over = over.observe(_trial(over, peak_memory_bytes=(1700, 901)))
    assert over.status == "no_capacity"


def test_trial_identity_and_candidate_are_checked() -> None:
    search = BatchSearch.start(_profile(), SearchSettings())
    with pytest.raises(ValueError, match="candidate"):
        search.observe(_trial(search, global_batch=2))
    prior = _trial(search)
    search = search.observe(prior)
    with pytest.raises(ValueError, match="fresh"):
        search.observe(_trial(search, trial_id=prior.trial_id))


@pytest.mark.parametrize(
    "changes",
    [
        {"nominal_size": (800, 800)},
        {"effective_size": (1024, 1024)},
        {"dependencies": {"torch": "different"}},
        {"precision": "bf16"},
        {"compilation": False},
        {"optimizers": ("AdamW",)},
        {"accumulation": "fixed:2"},
        {"ema": False},
        {"augmentation": "custom"},
        {"implementation_revision": "probe-v2"},
    ],
)
def test_profile_changes_are_incompatible(changes: dict[str, Any]) -> None:
    case = _case(_search(4))
    requested = TrainingProfile.model_validate(case.profile.model_dump() | changes)
    assert compatibility_issues(case, requested, SyntheticWorkload())


def test_hardware_compatibility_uses_ordered_capabilities_not_uuid() -> None:
    case = _case(_search(4))
    same = case.profile.model_copy(
        update={
            "gpus": (GPUHardware(name="Test GPU", total_memory_bytes=1000, uuid="replacement"),)
        }
    )
    assert not compatibility_issues(case, same, SyntheticWorkload())
    different = same.model_copy(
        update={"gpus": (GPUHardware(name="Test GPU", total_memory_bytes=2000),)}
    )
    assert compatibility_issues(case, different, SyntheticWorkload())
    assert compatibility_issues(case, _profile(2), SyntheticWorkload())


def test_density_and_class_bounds_are_upper_limits() -> None:
    case = _case(_search(4))
    assert not compatibility_issues(
        case, case.profile, SyntheticWorkload(classes=1, objects_per_image=1)
    )
    assert compatibility_issues(case, case.profile, SyntheticWorkload(classes=151))
    assert compatibility_issues(case, case.profile, SyntheticWorkload(objects_per_image=301))
    assert select_estimate((case,), case.profile, SyntheticWorkload()) == case
    with pytest.raises(ValueError, match="cy-batch-estimate"):
        select_estimate((_case(_search(0)),), case.profile, SyntheticWorkload())


def test_saved_success_requires_valid_search_evidence() -> None:
    case = _case(_search(4))
    values = case.model_dump()
    values["trials"] = values["trials"][:-1]
    with pytest.raises(ValidationError, match="evidence"):
        EstimateCase.model_validate(values)
    values = case.model_dump() | {"global_batch": 8, "per_gpu_batch": 8}
    with pytest.raises(ValidationError, match="evidence"):
        EstimateCase.model_validate(values)
    catalogue = EstimateCatalogue(cases=(case,))
    assert EstimateCatalogue.model_validate_json(catalogue.model_dump_json()) == catalogue


def test_case_key_is_stable_and_includes_workload_and_search_policy() -> None:
    case = _case(_search(4))
    key = estimate_key(case.profile, case.workload, case.settings)
    assert key == estimate_key(case.profile, case.workload, case.settings)
    assert key != estimate_key(case.profile, SyntheticWorkload(classes=151), case.settings)
    assert key != estimate_key(case.profile, case.workload, SearchSettings(memory_fraction=0.8))


@pytest.mark.parametrize("values", [{"classes": 0}, {"objects_per_image": True}])
def test_workload_rejects_invalid_bounds(values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SyntheticWorkload.model_validate(values)


def test_ceiling_below_world_size_is_invalid() -> None:
    with pytest.raises(ValueError, match="world size"):
        BatchSearch.start(_profile(4), SearchSettings(max_global_batch=3))


def test_recommendation_retains_target_and_actual_source_provenance() -> None:
    case = _case(_search(5))
    target = case.profile.model_copy(
        update={"gpus": (case.profile.gpus[0].model_copy(update={"uuid": "assigned-gpu"}),)}
    )
    recommendation = select_recommendation((case,), target, SyntheticWorkload())
    assert recommendation.origin == "measured"
    assert recommendation.profile == target
    assert recommendation.global_batch == recommendation.per_gpu_batch == 5
    assert recommendation.source_estimate_keys == (
        estimate_key(case.profile, case.workload, case.settings),
    )
    assert recommendation.source_statuses == ("validated",)
    assert recommendation.sources == (case,)


def test_identical_gpus_share_one_source_and_exceed_the_per_gpu_ceiling() -> None:
    source = _case(_search(99, ceiling=5))
    saved = source.model_dump_json()
    target = _profile(3)
    recommendation = select_recommendation((source,), target, SyntheticWorkload())
    assert recommendation.origin == "extrapolated"
    assert recommendation.global_batch == 15
    assert recommendation.per_gpu_batch == 5
    assert recommendation.global_batch % target.world_size == 0
    assert recommendation.status == "ceiling_limited"
    assert recommendation.source_statuses == ("ceiling_limited",)
    assert recommendation.sources == (source,)
    assert source.model_dump_json() == saved


def test_mixed_gpus_use_the_smallest_compatible_single_gpu_capacity() -> None:
    larger_gpu = GPUHardware(name="Different GPU", total_memory_bytes=2000, uuid="different")
    fast_profile = _profile().model_copy(update={"gpus": (larger_gpu,)})
    slower, faster = _case(_search(3)), _case(_search(99, profile=fast_profile, ceiling=8))
    target = _profile(2).model_copy(update={"gpus": (*_profile(2).gpus, larger_gpu)})
    recommendation = select_recommendation((faster, slower), target, SyntheticWorkload())
    assert recommendation.origin == "extrapolated"
    assert recommendation.global_batch == 9
    assert recommendation.per_gpu_batch == 3
    assert recommendation.sources == (slower, faster)
    assert recommendation.source_statuses == ("validated", "ceiling_limited")
    assert recommendation.status == "ceiling_limited"
    assert recommendation.profile == target


@pytest.mark.parametrize(
    "hardware",
    [
        GPUHardware(name="Unmeasured", total_memory_bytes=1000),
        GPUHardware(name="Test GPU", total_memory_bytes=2000),
    ],
)
def test_extrapolation_requires_each_gpu_type_and_capacity(hardware: GPUHardware) -> None:
    source = _case(_search(5))
    target = _profile().model_copy(update={"gpus": (*source.profile.gpus, hardware)})
    with pytest.raises(ValueError, match=r"compatible.*single-GPU"):
        select_recommendation((source,), target, SyntheticWorkload())


@pytest.mark.parametrize("invalid", ["failed", "no_capacity", "stale", "classes", "density"])
def test_invalid_sources_never_support_extrapolation(invalid: str) -> None:
    source = _case(_search(5))
    target, workload = _profile(2), SyntheticWorkload()
    if invalid == "failed":
        source = _case(_search(5, observe=lambda search: _trial(search, "timeout")))
    elif invalid == "no_capacity":
        source = _case(_search(0))
    elif invalid == "stale":
        target = target.model_copy(update={"implementation_revision": "new-probe"})
    elif invalid == "classes":
        workload = SyntheticWorkload(classes=151)
    else:
        workload = SyntheticWorkload(objects_per_image=301)
    with pytest.raises(ValueError, match=r"compatible.*single-GPU"):
        select_recommendation((source,), target, workload)


def test_legacy_exact_allocation_measurement_precedes_extrapolation() -> None:
    single, exact = _case(_search(5)), _case(_search(6, count=2))
    restored = EstimateCatalogue.model_validate_json(
        EstimateCatalogue(cases=(single, exact)).model_dump_json()
    )
    recommendation = select_recommendation(restored.cases, _profile(2), SyntheticWorkload())
    assert recommendation.origin == "measured"
    assert recommendation.global_batch == 6
    assert recommendation.sources == (exact,)


def test_multiple_compatible_single_gpu_measurements_are_conservative() -> None:
    larger, smaller = _case(_search(5)), _case(_search(3, ceiling=16))
    recommendation = select_recommendation((larger, smaller), _profile(2), SyntheticWorkload())
    assert recommendation.global_batch == 6
    assert recommendation.sources == (smaller,)


@pytest.mark.parametrize(
    "updates",
    [
        {"global_batch": 9},
        {"source_estimate_keys": ("invented",)},
        {"source_statuses": ("ceiling_limited",)},
        {"origin": "measured"},
        {"per_gpu_batch": 3, "global_batch": 6},
    ],
)
def test_recommendation_rejects_inconsistent_allocation_and_evidence(
    updates: dict[str, Any],
) -> None:
    source = _case(_search(5))
    recommendation = select_recommendation((source,), _profile(2), SyntheticWorkload())
    with pytest.raises(ValidationError):
        ResolvedRecommendation.model_validate(recommendation.model_dump() | updates)


def test_recommendation_serialization_preserves_sources_without_inventing_trials() -> None:
    source = _case(_search(5))
    recommendation = select_recommendation((source,), _profile(2), SyntheticWorkload())
    restored = ResolvedRecommendation.model_validate_json(recommendation.model_dump_json())
    assert restored == recommendation
    assert restored.sources[0].trials == source.trials
