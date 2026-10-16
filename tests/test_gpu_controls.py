"""Reasonless GPU declarations use real isolated locks without inspecting work."""

import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest

from clearml_yolo.adapters.queue.gpu_controls import GPUControls
from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.core.gpu_identity import identity_label
from clearml_yolo.core.queue import GPUHold, GuardianClaim, WorkerIdentity

pytestmark = pytest.mark.gpu_controls
GPU_A = "GPU-11111111-1111-1111-1111-111111111111"
GPU_B = "GPU-22222222-2222-2222-2222-222222222222"


@dataclass
class ControlCase:
    pool: LocalGPULocks
    controls: GPUControls
    store: NFSQueueStore
    claim: GuardianClaim


@pytest.fixture
def control_case(tmp_path: Path) -> ControlCase:
    from clearml_yolo.adapters.queue.identity import process_ticks
    from clearml_yolo.core.queue import JobSnapshot

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="control-test", boot_id="boot")
    local_root = tmp_path / "local"
    store = NFSQueueStore(tmp_path / "queue", identity, local_root=local_root)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(tmp_path),
                cwd=str(tmp_path),
                interpreter=sys.executable,
                package_version="1",
                package_identity="test",
            ),
        )
    )[0]
    pool = LocalGPULocks(identity, local_root)
    claim = GuardianClaim(
        job_id=job.id,
        owner_uid=os.geteuid(),
        host_id=identity.host_id,
        boot_id="boot",
        queue_root=str(store.root),
        devices=(GPU_A, GPU_B),
        marker=uuid4().hex,
        guardian_pid=99999999,
        guardian_born=1,
        ownership_since=process_ticks(),
    )
    lease = pool.acquire(claim)
    assert lease is not None
    lease.close()
    store.update(job.id, "recovery_required", devices=claim.devices)
    return ControlCase(pool, GPUControls(pool, physical_uuids=lambda: (GPU_A, GPU_B)), store, claim)


def test_physical_identity_public_api_ignores_cuda_visibility_and_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import gpu_resources

    class NVML:
        def nvmlInit(self) -> None:  # noqa: N802 - NVML binding contract
            pass

        def nvmlShutdown(self) -> None:  # noqa: N802 - NVML binding contract
            pass

        def nvmlDeviceGetCount(self) -> int:  # noqa: N802 - NVML binding contract
            return 2

        def nvmlDeviceGetHandleByIndex(self, index: int) -> int:  # noqa: N802
            return index

        def nvmlDeviceGetUUID(self, handle: int) -> str:  # noqa: N802
            return ("GPU-a", "GPU-b")[handle]

    monkeypatch.setattr(gpu_resources, "_nvml", NVML)
    for visibility in ("1,0", "1", ""):
        monkeypatch.setenv("CUDA_VISIBLE_DEVICES", visibility)
        assert gpu_resources.GPUInventory().physical_uuids() == ("GPU-a", "GPU-b")


def test_disable_and_enable_are_reasonless_and_cross_root(control_case: ControlCase) -> None:
    case = control_case
    hold = case.controls.disable("0")
    assert hold.uuid == GPU_A
    other = LocalGPULocks(case.pool.identity, case.pool.local_root)
    contender = case.claim.model_copy(update={"job_id": "other", "queue_root": "/other-root"})
    assert other.reserved() == {GPU_A}
    assert other.acquire(contender) is None
    case.controls.enable("0")
    lease = other.acquire(contender)
    assert lease is not None
    lease.release_verified()
    lease.close()


def test_free_selected_gpu_clears_holds_without_changing_job(control_case: ControlCase) -> None:
    case = control_case
    case.controls.disable("0")
    case.controls.disable("1")
    before = case.store.view().jobs[0]
    evidence = case.pool.claim_for(case.claim.job_id)
    result = case.controls.release("0")
    assert result.uuid == GPU_A
    assert result.actor_uid == os.geteuid()
    assert result.generation == 1
    assert case.pool.reserved() == {GPU_B}
    assert case.store.view().jobs[0] == before
    assert case.pool.claim_for(case.claim.job_id) == evidence
    assert case.controls.release("0").generation == 2
    assert case.pool.reserved() == {GPU_B}


