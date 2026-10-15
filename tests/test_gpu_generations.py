"""Generation fences preserve running processes while freeing selected capacity."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from clearml_yolo.adapters.queue.gpu_controls import GPUControls
from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity

GPU_A = "GPU-11111111-1111-1111-1111-111111111111"
GPU_B = "GPU-22222222-2222-2222-2222-222222222222"
pytestmark = pytest.mark.gpu_controls


def pool_and_claim(tmp_path: Path) -> tuple[LocalGPULocks, GuardianClaim]:
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="generations-test", boot_id="boot")
    pool = LocalGPULocks(identity, tmp_path / "local")
    claim = GuardianClaim(
        job_id="original",
        owner_uid=os.geteuid(),
        host_id=identity.host_id,
        boot_id="boot",
        queue_root="/unavailable-queue",
        devices=(GPU_A, GPU_B),
        marker="original",
        guardian_pid=os.getpid(),
        guardian_born=1,
    )
    return pool, claim


def test_free_live_allocation_is_per_device_and_old_writes_are_fenced(tmp_path: Path) -> None:
    pool, claim = pool_and_claim(tmp_path)
    controls = GPUControls(pool, physical_uuids=lambda: (GPU_A, GPU_B))
    old = pool.acquire(claim)
    assert old is not None
    new = None
    try:
        result = controls.release("0")
        assert result.uuid == GPU_A
        assert result.generation == 1
        assert pool.reserved() == {GPU_B}
        assert pool.allocated_devices(claim.job_id) == (GPU_B,)
        assert not old.is_current()
        contender = claim.model_copy(
            update={
                "job_id": "new",
                "marker": "new",
                "devices": (GPU_A,),
                "queue_root": "/other-queue",
            }
        )
        new = pool.acquire(contender)
        assert new is not None
        old.persist(old.claim.model_copy(update={"identities": ((123, 456),)}))
        evidence = pool.claim_for("original")
        assert evidence is not None
        assert evidence.identities == ((123, 456),)
        assert pool.claim_for("new") == new.claim
        old.release_verified()
        assert pool.reserved() == {GPU_A}
        assert pool.claim_for("new") == new.claim
    finally:
        if new is not None:
            new.release_verified()
            new.close()
        old.close()


def test_freed_first_gpu_stays_first_during_training_handoff(tmp_path: Path) -> None:
    pool, claim = pool_and_claim(tmp_path)
    old = pool.acquire(claim)
    assert old is not None
    new = None
    try:
        GPUControls(pool, physical_uuids=lambda: (GPU_A, GPU_B)).release("0")
        new = pool.acquire(
            claim.model_copy(update={"job_id": "new", "marker": "new", "devices": (GPU_A,)})
        )
        assert new is not None
        reduced = old.retain_first()
        assert reduced.devices == (GPU_A,)
        assert pool.allocated_devices("original") == ()
        assert pool.reserved() == {GPU_A}
        old.persist(reduced)
        old.release_verified()
        assert pool.claim_for("new") == new.claim
    finally:
        if new is not None:
            new.release_verified()
            new.close()
        old.close()


def test_stale_unlocked_claim_does_not_reserve_capacity_but_preserves_evidence(
    tmp_path: Path,
) -> None:
    pool, claim = pool_and_claim(tmp_path)
    old = pool.acquire(claim)
    assert old is not None
    old.close()
    assert pool.reserved() == set()
    new = pool.acquire(claim.model_copy(update={"job_id": "new", "marker": "new"}))
    assert new is not None
    try:
        assert pool.claim_for("original") == old.claim
        recovered = pool.acquire_recovery(old.claim)
        try:
            recovered.release_verified()
        finally:
            recovered.close()
        assert pool.reserved() == {GPU_A, GPU_B}
        assert pool.claim_for("new") == new.claim
    finally:
        new.release_verified()
        new.close()


def test_live_lock_in_other_process_remains_exclusive_until_explicit_free(tmp_path: Path) -> None:
    pool, claim = pool_and_claim(tmp_path)
    script = """
import sys, time
from pathlib import Path
from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity
pool = LocalGPULocks(WorkerIdentity.model_validate_json(sys.argv[1]), Path(sys.argv[2]))
lease = pool.acquire(GuardianClaim.model_validate_json(sys.argv[3]))
assert lease is not None
print('locked', flush=True)
time.sleep(60)
"""
    child = subprocess.Popen(  # noqa: S603 - fixed local test program
        [
            sys.executable,
            "-c",
            script,
            pool.identity.model_dump_json(),
            str(pool.local_root),
            claim.model_dump_json(),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    new = None
    try:
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "locked"
        assert pool.acquire(claim.model_copy(update={"job_id": "contender"})) is None
        GPUControls(pool, physical_uuids=lambda: (GPU_A, GPU_B)).release("0")
        assert child.poll() is None
        assert pool.reserved() == {GPU_B}
        new = pool.acquire(
            claim.model_copy(update={"job_id": "new", "marker": "new", "devices": (GPU_A,)})
        )
        assert new is not None
    finally:
        if new is not None:
            new.release_verified()
            new.close()
        child.terminate()
        child.wait(timeout=5)
        if child.stdout is not None:
            child.stdout.close()


def test_concurrent_processes_cannot_acquire_same_generation(tmp_path: Path) -> None:
    pool, claim = pool_and_claim(tmp_path)
    script = """
import sys
from pathlib import Path
from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity
pool = LocalGPULocks(WorkerIdentity.model_validate_json(sys.argv[1]), Path(sys.argv[2]))
print('ready', flush=True)
sys.stdin.readline()
lease = pool.acquire(GuardianClaim.model_validate_json(sys.argv[3]))
print('acquired' if lease is not None else 'busy', flush=True)
sys.stdin.readline()
if lease is not None:
    lease.release_verified()
    lease.close()
