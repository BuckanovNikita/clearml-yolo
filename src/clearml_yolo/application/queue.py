"""Queue operations and scheduling policy expressed through explicit effect ports."""

from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from clearml_yolo.core.queue import (
    GPUObservation,
    JobSnapshot,
    MoveDirection,
    PublicJob,
    QueueView,
    WorkerIdentity,
    earliest_runnable,
    waiting_reason,
)


class QueueStorage(Protocol):
    def submit(self, snapshots: Sequence[JobSnapshot]) -> tuple[PublicJob, ...]: ...
    def view(self, host_id: str | None = None) -> QueueView: ...
    def move(
        self,
        identifier: str,
        direction: MoveDirection,
        expected_revision: int,
        *,
        relative_job_id: str | None = None,
    ) -> QueueView: ...
    def cancel(self, identifier: str) -> PublicJob: ...
    def set_waiting(self, reasons: Mapping[str, str | None]) -> None: ...


class QueueInventory(Protocol):
    def snapshot(self) -> tuple[GPUObservation, ...]: ...


class QueueProcessPort(Protocol):
    def refresh(self) -> None: ...
    def live_owners(self) -> set[int]: ...
    def publish_inventory(self, observations: tuple[GPUObservation, ...]) -> None: ...
    def owner_inventory(self) -> dict[int, tuple[GPUObservation, ...]]: ...
    def reserved(self) -> set[str]: ...
    def start(
        self, job: PublicJob, devices: tuple[str, ...], *, expected_revision: int | None = None
    ) -> bool: ...
    def recover(self, identifier: str) -> PublicJob: ...
    def worker_registration(self) -> AbstractContextManager[None]: ...
    def pause(self, seconds: float) -> None: ...


class QueueService:
    """The CLI composes dependencies; this service never discovers infrastructure."""

    def __init__(
        self,
        storage: QueueStorage,
        inventory: QueueInventory,
        processes: QueueProcessPort,
        identity: WorkerIdentity,
    ) -> None:
        self.storage = storage
        self.inventory = inventory
        self.processes = processes
        self.identity = identity

    def submit(self, snapshots: Sequence[JobSnapshot]) -> tuple[PublicJob, ...]:
        validated = tuple(
            JobSnapshot.model_validate(snapshot.model_dump()) for snapshot in snapshots
        )
        return self.storage.submit(validated)

    def list(self, host_id: str | None = None) -> QueueView:
        if host_id is not None and host_id != self.identity.host_id:
            return self.storage.view(host_id)
        self.processes.refresh()
        view = self.storage.view(host_id)
        inventories = self.processes.owner_inventory()
        owners = set(inventories)
        reserved = self.processes.reserved()
        selected = earliest_runnable(
            view.jobs, (), owners, reserved=reserved, owner_observations=inventories
        )
        jobs: list[PublicJob] = []
        for job in view.jobs:
            if job.state == "pending":
                reason = waiting_reason(job, inventories.get(job.owner_uid, ()), owners, reserved)
                if reason is None:
                    reason = (
                        "Ready for owner worker admission"
                        if selected is not None and selected.job_id == job.id
                        else "Waiting for an earlier runnable job"
                    )
                jobs.append(job.model_copy(update={"waiting_reason": reason}))
            else:
                jobs.append(job)
        return view.model_copy(update={"jobs": tuple(jobs)})

    def move(
        self,
        job_id: str,
        direction: MoveDirection,
        expected_revision: int,
        *,
        relative_job_id: str | None = None,
    ) -> QueueView:
        return self.storage.move(
            job_id, direction, expected_revision, relative_job_id=relative_job_id
        )

    def cancel(self, job_id: str) -> PublicJob:
        return self.storage.cancel(job_id)

    def recover(self, job_id: str) -> PublicJob:
        return self.processes.recover(job_id)

    def tick(self) -> int:
        self.processes.refresh()
        view = self.storage.view()
        if not any(job.state == "pending" for job in view.jobs):
            return 0
        observations = self.inventory.snapshot()
        self.processes.publish_inventory(observations)
        inventories = self.processes.owner_inventory()
        owners = set(inventories)
        reserved = self.processes.reserved()
        self.storage.set_waiting(
            {
                job.id: waiting_reason(job, inventories.get(job.owner_uid, ()), owners, reserved)
                for job in view.jobs
                if job.state == "pending" and job.owner_uid == self.identity.owner_uid
            }
        )
        view = self.storage.view()
        allocation = earliest_runnable(
            view.jobs, observations, owners, reserved=reserved, owner_observations=inventories
        )
        if allocation is None:
            return 0
        job = next(job for job in view.jobs if job.id == allocation.job_id)
        if job.owner_uid != self.identity.owner_uid:
            return 0
        return int(self.processes.start(job, allocation.devices, expected_revision=view.revision))

    def worker(self, stop: Callable[[], bool], poll_seconds: float = 1) -> None:
        with self.processes.worker_registration():
            while not stop():
                self.tick()
                self.processes.pause(poll_seconds)
