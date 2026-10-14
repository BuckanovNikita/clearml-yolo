"""GPU operator controls use real isolated host locks and durable metadata."""

import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest

from clearml_yolo.adapters.queue.gpu_controls import GPUControls
from clearml_yolo.adapters.queue.locks import LocalGPULocks
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity, claim_token

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
def control_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ControlCase:
    from clearml_yolo.adapters.queue import coordination, storage
    from clearml_yolo.adapters.queue.identity import process_ticks
    from clearml_yolo.core.queue import JobSnapshot

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="control-test", boot_id="boot")
    local_root = tmp_path / "local"
    monkeypatch.setattr(
        storage,
        "host_transaction",
        lambda host: coordination.host_transaction(host, root=local_root),
    )
    store = NFSQueueStore(tmp_path / "queue", identity)
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


def test_hold_blocks_cross_root_admission_and_enable_restores_it(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.gpu_controls import GPUControls
    from clearml_yolo.adapters.queue.locks import LocalGPULocks
    from clearml_yolo.core.queue import GuardianClaim, WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="control-test", boot_id="boot")
    first = LocalGPULocks(identity, tmp_path / "local")
    controls = GPUControls(first, physical_uuids=lambda: ("GPU-a", "GPU-b"))
    hold = controls.disable("0", reason="maintenance")
    assert hold.uuid == "GPU-a"
    other = LocalGPULocks(identity, tmp_path / "local")
    claim = GuardianClaim(
        job_id="job",
        owner_uid=os.geteuid(),
        host_id=identity.host_id,
        boot_id="boot",
        queue_root="/other-root",
        devices=("GPU-a",),
        marker="marker",
        guardian_pid=0,
        guardian_born=0,
    )
    assert other.acquire(claim) is None
    assert other.reserved() == {"GPU-a"}
    controls.enable("0")
    lease = other.acquire(claim)
    assert lease is not None
    lease.release_verified()
    lease.close()


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


def test_release_reclaims_whole_allocation_retains_audit_and_fails_job(
    control_case: ControlCase,
) -> None:
    case = control_case
    token = claim_token(case.claim)
    audit = case.controls.release("0", token=token, reason="operator recovery")
    assert audit.claim == case.claim
    assert audit.finished
    assert audit.cleanup_verified
    assert not audit.forced
    assert case.pool.reserved() == set()
    assert case.store.view().jobs[0].state == "failed"
    assert "Manual GPU release" in (case.store.view().jobs[0].error or "")
    assert case.store.load_snapshot(case.claim.job_id).id == case.claim.job_id
    assert case.controls.release(GPU_B, token=token, reason="retry") == audit


def test_release_stale_token_preserves_claim_and_job(control_case: ControlCase) -> None:
    case = control_case
    with pytest.raises(RuntimeError, match="Stale claim token"):
        case.controls.release("0", token="0" * 64, reason="stale")
    assert case.pool.reserved() == {GPU_A, GPU_B}
    assert case.store.view().jobs[0].state == "recovery_required"
    assert not tuple(case.pool.root.glob("release-*.json"))


def test_force_release_refuses_real_held_lock(control_case: ControlCase) -> None:
    case = control_case
    lease = case.pool.acquire_recovery(case.claim)
    try:
        with pytest.raises(RuntimeError, match="locks"):
            case.controls.release("1", token=claim_token(case.claim), reason="force", force=True)
        assert case.pool.reserved() == {GPU_A, GPU_B}
    finally:
        lease.close()


def test_force_release_refuses_live_guardian_without_lock(control_case: ControlCase) -> None:
    from clearml_yolo.adapters.queue.identity import process_birth

    case = control_case
    changed = case.claim.model_copy(
        update={"guardian_pid": os.getpid(), "guardian_born": process_birth(os.getpid())}
    )
    lease = case.pool.acquire_recovery(case.claim)
    lease.persist(changed)
    lease.close()
    with pytest.raises(RuntimeError, match="Guardian is still alive"):
        case.controls.release("0", token=claim_token(changed), reason="force", force=True)
    assert case.pool.reserved() == {GPU_A, GPU_B}


