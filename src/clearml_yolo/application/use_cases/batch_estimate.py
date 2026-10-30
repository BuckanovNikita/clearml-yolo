"""Run independent capacity cases through injected probe and persistence ports."""

from collections.abc import Callable

from clearml_yolo.application.batch_ports import BatchEstimateStore, BatchProbe
from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    EstimateCase,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    estimate_key,
)


def _snapshot(
    search: BatchSearch,
    workload: SyntheticWorkload,
    timestamp: str,
    *,
    diagnostic: str | None = None,
) -> EstimateCase:
    pending = search.status == "searching" or diagnostic is not None
    return EstimateCase(
        profile=search.profile,
        workload=workload,
        settings=search.settings,
        status="failed" if pending else search.status,
        global_batch=None if pending else search.global_batch,
        per_gpu_batch=None if pending else search.per_gpu_batch,
        trials=search.trials,
        created_at=timestamp,
        diagnostic=diagnostic
        or (
            "Independent confirmation pending; search may still be running or was interrupted"
            if pending else search.diagnostic
        ),
    )


def _measure(
    profile: TrainingProfile,
    workload: SyntheticWorkload,
    settings: SearchSettings,
    *,
    probe: BatchProbe,
    store: BatchEstimateStore,
    now: Callable[[], str],
    prepare_profile: Callable[[TrainingProfile], TrainingProfile] | None,
) -> EstimateCase:
    search = BatchSearch.start(profile, settings)
    timestamp = now()
    case = _snapshot(search, workload, timestamp)
    # A refresh invalidates the old success before starting work. A killed owner
    # therefore leaves explicit incomplete evidence, never an apparently fresh hit.
    store.save(case)
    try:
        prepared = prepare_profile(profile) if prepare_profile is not None else profile
    except Exception as error:  # noqa: BLE001 - record failed preparation and continue other hardware groups.
        case = _snapshot(search, workload, timestamp, diagnostic=f"{type(error).__name__}: {error}")
        store.save(case)
        return case
    if estimate_key(prepared, workload, settings) != estimate_key(profile, workload, settings):
        raise ValueError("Probe preparation must preserve the measurement profile")
    search = BatchSearch.start(prepared, settings)
    while search.next_batch is not None:
        try:
            trial = probe.run(prepared, workload, settings, search.next_batch)
            search = search.observe(trial)
        except Exception as error:  # noqa: BLE001 - retain and report a failed case, then continue the matrix.
            case = _snapshot(
                search,
                workload,
                timestamp,
                diagnostic=f"{type(error).__name__}: {error}",
            )
            store.save(case)
            return case
        case = _snapshot(search, workload, timestamp)
        store.save(case)
    return case


def estimate_batches(
    profiles: tuple[TrainingProfile, ...],
    workload: SyntheticWorkload,
    settings: SearchSettings,
    *,
    probe: BatchProbe,
    store: BatchEstimateStore,
    now: Callable[[], str],
    refresh: bool = False,
    on_case: Callable[[EstimateCase, bool], None] | None = None,
    prepare_profile: Callable[[TrainingProfile], TrainingProfile] | None = None,
) -> tuple[EstimateCase, ...]:
    """Measure distinct single-GPU cases; reuse completed compatible evidence.

    The observer receives ``cached=True`` for a reused case. Clock, execution,
    persistence and presentation are injected; the application performs no IO.
    Preparation selects an idle representative only for uncached measurements.
    Cancellation propagates after the preceding progress snapshot is persisted.
    """
    if any(profile.world_size != 1 for profile in profiles):
        raise ValueError("Batch estimation searches require exactly one GPU per profile")
    results = []
    seen: set[str] = set()
    for profile in profiles:
        key = estimate_key(profile, workload, settings)
        if key in seen:
            continue
        seen.add(key)
        saved = tuple(
            case
            for case in store.read().cases
            if case.usable and estimate_key(case.profile, case.workload, case.settings) == key
        )
        cached = bool(saved) and not refresh
        case = (
            saved[-1]
            if cached
            else _measure(
                profile,
                workload,
                settings,
                probe=probe,
                store=store,
                now=now,
                prepare_profile=prepare_profile,
            )
        )
        results.append(case)
        if on_case is not None:
            on_case(case, cached)
    return tuple(results)
