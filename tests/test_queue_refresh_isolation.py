"""A private task read failure must not hide readable shared queue summaries."""

import os
import sys
from pathlib import Path

import pytest

from clearml_yolo.adapters.queue.runtime import QueueProcesses
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import GPUObservation, JobSnapshot, JobState, WorkerIdentity


class _NoGPUs:
    def snapshot(self) -> tuple[GPUObservation, ...]:
        return ()


def _service(project: Path) -> QueueService:
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(project / "queue", identity)
    return QueueService(
        store, _NoGPUs(), QueueProcesses(store, identity, local_root=project / "local"), identity
    )


def _snapshot(project: Path, label: str) -> JobSnapshot:
    return JobSnapshot(
        command="pipeline",
        label=label,
        config_json='{"private":"secret-value"}',
        project_root=str(project),
        cwd=str(project),
        interpreter=sys.executable,
        package_version="0.1.0",
        package_identity="old-package-identity",
    )


def test_missing_snapshot_retains_all_public_rows(tmp_path: Path) -> None:
    service = _service(tmp_path)
    broken, healthy = service.submit((_snapshot(tmp_path, "old"), _snapshot(tmp_path, "healthy")))
    store = service.storage
    assert isinstance(store, NFSQueueStore)
    store.snapshot_path(broken.id).unlink()

    view = service.list()

    assert tuple(job.id for job in view.jobs) == (broken.id, healthy.id)
    assert tuple(issue.job_id for issue in view.refresh_issues) == (broken.id,)
    assert "secret-value" not in view.model_dump_json()


def _status(project: Path, identifier: str, progress: str) -> Path:
    import json

    path = project / ".cy" / "queue-status" / f"{identifier}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"progress": progress}))
    path.chmod(0o600)
    return path


