"""Queue operations and scheduling policy expressed through explicit effect ports."""

from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from clearml_yolo.core.queue import (
    GPUControlStatus,
    GPUFreeResult,
    GPUHold,
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
    def held(self) -> set[str]: ...
    def allocated_devices(self, identifier: str) -> tuple[str, ...]: ...
    def start(
        self, job: PublicJob, devices: tuple[str, ...], *, expected_revision: int | None = None
    ) -> bool: ...
    def recover(self, identifier: str) -> PublicJob: ...
    def worker_registration(self) -> AbstractContextManager[None]: ...
    def pause(self, seconds: float) -> None: ...


class QueueGPUControlPort(Protocol):
    def list(self) -> tuple[GPUControlStatus, ...]: ...
    def disable(self, selector: str) -> GPUHold: ...
    def enable(self, selector: str) -> None: ...
    def release(self, selector: str) -> GPUFreeResult: ...


class QueueService:
    """The CLI composes dependencies; this service never discovers infrastructure."""

    def __init__(
        self,
        storage: QueueStorage,
        inventory: QueueInventory,
        processes: QueueProcessPort,
        identity: WorkerIdentity,
        *,
        controls: QueueGPUControlPort | None = None,
    ) -> None:
        self.storage = storage
        self.inventory = inventory
        self.processes = processes
        self.identity = identity
        self.controls = controls

    def gpu_list(self) -> tuple[GPUControlStatus, ...]:
        return self._gpu_controls().list()

    def gpu_disable(self, selector: str) -> GPUHold:
        return self._gpu_controls().disable(selector)

    def gpu_enable(self, selector: str) -> None:
        self._gpu_controls().enable(selector)

    def gpu_release(self, selector: str) -> GPUFreeResult:
        return self._gpu_controls().release(selector)

    def _gpu_controls(self) -> QueueGPUControlPort:
        if self.controls is None:
            raise RuntimeError("GPU controls require an explicitly composed control port")
        return self.controls

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
        held = self.processes.held()
        selected = earliest_runnable(
            view.jobs, (), owners, reserved=reserved, owner_observations=inventories
        )
        jobs: list[PublicJob] = []
        for job in view.jobs:
            if job.state == "pending":
                reason = waiting_reason(
                    job, inventories.get(job.owner_uid, ()), owners, reserved, held
                )
                if reason is None:
                    reason = (
                        "Ready for owner worker admission"
                        if selected is not None and selected.job_id == job.id
                        else "Waiting for an earlier runnable job"
                    )
                jobs.append(job.model_copy(update={"waiting_reason": reason}))
            else:
                jobs.append(self._allocation(job))
        return view.model_copy(update={"jobs": tuple(jobs)})

    def _allocation(self, job: PublicJob) -> PublicJob:
        if job.state in {"starting", "running", "cancelling", "recovery_required"}:
            return job.model_copy(update={"devices": self.processes.allocated_devices(job.id)})
        return job

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
        return self._allocation(self.storage.cancel(job_id))

    def recover(self, job_id: str) -> PublicJob:
        return self._allocation(self.processes.recover(job_id))

    def tick(self) -> int:
        self.processes.refresh()
        view = self.storage.view()
        if not any(job.state == "pending" for job in view.jobs):
            return 0
        try:
            observations = self.inventory.snapshot()
        except (OSError, RuntimeError):
            # Unknown memory never admits work or leaves a stale free observation.
            self.processes.publish_inventory(())
            self.storage.set_waiting(
                {
                    job.id: "GPU memory telemetry unavailable"
                    for job in view.jobs
                    if job.state == "pending" and job.owner_uid == self.identity.owner_uid
                }
            )
            return 0
        self.processes.publish_inventory(observations)
        inventories = self.processes.owner_inventory()
        owners = set(inventories)
        reserved = self.processes.reserved()
        held = self.processes.held()
        self.storage.set_waiting(
            {
                job.id: waiting_reason(
                    job, inventories.get(job.owner_uid, ()), owners, reserved, held
                )
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

    def worker(
        self,
        stop: Callable[[], bool],
        poll_seconds: float = 1,
        *,
        observe: Callable[[QueueView], None] | None = None,
    ) -> None:
        with self.processes.worker_registration():
            if observe is not None:
                observe(self.storage.view())
            while not stop():
                self.tick()
                if observe is not None:
                    observe(self.list())
                self.processes.pause(poll_seconds)
