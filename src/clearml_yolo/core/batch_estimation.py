"""Pure batch capacity search, reproducibility records and strict reuse policy."""

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from clearml_yolo.core.models import PRESETS, BackendName

type PositiveInt = Annotated[int, Field(strict=True, gt=0)]
type NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]
type NonemptyString = Annotated[str, Field(strict=True, min_length=1)]
type Shape = tuple[PositiveInt, PositiveInt]
type TrialStatus = Literal[
    "success",
    "oom",
    "memory_limit",
    "timeout",
    "crash",
    "nonfinite",
    "missing_asset",
    "contaminated",
    "cancelled",
    "error",
]
type UsableStatus = Literal["validated", "ceiling_limited", "numerically_limited"]
type SearchStatus = Literal["searching", "no_capacity", "failed"] | UsableStatus
type SearchStrategy = Literal["exponential_binary_v1", "memory_guided_v1"]

_STRATEGY_SCHEMA_VERSION = 3


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelVariant(_Record):
    selection: NonemptyString
    backend: BackendName
    preset: NonemptyString
    architecture: NonemptyString


def model_catalogue() -> tuple[ModelVariant, ...]:
    """The standard 44 YOLO detection assets plus the maintained native registry."""
    yolo = (
        [f"yolov3{suffix}u" for suffix in ("", "-spp", "-tiny")]
        + [f"yolov5{scale}{resolution}u" for scale in "nsmlx" for resolution in ("", "6")]
        + [f"yolov8{scale}" for scale in "nsmlx"]
        + [f"yolov9{scale}" for scale in "tsmce"]
        + [f"yolov10{scale}" for scale in "nsmblx"]
        + [f"yolo{version}{scale}" for version in ("11", "12", "26") for scale in "nsmlx"]
    )
    variants = [
        ModelVariant(
            selection=f"ultralytics/{stem}",
            backend="ultralytics",
            preset="default",
            architecture=f"{stem}.pt",
        )
        for stem in yolo
    ]
    variants.extend(
        ModelVariant.model_validate(
            {
                "selection": f"{backend}/{preset}",
                "backend": backend,
                "preset": preset,
                "architecture": f"{backend}/{preset}",
            }
        )
        for backend, presets in PRESETS.items()
        if backend != "ultralytics"
        for preset in presets
    )
    return tuple(variants)


def select_models(selections: tuple[str, ...] | None = None) -> tuple[ModelVariant, ...]:
    catalogue = model_catalogue()
    if selections is None:
        return catalogue
    if not selections:
        raise ValueError("Model selection must not be empty")
    lookup = {variant.selection: variant for variant in catalogue}
    for variant in catalogue:
        if variant.backend == "ultralytics":
            lookup[variant.architecture] = variant
            lookup[variant.architecture.removesuffix(".pt")] = variant
    result: list[ModelVariant] = []
    for selection in selections:
        if selection not in lookup:
            raise ValueError(f"Unknown estimator model {selection!r}")
        variant = lookup[selection]
        if variant in result:
            raise ValueError(f"Model selection contains duplicate {variant.selection!r}")
        result.append(variant)
    return tuple(result)


class GPUHardware(_Record):
    name: NonemptyString
    total_memory_bytes: PositiveInt
    uuid: str | None = None


class SyntheticWorkload(_Record):
    classes: PositiveInt = 150
    objects_per_image: PositiveInt = 300


class TrainingProfile(_Record):
    """Resolved memory-relevant recipe, supplied by effect-owning adapters.

    Accumulation records its policy, such as ``fixed:1`` or YOLO's batch-dependent
    nominal-batch rule. Augmentation identifies the complete resolved recipe.
    Hardware UUIDs retain provenance but are excluded from reuse matching.
    """

    model: ModelVariant
    nominal_size: Shape
    effective_size: Shape
    gpus: Annotated[tuple[GPUHardware, ...], Field(min_length=1)]
    dependencies: Annotated[dict[NonemptyString, NonemptyString], Field(min_length=1)]
    precision: NonemptyString
    compilation: StrictBool | NonemptyString
    optimizers: Annotated[tuple[NonemptyString, ...], Field(min_length=1)]
    accumulation: NonemptyString
    ema: StrictBool
    augmentation: NonemptyString
    implementation_revision: NonemptyString

    @model_validator(mode="after")
    def unique_configuration(self) -> Self:
        if len(set(self.optimizers)) != len(self.optimizers):
            raise ValueError("Optimizer paths must be unique")
        identities = [gpu.uuid for gpu in self.gpus if gpu.uuid is not None]
        if len(set(identities)) != len(identities):
            raise ValueError("GPU identities must be unique")
        if any(
            effective < nominal
            for nominal, effective in zip(self.nominal_size, self.effective_size, strict=True)
        ):
            raise ValueError("Effective shape must cover nominal shape")
        return self

    @property
    def world_size(self) -> int:
        return len(self.gpus)

    def compatibility_data(self) -> dict[str, object]:
        values: dict[str, object] = self.model_dump(mode="json", exclude={"gpus"})
        values["gpus"] = [
            {"name": gpu.name, "total_memory_bytes": gpu.total_memory_bytes} for gpu in self.gpus
        ]
        return values