def _replace_snapshot(store: NFSQueueStore, identifier: str, payload: str) -> None:
    import hashlib
    import json

    store.snapshot_path(identifier).write_text(payload)
    public = store.public_path(identifier)
    record = json.loads(public.read_text())
    record["snapshot_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    public.write_text(json.dumps(record))


def _damage_snapshot(
    store: NFSQueueStore, identifier: str, other: str, project: Path, fault: str, original: str
) -> None:
    import json

    path = store.snapshot_path(identifier)
    match fault:
        case "missing":
            path.unlink()
        case "malformed":
            _replace_snapshot(store, identifier, '{"config_json":"secret-value"')
        case "hash":
            path.write_text("secret-value")
        case "identity":
            record = json.loads(original)
            record["id"] = other
            _replace_snapshot(store, identifier, json.dumps(record))
        case "permissions":
            path.chmod(0o644)
        case "status":
            _status(project, identifier, "unused").write_text('{"progress":{"secret-value":1}}')
        case _:
            raise ValueError(f"Unknown test fault: {fault}")


@pytest.mark.parametrize(
    "fault", ["missing", "malformed", "hash", "identity", "permissions", "status"]
)
@pytest.mark.parametrize("state", ["pending", "completed", "archived"])
def test_mixed_queue_preserves_summaries_and_recovers(
    tmp_path: Path, fault: str, state: str
) -> None:
    service = _service(tmp_path)
    broken, healthy = service.submit((_snapshot(tmp_path, "old"), _snapshot(tmp_path, "healthy")))
    store = service.storage
    assert isinstance(store, NFSQueueStore)
    if state != "pending":
        store.update(broken.id, "completed")
    if state == "archived":
        store.set_archived((broken.id,), True)
    store.publish_status(broken.id, progress="previous progress", clearml_url=None)
    original_job = store.view().jobs[0]
    path = store.snapshot_path(broken.id)
    original = path.read_text()
    original_public = store.public_path(broken.id).read_text()
    _damage_snapshot(store, broken.id, healthy.id, tmp_path, fault, original)
    _status(tmp_path, healthy.id, "healthy progress")
    before = store.public_path(broken.id).read_bytes()

    view = service.list(visibility="all")

    assert view.jobs[0] == store.view().jobs[0]
    assert view.jobs[0].state == original_job.state
    assert view.jobs[0].progress == "previous progress"
    assert view.jobs[1].progress == "healthy progress"
    assert tuple(issue.job_id for issue in view.refresh_issues) == (broken.id,)
    assert "secret-value" not in view.model_dump_json()
    assert store.public_path(broken.id).read_bytes() == before
    main = service.list()
    archived = service.list(visibility="archived")
    assert tuple(job.id for job in main.jobs) == (
        (healthy.id,) if state == "archived" else (broken.id, healthy.id)
    )
    assert bool(main.refresh_issues) is (state != "archived")
    assert bool(archived.refresh_issues) is (state == "archived")

    path.write_text(original)
    path.chmod(0o600)
    store.public_path(broken.id).write_text(original_public)
    _status(tmp_path, broken.id, "repaired progress")
    restored = service.list(visibility="all")
    assert restored.refresh_issues == ()
    assert restored.jobs[0].progress == "repaired progress"
    assert restored.jobs[0].state == original_job.state


@pytest.mark.parametrize("state", ["pending", "running", "completed", "recovery_required"])
def test_monitoring_never_changes_outcome_or_releases_reservation(
    tmp_path: Path, state: JobState
) -> None:
    from clearml_yolo.core.queue import GuardianClaim

    service = _service(tmp_path)
    job = service.submit((_snapshot(tmp_path, "old"),))[0]
    store = service.storage
    processes = service.processes
    assert isinstance(store, NFSQueueStore)
    assert isinstance(processes, QueueProcesses)
    store.update(job.id, state)
    claim = GuardianClaim(
        job_id=job.id,
        owner_uid=job.owner_uid,
        host_id=job.host_id,
        boot_id="previous-boot",
        queue_root=str(store.root),
        devices=("GPU-test",),
        marker="owned-test",
        guardian_pid=99999999,
        guardian_born=1,
    )
    lease = processes.pool.acquire(claim)
    assert lease is not None
    try:
        before = store.public_path(job.id).read_bytes()
        assert service.list().jobs[0].state == state
        assert store.public_path(job.id).read_bytes() == before
        assert processes.reserved() == {"GPU-test"}
        assert processes.pool.claim_for(job.id) == lease.claim
        store.snapshot_path(job.id).unlink()
        assert service.list().jobs[0].state == state
        assert store.public_path(job.id).read_bytes() == before
        assert processes.reserved() == {"GPU-test"}
        assert processes.pool.claim_for(job.id) == lease.claim
    finally:
        lease.release_verified()


def test_strict_refresh_and_admission_still_reject_broken_snapshot(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.storage import PrivateSnapshotError

    service = _service(tmp_path)
    job = service.submit((_snapshot(tmp_path, "old"),))[0]
    store = service.storage
    assert isinstance(store, NFSQueueStore)
    store.snapshot_path(job.id).write_text("corrupt")
    for action in (service.processes.refresh, service.tick):
        with pytest.raises(PrivateSnapshotError, match="hash"):
            action()
    with pytest.raises(PrivateSnapshotError, match="hash"):
        service.processes.start(job, ("GPU-test",))
    assert store.view().jobs[0].state == "pending"
    assert service.processes.reserved() == set()


def test_invalid_public_record_is_queue_wide_error(tmp_path: Path) -> None:
    service = _service(tmp_path)
    job = service.submit((_snapshot(tmp_path, "old"),))[0]
    store = service.storage
    assert isinstance(store, NFSQueueStore)
    store.public_path(job.id).write_text('{"protocol":999}')
    with pytest.raises(RuntimeError, match="corrupt"):
        service.list()


def test_publication_failure_is_not_a_private_refresh_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.queue import storage

    service = _service(tmp_path)
    job = service.submit((_snapshot(tmp_path, "old"),))[0]
    _status(tmp_path, job.id, "new progress")

    def unavailable(path: Path, payload: str, mode: int = 0o644) -> None:
        raise OSError("Shared storage unavailable")

    monkeypatch.setattr(storage, "atomic_write", unavailable)
    with pytest.raises(OSError, match="Shared storage unavailable"):
        service.list()


def test_coordination_failure_during_snapshot_read_remains_queue_wide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from collections.abc import Iterator
    from contextlib import contextmanager

    service = _service(tmp_path)
    service.submit((_snapshot(tmp_path, "old"),))
    store = service.storage
    assert isinstance(store, NFSQueueStore)
    transaction = store.transaction
    count = 0

    @contextmanager
    def fail_second_transaction() -> Iterator[None]:
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("Coordination unavailable")
        with transaction():
            yield

    monkeypatch.setattr(store, "transaction", fail_second_transaction)
    with pytest.raises(RuntimeError, match="Coordination unavailable"):
        service.list()


def test_legacy_snapshot_is_viewable_without_hydra_and_execution_stays_strict(
    tmp_path: Path,
) -> None:
    import json
    import subprocess

    service = _service(tmp_path)
    legacy = _snapshot(tmp_path, "legacy").model_copy(
        update={"config_json": '{"legacy_settings":{"unknown":"${old:resolver}"}}'}
    )
    job = service.submit((legacy,))[0]
    script = """
import sys
class NoHydra:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'hydra', 'hydra_zen', 'omegaconf'}:
            raise AssertionError('Monitoring imported Hydra')
sys.meta_path.insert(0, NoHydra())
from pathlib import Path
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.adapters.queue.runtime import QueueProcesses
from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import WorkerIdentity
class NoGPUs:
    def snapshot(self): return ()
root = Path(sys.argv[1])
identity = WorkerIdentity.model_validate_json(sys.argv[2])
store = NFSQueueStore(root / 'queue', identity)
processes = QueueProcesses(store, identity, local_root=root/'local')
service = QueueService(store, NoGPUs(), processes, identity)
print(service.list().model_dump_json())
"""
    result = subprocess.run(  # noqa: S603 - isolated local monitoring probe
        [sys.executable, "-c", script, str(tmp_path), service.identity.model_dump_json()],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["jobs"][0]["id"] == job.id
    assert json.loads(result.stdout)["refresh_issues"] == []
    from clearml_yolo.entrypoints.hydra.queue_config import validate_snapshot

    with pytest.raises(ValueError, match="version"):
        validate_snapshot(legacy)


def test_real_cli_lists_healthy_and_missing_snapshot_jobs(tmp_path: Path) -> None:
    import json
    import subprocess

    from queue_cli_helpers import queue_command, queue_environment

    command = queue_command(tmp_path)
    environment = queue_environment(tmp_path)

    def run(*arguments: str) -> str:
        result = subprocess.run(  # noqa: S603 - isolated real queue CLI
            [*command, *arguments],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    for label in ("old", "healthy"):
        run("submit", "--gpus", "1", "--label", label, "--", "ground_truth=input.csv")
    initial = json.loads(run("list", "--json"))
    identifier = initial["jobs"][0]["id"]
    snapshot = next((tmp_path / "queue").glob(f"hosts/*/actors/*/jobs/{identifier}/snapshot.json"))
    snapshot.unlink()
    result = json.loads(run("list", "--json"))
    assert [job["label"] for job in result["jobs"]] == ["old", "healthy"]
    assert result["warning_count"] == 1
    assert result["refresh_issues"][0]["job_id"] == identifier
    assert result["refresh_issues"][0]["reference"] == "job-1"
    text = run("list")
    assert "Job 1" in text
    assert "Job 2" in text
    assert "Status unavailable; showing last recorded state" in text
