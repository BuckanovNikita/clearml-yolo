"""The estimator coordinates explicit ports and preserves resumable evidence."""

from typing import Any, override

import pytest

from clearml_yolo.application.use_cases.batch_estimate import estimate_batches
from clearml_yolo.core.batch_estimation import (
    BatchSearch,
    EstimateCase,
    EstimateCatalogue,
    GPUHardware,
    ModelVariant,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    TrialResult,
    estimate_key,
    select_models,
)


def sample_profile(count: int = 1) -> TrainingProfile:
    return TrainingProfile(
        model=select_models(("yolo11n",))[0],
        nominal_size=(960, 960),
        effective_size=(960, 960),
        gpus=tuple(GPUHardware(name="GPU", total_memory_bytes=1000) for _ in range(count)),
        dependencies={"torch": "test"},
        precision="fp16",
        compilation=True,
        optimizers=("AdamW", "MuSGD"),
        accumulation="fixed:1",
        ema=True,
        augmentation="native",
        implementation_revision="probe-v1",
    )


class MemoryStore:
    def __init__(self) -> None:
        self.cases: dict[str, EstimateCase] = {}
        self.writes: list[EstimateCase] = []

    def read(self) -> EstimateCatalogue:
        return EstimateCatalogue(cases=tuple(self.cases.values()))

    def save(self, case: EstimateCase) -> None:
        self.cases[estimate_key(case.profile, case.workload, case.settings)] = case
        self.writes.append(case)


class RecordingProbe:
    def __init__(self, *, capacity: int = 4) -> None:
        self.calls = 0
        self.capacity = capacity
        self.probed_profiles: list[TrainingProfile] = []

    def profile(self, model: ModelVariant, imgsz: int, devices: tuple[int, ...]) -> TrainingProfile:
        return sample_profile(len(devices)).model_copy(
            update={
                "model": model,
                "nominal_size": (imgsz, imgsz),
                "effective_size": (imgsz, imgsz),
            }
        )

    def run(
        self,
        profile: TrainingProfile,
        workload: SyntheticWorkload,
        settings: SearchSettings,
        global_batch: int,
    ) -> TrialResult:
        self.calls += 1
        self.probed_profiles.append(profile)
        return TrialResult(
            global_batch=global_batch,
            actual_global_batch=global_batch,
            status="success" if global_batch <= self.capacity else "oom",
            trial_id=f"group-{self.calls}",
            peak_memory_bytes=(800,) * profile.world_size,
            warmup_steps=settings.warmup_steps,
            measured_steps=settings.measured_steps,
            validation_steps=1,
            optimizer_paths=profile.optimizers,
        )


def sample_case(count: int = 1) -> EstimateCase:
    if count != 1:
        # Retain legacy distributed evidence without invoking today's estimator.
        profile, settings, workload = (
            sample_profile(count),
            SearchSettings(max_global_batch=8),
            SyntheticWorkload(),
        )
        probe = RecordingProbe()
        search = BatchSearch.start(profile, settings)
        while search.next_batch is not None:
            search = search.observe(probe.run(profile, workload, settings, search.next_batch))
        return EstimateCase(
            profile=profile,
            settings=settings,
            workload=workload,
            status=search.status,
            global_batch=search.global_batch,
            per_gpu_batch=search.per_gpu_batch,
            trials=search.trials,
            created_at="2026-10-26T12:00:00Z",
        )
    return estimate_batches(
        (sample_profile(count),),
        SyntheticWorkload(),
        SearchSettings(max_global_batch=8),
        probe=RecordingProbe(),
        store=MemoryStore(),
        now=lambda: "2026-10-26T12:00:00Z",
    )[0]


def test_completed_case_is_reused_and_refresh_repeats_trials() -> None:
    store, probe = MemoryStore(), RecordingProbe()
    profiles, workload, settings = (sample_profile(),), SyntheticWorkload(), SearchSettings()
    first = estimate_batches(
        profiles, workload, settings, probe=probe, store=store, now=lambda: "2026-10-26T12:00:00Z"
    )
    calls, writes = probe.calls, len(store.writes)
    assert first[0].global_batch == 4
    assert all(not case.usable for case in store.writes[:-1])
    assert (
        estimate_batches(
            profiles,
            workload,
            settings,
            probe=probe,
            store=store,
            now=lambda: "2026-10-26T12:00:00Z",
        )
        == first
    )
    assert (probe.calls, len(store.writes)) == (calls, writes)
    estimate_batches(
        profiles,
        workload,
        settings,
        refresh=True,
        probe=probe,
        store=store,
        now=lambda: "2026-10-26T12:00:00Z",
    )
    assert probe.calls == calls * 2


