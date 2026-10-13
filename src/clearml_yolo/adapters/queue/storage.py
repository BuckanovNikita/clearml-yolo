"""Atomic NFS manifests with private snapshots and owner-authored ordering events."""

import hashlib
import json
import os
import re
import stat
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import ValidationError

from clearml_yolo.adapters.queue.coordination import host_transaction
from clearml_yolo.core.queue import (
    JobSnapshot,
    JobState,
    MoveDirection,
    OrderingEvent,
    PublicJob,
    QueueRecord,
    QueueView,
    WorkerIdentity,
)


class _SubmissionBatch(QueueRecord):
    jobs: tuple[str, ...]


def _safe_host(host: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", host):
        raise ValueError("Host identity is not a safe queue partition")
    return host


def _job_id(identifier: str) -> str:
    try:
        parsed = UUID(identifier)
    except ValueError:
        raise ValueError("Invalid queue job ID") from None
    if str(parsed) != identifier:
        raise ValueError("Queue job ID must use canonical UUID syntax")
    return identifier


def atomic_write(path: Path, payload: str, mode: int = 0o644) -> None:
    """Publish a complete, flushed record; never truncate a committed record."""
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _directory(path: Path, mode: int) -> None:
    try:
        path.mkdir(mode=mode)
    except FileExistsError:
        if not path.is_dir() or path.is_symlink():
            raise RuntimeError(f"Queue directory is invalid: {path}") from None
    else:
        path.chmod(mode)


def _owned(path: Path, uid: int, *, private: bool = False) -> None:
    status = path.lstat()
    if stat.S_ISLNK(status.st_mode) or status.st_uid != uid:
        raise PermissionError(f"Queue filesystem ownership mismatch: {path.name}")
    if private and stat.S_IMODE(status.st_mode) & 0o077:
        raise PermissionError(f"Private queue record permissions are too broad: {path.name}")
    if not private and stat.S_IMODE(status.st_mode) & 0o022:
        raise PermissionError(
            f"Owner-authored queue record is writable by another user: {path.name}"
        )


def _read(path: Path, uid: int, *, private: bool = False) -> str:
    _owned(path, uid, private=private)
    return path.read_text(encoding="utf-8")


class NFSQueueStore:
    """Effects stay here; public reads never load another owner's configuration."""

    def __init__(self, root: Path, identity: WorkerIdentity) -> None:
        if os.name != "posix" or not hasattr(os, "geteuid"):
            raise RuntimeError("Shared cy-queue requires Linux native file coordination")
        if identity.owner_uid != os.geteuid():
            raise PermissionError("Queue identity must match the effective UID")
        self.root = root.expanduser().resolve()
        self.identity = identity
        self.root.mkdir(parents=True, exist_ok=True)
        _directory(self.root / "hosts", 0o777)
        self.host_root = self.root / "hosts" / _safe_host(identity.host_id)
        _directory(self.host_root, 0o777)
        _directory(self.host_root / "actors", 0o777)
        self.actor_root = self.host_root / "actors" / str(identity.owner_uid)
        _directory(self.actor_root, 0o755)
        _owned(self.actor_root, identity.owner_uid)
        for name in ("jobs", "events", "batches"):
            _directory(self.actor_root / name, 0o755)
            _owned(self.actor_root / name, identity.owner_uid)
        with self.transaction():
            self.queue_id = self._root_identity()

    @contextmanager
    def transaction(self, host_id: str | None = None) -> Iterator[None]:
        """Same-host processes share a local lock across every NFS root and alias."""
        if host_id is not None and host_id != self.identity.host_id:
            raise ValueError("Foreign host partitions are view-only")
        with host_transaction(self.identity.host_id):
            yield

    def _root_identity(self) -> str:
        path = self.root / "queue-identity.json"
        if not path.exists():
            temporary = self.root / f".queue-identity-{uuid4().hex}.tmp"
            record = {"protocol": 1, "id": str(uuid4()), "owner_uid": self.identity.owner_uid}
            atomic_write(temporary, json.dumps(record))
            try:
                with suppress(FileExistsError):
                    os.link(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        raw = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(raw, dict)
            or set(raw) != {"protocol", "id", "owner_uid"}
            or type(raw["protocol"]) is not int
            or raw["protocol"] != 1
            or type(raw["owner_uid"]) is not int
        ):
            raise RuntimeError("Shared queue root identity is corrupt or unsupported")
        _owned(path, raw["owner_uid"])
        return _job_id(raw["id"])

    def _actors(self, host_id: str) -> tuple[tuple[int, Path], ...]:
        actors = self.root / "hosts" / _safe_host(host_id) / "actors"
        if not actors.exists():
            return ()
        result: list[tuple[int, Path]] = []
        for path in actors.iterdir():
            if not path.name.isdecimal():
                raise RuntimeError("Queue actors contain an unknown committed entry")
            uid = int(path.name)
            _owned(path, uid)
            result.append((uid, path))
        return tuple(result)

    def _actor_jobs(self, actor: Path, uid: int, host_id: str) -> list[PublicJob]:
        jobs: list[PublicJob] = []
        _owned(actor / "batches", uid)
        _owned(actor / "jobs", uid)
        for path in (actor / "batches").glob("*.json"):
            batch = _SubmissionBatch.model_validate_json(_read(path, uid))
            for identifier in batch.jobs:
                public = actor / "jobs" / _job_id(identifier) / "public.json"
                job = PublicJob.model_validate_json(_read(public, uid))
                if job.owner_uid != uid or job.host_id != host_id or job.id != identifier:
                    raise RuntimeError("Shared queue manifest identity mismatch")
                jobs.append(job)
        return jobs

    def _view(self, host_id: str) -> QueueView:
        jobs: list[PublicJob] = []
        events: list[OrderingEvent] = []
        try:
            for uid, actor in self._actors(host_id):
                jobs.extend(self._actor_jobs(actor, uid, host_id))
                for path in (actor / "events").glob("*.json"):
                    event = OrderingEvent.model_validate_json(_read(path, uid))
                    if event.owner_uid != uid or event.host_id != host_id:
                        raise RuntimeError("Shared queue ordering event identity mismatch")
                    events.append(event)
        except (ValueError, TypeError, ValidationError, UnicodeError) as error:
            raise RuntimeError(
                f"Shared queue committed record is corrupt: {type(error).__name__}"
            ) from error
        if len({job.id for job in jobs}) != len(jobs):
            raise RuntimeError("Shared queue contains duplicate committed job IDs")
        jobs.sort(key=lambda job: job.submission_sequence)
        if len({job.submission_sequence for job in jobs}) != len(jobs):
            raise RuntimeError("Shared queue contains duplicate submission sequences")
        events.sort(key=lambda event: event.revision)
        if len({event.revision for event in events}) != len(events):
            raise RuntimeError("Shared queue ordering contains duplicate revisions")
        for event in events:
            jobs = self._reorder(jobs, event.job_id, event.direction, event.relative_job_id)
        revision = len(jobs) + len(events) + sum(job.revision for job in jobs)
        return QueueView(host_id=host_id, revision=revision, jobs=tuple(jobs))

    def view(self, host_id: str | None = None) -> QueueView:
        host = host_id or self.identity.host_id
        if not (self.root / "hosts" / _safe_host(host)).exists():
            return QueueView(host_id=host, revision=0, jobs=())
        if host != self.identity.host_id:
            return self._view(host)
        with self.transaction():
            return self._view(host)

    def hosts(self) -> tuple[str, ...]:
        return tuple(sorted(path.name for path in (self.root / "hosts").iterdir() if path.is_dir()))

    def submit(self, snapshots: Sequence[JobSnapshot]) -> tuple[PublicJob, ...]:
        validated: list[JobSnapshot] = []
        for index, submitted in enumerate(snapshots):
            snapshot = JobSnapshot.model_validate(submitted.model_dump())
            project = Path(snapshot.project_root)
            if not project.is_absolute() or not project.is_dir():
                raise ValueError("Submission requires an existing absolute project root")
            if not Path(snapshot.cwd).is_absolute() or not Path(snapshot.cwd).is_dir():
                raise ValueError("Submission requires an existing absolute working directory")
            if (
                not Path(snapshot.interpreter).is_absolute()
                or not Path(snapshot.interpreter).is_file()
            ):
                raise ValueError("Submission requires an existing absolute interpreter")
            validated.append(
                snapshot.model_copy(
                    update={
                        "id": str(uuid4()),
                        "owner_uid": self.identity.owner_uid,
                        "host_id": self.identity.host_id,
                        "boot_id": self.identity.boot_id,
                        "submitted_at": time.time() + index / 1_000_000,
                    }
                )
            )
        if not validated:
            return ()
        published: list[PublicJob] = []
        with self.transaction():
            current = self._view(self.identity.host_id)
            sequence = max((job.submission_sequence for job in current.jobs), default=0) + 1
            for index, initial in enumerate(validated):
                snapshot = initial.model_copy(update={"submission_sequence": sequence + index})
                directory = self.actor_root / "jobs" / snapshot.id
                _directory(directory, 0o755)
                payload = snapshot.model_dump_json()
                atomic_write(directory / "snapshot.json", payload, 0o600)
                job = PublicJob(
                    id=snapshot.id,
                    owner_uid=snapshot.owner_uid,
                    host_id=snapshot.host_id,
                    boot_id=snapshot.boot_id,
                    command=snapshot.command,
                    label=snapshot.label,
                    request=snapshot.request,
                    submitted_at=snapshot.submitted_at,
                    submission_sequence=snapshot.submission_sequence,
                    snapshot_hash=hashlib.sha256(payload.encode()).hexdigest(),
                )
                atomic_write(directory / "public.json", job.model_dump_json())
                published.append(job)
            # Only this final manifest commits the entire prepared batch.
            atomic_write(
                self.actor_root / "batches" / f"{uuid4().hex}.json",
                json.dumps(
                    {
                        "protocol": 1,
                        "jobs": [job.id for job in published],
                    }
                ),
            )
        return tuple(published)

    def _find(self, identifier: str) -> PublicJob:
        _job_id(identifier)
        for job in self._view(self.identity.host_id).jobs:
            if job.id == identifier:
                return job
        raise ValueError("Queue job is missing from the local host partition")

    def public_path(self, identifier: str) -> Path:
        with self.transaction():
            job = self._find(identifier)
        return self.host_root / "actors" / str(job.owner_uid) / "jobs" / job.id / "public.json"

    def snapshot_path(self, identifier: str) -> Path:
        with self.transaction():
            job = self._find(identifier)
            self._require_owner(job)
        return self.actor_root / "jobs" / job.id / "snapshot.json"

    def load_snapshot(self, identifier: str) -> JobSnapshot:
        with self.transaction():
            job = self._find(identifier)
            self._require_owner(job)
            path = self.actor_root / "jobs" / job.id / "snapshot.json"
            payload = _read(path, job.owner_uid, private=True)
            if hashlib.sha256(payload.encode()).hexdigest() != job.snapshot_hash:
                raise RuntimeError("Private queue snapshot hash mismatch; execution refused")
            try:
                snapshot = JobSnapshot.model_validate_json(payload)
            except ValidationError as error:
                raise RuntimeError("Private queue snapshot is corrupt") from error
            if (
                snapshot.id != job.id
                or snapshot.owner_uid != job.owner_uid
                or snapshot.host_id != job.host_id
            ):
                raise RuntimeError("Private queue snapshot identity mismatch")
            return snapshot

    def _require_owner(self, job: PublicJob) -> None:
        if job.owner_uid != os.geteuid() or job.owner_uid != self.identity.owner_uid:
            raise PermissionError("Only the effective job owner may change or execute this job")

    @staticmethod
    def _reorder(
        jobs: list[PublicJob],
        identifier: str,
        direction: MoveDirection,
        relative: str | None,
    ) -> list[PublicJob]:
        positions = {job.id: index for index, job in enumerate(jobs)}
        if identifier not in positions:
            raise RuntimeError("Ordering references a missing job")
        position = positions[identifier]
        if direction in {"before", "after"}:
            if relative is None or relative not in positions or relative == identifier:
                raise ValueError("Relative ordering requires another existing job")
            target = positions[relative]
            if position < target:
                target -= 1
            target += int(direction == "after")
        else:
            target = {
                "up": max(0, position - 1),
                "down": min(len(jobs) - 1, position + 1),
                "top": 0,
                "bottom": len(jobs) - 1,
            }[direction]
        updated = jobs.copy()
        updated.insert(target, updated.pop(position))
        return updated

    def move(
        self,
        identifier: str,
        direction: MoveDirection,
        expected_revision: int,
        *,
        relative_job_id: str | None = None,
    ) -> QueueView:
        with self.transaction():
            view = self._view(self.identity.host_id)
            if expected_revision != view.revision:
                raise RuntimeError("Stale queue revision; refresh before reordering")
            job = self._find(identifier)
            if job.state != "pending":
                raise ValueError("Only pending jobs can be reordered")
            pending = [item for item in view.jobs if item.state == "pending"]
            self._reorder(pending, identifier, direction, relative_job_id)
            position = next(index for index, item in enumerate(pending) if item.id == identifier)
            if direction in {"up", "top"}:
                target = position - 1 if direction == "up" else 0
                if position == 0:
                    return view
                relative_job_id, direction = pending[target].id, "before"
            elif direction in {"down", "bottom"}:
                target = position + 1 if direction == "down" else len(pending) - 1
                if position == len(pending) - 1:
                    return view
                relative_job_id, direction = pending[target].id, "after"
            event = OrderingEvent(
                revision=view.revision + 1,
                owner_uid=self.identity.owner_uid,
                host_id=self.identity.host_id,
                job_id=identifier,
                direction=direction,
                relative_job_id=relative_job_id,
            )
            atomic_write(
                self.actor_root / "events" / f"{event.revision:020d}-{uuid4().hex}.json",
                event.model_dump_json(),
            )
            return self._view(self.identity.host_id)

    def update(
        self,
        identifier: str,
        state: JobState,
        *,
        devices: tuple[str, ...] | None = None,
        error: str | None = None,
        expected_state: JobState | None = None,
    ) -> PublicJob:
        with self.transaction():
            job = self._find(identifier)
            self._require_owner(job)
            if expected_state is not None and job.state != expected_state:
                raise RuntimeError("Queue job state changed before this operation")
            values: dict[str, object] = {
                "state": state,
                "revision": job.revision + 1,
                "error": error,
                "updated_at": time.time(),
            }
            if devices is not None:
                values["devices"] = devices
            result = PublicJob.model_validate(job.model_dump() | values)
            atomic_write(
                self.actor_root / "jobs" / job.id / "public.json", result.model_dump_json()
            )
            return result

    def prepare_start(
        self,
        identifier: str,
        devices: tuple[str, ...],
        payload: str,
        *,
        expected_revision: int | None = None,
    ) -> bool:
        """Commit one immutable launch payload while claiming the pending transition."""
        with self.transaction():
            if (
                expected_revision is not None
                and self._view(self.identity.host_id).revision != expected_revision
            ):
                return False
            job = self._find(identifier)
            self._require_owner(job)
            if job.state != "pending":
                return False
            directory = self.actor_root / "jobs" / job.id
            atomic_write(directory / "guardian.json", payload, 0o600)
            result = job.model_copy(
                update={
                    "state": "starting",
                    "devices": devices,
                    "updated_at": time.time(),
                    "revision": job.revision + 1,
                }
            )
            atomic_write(directory / "public.json", result.model_dump_json())
            return True

    def cancel(self, identifier: str) -> PublicJob:
        with self.transaction():
            job = self._find(identifier)
            self._require_owner(job)
            if job.state in {"completed", "failed", "cancelled"}:
                return job
            if job.state == "recovery_required":
                atomic_write(
                    self.actor_root / "jobs" / job.id / "cancel.json", '{"protocol":1}', 0o600
                )
                return job
            state: JobState = "cancelled" if job.state == "pending" else "cancelling"
            result = job.model_copy(update={"state": state, "revision": job.revision + 1})
            atomic_write(self.actor_root / "jobs" / job.id / "cancel.json", '{"protocol":1}', 0o600)
            atomic_write(
                self.actor_root / "jobs" / job.id / "public.json", result.model_dump_json()
            )
            return result

    def cancelled(self, identifier: str) -> bool:
        return (self.actor_root / "jobs" / _job_id(identifier) / "cancel.json").exists()

    def set_waiting(self, reasons: Mapping[str, str | None]) -> None:
        with self.transaction():
            for identifier, reason in reasons.items():
                job = self._find(identifier)
                self._require_owner(job)
                if job.state == "pending" and job.waiting_reason != reason:
                    result = job.model_copy(
                        update={"waiting_reason": reason, "revision": job.revision + 1}
                    )
                    atomic_write(
                        self.actor_root / "jobs" / job.id / "public.json", result.model_dump_json()
                    )

    def publish_status(
        self, identifier: str, *, progress: str | float | None, clearml_url: str | None
    ) -> None:
        with self.transaction():
            job = self._find(identifier)
            self._require_owner(job)
            if job.progress != progress or job.clearml_url != clearml_url:
                result = PublicJob.model_validate(
                    job.model_dump()
                    | {
                        "progress": progress,
                        "clearml_url": clearml_url,
                        "revision": job.revision + 1,
                    }
                )
                atomic_write(
                    self.actor_root / "jobs" / job.id / "public.json", result.model_dump_json()
                )

    def finish_recovery(self, identifier: str, release_verified: Callable[[], None]) -> PublicJob:
        """Readers observe terminal status only after the verified local release commits."""
        with self.transaction():
            job = self._find(identifier)
            self._require_owner(job)
            result = job.model_copy(
                update={
                    "state": "cancelled",
                    "revision": job.revision + 1,
                    "error": (
                        "Owner recovered abandoned execution after verified descendant cleanup"
                    ),
                }
            )
            atomic_write(
                self.actor_root / "jobs" / job.id / "public.json", result.model_dump_json()
            )
            release_verified()
            return result
