"""Opt-in Linux acceptance with temporary real users; run --help before --run.

The root controller only provisions, switches identities and removes its fixtures.
Queue operations and guarded subprocesses run as two locked-password test users.
Synthetic host/device facts isolate production coordination and physical hardware.
"""

import argparse
import grp
import json
import os
import pwd
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from types import FrameType
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict

from clearml_yolo.adapters.queue.coordination import bind_coordination_root
from clearml_yolo.adapters.queue.identity import process_birth
from clearml_yolo.adapters.queue.records import GuardianPayload
from clearml_yolo.adapters.queue.runtime import QueueProcesses
from clearml_yolo.adapters.queue.settings import load_queue_settings
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import (
    GPUObservation,
    GuardianClaim,
    JobSnapshot,
    PublicJob,
    WorkerIdentity,
)

_HOST = "multiuser-acceptance"
_JOBS_PER_USER = 6
_TIMEOUT = 45
_REPO = Path(__file__).resolve().parents[1]


class _Account(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    label: Literal["A", "B"]
    uid: int
    gid: int
    home: str


class _Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: str
    group: str
    gid: int
    accounts: tuple[_Account, ...] = ()


def _run(argv: Sequence[str], *, timeout: float = _TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed local provisioning/test commands, never a shell
        argv, check=True, capture_output=True, text=True, timeout=timeout
    )


def _wait_until(predicate: Callable[[], bool], description: str) -> None:
    deadline = time.monotonic() + _TIMEOUT
    while not predicate():
        if time.monotonic() >= deadline:
            raise TimeoutError(description)
        time.sleep(0.02)


def _denied(operation: Callable[[], object]) -> None:
    try:
        operation()
    except PermissionError:
        return
    raise AssertionError("A foreign owner operation unexpectedly succeeded")


def _reject_binding(root: Path, bootstrap: Path) -> None:
    try:
        bind_coordination_root(_HOST, root, bootstrap_root=bootstrap)
    except RuntimeError:
        return
    raise AssertionError("A conflicting coordination root was accepted")


class _Inventory:
    def snapshot(self) -> tuple[GPUObservation, ...]:
        return (GPUObservation(uuid="GPU-test", available=True),)


_WORKLOAD = """
import fcntl,json,os,sys,time
from pathlib import Path
with open(sys.argv[1], 'r+') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    Path('workload-owner.json').write_text(json.dumps({'uid': os.geteuid()}))
    progress = Path(os.environ['CY_PROGRESS_FILE'])
    progress.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    progress.write_text(json.dumps({'progress': 'Controlled workload complete'}))
    progress.chmod(0o600)
    print('Controlled workload complete', flush=True)
    time.sleep(0.5)
"""


class _Actor:
    def __init__(self, root: Path, label: str) -> None:
        self.root = root
        self.manifest = _Manifest.model_validate_json((root / "ownership.json").read_text())
        self.account = next(item for item in self.manifest.accounts if item.label == label)
        self.other = next(item for item in self.manifest.accounts if item.label != label)
        assert os.geteuid() == self.account.uid != 0
        os.umask(0o077)
        self.project = Path(self.account.home) / "project"
        self.control = root / "control"
        self.settings = load_queue_settings()
        assert self.settings.config_path == root / "queue.toml"
        assert self.settings.name == "Multi-user acceptance"
        bind_coordination_root(
            _HOST, self.settings.coordination_root, bootstrap_root=root / "bootstrap"
        )
        self.identity = WorkerIdentity(
            owner_uid=os.geteuid(),
            host_id=_HOST,
            boot_id=Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip(),
        )
        self.store = NFSQueueStore(
            self.settings.root, self.identity, local_root=self.settings.coordination_root
        )
        self.processes = QueueProcesses(self.store, self.identity, command_builder=self._command)
        self.service = QueueService(self.store, _Inventory(), self.processes, self.identity)

    def _command(
        self, snapshot: JobSnapshot, _path: Path, _devices: tuple[str, ...]
    ) -> Sequence[str]:
        return (snapshot.interpreter, "-c", _WORKLOAD, str(self.control / "workload.lock"))

    def _snapshot(self, label: str) -> JobSnapshot:
        return JobSnapshot(
            command="train",
            label=label,
            config_json=json.dumps({"private_input": f"Owner {self.account.label} private input"}),
            project_root=str(self.project),
            cwd=str(self.project),
            interpreter=sys.executable,
            package_version="acceptance",
            package_identity="acceptance-fixture",
        )

    def _job(self, label: str) -> PublicJob:
        return next(job for job in self.store.view().jobs if job.label == label)

    def _first(self, *, other: bool = False) -> PublicJob:
        account = self.other if other else self.account
        return self._job(f"Owner {account.label} job 1")

    def _gate(self, stage: str) -> None:
        (self.control / f"{stage}-{self.account.label}.ready").touch(mode=0o644)
        _wait_until((self.control / f"{stage}.go").exists, f"Waiting for {stage} gate")

    def inspect(self) -> dict[str, object]:
        view = self.service.list(visibility="all")
        assert "private_input" not in view.model_dump_json()
        return {
            "configuration": str(self.settings.config_path),
            "root": str(self.store.root),
            "coordination": str(self.processes.local_root),
            "sequences": sorted(job.submission_sequence for job in view.jobs),
            "main": [job.label for job in self.service.list().jobs],
            "archived": [job.label for job in self.service.list(visibility="archived").jobs],
        }

    def submit(self) -> dict[str, object]:
        self._gate("submit")
        numbers = []
        for number in range(1, _JOBS_PER_USER + 1):
            job = self.store.submit((self._snapshot(f"Owner {self.account.label} job {number}"),))[
                0
            ]
            numbers.append(job.submission_sequence)
        return {"sequences": numbers}

    def permissions(self) -> dict[str, object]:
        own, foreign = self._first(), self._first(other=True)
        own_path = self.store.snapshot_path(own.id)
        assert stat.S_IMODE(own_path.stat().st_mode) == 0o600
        assert "private_input" in own_path.read_text()
        foreign_path = self.store.public_path(foreign.id).with_name("snapshot.json")
        _denied(foreign_path.read_bytes)
        _denied(lambda: foreign_path.open("ab"))
        _denied(lambda: self.store.public_path(foreign.id).open("ab"))
        _denied(lambda: self.store.load_snapshot(foreign.id))
        return {"private_snapshots": "owner-only", "public_summary": "readable"}

    def foreign(self) -> dict[str, object]:
        foreign = self._first(other=True)
        _denied(lambda: self.service.cancel(foreign.id))
        _denied(lambda: self.store.update(foreign.id, "completed"))
        _denied(lambda: self.service.archive((foreign.id,)))
        _denied(lambda: self.service.restore((foreign.id,)))
        _denied(lambda: self.service.recover(foreign.id))
        _denied(lambda: self.processes.start(foreign, ("GPU-test",)))
        return {"foreign_mutations": "refused"}

    def reorder(self) -> dict[str, object]:
        foreign = self._first(other=True)
        view = self.service.move(
            f"job-{foreign.submission_sequence}", "top", self.store.view().revision
        )
        assert view.jobs[0].id == foreign.id
        return {"foreign_pending_reorder": "allowed"}

    def archive(self) -> dict[str, object]:
        own = self._first()
        self.store.update(own.id, "completed")
        self.service.archive((f"job-{own.submission_sequence}",))
        revision = self.store.view().revision
        self.service.archive((f"job-{own.submission_sequence}",))
        assert self.store.view().revision == revision
        return self.inspect()

    def restore(self) -> dict[str, object]:
        self.service.restore((self._first().id,))
        return self.inspect()

    def recovery_visibility(self) -> dict[str, object]:
        own = self._first()
        self.service.archive((own.id,))
        self.store.update(own.id, "recovery_required")
        assert own.id in {job.id for job in self.service.list().jobs}
        assert own.id not in {job.id for job in self.service.list(visibility="archived").jobs}
        self.store.update(own.id, "cancelled")
        self.service.restore((own.id,))
        return {"injected_recovery": "visible in main"}

    def prepare_worker(self) -> dict[str, object]:
        for job in self.store.view().jobs:
            if job.owner_uid == self.account.uid and job.state == "pending":
                self.service.cancel(job.id)
        self.store.submit((self._snapshot(f"Owner {self.account.label} workload"),))
        return {"workload": "submitted"}

    def duplicate_worker(self) -> dict[str, object]:
        try:
            with self.processes.worker_registration():
                raise AssertionError("Duplicate worker registration succeeded")
        except RuntimeError as error:
            if "already registered" not in str(error):
                raise AssertionError("Duplicate worker failed for an unexpected reason") from error
        return {"duplicate_owner_worker": "refused"}

    def worker(self) -> dict[str, object]:
        job = self._job(f"Owner {self.account.label} workload")
        with self.processes.worker_registration():
            self.processes.publish_inventory(_Inventory().snapshot())
            self._gate("worker")

            def finished() -> bool:
                self.service.tick()
                current = self._job(job.label)
                if current.state in {"failed", "recovery_required"}:
                    raise AssertionError(
                        f"Controlled workload ended as {current.state}: {current.error}"
                    )
                return current.state == "completed"

            _wait_until(finished, "Controlled owner workload did not complete")
            self.processes.refresh()
        payload = GuardianPayload.model_validate_json(
            (self.store.snapshot_path(job.id).parent / "guardian.json").read_text()
        )
        assert payload.local_root == str(self.settings.coordination_root)
        assert payload.identity.owner_uid == self.account.uid
        assert (
            json.loads((self.project / "workload-owner.json").read_text())["uid"]
            == self.account.uid
        )
        assert (
            self.project / ".cy" / "queue-logs" / f"{job.id}.log"
        ).read_text().strip() == "Controlled workload complete"
        return {"workload_owner": self.account.label, "state": "completed"}

    def execution_privacy(self) -> dict[str, object]:
        own = self._job(f"Owner {self.account.label} workload")
        foreign = self._job(f"Owner {self.other.label} workload")
        for folder, extension in (("queue-logs", "log"), ("queue-status", "json")):
            own_path = self.project / ".cy" / folder / f"{own.id}.{extension}"
            assert own_path.is_file()
            assert stat.S_IMODE(own_path.stat().st_mode) == 0o600
            foreign_path = (
                Path(self.other.home) / "project" / ".cy" / folder / f"{foreign.id}.{extension}"
            )
            _denied(foreign_path.read_bytes)
            _denied(partial(foreign_path.open, "ab"))
        assert self._job(own.label).progress == "Controlled workload complete"
        return {"logs_and_progress": "owner-only"}

    def binding(self) -> dict[str, object]:
        _reject_binding(self.root / "conflicting", self.root / "bootstrap")
        assert not (self.root / "conflicting").exists()
        return {"conflicting_coordination": "refused"}

    def reserve(self) -> dict[str, object]:
        born = process_birth(os.getpid())
        assert born is not None
        claim = GuardianClaim(
            job_id="acceptance-reservation",
            owner_uid=self.account.uid,
            host_id=_HOST,
            boot_id=self.identity.boot_id,
            queue_root=str(self.store.root),
            devices=("GPU-test",),
            marker="acceptance-reservation",
            guardian_pid=os.getpid(),
            guardian_born=born,
        )
        lease = self.processes.pool.acquire(claim)
        assert lease is not None
        try:
            self._gate("reservation")
        finally:
            lease.release_verified()
            lease.close()
        return {"reservation": "released"}

    def cross_root(self) -> dict[str, object]:
        alternative = NFSQueueStore(
            self.root / "other-metadata", self.identity, local_root=self.settings.coordination_root
        )
        pool = QueueProcesses(alternative, self.identity).pool
        assert pool.reserved() == {"GPU-test"}
        born = process_birth(os.getpid())
        assert born is not None
        claim = GuardianClaim(
            job_id="acceptance-competing-reservation",
            owner_uid=self.account.uid,
            host_id=_HOST,
            boot_id=self.identity.boot_id,
            queue_root=str(alternative.root),
            devices=("GPU-test",),
            marker="acceptance-competing-reservation",
            guardian_pid=os.getpid(),
            guardian_born=born,
        )
        assert pool.acquire(claim) is None
        return {"cross_user_cross_root_exclusion": "enforced"}


def _actor_main(root: Path, label: str, action: str) -> None:
    actor = _Actor(root, label)
    actions: dict[str, Callable[[], dict[str, object]]] = {
        "inspect": actor.inspect,
        "submit": actor.submit,
        "permissions": actor.permissions,
        "foreign": actor.foreign,
        "reorder": actor.reorder,
        "archive": actor.archive,
        "restore": actor.restore,
        "recovery": actor.recovery_visibility,
        "prepare-worker": actor.prepare_worker,
        "duplicate-worker": actor.duplicate_worker,
        "worker": actor.worker,
        "execution-privacy": actor.execution_privacy,
        "binding": actor.binding,
        "reserve": actor.reserve,
        "cross-root": actor.cross_root,
    }
    sys.stdout.write(json.dumps(actions[action]()) + "\n")


class _Fixture:
    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="cy-queue-multiuser-"))
        self.root.chmod(0o755)
        self.group = f"cyqt{os.getpid()}"
        self.gid: int | None = None
        self.accounts: list[_Account] = []
        self.created_names: list[str] = []
        self.processes: list[subprocess.Popen[str]] = []

    def _ledger(self) -> None:
        assert self.gid is not None
        path = self.root / "ownership.json"
        path.write_text(
            _Manifest(
                root=str(self.root), group=self.group, gid=self.gid, accounts=tuple(self.accounts)
            ).model_dump_json(),
            encoding="utf-8",
        )
        path.chmod(0o640)
        os.chown(path, 0, self.gid)

    def provision(self) -> None:
        try:
            grp.getgrnam(self.group)
        except KeyError:
            pass
        else:
            raise RuntimeError("Temporary acceptance group already exists")
        _run(["/usr/sbin/groupadd", self.group])
        self.gid = grp.getgrnam(self.group).gr_gid
        self._ledger()
        for label in ("A", "B"):
            name = f"{self.group}{label.lower()}"
            try:
                pwd.getpwnam(name)
            except KeyError:
                pass
            else:
                raise RuntimeError("Temporary acceptance account already exists")
            home = self.root / f"home-{label.lower()}"
            self.created_names.append(name)
            _run(
                [
                    "/usr/sbin/useradd",
                    "--no-create-home",
                    "--no-user-group",
                    "--no-log-init",
                    "--home-dir",
                    str(home),
                    "--shell",
                    "/usr/sbin/nologin",
                    "--gid",
                    self.group,
                    "--password",
                    "!",
                    name,
                ]
            )
            entry = pwd.getpwnam(name)
            account = _Account(
                name=name, label=label, uid=entry.pw_uid, gid=entry.pw_gid, home=str(home)
            )
            self.accounts.append(account)
            self._ledger()
            for directory in (home, home / "project"):
                directory.mkdir(mode=0o700)
                os.chown(directory, account.uid, account.gid)
            assert _run(["/usr/bin/passwd", "--status", name]).stdout.split()[1] == "L"
        control = self.root / "control"
        control.mkdir(mode=0o1777)
        control.chmod(0o1777)
        lock = control / "workload.lock"
        lock.touch(mode=0o666)
        lock.chmod(0o666)
        # Provision only shared parents; production code creates its metadata root
        # and actor directories under the first test user's restrictive umask.
        for directory_name in ("metadata-parent", "coordination", "bootstrap", "other-metadata"):
            path = self.root / directory_name
            path.mkdir(mode=0o1777)
            path.chmod(0o1777)
        config = self.root / "queue.toml"
        config.write_text(
            '[queue]\nname = "Multi-user acceptance"\n'
            f"root = {json.dumps(str(self.root / 'metadata-parent' / 'queue'))}\n"
            f"coordination_root = {json.dumps(str(self.root / 'coordination'))}\n",
            encoding="utf-8",
        )
        config.chmod(0o640)
        os.chown(config, 0, self.gid)
        (self.root / "memory.json").write_text('{"GPU-test": 0}', encoding="utf-8")
        (self.root / "memory.json").chmod(0o644)

    def argv(self, label: str, action: str) -> list[str]:
        account = next(item for item in self.accounts if item.label == label)
        return [
            "/usr/sbin/runuser",
            "--user",
            account.name,
            "--",
            "/usr/bin/env",
            "-i",
            f"HOME={account.home}",
            f"USER={account.name}",
            f"LOGNAME={account.name}",
            "PATH=/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE=1",
            "PYTHONNOUSERSITE=1",
            f"PYTHONPATH={_REPO / 'tests' / 'queue_nvml'}:{_REPO / 'src'}",
            f"CY_HOME={Path(account.home) / 'project'}",
            f"CY_QUEUE_CONFIG={self.root / 'queue.toml'}",
            f"CY_TEST_QUEUE_MEMORY={self.root / 'memory.json'}",
            sys.executable,
            str(Path(__file__).resolve()),
            "--actor",
            str(self.root),
            label,
            action,
        ]

    def actor(self, label: str, action: str) -> dict[str, object]:
        return cast(dict[str, object], json.loads(_run(self.argv(label, action)).stdout))

    def start(self, label: str, action: str) -> subprocess.Popen[str]:
        process = subprocess.Popen(  # noqa: S603 - exact runuser command for a recorded fixture account
            self.argv(label, action), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        self.processes.append(process)
        return process

    def finish(self, process: subprocess.Popen[str]) -> dict[str, object]:
        output, error = process.communicate(timeout=_TIMEOUT)
        if process.returncode:
            raise RuntimeError(f"Real-user acceptance operation failed: {error}")
        return cast(dict[str, object], json.loads(output))

    def ready(self, stage: str, labels: Sequence[str]) -> None:
        _wait_until(
            lambda: all(
                (self.root / "control" / f"{stage}-{label}.ready").exists() for label in labels
            ),
            f"Actors did not reach {stage}",
        )

    def release(self, stage: str) -> None:
        (self.root / "control" / f"{stage}.go").touch(mode=0o644)

    def cleanup(self) -> None:
        for account in self.accounts:
            entry = pwd.getpwnam(account.name)
            if entry.pw_uid != account.uid or entry.pw_dir != account.home:
                raise RuntimeError("Temporary account ownership changed; cleanup refused")
            _signal_uid(account.uid, signal.SIGTERM)
        time.sleep(0.2)
        for account in self.accounts:
            _signal_uid(account.uid, signal.SIGKILL)
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
        for name in reversed(self.created_names):
            with suppress(KeyError):
                entry = pwd.getpwnam(name)
                assert Path(entry.pw_dir).is_relative_to(self.root)
                _run(["/usr/sbin/userdel", name])
        if self.gid is not None:
            assert grp.getgrnam(self.group).gr_gid == self.gid
            _run(["/usr/sbin/groupdel", self.group])
        shutil.rmtree(self.root)
        for name in self.created_names:
            try:
                pwd.getpwnam(name)
            except KeyError:
                continue
            raise AssertionError("A temporary acceptance account remains")


def _signal_uid(uid: int, signum: signal.Signals) -> None:
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal():
            continue
        with suppress(FileNotFoundError, ProcessLookupError):
            descriptor = os.pidfd_open(int(path.name))
            try:
                rows = (path / "status").read_text().splitlines()
                effective = next(row.split()[2] for row in rows if row.startswith("Uid:"))
                if int(effective) == uid:
                    signal.pidfd_send_signal(descriptor, signum)
            finally:
                os.close(descriptor)


def _exercise(fixture: _Fixture, checks: list[str]) -> None:
    first, second = fixture.actor("A", "inspect"), fixture.actor("B", "inspect")
    assert first == second
    checks.append(
        "Both real Unix users loaded the same group-readable configuration "
        "and shared roots under umask 077."
    )
    workers = [fixture.start(label, "submit") for label in ("A", "B")]
    fixture.ready("submit", ("A", "B"))
    fixture.release("submit")
    results = [fixture.finish(process) for process in workers]
    numbers: list[int] = []
    for result in results:
        sequences = result["sequences"]
        assert isinstance(sequences, list)
        assert all(type(number) is int for number in sequences)
        numbers.extend(sequences)
    assert sorted(numbers) == list(range(1, 2 * _JOBS_PER_USER + 1))
    assert fixture.actor("A", "inspect") == fixture.actor("B", "inspect")
    checks.append(
        "Concurrent submissions committed twelve unique stable job numbers; "
        "both users read identical shared history."
    )
    for label in ("A", "B"):
        fixture.actor(label, "permissions")
        fixture.actor(label, "foreign")
        fixture.actor(label, "reorder")
        fixture.actor(label, "binding")
    checks.append(
        "Public summaries were readable; private snapshots and foreign record writes "
        "were denied by real filesystem permissions."
    )
    checks.append(
        "Foreign cancellation, update, archive, restore, recovery and execution were refused; "
        "both users could reorder the other's pending job."
    )
    checks.append("Both users rejected a conflicting coordination root without creating it.")
    for label, other in (("A", "B"), ("B", "A")):
        archived = fixture.actor(label, "archive")
        assert archived == fixture.actor(other, "inspect")
        assert archived["archived"] == [f"Owner {label} job 1"]
        main = archived["main"]
        assert isinstance(main, list)
        assert f"Owner {label} job 1" not in main
        fixture.actor(other, "foreign")
        restored = fixture.actor(label, "restore")
        assert restored == fixture.actor(other, "inspect")
        fixture.actor(label, "recovery")
    checks.append(
        "Owner archive/restore persisted across fresh processes and both users' views; "
        "repeat archive was idempotent. Injected recovery-required state "
        "resurfaced in the main view."
    )
    reservation = fixture.start("A", "reserve")
    fixture.ready("reservation", ("A",))
    fixture.actor("B", "cross-root")
    fixture.release("reservation")
    fixture.finish(reservation)
    checks.append(
        "A real advisory GPU reservation held by one user excluded the other user "
        "through a second metadata root."
    )
    for label in ("A", "B"):
        fixture.actor(label, "prepare-worker")
    workers = [fixture.start(label, "worker") for label in ("A", "B")]
    fixture.ready("worker", ("A", "B"))
    for label in ("A", "B"):
        fixture.actor(label, "duplicate-worker")
    fixture.release("worker")
    for process in workers:
        fixture.finish(process)
    checks.append(
        "Two real owner workers and independent guardians completed controlled subprocess "
        "workloads under their respective UIDs, with one synthetic-device allocation at a time. "
        "Duplicate owner workers were refused."
    )
    for label in ("A", "B"):
        fixture.actor(label, "execution-privacy")
    checks.append(
        "Guardian payloads retained the configured coordination path; actual logs and progress "
        "stayed private in each owner's project while public progress was published."
    )


def _interrupted(_signum: int, _frame: FrameType | None) -> None:
    raise InterruptedError("Acceptance interrupted; cleaning up task-owned resources")


def _controller(evidence: Path) -> int:
    if os.geteuid() != 0:
        raise PermissionError("Run --run as root; --help needs no elevated privileges")
    checks: list[str] = []
    failures: list[str] = []
    fixture = _Fixture()
    previous = {item: signal.signal(item, _interrupted) for item in (signal.SIGINT, signal.SIGTERM)}
    try:
        fixture.provision()
        _exercise(fixture, checks)
    except (Exception, KeyboardInterrupt) as error:  # noqa: BLE001 - retain evidence and always clean isolated fixtures
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        failures.append(f"{type(error).__name__}: {detail}")
    finally:
        # A second terminal interruption must not abandon provisioned accounts.
        for item in previous:
            signal.signal(item, signal.SIG_IGN)
        try:
            fixture.cleanup()
            checks.append(
                "All task-owned processes, temporary accounts, group and fixture files "
                "were removed; "
                "account absence was checked afterward."
            )
        except Exception as error:  # noqa: BLE001 - final cleanup boundary must retain its evidence
            failures.append(f"Cleanup gap: {error}")
        finally:
            for item, handler in previous.items():
                signal.signal(item, handler)
    lines = [
        "# Real two-user queue acceptance",
        "",
        f"Date: {datetime.now(UTC):%Y-%m-%d %H:%M UTC}",
        "",
        f"Result: {'FAILED' if failures else 'PASSED'}",
        "",
        (
            "Command: `python tests/queue_multiuser_harness.py --run --evidence <this-file>` "
            "(root controller)."
        ),
        "",
        "## Executed checks",
        "",
        *(f"- {check}" for check in checks),
        "",
        "## Boundaries",
        "",
        (
            "The harness uses actual temporary Unix accounts, file permissions, flock locks, "
            "owner workers, guardians and subprocesses. Root performs provisioning, identity "
            "switching and cleanup only. The executed-check list records which stages completed; "
            "queue operations run as the test users."
        ),
        "",
        (
            "A synthetic host with a fixture-only bootstrap path left production coordination "
            "untouched. The existing test NVML module supplied synthetic device/memory facts. "
            "No physical GPU, network filesystem, ClearML service, model training, or production "
            "host configuration was exercised. Recovery visibility used an injected recovery "
            "state; guardian-crash recovery remains covered by separate process tests."
        ),
        "",
    ]
    if failures:
        lines.extend(["## Failures", "", *failures, ""])
    body = "\n".join(lines)
    body = re.sub(
        r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b|\b[0-9a-f]{32,64}\b",
        "[internal identifier]",
        body,
    )
    evidence = evidence.resolve()
    evidence.parent.mkdir(parents=True, exist_ok=True)
    previous_evidence = evidence.read_text(encoding="utf-8") if evidence.exists() else ""
    evidence.write_text(
        previous_evidence + ("\n---\n\n" if previous_evidence else "") + body, encoding="utf-8"
    )
    owner = evidence.parent.stat()
    os.chown(evidence, owner.st_uid, owner.st_gid)
    outcome = "FAILED" if failures else "PASSED"
    sys.stdout.write(f"Two-user queue acceptance {outcome}; evidence recorded.\n")
    return int(bool(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        action="store_true",
        help="Provision two temporary users, verify and clean up; requires root",
    )
    parser.add_argument(
        "--evidence", type=Path, help="Markdown evidence destination, required with --run"
    )
    parser.add_argument(
        "--actor", nargs=3, metavar=("ROOT", "OWNER", "ACTION"), help=argparse.SUPPRESS
    )
    arguments = parser.parse_args()
    if arguments.actor:
        root, label, action = arguments.actor
        _actor_main(Path(root), label, action)
        return 0
    if not arguments.run or arguments.evidence is None:
        parser.error("Pass --run --evidence PATH, or use --help")
    return _controller(arguments.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
