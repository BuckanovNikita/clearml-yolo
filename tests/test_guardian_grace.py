"""Ordinary owned subprocesses verify owner-first queue cancellation."""

import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.adapters.queue.identity import process_birth
from clearml_yolo.adapters.queue.runtime import QueueProcesses
from clearml_yolo.adapters.queue.storage import NFSQueueStore
from clearml_yolo.core.queue import JobSnapshot, PublicJob, WorkerIdentity


def _wait_for(path: Path, timeout: float = 10) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file() and path.read_text(encoding="utf-8"):
            return path.read_text(encoding="utf-8")
        time.sleep(0.02)
    pytest.fail(f"Task-owned process did not write {path}")


@contextmanager
def _job(directory: Path, script: str) -> Iterator[tuple[NFSQueueStore, QueueProcesses, PublicJob]]:
    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="host", boot_id="boot")
    store = NFSQueueStore(directory / "queue", identity)
    job = store.submit(
        (
            JobSnapshot(
                command="train",
                config_json="{}",
                project_root=str(directory),
                cwd=str(directory),
                interpreter=sys.executable,
                package_version="1",
                package_identity="hash",
            ),
        )
    )[0]
    processes = QueueProcesses(
        store,
        identity,
        local_root=directory / "local",
        command_builder=lambda snapshot, path, devices: [
            snapshot.interpreter,
            "-c",
            script,
            str(directory),
        ],
    )
    try:
        assert processes.start(job, ("GPU-a", "GPU-b"))
        yield store, processes, job
    finally:
        # A failed assertion must not leave a guardian or its children alive.
        claim = processes.pool.claim_for(job.id)
        identities = dict(claim.identities) if claim is not None else {}
        for path in directory.glob("*.pid"):
            pid = int(path.read_text(encoding="utf-8"))
            born = process_birth(pid)
            if born is not None:
                identities[pid] = born
        if claim is not None:
            identities[claim.guardian_pid] = claim.guardian_born
        for pid, born in identities.items():
            with suppress(ProcessLookupError):
                descriptor = os.pidfd_open(pid)
                try:
                    if process_birth(pid) == born:
                        signal.pidfd_send_signal(descriptor, signal.SIGKILL)
                finally:
                    os.close(descriptor)
        for process in processes._guardians.values():
            process.wait(timeout=5)
        processes.refresh()


