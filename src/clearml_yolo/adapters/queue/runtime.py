"""Persistent owner workers launch independent guardians through explicit argv."""

import fcntl
import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from clearml_yolo.adapters.queue.guardian import cleanup_tree
from clearml_yolo.adapters.queue.identity import process_birth, process_ticks
from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.adapters.queue.records import ChildStatus, GuardianPayload, WorkerRecord
from clearml_yolo.adapters.queue.storage import NFSQueueStore, _read, atomic_write
from clearml_yolo.adapters.runtime.process_tree import (
    LinuxProcessTree,
    check_interpreter_supervision,
    defer_interruptions,
    require_process_supervision,
)
from clearml_yolo.core.queue import (
    QUEUE_COMPATIBILITY,
    GPUObservation,
    GuardianClaim,
    JobSnapshot,
    PublicJob,
    WorkerIdentity,
)

CommandBuilder = Callable[[JobSnapshot, Path, tuple[str, ...]], Sequence[str]]


_WORKER_HEARTBEAT_SECONDS = 10
_STARTUP_WINDOW_SECONDS = 30
_MAX_STATUS_BYTES = 65536


class QueueProcesses:
    def __init__(
        self,
        store: NFSQueueStore,
        identity: WorkerIdentity,
        *,
        child_module: str = "clearml_yolo.entrypoints.queue_run",
        local_root: Path | None = None,
        command_builder: CommandBuilder | None = None,
    ) -> None:
        self.store = store
        self.identity = identity
        selected = local_root.resolve() if local_root is not None else store.local_root
        if store.local_root is not None and selected != store.local_root:
            raise ValueError("Worker and storage coordination roots must agree")
        self.local_root = selected
        self.pool = LocalGPULocks(identity, selected)
        self.child_module = child_module
        self.command_builder = command_builder
        self._guardians: dict[int, subprocess.Popen[bytes]] = {}
        self._worker_born: int | None = None
        self._observations: tuple[GPUObservation, ...] = ()

    def pause(self, seconds: float) -> None:
        time.sleep(seconds)

    def _heartbeat(self) -> None:
        if self._worker_born is not None:
            record = WorkerRecord(
                identity=self.identity,
                pid=os.getpid(),
                born=self._worker_born,
                heartbeat=time.time(),
                observations=self._observations,
            )
            atomic_write(self.store.actor_root / "worker.json", record.model_dump_json())

    @contextmanager
    def worker_registration(self) -> Iterator[None]:
        require_process_supervision()
        self.pool.ensure_control_fence()
        queue_key = self.store.queue_id
        path = self.pool.root / f"worker-{self.identity.owner_uid}-{queue_key}.lock"
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        if os.fstat(descriptor).st_uid != os.geteuid():
            os.close(descriptor)
            raise PermissionError("Owner worker lock belongs to another UID")
        registered = False
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError(
                    "One live queue worker per owner/root is already registered"
                ) from None
            self._worker_born = process_birth(os.getpid())
            if self._worker_born is None:
                raise RuntimeError("Worker process identity is unavailable")
            registered = True
            self._heartbeat()
            yield
        finally:
            try:
                if registered:
                    self._worker_born = None
                    (self.store.actor_root / "worker.json").unlink(missing_ok=True)
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)

    def publish_inventory(self, observations: tuple[GPUObservation, ...]) -> None:
        self._observations = observations
        self._heartbeat()

    def owner_inventory(self) -> dict[int, tuple[GPUObservation, ...]]:
        result: dict[int, tuple[GPUObservation, ...]] = {}
        for actor in (self.store.host_root / "actors").iterdir():
            path = actor / "worker.json"
            try:
                record = WorkerRecord.model_validate_json(_read(path, int(actor.name)))
            except FileNotFoundError:
                continue
            uid = int(actor.name)
            if record.identity.owner_uid != uid or record.identity.host_id != self.identity.host_id:
                raise RuntimeError("Worker liveness identity does not match its host/owner")
            if record.compatibility != QUEUE_COMPATIBILITY:
                raise RuntimeError("An incompatible worker protocol stops queue admission")
            if (
                record.identity.boot_id == self.identity.boot_id
                and process_birth(record.pid) == record.born
                and time.time() - record.heartbeat <= _WORKER_HEARTBEAT_SECONDS
            ):
                result[uid] = record.observations
        return result

    def live_owners(self) -> set[int]:
        return set(self.owner_inventory())

    def reserved(self) -> set[str]:
        return self.pool.reserved()

    def held(self) -> set[str]:
        return {hold.uuid for hold in self.pool.holds()}

    def allocated_devices(self, identifier: str) -> tuple[str, ...]:
        return self.pool.allocated_devices(identifier)

    def refresh(self) -> None:
        self._heartbeat()
        for pid, process in tuple(self._guardians.items()):
            if process.poll() is not None:
                process.wait()
                del self._guardians[pid]
        for job in self.store.view().jobs:
            if job.owner_uid == self.identity.owner_uid:
                self._refresh_job(job)
                self._refresh_status(job)

    def _refresh_job(self, job: PublicJob) -> None:
        claim = self.pool.claim_for(job.id)
        if claim is not None:
            if claim.owner_uid != self.identity.owner_uid:
                raise RuntimeError("Local GPU claim owner disagrees with the NFS job owner")
            live = (
                claim.boot_id == self.identity.boot_id
                and process_birth(claim.guardian_pid) == claim.guardian_born
            )
            if not live and job.state != "recovery_required":
                self.store.update(
                    job.id,
                    "recovery_required",
                    error=("Guardian exited without verified cleanup; owner recovery required"),
                )
            return
        if job.state not in {"starting", "running", "cancelling"}:
            return
        directory = self.store.snapshot_path(job.id).parent
        launch_path = directory / "launch.json"
        if launch_path.exists():
            launch = WorkerRecord.model_validate_json(
                _read(launch_path, job.owner_uid, private=True)
            )
            if (
                launch.identity.boot_id == self.identity.boot_id
                and process_birth(launch.pid) == launch.born
            ):
                return
        elif time.time() - job.updated_at < _STARTUP_WINDOW_SECONDS:
            return
        self.store.update(
            job.id,
            "recovery_required",
            error=("Execution state is uncertain; owner recovery required"),
        )

    def start(
        self, job: PublicJob, devices: tuple[str, ...], *, expected_revision: int | None = None
    ) -> bool:
        snapshot = self.store.load_snapshot(job.id)
        check_interpreter_supervision(snapshot.interpreter)
        path = self.store.snapshot_path(job.id)
        directory = path.parent
        argv = (
            tuple(self.command_builder(snapshot, path, devices))
            if self.command_builder
            else (
                snapshot.interpreter,
                "-m",
                self.child_module,
                "--snapshot",
                str(path),
                "--devices",
                str(len(devices)),
            )
        )
        payload = GuardianPayload(
            job_id=job.id,
            identity=self.identity,
            queue_root=str(self.store.root),
            local_root=str(self.local_root) if self.local_root else None,
            devices=devices,
            marker=uuid4().hex,
            ownership_since=process_ticks(),
            argv=argv,
            snapshot_path=str(path),
            cwd=snapshot.cwd,
            project_root=snapshot.project_root,
            start_gate=str(directory / f"guardian-{uuid4().hex}.ready"),
        )
        payload_path = directory / "guardian.json"
        if not self.store.prepare_start(
            job.id, devices, payload.model_dump_json(), expected_revision=expected_revision
        ):
            return False
        process = subprocess.Popen(  # noqa: S603 - fixed package adapter with private transport
            [sys.executable, "-m", "clearml_yolo.adapters.queue.guardian", str(payload_path)],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._guardians[process.pid] = process
        born = process_birth(process.pid)
        if born is None:
            self.store.update(
                job.id, "recovery_required", error="Guardian identity disappeared before startup"
            )
            return False
        launch = WorkerRecord(
            identity=self.identity, pid=process.pid, born=born, heartbeat=time.time()
        )
        atomic_write(directory / "launch.json", launch.model_dump_json(), 0o600)
        Path(payload.start_gate).touch(mode=0o600)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            current = next(item for item in self.store.view().jobs if item.id == job.id)
            if current.state != "starting":
                return current.state != "pending"
            if process.poll() is not None:
                self.refresh()
                return False
            time.sleep(0.02)
        self.store.update(
            job.id,
            "recovery_required",
            error="Guardian startup did not complete; owner recovery required",
        )
        return False

    @defer_interruptions()
    def recover(self, identifier: str) -> PublicJob:
        jobs = {job.id: job for job in self.store.view().jobs}
        if identifier not in jobs:
            raise ValueError("Queue job is missing from the local host partition")
        job = jobs[identifier]
        if job.owner_uid != os.geteuid():
            raise PermissionError("Only the effective owner may recover this job")
        if job.state != "recovery_required":
            raise ValueError("Only jobs requiring recovery can be recovered")
        claim = self.pool.claim_for(job.id)
        if claim is None:
            claim = self._startup_claim(job)
        if (
            claim.boot_id == self.identity.boot_id
            and process_birth(claim.guardian_pid) == claim.guardian_born
        ):
            raise RuntimeError("Guardian is still alive; cancel it before attempting recovery")
        lease = self.pool.acquire_recovery(claim)
        try:
            self.store.cancel(job.id)
            same_boot = claim.boot_id == self.identity.boot_id
            root = (claim.child_pid or 0) if same_boot else 0
            tree = LinuxProcessTree(
                root,
                claim.marker,
                born=(claim.child_born or claim.ownership_since) if same_boot else process_ticks(),
                identities=dict(claim.identities) if same_boot else {},
            )
            cleanup_tree(tree)
            return self.store.finish_recovery(job.id, lease.release_verified)
        finally:
            lease.close()

    def _startup_claim(self, job: PublicJob) -> GuardianClaim:
        directory = self.store.snapshot_path(job.id).parent
        payload = GuardianPayload.model_validate_json(
            _read(directory / "guardian.json", job.owner_uid, private=True)
        )
        if (
            payload.job_id != job.id
            or payload.identity.owner_uid != self.identity.owner_uid
            or payload.identity.host_id != self.identity.host_id
        ):
            raise RuntimeError("Startup recovery evidence has inconsistent ownership")
        launch_path = directory / "launch.json"
        launch = (
            WorkerRecord.model_validate_json(_read(launch_path, job.owner_uid, private=True))
            if launch_path.exists()
            else None
        )
        return GuardianClaim(
            job_id=job.id,
            owner_uid=job.owner_uid,
            host_id=job.host_id,
            boot_id=payload.identity.boot_id,
            queue_root=str(self.store.root),
            devices=payload.devices,
            marker=payload.marker,
            ownership_since=payload.ownership_since,
            guardian_pid=launch.pid if launch is not None else 0,
            guardian_born=launch.born if launch is not None else 0,
        )

    def _refresh_status(self, job: PublicJob) -> None:
        snapshot = self.store.load_snapshot(job.id)
        project = Path(snapshot.project_root).resolve()
        path = project / ".cy" / "queue-status" / f"{job.id}.json"
        if not path.exists():
            return
        if not path.resolve().is_relative_to(project) or path.stat().st_size > _MAX_STATUS_BYTES:
            raise RuntimeError("Child queue status is outside its project or exceeds its bound")
        status = ChildStatus.model_validate_json(_read(path, job.owner_uid, private=True))
        self.store.publish_status(job.id, progress=status.progress, clearml_url=status.task_url)
