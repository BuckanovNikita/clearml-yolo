"""Explicit storage and native execution boundaries for local batch estimation."""

from typing import Protocol

from clearml_yolo.core.batch_estimation import (
    EstimateCase,
    EstimateCatalogue,
    ModelVariant,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    TrialResult,
)


class BatchProbe(Protocol):
    def profile(
        self, model: ModelVariant, imgsz: int, devices: tuple[int, ...]
    ) -> TrainingProfile: ...

    def run(
        self,
        profile: TrainingProfile,
        workload: SyntheticWorkload,
        settings: SearchSettings,
        global_batch: int,
    ) -> TrialResult: ...


class BatchEstimateStore(Protocol):
    def read(self) -> EstimateCatalogue: ...

    def save(self, case: EstimateCase) -> None: ...