def _wait_cancelled(store: NFSQueueStore, processes: QueueProcesses, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while store.view().jobs[0].state != "cancelled":
        assert time.monotonic() < deadline
        processes.refresh()
        time.sleep(0.02)
    processes.refresh()


def _short_guardian_grace(monkeypatch: pytest.MonkeyPatch) -> None:
    original = subprocess.Popen

    def launch(argv: list[str], **options: Any) -> subprocess.Popen[bytes]:
        if argv[1:3] == ["-m", "clearml_yolo.adapters.queue.guardian"]:
            argv = [
                argv[0],
                "-c",
                (
                    "from clearml_yolo.adapters.queue import guardian; "
                    "guardian._OWNER_SHUTDOWN_GRACE_SECONDS=0.6; guardian.main()"
                ),
                argv[3],
            ]
        return original(argv, **options)

    monkeypatch.setattr(subprocess, "Popen", launch)


def test_cancellation_keeps_publishers_alive_and_capacity_owned_through_final_logs(
    tmp_path: Path,
) -> None:
    script = """
import os,signal,subprocess,sys,time
from pathlib import Path
directory=Path(sys.argv[1])
child_script='''
import os,signal,sys,time
from pathlib import Path
directory=Path(sys.argv[1])
def term(signum,frame):
    (directory/"publisher.term").write_text("terminated")
    raise SystemExit(0)
signal.signal(signal.SIGTERM,term)
(directory/"publisher.pid").write_text(str(os.getpid()))
time.sleep(60)
'''
publisher=subprocess.Popen([sys.executable,"-c",child_script,str(directory)],start_new_session=True)
cancelled=False
def cancel(signum,frame):
    global cancelled
    cancelled=True
signal.signal(signal.SIGTERM,cancel)
(directory/"owner.pid").write_text(str(os.getpid()))
while not cancelled:
    time.sleep(0.01)
(directory/"shutdown.started").write_text("started")
late_script=("import os,signal,sys,time; from pathlib import Path; "
    "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
    "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)")
late=subprocess.Popen([sys.executable,"-c",late_script,str(directory/"late.pid")],start_new_session=True)
time.sleep(2)
if publisher.poll() is not None:
    (directory/"publisher.premature").write_text("died before final publication")
    raise SystemExit(2)
print("FINAL OWNER LOG PUBLISHED",flush=True)
(directory/"publication.done").write_text("published")
publisher.terminate()
publisher.wait(timeout=5)
"""
    with _job(tmp_path, script) as (store, processes, job):
        publisher_pid = int(_wait_for(tmp_path / "publisher.pid"))
        _wait_for(tmp_path / "owner.pid")
        store.cancel(job.id)
        _wait_for(tmp_path / "shutdown.started")
        assert process_birth(publisher_pid) is not None
        assert not (tmp_path / "publisher.term").exists()
        assert processes.reserved() == {"GPU-a", "GPU-b"}
        late_pid = int(_wait_for(tmp_path / "late.pid"))
        deadline = time.monotonic() + 1
        while True:
            claim = processes.pool.claim_for(job.id)
            assert claim is not None
            if late_pid in dict(claim.identities):
                break
            assert time.monotonic() < deadline
            time.sleep(0.02)
        assert not (tmp_path / "publication.done").exists()
        # Repeated guardian interrupts must preserve the owner's original grace.
        os.kill(claim.guardian_pid, signal.SIGINT)
        os.kill(claim.guardian_pid, signal.SIGTERM)
        assert _wait_for(tmp_path / "publication.done") == "published"
        assert not (tmp_path / "publisher.premature").exists()
        _wait_cancelled(store, processes)
        assert process_birth(publisher_pid) is None
        assert process_birth(late_pid) is None
        assert processes.reserved() == set()
        log = tmp_path / ".cy" / "queue-logs" / f"{job.id}.log"
        assert "FINAL OWNER LOG PUBLISHED" in log.read_text(encoding="utf-8")
        claim_path = store.snapshot_path(job.id).parent / "claim.json"
        persisted = json.loads(claim_path.read_text(encoding="utf-8"))
        assert late_pid in dict(persisted["identities"])


def test_ignored_owner_signal_escalates_at_deadline_despite_repeated_guardian_signals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _short_guardian_grace(monkeypatch)
    script = """
import json,os,signal,subprocess,sys,time
from pathlib import Path
directory=Path(sys.argv[1])
received=[]
def ignore(signum,frame):
    received.append(time.monotonic())
    (directory/"owner.signals").write_text(json.dumps(received))
signal.signal(signal.SIGTERM,ignore)
child_script=("import os,signal,sys,time; from pathlib import Path; "
    "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
    "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)")
subprocess.Popen([sys.executable,"-c",child_script,str(directory/"child.pid")],start_new_session=True)
(directory/"owner.pid").write_text(str(os.getpid()))
time.sleep(60)
"""
    with _job(tmp_path, script) as (store, processes, job):
        owner_pid = int(_wait_for(tmp_path / "owner.pid"))
        child_pid = int(_wait_for(tmp_path / "child.pid"))
        claim = processes.pool.claim_for(job.id)
        assert claim is not None
        started = time.monotonic()
        os.kill(claim.guardian_pid, signal.SIGTERM)
        _wait_for(tmp_path / "owner.signals")
        time.sleep(0.2)
        os.kill(claim.guardian_pid, signal.SIGINT)
        os.kill(claim.guardian_pid, signal.SIGTERM)
        assert process_birth(owner_pid) is not None
        assert process_birth(child_pid) is not None
        assert processes.reserved() == {"GPU-a", "GPU-b"}
        _wait_cancelled(store, processes, timeout=8)
        signals = json.loads((tmp_path / "owner.signals").read_text(encoding="utf-8"))
        # Initial owner-only TERM, then whole-tree TERM after the unchanged grace.
        assert len(signals) == 2
        assert signals[1] - signals[0] >= 0.6
        assert time.monotonic() - started < 8
        assert process_birth(owner_pid) is None
        assert process_birth(child_pid) is None
        assert processes.reserved() == set()


def test_owner_signal_rejects_reused_birth_without_signalling_replacement() -> None:
    from clearml_yolo.adapters.queue.guardian import _signal_owner

    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    try:
        born = process_birth(child.pid)
        assert born is not None
        assert not _signal_owner(child.pid, born - 1)
        assert child.poll() is None
        assert _signal_owner(child.pid, born)
        assert child.wait(timeout=5) == -signal.SIGTERM
        assert not _signal_owner(child.pid, born)
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)