"""
    children: list[subprocess.Popen[str]] = []
    try:
        for index in range(2):
            contender = claim.model_copy(
                update={"job_id": f"contender-{index}", "marker": f"contender-{index}"}
            )
            child = subprocess.Popen(  # noqa: S603 - fixed local test program
                [
                    sys.executable,
                    "-c",
                    script,
                    pool.identity.model_dump_json(),
                    str(pool.local_root),
                    contender.model_dump_json(),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )
            children.append(child)
        for child in children:
            assert child.stdout is not None
            assert child.stdout.readline().strip() == "ready"
        for child in children:
            assert child.stdin is not None
            child.stdin.write("start\n")
            child.stdin.flush()
        results = []
        for child in children:
            assert child.stdout is not None
            results.append(child.stdout.readline().strip())
        assert sorted(results) == ["acquired", "busy"]
        assert pool.reserved() == {GPU_A, GPU_B}
    finally:
        for child in children:
            if child.stdin is not None:
                child.stdin.close()
            child.wait(timeout=5)
            if child.stdout is not None:
                child.stdout.close()
    assert pool.reserved() == set()


def test_legacy_generation_zero_claim_remains_recoverable_after_reallocation(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.queue.storage import atomic_write

    pool, claim = pool_and_claim(tmp_path)
    payload = claim.model_dump(exclude={"generations"})
    import json

    for uuid in claim.devices:
        atomic_write(pool.claim_path(uuid), json.dumps(payload))
    assert pool.reserved() == set()
    replacement = pool.acquire(
        claim.model_copy(update={"job_id": "replacement", "marker": "replacement"})
    )
    assert replacement is not None
    try:
        assert pool.claim_for(claim.job_id) == claim
        recovered = pool.acquire_recovery(claim)
        try:
            recovered.release_verified()
        finally:
            recovered.close()
        assert pool.claim_for(claim.job_id) is None
        assert pool.reserved() == {GPU_A, GPU_B}
    finally:
        replacement.release_verified()
        replacement.close()


def test_same_job_retry_selects_new_process_evidence_and_preserves_old_marker(
    tmp_path: Path,
) -> None:
    pool, claim = pool_and_claim(tmp_path)
    old = pool.acquire(claim)
    assert old is not None
    old.close()
    retried = pool.acquire(claim.model_copy(update={"marker": "retry", "ownership_since": 10}))
    assert retried is not None
    try:
        assert pool.claim_for(claim.job_id) == retried.claim
        assert pool.claim_for(claim.job_id, marker=claim.marker) == old.claim
    finally:
        retried.release_verified()
        retried.close()


@pytest.mark.parametrize("freed_index", [0, 1], ids=["retained-gpu", "released-sibling"])
@pytest.mark.parametrize("recover", [False, True], ids=["live-completion", "recovered-completion"])
def test_handoff_completion_removes_revoked_history_without_touching_new_allocation(
    tmp_path: Path,
    freed_index: int,
    recover: bool,
) -> None:
    pool, claim = pool_and_claim(tmp_path)
    old = pool.acquire(claim)
    assert old is not None
    newer = None
    try:
        freed_uuid = claim.devices[freed_index]
        GPUControls(pool, physical_uuids=lambda: claim.devices).release(str(freed_index))
        newer = pool.acquire(
            claim.model_copy(
                update={
                    "job_id": "newer",
                    "marker": "newer",
                    "devices": (freed_uuid,),
                }
            )
        )
        assert newer is not None
        reduced = old.retain_first()
        assert reduced.devices == (GPU_A,)
        if recover:
            old.close()
            old = pool.acquire_recovery(reduced)
        old.release_verified()
        assert pool.claim_for(claim.job_id) is None
        assert pool.claim_for("newer") == newer.claim
        assert pool.allocated_devices("newer") == (freed_uuid,)
        assert pool.reserved() == {freed_uuid}
    finally:
        old.close()
        if newer is not None:
            newer.release_verified()
            newer.close()


@pytest.mark.parametrize("newer_live", [False, True], ids=["stale-successor", "live-successor"])
def test_interrupted_handoff_never_reuses_missing_siblings_lock_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    newer_live: bool,
) -> None:
    from clearml_yolo.adapters.queue import locks

    pool, claim = pool_and_claim(tmp_path)
    old = pool.acquire(claim)
    assert old is not None
    original_write = locks._write_claim

    def interrupted(path: Path, value: GuardianClaim | None) -> None:
        if path == pool.claim_path(GPU_A) and value is not None:
            raise OSError("interrupted before reduced retained record")
        original_write(path, value)

    with monkeypatch.context() as fail:
        fail.setattr(locks, "_write_claim", interrupted)
        with pytest.raises(OSError, match="before reduced"):
            old.retain_first()
    original_evidence = pool.claim_for(claim.job_id)
    assert original_evidence == old.claim
    old.close()
    assert not pool.claim_path(GPU_B).exists()
    newer = pool.acquire(
        claim.model_copy(
            update={
                "job_id": "newer",
                "marker": "newer",
                "devices": (GPU_B,),
            }
        )
    )
    assert newer is not None
    if not newer_live:
        newer.close()
    # Original recovery must remain independent of both a live and stale successor.
    recovered = pool.acquire_recovery(original_evidence)
    try:
        recovered.release_verified()
        assert pool.claim_for(claim.job_id) is None
        assert pool.claim_for("newer") == newer.claim
        assert pool.reserved() == ({GPU_B} if newer_live else set())
    finally:
        recovered.close()
        newer.close()
    newer_recovery = pool.acquire_recovery(newer.claim)
    try:
        newer_recovery.release_verified()
    finally:
        newer_recovery.close()
