"""Validated private guardian transport and public worker liveness records."""

from pydantic import BaseModel, ConfigDict

from clearml_yolo.core.queue import QUEUE_COMPATIBILITY, GPUObservation, QueueRecord, WorkerIdentity


class GuardianPayload(QueueRecord):
    job_id: str
    identity: WorkerIdentity
    queue_root: str
    local_root: str | None = None
    devices: tuple[str, ...]
    marker: str
    ownership_since: int
    argv: tuple[str, ...]
    snapshot_path: str
    cwd: str
    project_root: str
    start_gate: str


class WorkerRecord(QueueRecord):
    compatibility: str = QUEUE_COMPATIBILITY
    identity: WorkerIdentity
    pid: int
    born: int
    heartbeat: float
    observations: tuple[GPUObservation, ...] = ()


class ChildStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    task_url: str | None = None
    progress: str | float | None = None
    iteration: int | None = None
