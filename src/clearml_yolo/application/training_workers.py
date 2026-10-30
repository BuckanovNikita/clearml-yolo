"""Serializable native worker contracts; no SDK objects or effect ownership."""

from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.batch_estimation import (
    EstimateCase,
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    TrialStatus,
    estimate_key,
)
from clearml_yolo.core.models import BackendTrainResult, ModelConfig
from clearml_yolo.core.transforms import TransformConfig


class TrainingWorkerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    token: str
    config: ModelConfig
    prepared: PreparedDataset
    output: Path
    world_size: int = Field(gt=0)
    transforms: TransformConfig | None = None


class WorkerScalar(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: float = Field(allow_inf_nan=False)
    step: int


class TrainingWorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    token: str
    rank: int = Field(ge=0)
    status: Literal["success", "oom", "nonfinite", "missing_asset", "error"]
    result: BackendTrainResult | None = None
    diagnostic: str = ""


class BatchProbeRequest(BaseModel):
    """One optimizer path in one fresh group; ranks use LOCAL_RANK/WORLD_SIZE."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    profile: TrainingProfile
    workload: SyntheticWorkload
    settings: SearchSettings
    global_batch: int = Field(gt=0)
    optimizer: str
    output: Path
    config: ModelConfig | None = None


class ProbeRankResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    rank: int = Field(ge=0)
    status: TrialStatus
    actual_global_batch: int | None = None
    peak_memory_bytes: int = Field(default=0, ge=0)
    non_allocator_memory_bytes: int = Field(default=0, ge=0)
    warmup_steps: int = Field(default=0, ge=0)
    measured_steps: int = Field(default=0, ge=0)
    validation_steps: int = Field(default=0, ge=0)
    diagnostic: str = ""


class BatchCaseRequest(BaseModel):
    """One complete search pinned to an identified single GPU by composition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str = Field(min_length=1)
    estimate_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile: TrainingProfile
    workload: SyntheticWorkload
    settings: SearchSettings
    catalogue_path: Path
    output: Path

    @model_validator(mode="after")
    def identified_case(self) -> Self:
        if self.profile.world_size != 1 or not self.profile.gpus[0].uuid:
            raise ValueError("A case requires exactly one identified GPU")
        if self.estimate_key != estimate_key(self.profile, self.workload, self.settings):
            raise ValueError("Case key does not match the requested measurement")
        return self


class BatchCaseResult(BaseModel):
    """A completed search, distinct from an intermediate catalogue snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str = Field(min_length=1)
    estimate_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    case: EstimateCase

    @model_validator(mode="after")
    def matching_evidence(self) -> Self:
        case = self.case
        if self.estimate_key != estimate_key(case.profile, case.workload, case.settings):
            raise ValueError("Receipt key does not match its measurement evidence")
        return self
