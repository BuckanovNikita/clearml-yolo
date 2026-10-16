"""Immutable shared-queue records and deterministic whole-device allocation."""

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROTOCOL_VERSION: Literal[1] = 1
QUEUE_COMPATIBILITY = "shared-cy-queue-v1"
JobState = Literal[
    "pending",
    "starting",
    "running",
    "cancelling",
    "completed",
    "failed",
    "cancelled",
    "recovery_required",
]
MoveDirection = Literal["up", "down", "top", "bottom", "before", "after"]
QueueVisibility = Literal["main", "archived", "all"]
TERMINAL_JOB_STATES: frozenset[JobState] = frozenset({"completed", "failed", "cancelled"})


class QueueRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol: Literal[1] = PROTOCOL_VERSION

    @field_validator("protocol", mode="before")
    @classmethod
    def validate_protocol(cls, value: object) -> int:
        if type(value) is not int or value != PROTOCOL_VERSION:
            raise ValueError("Unknown queue record protocol")
        return value


class ResourceRequest(QueueRecord):
    """A count or ordered physical identities, never both."""

    gpus: int | None = Field(default=None, strict=True, gt=0)
    devices: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if self.gpus is None and self.devices is None:
            object.__setattr__(self, "gpus", 1)
        if self.gpus is not None and self.devices is not None:
            raise ValueError("Choose either a GPU count or exact ordered GPU UUIDs")
        if self.devices is not None and (
            not self.devices
            or len(set(self.devices)) != len(self.devices)
            or any(
                not value.startswith("GPU-") or not value.removeprefix("GPU-")
                for value in self.devices
            )
        ):
            raise ValueError("Exact GPU UUIDs must be nonempty, unique whole-GPU identities")
        return self

    @property
    def count(self) -> int:
        return len(self.devices) if self.devices is not None else int(self.gpus or 1)


class JobSnapshot(QueueRecord):
    """Configuration is immutable JSON text, keeping nested mappings immutable too."""

    id: str = ""
    owner_uid: int = Field(default=0, strict=True, ge=0)
    host_id: str = ""
    boot_id: str = ""
    submitted_at: float = 0
    submission_sequence: int = Field(default=0, strict=True, ge=0)
    command: str = Field(min_length=1)
    label: str = ""
    config_json: str
    project_root: str = Field(min_length=1)
    cwd: str = Field(min_length=1)
    interpreter: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    package_identity: str = Field(min_length=1)
    request: ResourceRequest = Field(default_factory=ResourceRequest)

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        value = json.loads(self.config_json)
        if not isinstance(value, dict):
            raise ValueError("A job configuration must be a resolved JSON mapping")  # noqa: TRY004 - Pydantic validation
        return self


class WorkerIdentity(QueueRecord):
    owner_uid: int = Field(strict=True, ge=0)
    host_id: str = Field(min_length=1)
    boot_id: str = Field(min_length=1)


class PublicJob(QueueRecord):
    id: str
    owner_uid: int = Field(strict=True, ge=0)
    host_id: str
    boot_id: str
    command: str
    label: str = ""
    request: ResourceRequest
    submitted_at: float
    submission_sequence: int = Field(default=0, strict=True, ge=0)
    updated_at: float = 0
    snapshot_hash: str = ""
    state: JobState = "pending"
    revision: int = Field(default=0, strict=True, ge=0)
    devices: tuple[str, ...] = ()
    error: str | None = None
    waiting_reason: str | None = None
    progress: str | float | None = None
    clearml_url: str | None = None


class QueueView(QueueRecord):
    host_id: str
    revision: int
    jobs: tuple[PublicJob, ...]
    archived_job_ids: tuple[str, ...] = ()


class ArchiveRecord(QueueRecord):
    """Owner-authored visibility metadata, independent of the executable job record."""

    job_id: str
    owner_uid: int = Field(strict=True, ge=0)
    host_id: str
    archived: bool = Field(strict=True)
    revision: int = Field(strict=True, ge=1)
    updated_at: float