def test_stale_or_failed_entries_are_reprobed() -> None:
    store, probe = MemoryStore(), RecordingProbe()
    previous = sample_case()
    store.save(
        previous.model_copy(
            update={
                "status": "failed",
                "global_batch": None,
                "per_gpu_batch": None,
                "trials": (),
                "diagnostic": "interrupted",
            }
        )
    )
    result = estimate_batches(
        (previous.profile,),
        previous.workload,
        previous.settings,
        probe=probe,
        store=store,
        now=lambda: "now",
    )
    assert result[0].usable
    assert probe.calls > 0


def test_interruption_leaves_failed_progress_and_completed_peer_cases() -> None:
    store = MemoryStore()
    prior = sample_case(2)
    store.save(prior)

    class InterruptedProbe(RecordingProbe):
        @override
        def run(self, *args: Any, **kwargs: Any) -> TrialResult:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        estimate_batches(
            (sample_profile(),),
            SyntheticWorkload(),
            SearchSettings(),
            probe=InterruptedProbe(),
            store=store,
            now=lambda: "now",
        )
    assert store.read().cases[0] == prior
    assert store.read().cases[-1].status == "failed"
    assert not store.read().cases[-1].usable


def test_probe_error_is_visible_and_next_profile_still_runs() -> None:
    store = MemoryStore()

    class FailingProbe(RecordingProbe):
        @override
        def run(self, profile: TrainingProfile, *args: Any, **kwargs: Any) -> TrialResult:
            if profile.model == sample_profile().model:
                raise RuntimeError("asset download failed")
            return super().run(profile, *args, **kwargs)

    reports = []
    result = estimate_batches(
        (
            sample_profile(),
            sample_profile().model_copy(update={"model": select_models(("yolo11s",))[0]}),
        ),
        SyntheticWorkload(),
        SearchSettings(),
        probe=FailingProbe(),
        store=store,
        now=lambda: "now",
        on_case=lambda case, cached: reports.append((case.status, cached)),
    )
    assert result[0].status == "failed"
    assert "asset download failed" in result[0].diagnostic
    assert result[1].usable
    assert reports == [("failed", False), ("validated", False)]


def test_duplicate_hardware_profiles_measure_once_even_during_refresh() -> None:
    store, probe = MemoryStore(), RecordingProbe()
    profile = sample_profile()
    other = profile.model_copy(
        update={"gpus": (profile.gpus[0].model_copy(update={"uuid": "GPU-other"}),)}
    )
    results = estimate_batches(
        (profile, other),
        SyntheticWorkload(),
        SearchSettings(),
        probe=probe,
        store=store,
        now=lambda: "now",
        refresh=True,
    )
    assert len(results) == 1
    assert len({case.trial_id for case in results[0].trials}) == probe.calls
    assert all(item.world_size == 1 for item in probe.probed_profiles)


def test_multi_gpu_search_is_rejected_before_any_effects() -> None:
    store, probe = MemoryStore(), RecordingProbe()
    with pytest.raises(ValueError, match="exactly one GPU"):
        estimate_batches(
            (sample_profile(), sample_profile(2)),
            SyntheticWorkload(),
            SearchSettings(),
            probe=probe,
            store=store,
            now=lambda: "now",
        )
    assert probe.calls == 0
    assert not store.writes


def test_cached_measurement_does_not_require_idle_preparation() -> None:
    case = sample_case()
    store = MemoryStore()
    store.save(case)
    results = estimate_batches(
        (case.profile,),
        case.workload,
        case.settings,
        probe=RecordingProbe(),
        store=store,
        now=lambda: "now",
        prepare_profile=lambda _: pytest.fail("cached evidence needs no GPU"),
    )
    assert results == (case,)


def test_refresh_invalidates_saved_success_when_idle_preparation_fails() -> None:
    case = sample_case()
    store, probe = MemoryStore(), RecordingProbe()
    store.save(case)

    def busy(_: TrainingProfile) -> TrainingProfile:
        raise RuntimeError("GPU busy")

    (result,) = estimate_batches(
        (case.profile,),
        case.workload,
        case.settings,
        probe=probe,
        store=store,
        now=lambda: "now",
        refresh=True,
        prepare_profile=busy,
    )
    assert result.status == "failed"
    assert "GPU busy" in result.diagnostic
    assert not any(saved.usable for saved in store.read().cases)
    assert probe.calls == 0