def test_free_never_reads_queue_memory_processes_or_existing_claims(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import identity
    from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory
    from clearml_yolo.adapters.runtime.process_tree import LinuxProcessTree

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Manual free examined existing work")

    case = control_case
    monkeypatch.setattr(NFSQueueStore, "__init__", forbidden)
    monkeypatch.setattr(GPUInventory, "snapshot", forbidden)
    monkeypatch.setattr(identity, "process_birth", forbidden)
    monkeypatch.setattr(LinuxProcessTree, "terminate", forbidden)
    monkeypatch.setattr(case.pool, "transaction_claims", forbidden)
    monkeypatch.setattr(case.pool, "_holds", forbidden)
    result = case.controls.release("0")
    assert result.uuid == GPU_A


def test_failed_generation_write_is_atomic_and_retry_succeeds(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import generations

    case = control_case
    hold = case.controls.disable("0")

    def interrupted(_path: Path, _payload: str) -> None:
        raise OSError("injected generation write failure")

    with monkeypatch.context() as fail:
        fail.setattr(generations, "atomic_write", interrupted)
        with pytest.raises(OSError, match="generation write failure"):
            case.controls.release("0")
    assert case.pool.holds() == (hold,)
    assert not tuple(case.pool.root.glob("generation-*.json"))
    assert case.controls.release("0").generation == 1
    assert case.pool.holds() == ()


def test_absent_gpu_short_selector_can_free_without_inventory(control_case: ControlCase) -> None:
    absent = GPUControls(control_case.pool, physical_uuids=lambda: ())
    assert all(card.physical_index is None for card in absent.list())
    assert absent.release(identity_label(GPU_A)).uuid == GPU_A
    assert absent.release(GPU_B).uuid == GPU_B


@pytest.mark.parametrize(
    "selector", ["-1", "+1", "1.0", "0,1", "GPU-111", "MIG-111", " 0 ", "", "3"]
)
def test_invalid_selectors_do_not_write_holds(control_case: ControlCase, selector: str) -> None:
    with pytest.raises(ValueError, match=r"selector|index"):
        control_case.controls.disable(selector)
    assert control_case.pool.holds() == ()


def test_generation_fence_rejects_old_workers_without_preempting_lease(
    control_case: ControlCase,
) -> None:
    from clearml_yolo.core.queue import QUEUE_COMPATIBILITY

    case = control_case
    lease = case.pool.acquire_recovery(case.claim)
    try:
        records = [
            GuardianClaim.model_validate_json(path.read_bytes())
            for path in case.pool.root.glob("gpu-*.claim.json")
        ]
        assert any(
            record.compatibility not in {QUEUE_COMPATIBILITY, "shared-cy-queue-gpu-controls-v1"}
            for record in records
        )
        assert case.pool.reserved() == {GPU_A, GPU_B}
        case.controls.release("0")
        lease.persist(lease.claim)
        lease.release_verified()
        assert case.pool.reserved() == set()
    finally:
        lease.close()


def test_worker_supervision_fails_before_registration_or_fence(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import runtime

    case = control_case
    processes = runtime.QueueProcesses(
        case.store, case.pool.identity, local_root=case.pool.local_root
    )

    fence = (case.pool.root / "gpu-controls.claim.json").read_bytes()
    monkeypatch.delattr(os, "pidfd_open")
    with pytest.raises(RuntimeError, match="pidfd_open"), processes.worker_registration():
        pytest.fail("Unsupported worker registered")
    assert not (case.store.actor_root / "worker.json").exists()
    assert not tuple(case.pool.root.glob("worker-*.lock"))
    assert (case.pool.root / "gpu-controls.claim.json").read_bytes() == fence


def test_selected_interpreter_supervision_fails_before_prepare_start(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import runtime

    case = control_case
    processes = runtime.QueueProcesses(
        case.store, case.pool.identity, local_root=case.pool.local_root
    )
    job = case.store.update(case.claim.job_id, "pending")

    def unsupported(interpreter: str) -> None:
        assert interpreter == sys.executable
        raise RuntimeError("unsupported selected interpreter")

    monkeypatch.setattr(runtime, "check_interpreter_supervision", unsupported)
    with pytest.raises(RuntimeError, match="unsupported selected"):
        processes.start(job, (GPU_A,))
    assert case.store.view().jobs[0].state == "pending"
    assert not (case.store.snapshot_path(job.id).parent / "guardian.json").exists()
    assert case.pool.claim_for(job.id) == case.claim


def test_guardian_supervision_fails_before_capacity_or_launch(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import guardian
    from clearml_yolo.adapters.queue.records import GuardianPayload

    case = control_case
    directory = case.store.snapshot_path(case.claim.job_id).parent
    payload = GuardianPayload(
        job_id=case.claim.job_id,
        identity=case.pool.identity,
        queue_root=str(case.store.root),
        local_root=str(case.pool.local_root),
        devices=(GPU_A,),
        marker="guardian-test",
        ownership_since=0,
        argv=(sys.executable, "-c", "raise SystemExit(99)"),
        snapshot_path=str(case.store.snapshot_path(case.claim.job_id)),
        cwd=str(directory),
        project_root=str(directory),
        start_gate=str(directory / "gate"),
    )
    path = directory / "guardian.json"
    path.write_text(payload.model_dump_json(), encoding="utf-8")

    monkeypatch.delattr(signal, "pidfd_send_signal")
    runner = guardian._Guardian(path)
    with pytest.raises(RuntimeError, match="pidfd_send_signal"):
        runner._prepare()
    assert runner.child is None
    assert runner.lease is None
    assert case.pool.claim_for(case.claim.job_id) == case.claim


def test_snapshot_interpreter_missing_api_is_probed_in_fresh_process(
    control_case: ControlCase,
) -> None:
    from clearml_yolo.adapters.queue import runtime
    from clearml_yolo.core.queue import JobSnapshot

    case = control_case
    script = case.store.root / "unsupported-python"
    script.write_text(
        f"#!{sys.executable}\nimport os, sys\ndel os.pidfd_open\nexec(sys.argv[2])\n",
        encoding="utf-8",
    )
    script.chmod(0o700)
    original = case.store.load_snapshot(case.claim.job_id)
    job = case.store.submit(
        (
            JobSnapshot.model_validate(
                original.model_dump() | {"id": "", "interpreter": str(script)},
            ),
        )
    )[0]
    processes = runtime.QueueProcesses(
        case.store, case.pool.identity, local_root=case.pool.local_root
    )
    with pytest.raises(RuntimeError, match="pidfd_open"):
        processes.start(job, (GPU_A,))
    assert next(item for item in case.store.view().jobs if item.id == job.id).state == "pending"
    assert not (case.store.snapshot_path(job.id).parent / "guardian.json").exists()
    assert case.pool.claim_for(job.id) is None


def test_free_invalidates_foreign_hold_without_reading_or_deleting_it(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protected foreign records need no mutation; actual UID switching is not required."""
    from clearml_yolo.adapters.queue.storage import atomic_write

    case = control_case
    foreign_uid = os.geteuid() + 1
    hold = GPUHold(
        uuid=GPU_A, owner_uid=foreign_uid, host_id=case.pool.identity.host_id, created_at=0
    )
    path = case.pool.hold_path(GPU_A, foreign_uid)
    atomic_write(path, hold.model_dump_json())
    before = path.read_bytes()
    original_read = Path.read_bytes
    original_unlink = Path.unlink

    def protected_read(selected: Path) -> bytes:
        if selected == path:
            pytest.fail("Manual free inspected a foreign hold")
        return original_read(selected)

    def protected_unlink(selected: Path, *, missing_ok: bool = False) -> None:
        if selected == path:
            pytest.fail("Manual free deleted a foreign hold")
        original_unlink(selected, missing_ok=missing_ok)

    with monkeypatch.context() as protected:
        protected.setattr(Path, "read_bytes", protected_read)
        protected.setattr(Path, "unlink", protected_unlink)
        case.controls.release("0")
        assert case.pool.holds() == ()
    assert path.read_bytes() == before


def test_enable_only_removes_callers_hold(control_case: ControlCase) -> None:
    from clearml_yolo.adapters.queue.storage import atomic_write

    case = control_case
    own = case.controls.disable("0")
    foreign_path = case.pool.hold_path(GPU_A, own.owner_uid + 1)
    atomic_write(foreign_path, "foreign record must not be touched")
    case.controls.enable("0")
    assert not case.pool.hold_path(GPU_A, own.owner_uid).exists()
    assert foreign_path.read_text() == "foreign record must not be touched"


def test_interruption_after_generation_commit_keeps_free_durable(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import generations

    case = control_case
    case.controls.disable("0")
    from clearml_yolo.adapters.queue.storage import atomic_write

    write = atomic_write

    def committed_then_interrupted(path: Path, payload: str) -> None:
        write(path, payload)
        raise OSError("interrupted after commit")

    with monkeypatch.context() as fail:
        fail.setattr(generations, "atomic_write", committed_then_interrupted)
        with pytest.raises(OSError, match="after commit"):
            case.controls.release("0")
    assert case.pool.holds() == ()
    assert case.controls.release("0").generation == 2
