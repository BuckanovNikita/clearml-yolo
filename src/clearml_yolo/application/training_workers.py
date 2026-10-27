"""Serializable native worker contracts; no SDK objects or effect ownership."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from clearml_yolo.application.contracts import PreparedDataset
from clearml_yolo.core.batch_estimation import (
    SearchSettings,
    SyntheticWorkload,
    TrainingProfile,
    TrialStatus,
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
