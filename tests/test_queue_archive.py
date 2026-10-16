"""Archiving changes visibility without losing durable ordering or execution evidence."""

import json
import os
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from clearml_yolo.adapters.queue.runtime import QueueProcesses
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import GPUObservation, JobSnapshot, JobState, WorkerIdentity


class _NoGPUs:
    def snapshot(self) -> tuple[GPUObservation, ...]:
        return ()


def _store(project: Path, *, host: str = "archive-host") -> NFSQueueStore:
    return NFSQueueStore(
        project / "queue",
        WorkerIdentity(owner_uid=os.geteuid(), host_id=host, boot_id="archive-boot"),
    )


def _snapshot(project: Path, label: str = "Training experiment") -> JobSnapshot:
    return JobSnapshot(
        command="train",
        label=label,
        config_json='{"secret":"private-value"}',
        project_root=str(project),
        cwd=str(project),
        interpreter=sys.executable,
        package_version="1",
        package_identity="source-identity",
    )


def _service(store: NFSQueueStore, project: Path) -> QueueService:
    processes = QueueProcesses(store, store.identity, local_root=project / "coordination")
    return QueueService(store, _NoGPUs(), processes, store.identity)


def test_archive_is_durable_idempotent_and_preserves_execution_records(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.submit((_snapshot(tmp_path),))[0]
    store.update(job.id, "completed")
    public = store.public_path(job.id)
    snapshot = store.snapshot_path(job.id)
    original = public.read_bytes(), snapshot.read_bytes()
    revision = store.view().revision

    archived = store.set_archived(("job-1",), True)

    assert archived.archived_job_ids == (job.id,)
    assert len(archived.jobs) == 1
    assert archived.revision == revision + 1
    assert (public.read_bytes(), snapshot.read_bytes()) == original
    assert stat.S_IMODE((public.parent / "archive.json").stat().st_mode) == 0o644
    assert store.set_archived((job.id, "job-1"), True).revision == archived.revision
    reopened = _store(tmp_path)
    assert reopened.view().archived_job_ids == (job.id,)
    restored = reopened.set_archived(("job-1",), False)
    assert restored.archived_job_ids == ()
    assert restored.revision == revision + 2
    assert reopened.set_archived((job.id,), False).revision == restored.revision
    assert (public.read_bytes(), snapshot.read_bytes()) == original


@pytest.mark.parametrize("state", ["completed", "failed", "cancelled"])
def test_each_terminal_outcome_can_be_archived(tmp_path: Path, state: JobState) -> None:
    store = _store(tmp_path)
    job = store.submit((_snapshot(tmp_path),))[0]
    store.update(job.id, state)
    view = store.set_archived((job.id,), True)
    assert view.jobs[0].state == state
    assert view.archived_job_ids == (job.id,)


@pytest.mark.parametrize(
    "state", ["pending", "starting", "running", "cancelling", "recovery_required"]
)
def test_archive_rejects_unfinished_jobs_before_changing_any_target(
    tmp_path: Path, state: JobState
) -> None:
    store = _store(tmp_path)
    first, second = store.submit((_snapshot(tmp_path), _snapshot(tmp_path)))
    store.update(first.id, "completed")
    store.update(second.id, state)
    revision = store.view().revision
    with pytest.raises(ValueError, match=r"terminal|completed|finished"):
        store.set_archived((first.id, second.id), True)
    assert store.view().archived_job_ids == ()
    assert store.view().revision == revision


@pytest.mark.parametrize("archived", [True, False])
def test_archive_and_restore_require_effective_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archived: bool
) -> None:
    store = _store(tmp_path)
    job = store.submit((_snapshot(tmp_path),))[0]
    store.update(job.id, "cancelled")
    store.set_archived((job.id,), not archived)
    before = store.view()
    uid = os.geteuid()
    # The filesystem stays real; this isolates the effective-identity boundary.
    monkeypatch.setattr(os, "geteuid", lambda: uid + 1)
    with pytest.raises(PermissionError, match="owner"):
        store.set_archived((job.id,), archived)
    assert store.view() == before


@pytest.mark.parametrize("damage", ["invalid_json", "wrong_job", "string_boolean", "dangling_link"])
def test_corrupt_archive_metadata_fails_closed(tmp_path: Path, damage: str) -> None:
    store = _store(tmp_path)
    job = store.submit((_snapshot(tmp_path),))[0]
    store.update(job.id, "completed")
    public = store.public_path(job.id)
    store.set_archived((job.id,), True)
    path = public.parent / "archive.json"
    if damage == "invalid_json":
        path.write_text("{", encoding="utf-8")
    elif damage == "dangling_link":
        path.unlink()
        path.symlink_to(path.with_name("missing.json"))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["job_id" if damage == "wrong_job" else "archived"] = (
            "another-job" if damage == "wrong_job" else "true"
        )
        path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((RuntimeError, PermissionError), match=r"corrupt|identity|ownership"):
        store.view()