def resolve_job_reference(jobs: Sequence[PublicJob], reference: str) -> PublicJob:
    """Resolve immutable submission numbers or compatible exact internal identifiers."""
    match = re.fullmatch(r"job-([1-9][0-9]*)", reference)
    matches = (
        [job for job in jobs if job.submission_sequence == int(match[1])]
        if match is not None
        else [job for job in jobs if job.id == reference]
    )
    if not matches:
        raise ValueError("Queue job is missing from the local host partition; use job-N from list")
    if len(matches) != 1:
        raise ValueError("Queue job reference is ambiguous; refresh the queue")
    return matches[0]


class GPUObservation(QueueRecord):
    uuid: str
    available: bool
    logical_index: int | None = None


class Allocation(QueueRecord):
    job_id: str
    devices: tuple[str, ...]


class OrderingEvent(QueueRecord):
    revision: int
    owner_uid: int
    host_id: str
    job_id: str
    direction: MoveDirection
    relative_job_id: str | None = None


class GuardianClaim(QueueRecord):
    compatibility: str = QUEUE_COMPATIBILITY
    job_id: str
    owner_uid: int
    host_id: str
    boot_id: str
    queue_root: str
    devices: tuple[str, ...]
    marker: str
    guardian_pid: int
    guardian_born: int
    ownership_since: int = 0
    child_pid: int | None = None
    child_born: int | None = None
    identities: tuple[tuple[int, int], ...] = ()
    # Missing entries represent generation zero for persisted legacy records.
    generations: tuple[tuple[str, int], ...] = ()


def claim_token(claim: GuardianClaim) -> str:
    """Identify one lease, independently of its evolving descendant evidence."""
    payload = claim.model_dump(exclude={"child_pid", "child_born", "identities"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class GPUFreeResult(QueueRecord):
    uuid: str
    actor_uid: int = Field(strict=True, ge=0)
    generation: int = Field(strict=True, ge=1)
    created_at: float


class GPUHold(QueueRecord):
    uuid: str
    owner_uid: int = Field(strict=True, ge=0)
    host_id: str
    reason: str = Field(default="Operator disabled GPU", min_length=1, max_length=2048)
    created_at: float
    generation: int = Field(default=0, strict=True, ge=0)


class GPUControlStatus(QueueRecord):
    uuid: str
    physical_index: int | None = None
    holds: tuple[GPUHold, ...] = ()
    claim: GuardianClaim | None = None


def earliest_runnable(
    jobs: Sequence[PublicJob],
    observations: Sequence[GPUObservation],
    live_owners: AbstractSet[int],
    *,
    reserved: AbstractSet[str] = frozenset(),
    owner_observations: Mapping[int, Sequence[GPUObservation]] | None = None,
) -> Allocation | None:
    """Skip absent workers and requests whose entire allocation does not fit."""
    for job in jobs:
        if job.state != "pending" or job.owner_uid not in live_owners:
            continue
        cards = (
            owner_observations.get(job.owner_uid, ())
            if owner_observations is not None
            else observations
        )
        available = tuple(
            card.uuid for card in cards if card.available and card.uuid not in reserved
        )
        exact = job.request.devices
        if exact is not None:
            if all(uuid in available for uuid in exact):
                return Allocation(job_id=job.id, devices=exact)
        elif len(available) >= job.request.count:
            return Allocation(job_id=job.id, devices=available[: job.request.count])
    return None


def waiting_reason(
    job: PublicJob,
    observations: Sequence[GPUObservation],
    live_owners: AbstractSet[int],
    reserved: AbstractSet[str],
    held: AbstractSet[str] = frozenset(),
) -> str | None:
    if job.owner_uid not in live_owners:
        return "Owner worker unavailable"
    if not observations:
        return "Owner GPU telemetry unavailable"
    available = {card.uuid for card in observations if card.available and card.uuid not in reserved}
    if job.request.devices is not None:
        if not set(job.request.devices).issubset(card.uuid for card in observations):
            return "Requested GPUs are outside the owner worker CUDA visibility"
        if not set(job.request.devices).issubset(available):
            return (
                "Requested GPU allocation is disabled by an operator hold"
                if held & set(job.request.devices)
                else "Waiting for the complete exact GPU allocation"
            )
    elif len(available) < job.request.count:
        return (
            "Waiting for GPU capacity: operator holds disable visible devices"
            if held & {card.uuid for card in observations}
            else (
                f"Waiting for GPU capacity: {job.request.count} requested, "
                f"{len(available)} available"
            )
        )
    return None