def test_force_release_refuses_real_owned_descendant_and_normal_release_cleans_it(
    control_case: ControlCase,
) -> None:
    from clearml_yolo.adapters.queue.identity import process_birth
    from clearml_yolo.adapters.runtime.process_tree import OWNER_ENV

    case = control_case
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        env=dict(os.environ) | {OWNER_ENV: case.claim.marker},
    )
    try:
        changed = case.claim.model_copy(
            update={"child_pid": child.pid, "child_born": process_birth(child.pid)}
        )
        lease = case.pool.acquire_recovery(case.claim)
        lease.persist(changed)
        lease.close()
        with pytest.raises(RuntimeError, match="descendant"):
            case.controls.release("0", token=claim_token(changed), reason="force", force=True)
        assert child.poll() is None
        audit = case.controls.release("0", token=claim_token(changed), reason="verified")
        child.wait(timeout=5)
        assert child.returncode == -signal.SIGTERM
        assert audit.cleanup_verified
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)


def test_force_override_audits_unverifiable_evidence_without_signals(
    control_case: ControlCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.runtime.process_tree import (
        LinuxProcessTree,
        UnverifiableProcessTreeError,
    )

    def denied(_tree: LinuxProcessTree) -> bool:
        raise UnverifiableProcessTreeError("injected inaccessible evidence")

    def no_signals(_tree: LinuxProcessTree, _signal: signal.Signals) -> None:
        pytest.fail("Force release signalled an owned process")

    case = control_case
    monkeypatch.setattr(LinuxProcessTree, "running", denied)
    monkeypatch.setattr(LinuxProcessTree, "signal", no_signals)
    audit = case.controls.release(
        "0", token=claim_token(case.claim), reason="unverifiable stale metadata", force=True
    )
    assert audit.forced
    assert not audit.cleanup_verified
    assert "unverified cleanup override" in (case.store.view().jobs[0].error or "")


def test_release_audit_precedes_partial_removal_and_retry_finishes_all_devices(
    control_case: ControlCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = control_case
    original = Path.unlink
    token = claim_token(case.claim)
    count = 0

    def interrupted(path: Path, *, missing_ok: bool = False) -> None:
        nonlocal count
        if path in (case.pool.claim_path(GPU_A), case.pool.claim_path(GPU_B)):
            assert (case.pool.root / f"release-{token}.json").is_file()
            from clearml_yolo.core.queue import PublicJob

            public = case.store.actor_root / "jobs" / case.claim.job_id / "public.json"
            assert PublicJob.model_validate_json(public.read_bytes()).state == "failed"
            count += 1
            if count == 2:
                raise OSError("injected partial claim removal")
        original(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", interrupted)
    with pytest.raises(OSError, match="partial claim removal"):
        case.controls.release("0", token=token, reason="partial")
    monkeypatch.setattr(Path, "unlink", original)
    assert case.pool.reserved() == {GPU_A, GPU_B}
    audit = case.controls.release(GPU_A, token=token, reason="retry")
    assert audit.finished
    assert audit.reason == "partial"
    assert case.pool.reserved() == set()


@pytest.mark.parametrize(
    "selector", ["-1", "+1", "1.0", "0,1", "GPU-111", "MIG-111", " 0 ", "", "3"]
)
def test_invalid_selectors_do_not_write_holds(control_case: ControlCase, selector: str) -> None:
    with pytest.raises(ValueError, match=r"selector|index"):
        control_case.controls.disable(selector, reason="maintenance")
    assert control_case.pool.holds() == ()


def test_uuid_release_works_for_absent_physical_card(control_case: ControlCase) -> None:
    case = control_case
    absent = GPUControls(case.pool, physical_uuids=lambda: ())
    assert absent.list()[0].physical_index is None
    assert absent.release(GPU_A, token=claim_token(case.claim), reason="removed card").finished


def test_control_fence_stops_legacy_scan_without_preempting_existing_lease(
    control_case: ControlCase,
) -> None:
    from clearml_yolo.core.queue import QUEUE_COMPATIBILITY

    case = control_case
    lease = case.pool.acquire_recovery(case.claim)
    try:
        case.pool.ensure_control_fence()
        records = [
            GuardianClaim.model_validate_json(path.read_bytes())
            for path in case.pool.root.glob("gpu-*.claim.json")
        ]
        assert any(claim.compatibility != QUEUE_COMPATIBILITY for claim in records)
        assert case.pool.reserved() == {GPU_A, GPU_B}
        lease.release_verified()
        assert case.pool.reserved() == set()
        assert (case.pool.root / "gpu-controls.claim.json").exists()
    finally:
        lease.close()


def test_enable_keeps_another_owners_hold_and_fence(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = control_case
    hold = case.controls.disable("0", reason="owner maintenance")
    fence = (case.pool.root / "gpu-controls.claim.json").read_bytes()
    with monkeypatch.context() as other:
        other.setattr(os, "geteuid", lambda: hold.owner_uid + 1)
        foreign = LocalGPULocks(
            case.pool.identity.model_copy(update={"owner_uid": hold.owner_uid + 1}),
            case.pool.local_root,
        )
        GPUControls(foreign, physical_uuids=lambda: (GPU_A, GPU_B)).enable("0")
    assert case.pool.holds() == (hold,)
    assert (case.pool.root / "gpu-controls.claim.json").read_bytes() == fence


def test_release_refuses_foreign_owner_before_audit(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = control_case
    with monkeypatch.context() as other:
        other.setattr(os, "geteuid", lambda: case.claim.owner_uid + 1)
        with pytest.raises(PermissionError, match="effective owner"):
            case.controls.release("0", token=claim_token(case.claim), reason="foreign", force=True)
    assert case.pool.reserved() == {GPU_A, GPU_B}
    assert not tuple(case.pool.root.glob("release-*.json"))


def test_force_denied_guardian_cannot_hide_confirmed_live_child(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import gpu_controls
    from clearml_yolo.adapters.queue.identity import process_birth

    case = control_case
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        born = process_birth(child.pid)
        assert born is not None
        changed = case.claim.model_copy(update={"identities": ((child.pid, born),)})
        lease = case.pool.acquire_recovery(case.claim)
        lease.persist(changed)
        lease.close()

        def denied_guardian(pid: int) -> int | None:
            if pid == case.claim.guardian_pid:
                raise PermissionError("injected guardian stat denial")
            return process_birth(pid)

        monkeypatch.setattr(gpu_controls, "process_birth", denied_guardian)
        with pytest.raises(RuntimeError, match="descendant"):
            case.controls.release("0", token=claim_token(changed), reason="force", force=True)
        assert child.poll() is None
        assert case.pool.reserved() == {GPU_A, GPU_B}
    finally:
        child.kill()
        child.wait(timeout=5)


def test_merge_rejects_conflicting_descendant_evidence(control_case: ControlCase) -> None:
    from clearml_yolo.adapters.queue.storage import atomic_write

    case = control_case
    first = case.claim.model_copy(update={"identities": ((123, 456),)})
    second = case.claim.model_copy(update={"identities": ((123, 789),)})
    atomic_write(case.pool.claim_path(GPU_A), first.model_dump_json())
    atomic_write(case.pool.claim_path(GPU_B), second.model_dump_json())
    with pytest.raises(RuntimeError, match="conflicting process birth"):
        case.controls.release("0", token=claim_token(first), reason="conflicting")
    assert case.pool.reserved() == {GPU_A, GPU_B}


@pytest.mark.parametrize("force", [True, False])
def test_interrupted_audit_retry_requires_original_force_mode(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
    force: bool,
) -> None:
    case = control_case
    original = Path.unlink

    def interrupted(path: Path, *, missing_ok: bool = False) -> None:
        if path == case.pool.claim_path(GPU_A):
            raise OSError("injected interrupted release")
        original(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", interrupted)
    with pytest.raises(OSError, match="interrupted release"):
        case.controls.release("0", token=claim_token(case.claim), reason="first", force=force)
    monkeypatch.setattr(Path, "unlink", original)
    with pytest.raises(ValueError, match="original force mode"):
        case.controls.release("0", token=claim_token(case.claim), reason="second", force=not force)
    assert case.pool.reserved() == {GPU_A, GPU_B}
    assert case.controls.release(
        "0", token=claim_token(case.claim), reason="retry", force=force
    ).finished


def test_admission_rechecks_hold_after_scheduler_observation(control_case: ControlCase) -> None:
    case = control_case
    lease = case.pool.acquire_recovery(case.claim)
    lease.release_verified()
    lease.close()
    assert case.pool.reserved() == set()
    case.controls.disable("0", reason="admission race")
    other = LocalGPULocks(case.pool.identity, case.pool.local_root)
    contender = case.claim.model_copy(update={"queue_root": "/second-root", "job_id": "contender"})
    assert other.acquire(contender) is None
    assert other.reserved() == {GPU_A}


def test_release_rechecks_current_token_after_competing_claim_change(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = control_case
    original = NFSQueueStore.__init__
    replacement = case.claim.model_copy(update={"marker": uuid4().hex})

    def competing(store: NFSQueueStore, root: Path, identity: WorkerIdentity) -> None:
        lease = case.pool.acquire_recovery(case.claim)
        lease.persist(replacement)
        lease.close()
        original(store, root, identity)

    monkeypatch.setattr(NFSQueueStore, "__init__", competing)
    with pytest.raises(RuntimeError, match="Stale claim token"):
        case.controls.release("0", token=claim_token(case.claim), reason="competing")
    assert case.pool.claim_for(case.claim.job_id) == replacement
    assert not tuple(case.pool.root.glob("release-*.json"))


def test_failed_audit_write_preserves_capacity_and_original_state(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import gpu_controls

    def interrupted(_path: Path, _payload: str) -> None:
        raise OSError("injected audit write failure")

    case = control_case
    monkeypatch.setattr(gpu_controls, "atomic_write", interrupted)
    with pytest.raises(OSError, match="audit write failure"):
        case.controls.release("0", token=claim_token(case.claim), reason="failed audit")
    assert case.pool.reserved() == {GPU_A, GPU_B}
    assert case.store.view().jobs[0].state == "recovery_required"
    assert not tuple(case.pool.root.glob("release-*.json"))


@pytest.mark.parametrize("write_failure", [False, True])
def test_release_retry_durably_downgrades_newly_uncertain_cleanup(
    control_case: ControlCase, monkeypatch: pytest.MonkeyPatch, write_failure: bool
) -> None:
    from clearml_yolo.adapters.queue import gpu_controls
    from clearml_yolo.core.queue import GPUReleaseAudit

    case = control_case
    token = claim_token(case.claim)
    audit_path = case.pool.root / f"release-{token}.json"

    def interrupted(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected transaction interruption")

    with monkeypatch.context() as initial:
        initial.setattr(GPUControls, "_verify_cleanup", lambda *_args, **_kwargs: True)
        initial.setattr(NFSQueueStore, "transaction_update", interrupted)
        with pytest.raises(OSError, match="transaction interruption"):
            case.controls.release("0", token=token, reason="original", force=True)
    assert GPUReleaseAudit.model_validate_json(audit_path.read_text()).cleanup_verified
    monkeypatch.setattr(GPUControls, "_verify_cleanup", lambda *_args, **_kwargs: False)
    if write_failure:
        monkeypatch.setattr(gpu_controls, "atomic_write", interrupted)
        with pytest.raises(OSError, match="transaction interruption"):
            case.controls.release("0", token=token, reason="retry", force=True)
        assert case.pool.reserved() == {GPU_A, GPU_B}
        assert case.store.view().jobs[0].state == "recovery_required"
    else:
        audit = case.controls.release("0", token=token, reason="retry", force=True)
        assert audit.finished
        assert not audit.cleanup_verified
        assert audit.reason == "original"
        assert GPUReleaseAudit.model_validate_json(audit_path.read_text()) == audit
        assert "unverified cleanup override" in (case.store.view().jobs[0].error or "")


def test_worker_supervision_fails_before_registration_or_fence(
    control_case: ControlCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.queue import runtime

    case = control_case
    processes = runtime.QueueProcesses(
        case.store, case.pool.identity, local_root=case.pool.local_root
    )

    monkeypatch.delattr(os, "pidfd_open")
    with pytest.raises(RuntimeError, match="pidfd_open"), processes.worker_registration():
        pytest.fail("Unsupported worker registered")
    assert not (case.store.actor_root / "worker.json").exists()
    assert not tuple(case.pool.root.glob("worker-*.lock"))
    assert not (case.pool.root / "gpu-controls.claim.json").exists()


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


def test_force_finds_marked_live_descendant_without_persisted_child_evidence(
    control_case: ControlCase,
) -> None:
    from clearml_yolo.adapters.runtime.process_tree import OWNER_ENV

    case = control_case
    claim = case.claim.model_copy(update={"ownership_since": 0})
    lease = case.pool.acquire_recovery(case.claim)
    lease.persist(claim)
    lease.close()
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        env=dict(os.environ) | {OWNER_ENV: case.claim.marker},
    )
    try:
        with pytest.raises(RuntimeError, match="descendant"):
            case.controls.release("0", token=claim_token(claim), reason="force", force=True)
        assert child.poll() is None
    finally:
        child.kill()
        child.wait(timeout=5)


def test_gpu_cli_lists_tokens_and_runs_owned_controls(
    control_case: ControlCase,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from clearml_yolo.adapters.queue.inventory import QueueGPUInventory
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.entrypoints.queue import _gpu_operation, _parser

    case = control_case
    service = QueueService(
        case.store,
        QueueGPUInventory(),
        QueueProcesses(case.store, case.pool.identity, local_root=case.pool.local_root),
        case.pool.identity,
        controls=case.controls,
    )
    _gpu_operation(service, _parser().parse_args(["gpu", "list", "--json"]))
    cards = json.loads(capsys.readouterr().out)
    assert [(card["physical_index"], card["uuid"]) for card in cards] == [(0, GPU_A), (1, GPU_B)]
    assert {card["claim_token"] for card in cards} == {claim_token(case.claim)}
    _gpu_operation(
        service, _parser().parse_args(["gpu", "disable", "1", "--reason", "CLI maintenance"])
    )
    assert json.loads(capsys.readouterr().out)["uuid"] == GPU_B
    _gpu_operation(
        service,
        _parser().parse_args(
            [
                "gpu",
                "release",
                "0",
                "--claim-token",
                claim_token(case.claim),
                "--reason",
                "CLI release",
            ]
        ),
    )
    assert json.loads(capsys.readouterr().out)["finished"] is True
    assert case.pool.reserved() == {GPU_B}
    _gpu_operation(service, _parser().parse_args(["gpu", "enable", "1"]))
    assert capsys.readouterr().out == "Own GPU hold removed\n"
    assert case.pool.reserved() == set()


@pytest.mark.parametrize("operation", ["disable", "release"])
def test_gpu_cli_requires_release_token_and_explicit_reason(operation: str) -> None:
    from clearml_yolo.entrypoints.queue import _parser

    with pytest.raises(SystemExit) as exit_info:
        _parser().parse_args(["gpu", operation, "0"])
    assert exit_info.value.code == 2
