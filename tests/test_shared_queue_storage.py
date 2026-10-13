"""Durable owner-private snapshots and public, revision-checked ordering."""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.core.queue import JobSnapshot


def test_namespace_is_public_under_restrictive_umask(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.coordination import host_directory

    previous = os.umask(0o077)
    try:
        directory = host_directory("restricted-host", tmp_path / "coordination")
    finally:
        os.umask(previous)
    records = list(directory.glob("namespace-*.json"))
    assert len(records) == 1
    assert stat.S_IMODE(records[0].stat().st_mode) == 0o644
    assert stat.S_IMODE(directory.stat().st_mode) == 0o1777


def _store(root: Path, host: str = "test-host") -> NFSQueueStore:
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import WorkerIdentity

    return NFSQueueStore(root, WorkerIdentity(owner_uid=os.geteuid(), host_id=host, boot_id="boot"))


def _snapshot(project: Path, label: str = "first") -> JobSnapshot:
    from clearml_yolo.core.queue import JobSnapshot

    return JobSnapshot(
        command="train",
        label=label,
        config_json='{"token":"private-value"}',
        project_root=str(project),
        cwd=str(project),
        interpreter=sys.executable,
        package_version="1",
        package_identity="source-hash",
    )


def test_private_snapshot_public_summary_and_immutable_hash(tmp_path: Path) -> None:
    store = _store(tmp_path / "queue")
    job = store.submit((_snapshot(tmp_path),))[0]
    snapshot_path = store.snapshot_path(job.id)
    assert stat.S_IMODE(snapshot_path.stat().st_mode) == 0o600
    assert snapshot_path.stat().st_uid == os.geteuid()
    assert "private-value" not in store.view().model_dump_json()
    assert store.load_snapshot(job.id).config_json == '{"token":"private-value"}'
    raw = json.loads(snapshot_path.read_text())
    raw["config_json"] = '{"token":"changed"}'
    snapshot_path.write_text(json.dumps(raw))
    with pytest.raises(RuntimeError, match="hash"):
        store.load_snapshot(job.id)


def test_move_revision_and_relative_order_are_atomic(tmp_path: Path) -> None:
    store = _store(tmp_path / "queue")
    jobs = store.submit(tuple(_snapshot(tmp_path, label) for label in ("a", "b", "c")))
    view = store.view()
    moved = store.move(jobs[2].id, "before", view.revision, relative_job_id=jobs[0].id)
    assert [job.label for job in moved.jobs] == ["c", "a", "b"]
    with pytest.raises(RuntimeError, match="revision"):
        store.move(jobs[1].id, "top", view.revision)
    moved = store.move(jobs[2].id, "bottom", moved.revision)
    assert [job.label for job in moved.jobs] == ["a", "b", "c"]


def test_foreign_host_is_view_only_and_corrupt_public_record_blocks(tmp_path: Path) -> None:
    store = _store(tmp_path / "queue")
    job = store.submit((_snapshot(tmp_path),))[0]
    other_host = _store(tmp_path / "queue", "other-host")
    assert other_host.view().jobs == ()
    assert other_host.view("test-host").jobs[0].id == job.id
    with pytest.raises(ValueError, match="missing"):
        other_host.cancel(job.id)
    store.public_path(job.id).write_text('{"protocol":999}')
    with pytest.raises(RuntimeError, match=r"corrupt|protocol"):
        store.view()


def test_submission_validates_entire_batch_before_any_commit(tmp_path: Path) -> None:
    store = _store(tmp_path / "queue")
    good = _snapshot(tmp_path)
    bad = good.model_copy(update={"project_root": "/nonexistent/project"})
    with pytest.raises(ValueError, match="project"):
        store.submit((good, bad))
    assert store.view().jobs == ()


def test_effective_uid_cannot_be_asserted_by_configuration(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import WorkerIdentity

    with pytest.raises(PermissionError, match="effective"):
        NFSQueueStore(
            tmp_path, WorkerIdentity(owner_uid=os.geteuid() + 1, host_id="h", boot_id="b")
        )


def test_competing_start_does_not_replace_committed_guardian_payload(tmp_path: Path) -> None:
    store = _store(tmp_path / "queue")
    job = store.submit((_snapshot(tmp_path),))[0]
    assert store.prepare_start(job.id, ("GPU-a",), '{"first":true}')
    assert not store.prepare_start(job.id, ("GPU-b",), '{"second":true}')
    path = store.snapshot_path(job.id).parent / "guardian.json"
    assert path.read_text(encoding="utf-8") == '{"first":true}'


def test_submission_sequence_survives_wall_clock_moving_backwards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    store = _store(tmp_path / "queue")
    monkeypatch.setattr(time, "time", lambda: 100.0)
    first = store.submit((_snapshot(tmp_path, "first"),))[0]
    monkeypatch.setattr(time, "time", lambda: 1.0)
    second = store.submit((_snapshot(tmp_path, "second"),))[0]
    assert [job.id for job in store.view().jobs] == [first.id, second.id]
    assert first.submission_sequence < second.submission_sequence


def test_reorder_after_admission_decision_rejects_stale_claim(tmp_path: Path) -> None:
    store = _store(tmp_path / "queue")
    jobs = store.submit((_snapshot(tmp_path, "first"), _snapshot(tmp_path, "second")))
    view = store.view()
    store.move(jobs[1].id, "top", view.revision)
    assert not store.prepare_start(jobs[0].id, ("GPU-a",), "{}", expected_revision=view.revision)
    assert all(job.state == "pending" for job in store.view().jobs)


def test_pending_move_crosses_completed_history_using_pending_neighbors(tmp_path: Path) -> None:
    store = _store(tmp_path / "queue")
    jobs = store.submit(
        tuple(_snapshot(tmp_path, label) for label in ("first", "finished", "last"))
    )
    store.update(jobs[1].id, "completed")
    view = store.view()
    moved = store.move(jobs[2].id, "up", view.revision)
    assert [job.label for job in moved.jobs if job.state == "pending"] == ["last", "first"]
    store.update(jobs[0].id, "completed")
    assert [job.label for job in store.view().jobs] == ["last", "first", "finished"]