class SearchSettings(_Record):
    search_strategy: SearchStrategy = "memory_guided_v1"
    memory_fraction: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] = 0.9
    max_global_batch: PositiveInt = 1024
    warmup_steps: PositiveInt = 5
    measured_steps: PositiveInt = 10
    trial_timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 300


class TrialResult(_Record):
    """One fresh process group's aggregate evidence across all optimizer paths.

    Peaks contain the maximum for each rank over training and validation, across
    every optimizer path. Step counts are minima across ranks and optimizer paths.
    Only an explicitly confirmed CUDA allocation failure may have status ``oom``.
    """

    global_batch: PositiveInt
    status: TrialStatus
    trial_id: NonemptyString
    actual_global_batch: PositiveInt | None = None
    peak_memory_bytes: tuple[NonnegativeInt, ...] = ()
    warmup_steps: NonnegativeInt = 0
    measured_steps: NonnegativeInt = 0
    validation_steps: NonnegativeInt = 0
    optimizer_paths: tuple[NonemptyString, ...] = ()
    diagnostic: str = ""
    duration_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0


def _trial_observation(
    trial: TrialResult, profile: TrainingProfile, settings: SearchSettings
) -> tuple[TrialStatus, str]:
    if trial.status != "success":
        return trial.status, trial.diagnostic or trial.status
    evidence = {
        "actual batch": trial.actual_global_batch == trial.global_batch,
        "rank memory peaks": len(trial.peak_memory_bytes) == profile.world_size
        and all(peak > 0 for peak in trial.peak_memory_bytes),
        "warmup optimizer steps": trial.warmup_steps >= settings.warmup_steps,
        "measured optimizer steps": trial.measured_steps >= settings.measured_steps,
        "validation": trial.validation_steps > 0,
        "optimizer paths": trial.optimizer_paths == profile.optimizers,
    }
    missing = tuple(name for name, valid in evidence.items() if not valid)
    if missing:
        return "error", "Incomplete trial evidence: " + ", ".join(missing)
    if any(
        peak > int(gpu.total_memory_bytes * settings.memory_fraction)
        for peak, gpu in zip(trial.peak_memory_bytes, profile.gpus, strict=True)
    ):
        return "memory_limit", "A rank exceeded the per-GPU memory budget"
    return "success", trial.diagnostic