def test_main_archived_and_all_views_keep_history_and_surface_recovery(tmp_path: Path) -> None:
    store = _store(tmp_path)
    service = _service(store, tmp_path)
    first, second = store.submit((_snapshot(tmp_path, "first"), _snapshot(tmp_path, "second")))
    store.update(first.id, "completed")
    result = service.archive(("job-1",))
    assert [job.id for job in result.jobs] == [second.id]
    assert [job.id for job in service.list().jobs] == [second.id]
    assert [job.id for job in service.list(visibility="archived").jobs] == [first.id]
    assert [job.id for job in service.list(visibility="all").jobs] == [first.id, second.id]
    assert service.list().revision == store.view().revision
    moved = service.move("job-2", "top", store.view().revision)
    assert [job.id for job in moved.jobs] == [second.id]
    store.update(first.id, "recovery_required")
    assert [job.id for job in service.list().jobs] == [first.id, second.id]
    assert service.list(visibility="archived").jobs == ()
    assert service.list().archived_job_ids == (first.id,)
    restored = service.restore(("job-1",))
    assert restored.archived_job_ids == ()
    assert restored.jobs[0].state == "recovery_required"


def test_archive_preserves_order_replay_numbering_and_stale_revision_checks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first, second, third = store.submit(tuple(_snapshot(tmp_path) for _ in range(3)))
    store.move("job-2", "before", store.view().revision, relative_job_id="job-1")
    store.update(second.id, "completed")
    before_archive = store.view()
    store.set_archived(("job-2",), True)
    with pytest.raises(RuntimeError, match="revision"):
        store.move("job-3", "top", before_archive.revision)
    assert not store.prepare_start(first.id, (), "{}", expected_revision=before_archive.revision)
    fourth = store.submit((_snapshot(tmp_path),))[0]
    assert fourth.submission_sequence == 4
    assert [job.id for job in _store(tmp_path).view().jobs] == [
        second.id,
        first.id,
        third.id,
        fourth.id,
    ]
    service = _service(store, tmp_path)
    assert [job.submission_sequence for job in service.list().jobs] == [1, 3, 4]
    service.restore(("job-2",))
    assert [job.submission_sequence for job in service.list().jobs] == [2, 1, 3, 4]


def test_readable_references_resolve_existing_ids_and_reject_ambiguity(tmp_path: Path) -> None:
    from clearml_yolo.core.queue import resolve_job_reference

    store = _store(tmp_path)
    first, second = store.submit((_snapshot(tmp_path), _snapshot(tmp_path)))
    assert resolve_job_reference((first, second), "job-2") == second
    assert resolve_job_reference((first, second), first.id) == first
    for reference in ("job-0", "job-99", "job-01", "unknown"):
        with pytest.raises(ValueError, match=r"missing|reference"):
            resolve_job_reference((first, second), reference)
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_job_reference(
            (first, second.model_copy(update={"submission_sequence": 1})), "job-1"
        )
    service = _service(store, tmp_path)
    assert service.cancel("job-2").id == second.id
    with pytest.raises(ValueError, match="requiring recovery"):
        service.recover("job-1")


def test_foreign_host_archive_visibility_is_read_only(tmp_path: Path) -> None:
    store = _store(tmp_path)
    job = store.submit((_snapshot(tmp_path),))[0]
    store.update(job.id, "completed")
    store.set_archived((job.id,), True)
    other = _store(tmp_path, host="other-host")
    service = _service(other, tmp_path)
    assert service.list("archive-host").jobs == ()
    assert service.list("archive-host", visibility="archived").jobs[0].id == job.id
    with pytest.raises(ValueError, match="missing"):
        service.restore(("job-1",))


def test_new_metadata_root_remains_shared_under_restrictive_umask(tmp_path: Path) -> None:
    previous = os.umask(0o077)
    try:
        store = NFSQueueStore(
            tmp_path / "queue",
            WorkerIdentity(owner_uid=os.geteuid(), host_id="archive-host", boot_id="boot"),
            local_root=tmp_path / "coordination",
        )
        job = store.submit((_snapshot(tmp_path),))[0]
    finally:
        os.umask(previous)
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o1777
    assert (tmp_path / "coordination" / "archive-host" / "nfs-transaction.lock").exists()
    assert stat.S_IMODE(store.public_path(job.id).stat().st_mode) == 0o644
    assert stat.S_IMODE(store.snapshot_path(job.id).stat().st_mode) == 0o600
    store.root.chmod(0o770)
    _store(tmp_path)
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o770


def test_concurrent_archive_retries_commit_one_visibility_change(tmp_path: Path) -> None:
    stores = tuple(_store(tmp_path) for _ in range(4))
    job = stores[0].submit((_snapshot(tmp_path),))[0]
    stores[0].update(job.id, "completed")
    revision = stores[0].view().revision
    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = tuple(executor.map(lambda store: store.set_archived(("job-1",), True), stores))
    assert all(view.revision == revision + 1 for view in outcomes)
    assert all(view.archived_job_ids == (job.id,) for view in outcomes)


def test_partial_archive_io_failure_is_visible_and_safe_to_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.queue import storage

    store = _store(tmp_path)
    first, second = store.submit((_snapshot(tmp_path), _snapshot(tmp_path)))
    store.update(first.id, "completed")
    store.update(second.id, "completed")
    failing_path = store.public_path(second.id).with_name("archive.json")
    write = storage.atomic_write

    def fail_second_archive(path: Path, payload: str, mode: int = 0o644) -> None:
        if path == failing_path:
            raise OSError("Storage became unavailable")
        write(path, payload, mode)

    with monkeypatch.context() as patch:
        patch.setattr(storage, "atomic_write", fail_second_archive)
        with pytest.raises(OSError, match="unavailable"):
            store.set_archived((first.id, second.id), True)
    assert store.view().archived_job_ids == (first.id,)
    result = store.set_archived((first.id, second.id), True)
    assert result.archived_job_ids == (first.id, second.id)
    assert [job.state for job in result.jobs] == ["completed", "completed"]