class BatchSearch(_Record):
    """Versioned capacity search whose only output is the next measured trial.

    Bounds count images per rank so every candidate divides exactly by world size.
    Successful discovery is followed by a fresh trial at the winner. Numerical
    failure can confirm a smaller candidate, but never implies a capacity boundary.
    """

    profile: TrainingProfile
    settings: SearchSettings
    lower: NonnegativeInt = 0
    upper: PositiveInt | None = None
    next_batch: PositiveInt | None
    confirming: StrictBool = False
    status: SearchStatus = "searching"
    global_batch: PositiveInt | None = None
    per_gpu_batch: PositiveInt | None = None
    trials: tuple[TrialResult, ...] = ()
    diagnostic: str = ""
    numerical_failure: str = ""

    @classmethod
    def start(cls, profile: TrainingProfile, settings: SearchSettings) -> Self:
        if settings.max_global_batch < profile.world_size:
            raise ValueError("Search ceiling must cover at least one image per rank/world size")
        return cls(profile=profile, settings=settings, next_batch=profile.world_size)

    def observe(self, trial: TrialResult) -> Self:
        if self.status != "searching" or trial.global_batch != self.next_batch:
            raise ValueError("Trial batch must match the pending search candidate")
        if any(prior.trial_id == trial.trial_id for prior in self.trials):
            raise ValueError("Every trial must use a fresh process group identity")
        status, diagnostic = _trial_observation(trial, self.profile, self.settings)
        current = self.model_copy(
            update={
                "trials": (*self.trials, trial),
                "diagnostic": diagnostic,
            }
        )
        if self.confirming:
            return BatchSearch._confirmed(current, status, diagnostic)
        if status == "nonfinite" and self.lower > 0:
            return current.model_copy(
                update={
                    "confirming": True,
                    "next_batch": self.lower * self.profile.world_size,
                    "numerical_failure": (
                        f"Numerical failure at global batch {trial.global_batch}: {diagnostic}"
                    ),
                }
            )
        if status not in {"success", "oom", "memory_limit"}:
            return BatchSearch._finish(current, "failed")
        per_rank = trial.global_batch // self.profile.world_size
        if status == "success":
            return BatchSearch._advance(current.model_copy(update={"lower": per_rank}))
        if per_rank == 1:
            return BatchSearch._finish(current, "no_capacity")
        return BatchSearch._advance(current.model_copy(update={"upper": per_rank}))

    def _confirmed(self, status: TrialStatus, diagnostic: str) -> Self:
        cause = f"{self.numerical_failure}; " if self.numerical_failure else ""
        if status != "success":
            return BatchSearch._finish(
                self, "failed", diagnostic=f"{cause}Fresh winner confirmation failed: {diagnostic}"
            )
        batch = self.lower * self.profile.world_size
        if self.numerical_failure:
            return BatchSearch._finish(
                self,
                "numerically_limited",
                batch=batch,
                diagnostic=(
                    f"{cause}independently confirmed global batch {batch}; "
                    "maximum capacity was not determined"
                ),
            )
        ceiling = self.settings.max_global_batch // self.profile.world_size
        return BatchSearch._finish(
            self, "ceiling_limited" if self.lower == ceiling else "validated", batch=batch
        )

    def _finish(
        self, status: SearchStatus, *, batch: int | None = None, diagnostic: str | None = None
    ) -> Self:
        return self.model_copy(
            update={
                "status": status,
                "next_batch": None,
                "global_batch": batch,
                "per_gpu_batch": batch // self.profile.world_size if batch is not None else None,
                "diagnostic": self.diagnostic if diagnostic is None else diagnostic,
            }
        )

    def _advance(self) -> Self:
        ceiling = self.settings.max_global_batch // self.profile.world_size
        if self.lower == ceiling or (self.upper is not None and self.upper - self.lower == 1):
            return self.model_copy(
                update={
                    "confirming": True,
                    "next_batch": self.lower * self.profile.world_size,
                }
            )
        candidate = (
            self._growth_candidate(ceiling)
            if self.upper is None else (self.lower + self.upper) // 2
        )
        return self.model_copy(update={"next_batch": candidate * self.profile.world_size})

    def _growth_candidate(self, ceiling: int) -> int:
        fallback = min(self.lower * 2, ceiling)
        if self.settings.search_strategy == "exponential_binary_v1" or len(self.trials) <= 1:
            return fallback
        # Before any observed upper bound, every completed discovery trial is a
        # fully evidenced under-budget success. Failures either bound or stop it.
        previous, current = self.trials[-2:]
        first = previous.global_batch // self.profile.world_size
        second = current.global_batch // self.profile.world_size
        predictions = []
        for before, after, gpu in zip(
            previous.peak_memory_bytes, current.peak_memory_bytes, self.profile.gpus, strict=True
        ):
            if after <= before:
                return fallback
            budget = int(gpu.total_memory_bytes * self.settings.memory_fraction)
            predictions.append(second + (budget - after) * (second - first) // (after - before))
        return max(self.lower + 1, min(*predictions, 4 * self.lower, ceiling))


class EstimateCase(_Record):
    profile: TrainingProfile
    workload: SyntheticWorkload
    settings: SearchSettings
    status: SearchStatus
    global_batch: PositiveInt | None = None
    per_gpu_batch: PositiveInt | None = None
    trials: tuple[TrialResult, ...] = ()
    created_at: NonemptyString
    diagnostic: str = ""

    @model_validator(mode="before")
    @classmethod
    def historical_search_strategy(cls, value: object) -> object:
        # Only a persisted case gets legacy inference. New direct SearchSettings
        # calls default to guided search; do not mutate a caller's raw history.
        if isinstance(value, dict):
            settings = value.get("settings")
            if isinstance(settings, dict) and "search_strategy" not in settings:
                return value | {
                    "settings": settings | {"search_strategy": "exponential_binary_v1"}
                }
        return value

    @model_validator(mode="after")
    def verified_evidence(self) -> Self:
        if self.status == "searching":
            raise ValueError("Save an interrupted search as failed, never as usable evidence")
        search = BatchSearch.start(self.profile, self.settings)
        for trial in self.trials:
            search = search.observe(trial)
        if self.status == "failed" and self.global_batch is None and self.per_gpu_batch is None:
            # Schema-1 readers accepted a terminal numerical failure without a
            # case diagnostic. Preserve that failed history, never promote it.
            terminal_nonfinite = bool(self.trials) and self.trials[-1].status == "nonfinite"
            if not self.diagnostic and search.status != "failed" and not terminal_nonfinite:
                raise ValueError("Interrupted/failed cases require diagnostic evidence")
            return self
        if (self.status, self.global_batch, self.per_gpu_batch) != (
            search.status,
            search.global_batch,
            search.per_gpu_batch,
        ):
            raise ValueError("Saved estimate does not match independently repeated trial evidence")
        return self

    @property
    def usable(self) -> bool:
        return self.status in {"validated", "ceiling_limited", "numerically_limited"}


class EstimateCatalogue(_Record):
    # Read historical catalogues unchanged; ordinary saves write explicit strategies.
    schema_version: Literal[1, 2, 3] = 3
    cases: tuple[EstimateCase, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def explicit_current_strategies(cls, value: object) -> object:
        if (
            isinstance(value, dict)
            and value.get("schema_version", _STRATEGY_SCHEMA_VERSION) == _STRATEGY_SCHEMA_VERSION
        ):
            cases = value.get("cases", ())
            if isinstance(cases, (list, tuple)):
                for case in cases:
                    if isinstance(case, dict):
                        settings = case.get("settings")
                        if isinstance(settings, dict) and "search_strategy" not in settings:
                            raise ValueError(
                                "Catalogue schema 3 requires an explicit search strategy"
                            )
        return value

    @model_validator(mode="after")
    def legacy_statuses(self) -> Self:
        if self.schema_version == 1 and any(
            case.status == "numerically_limited" for case in self.cases
        ):
            raise ValueError("Numerically limited estimates require catalogue schema 2")
        if self.schema_version < _STRATEGY_SCHEMA_VERSION and any(
            case.settings.search_strategy != "exponential_binary_v1" for case in self.cases
        ):
            raise ValueError("Memory-guided estimates require catalogue schema 3")
        return self


def estimate_key(
    profile: TrainingProfile, workload: SyntheticWorkload, settings: SearchSettings
) -> str:
    """Stable storage key; actual device UUIDs and observation times are provenance."""
    settings_data = settings.model_dump(mode="json")
    if settings.search_strategy == "exponential_binary_v1":
        # Existing source keys are durable provenance, including when old cases
        # are written into a schema-3 catalogue alongside guided measurements.
        settings_data.pop("search_strategy")
    payload = {
        "profile": profile.compatibility_data(),
        "workload": workload.model_dump(mode="json"),
        "settings": settings_data,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def compatibility_issues(
    case: EstimateCase, profile: TrainingProfile, workload: SyntheticWorkload
) -> tuple[str, ...]:
    issues = []
    if not case.usable:
        issues.append(f"estimate status is {case.status}")
    saved, requested = case.profile.compatibility_data(), profile.compatibility_data()
    issues.extend(f"profile {key} differs" for key in saved if saved[key] != requested[key])
    if workload.classes > case.workload.classes:
        issues.append("dataset class count exceeds synthetic bounds")
    if workload.objects_per_image > case.workload.objects_per_image:
        issues.append("dataset object density exceeds synthetic bounds")
    return tuple(issues)


def select_estimate(
    cases: tuple[EstimateCase, ...], profile: TrainingProfile, workload: SyntheticWorkload
) -> EstimateCase:
    compatible = [case for case in cases if not compatibility_issues(case, profile, workload)]
    if not compatible:
        raise ValueError(
            "No compatible validated batch estimate. Run cy-batch-estimate for this model, "
            "resolution, GPU allocation and dataset bounds, or set an explicit training batch."
        )
    # Multiple compatible measurements are conservatively combined; insertion order
    # breaks ties without treating an unvalidated timestamp as ordering evidence.
    return min(compatible, key=lambda case: case.global_batch or 0)


class ResolvedRecommendation(_Record):
    """A target allocation's recommendation, separate from stored trial evidence.

    Sources retain their measured allocation and boundary/ceiling status. An
    extrapolation's status describes its sources, never a measured multi-GPU bound.
    """

    origin: Literal["measured", "extrapolated"]
    profile: TrainingProfile
    global_batch: PositiveInt
    per_gpu_batch: PositiveInt
    sources: Annotated[tuple[EstimateCase, ...], Field(min_length=1)]
    source_estimate_keys: Annotated[tuple[NonemptyString, ...], Field(min_length=1)]
    source_statuses: Annotated[tuple[UsableStatus, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def source_evidence(self) -> Self:
        if self.global_batch != self.per_gpu_batch * self.profile.world_size:
            raise ValueError("Recommended global batch must divide equally across target GPUs")
        if self.source_estimate_keys != tuple(
            estimate_key(source.profile, source.workload, source.settings)
            for source in self.sources
        ) or self.source_statuses != tuple(source.status for source in self.sources):
            raise ValueError("Recommendation keys and statuses must match measured sources")
        if self.origin == "measured":
            source = self.sources[0]
            if (
                len(self.sources) != 1
                or compatibility_issues(source, self.profile, source.workload)
                or self.global_batch != source.global_batch
            ):
                raise ValueError("Measured recommendation requires exact-allocation evidence")
        else:
            target_hardware = {(gpu.name, gpu.total_memory_bytes): gpu for gpu in self.profile.gpus}
            source_hardware = {
                (source.profile.gpus[0].name, source.profile.gpus[0].total_memory_bytes)
                for source in self.sources
            }
            if (
                self.profile.world_size == 1
                or source_hardware != set(target_hardware)
                or len(source_hardware) != len(self.sources)
            ):
                raise ValueError("Extrapolation requires one source per target hardware group")
            for source in self.sources:
                gpu = source.profile.gpus[0]
                target = self.profile.model_copy(
                    update={"gpus": (target_hardware[gpu.name, gpu.total_memory_bytes],)}
                )
                if compatibility_issues(source, target, source.workload):
                    raise ValueError("Extrapolation requires compatible single-GPU sources")
            if self.per_gpu_batch != min(source.per_gpu_batch or 0 for source in self.sources):
                raise ValueError("Extrapolation must use the smallest source per-GPU capacity")
        return self

    @property
    def status(self) -> UsableStatus:
        if "numerically_limited" in self.source_statuses:
            return "numerically_limited"
        return "ceiling_limited" if "ceiling_limited" in self.source_statuses else "validated"


def _recommendation(
    profile: TrainingProfile,
    sources: tuple[EstimateCase, ...],
    origin: Literal["measured", "extrapolated"],
) -> ResolvedRecommendation:
    statuses: list[UsableStatus] = []
    capacities = []
    for source in sources:
        if (
            source.status not in ("validated", "ceiling_limited", "numerically_limited")
            or source.per_gpu_batch is None
        ):
            raise ValueError("A recommendation requires usable measured sources")
        statuses.append(source.status)
        capacities.append(source.per_gpu_batch)
    capacity = min(capacities)
    return ResolvedRecommendation(
        origin=origin,
        profile=profile,
        global_batch=profile.world_size * capacity,
        per_gpu_batch=capacity,
        sources=sources,
        source_estimate_keys=tuple(
            estimate_key(source.profile, source.workload, source.settings) for source in sources
        ),
        source_statuses=tuple(statuses),
    )


def select_recommendation(
    cases: tuple[EstimateCase, ...], profile: TrainingProfile, workload: SyntheticWorkload
) -> ResolvedRecommendation:
    """Prefer exact measured allocations, else scale compatible single-GPU evidence.

    Hardware types and total memory must match. Repeated identical GPUs share one
    source; heterogeneous allocations use the smallest per-GPU capacity uniformly.
    Workload and every nonallocation training-profile input remain compatibility gates.
    """
    exact = tuple(case for case in cases if not compatibility_issues(case, profile, workload))
    if exact:
        return _recommendation(profile, (select_estimate(exact, profile, workload),), "measured")
    sources = []
    seen = set()
    for gpu in profile.gpus:
        hardware = (gpu.name, gpu.total_memory_bytes)
        if hardware in seen:
            continue
        seen.add(hardware)
        single = profile.model_copy(update={"gpus": (gpu,)})
        try:
            sources.append(select_estimate(cases, single, workload))
        except ValueError as error:
            raise ValueError(
                "No compatible validated single-GPU batch estimate for "
                f"{gpu.name} ({gpu.total_memory_bytes} bytes). Run cy-batch-estimate "
                "for each selected GPU type/capacity with this model, training profile "
                "and dataset bounds, or set an explicit training batch."
            ) from error
    return _recommendation(profile, tuple(sources), "extrapolated")
