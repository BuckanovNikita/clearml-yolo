"""Real process regressions for detached ranks and repeated cancellation signals."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import pytest

from clearml_yolo.adapters.runtime.process_tree import OWNER_ENV

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="requires Linux /proc")


def _ready(path: Path) -> str:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if path.is_file():
            value = path.read_text(encoding="utf-8")
            if value:
                return value
        time.sleep(0.02)
    pytest.fail(f"Process did not publish readiness: {path.name}")


def _running(pid: int) -> bool:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return False
    return fields[0] != "Z"


def _kill(pid: int) -> None:
    with suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)
    deadline = time.monotonic() + 5
    while _running(pid) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not _running(pid), f"Task-owned process {pid} survived test teardown"


@pytest.mark.parametrize("root_exits_first", [False, True])
def test_cancellation_kills_detached_rank_and_preserves_unrelated_process(
    tmp_path: Path, root_exits_first: bool
) -> None:
    from clearml_yolo.adapters.runtime import supervision as execution

    child_pid_path = tmp_path / "rank.pid"
    child_ready_path = tmp_path / "rank.ready"
    child_script = dedent("""
        import signal, sys, time
        from pathlib import Path
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        Path(sys.argv[1]).write_text("ready", encoding="utf-8")
        time.sleep(60)
        """)
    token = uuid4().hex
    worker_script = dedent("""
        import subprocess, sys, time
        from pathlib import Path
        child = subprocess.Popen(
            [sys.executable, "-c", sys.argv[1], sys.argv[3]], start_new_session=True,
        )
        Path(sys.argv[2]).write_text(str(child.pid), encoding="utf-8")
        """) + ("raise SystemExit(0)" if root_exits_first else "time.sleep(60)")
    unrelated = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    worker = subprocess.Popen(  # noqa: S603 - fixed task-owned process tree
        [
            sys.executable,
            "-c",
            worker_script,
            child_script,
            str(child_pid_path),
            str(child_ready_path),
        ],
        start_new_session=True,
        env={**os.environ, OWNER_ENV: token},
    )
    child_pid: int | None = None
    try:
        execution._attach_process_tree(worker, token)
        child_pid = int(_ready(child_pid_path))
        _ready(child_ready_path)
        assert os.getpgid(child_pid) != worker.pid
        if root_exits_first:
            worker.wait(timeout=5)
        else:
            assert worker.poll() is None

        execution.cancel_process(worker)

        assert worker.poll() is not None
        assert not _running(child_pid), "Detached DDP-style rank survived successful cancellation"
        assert unrelated.poll() is None, "Cancellation killed an unrelated process"
    finally:
        _kill(worker.pid)
        worker.wait(timeout=5)
        if child_pid is None and child_pid_path.is_file():
            child_pid = int(child_pid_path.read_text(encoding="utf-8"))
        if child_pid is not None:
            _kill(child_pid)
        _kill(unrelated.pid)
        unrelated.wait(timeout=5)


def test_repeated_ctrl_c_finishes_worker_cleanup(tmp_path: Path) -> None:
    worker_pid_path = tmp_path / "worker.pid"
    worker_ready_path = tmp_path / "worker.ready"
    supervisor_ready_path = tmp_path / "supervisor.ready"
    termination_path = tmp_path / "termination.ready"
    queue_root = tmp_path / "queue"
    worker_script = dedent("""
        import signal, sys, time
        from pathlib import Path
        def terminating(signum, frame):
            Path(sys.argv[2]).write_text("received", encoding="utf-8")
        signal.signal(signal.SIGTERM, terminating)
        Path(sys.argv[1]).write_text("ready", encoding="utf-8")
        time.sleep(60)
        """)
    supervisor_script = dedent("""
        import subprocess, sys
        from pathlib import Path
        from clearml_yolo.adapters.runtime import supervision as execution
        worker = subprocess.Popen(
            [sys.executable, "-c", sys.argv[1], sys.argv[3], sys.argv[5]],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        execution._attach_process_tree(worker)
        Path(sys.argv[2]).write_text(str(worker.pid), encoding="utf-8")
        Path(sys.argv[4]).write_text("ready", encoding="utf-8")
        try:
            worker.wait()
        finally:
            execution.cancel_process(worker)
        """)
    supervisor = subprocess.Popen(  # noqa: S603 - signals target this isolated test supervisor
        [
            sys.executable,
            "-c",
            supervisor_script,
            worker_script,
            str(worker_pid_path),
            str(worker_ready_path),
            str(supervisor_ready_path),
            str(termination_path),
            str(queue_root),
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    worker_pid: int | None = None
    try:
        worker_pid = int(_ready(worker_pid_path))
        _ready(worker_ready_path)
        _ready(supervisor_ready_path)
        os.kill(supervisor.pid, signal.SIGINT)
        _ready(termination_path)

        os.kill(supervisor.pid, signal.SIGINT)
        _, errors = supervisor.communicate(timeout=15)

        assert supervisor.returncode != 0, "Cancellation unexpectedly reported success"
        assert not _running(worker_pid), f"Repeated Ctrl+C abandoned the live worker:\n{errors}"
    finally:
        _kill(supervisor.pid)
        supervisor.wait(timeout=5)
        if supervisor.stderr is not None:
            supervisor.stderr.close()
        if worker_pid is None and worker_pid_path.is_file():
            worker_pid = int(worker_pid_path.read_text(encoding="utf-8"))
        if worker_pid is not None:
            _kill(worker_pid)


def test_cleanup_defers_first_interrupt_and_restores_handlers() -> None:
    from clearml_yolo.adapters.runtime.process_tree import defer_interruptions

    previous = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}
    events: list[str] = []

    def cleanup() -> None:
        with defer_interruptions():
            signal.raise_signal(signal.SIGINT)
            with defer_interruptions():
                signal.raise_signal(signal.SIGTERM)
                events.append("inner cleanup finished")
            events.append("outer cleanup finished")

    with pytest.raises(KeyboardInterrupt):
        cleanup()
    assert events == ["inner cleanup finished", "outer cleanup finished"]
    assert {signum: signal.getsignal(signum) for signum in previous} == previous


def test_reused_pid_is_not_signalled(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    from clearml_yolo.adapters.runtime import process_tree

    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    try:
        tree = process_tree.LinuxProcessTree(process.pid)
        original = process_tree._read_process

        def replaced_identity(pid: int) -> process_tree._Process | None:
            status = original(pid)
            if pid == process.pid and status is not None:
                return replace(status, born=status.born + 1)
            return status

        monkeypatch.setattr(process_tree, "_read_process", replaced_identity)
        tree.signal(signal.SIGKILL)
        assert process.poll() is None, "A reused PID was treated as an owned process"
    finally:
        _kill(process.pid)
        process.wait(timeout=5)


def test_inaccessible_owned_process_prevents_verified_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    try:
        tree = process_tree.LinuxProcessTree(process.pid)
        original = process_tree._read_process

        def inaccessible(pid: int) -> process_tree._Process | None:
            if pid == process.pid:
                raise PermissionError("test-owned process is inaccessible")
            return original(pid)

        monkeypatch.setattr(process_tree, "_read_process", inaccessible)
        with pytest.raises(RuntimeError, match="Cannot verify model process cleanup"):
            tree.running()
    finally:
        _kill(process.pid)
        process.wait(timeout=5)


def test_native_torchrun_ranks_do_not_escape_cancellation(tmp_path: Path) -> None:
    from clearml_yolo.adapters.runtime import supervision as execution

    rank_script = tmp_path / "rank.py"
    rank_script.write_text(
        dedent("""
            import os, signal, sys, time
            from pathlib import Path
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            Path(sys.argv[1], "rank-" + os.environ["LOCAL_RANK"] + ".pid").write_text(
                str(os.getpid()), encoding="utf-8"
            )
            time.sleep(60)
            """),
        encoding="utf-8",
    )
    worker_script = dedent("""
        import subprocess, sys
        from clearml_yolo.adapters.runtime.supervision import interruption
        with interruption():
            subprocess.run(
                [sys.executable, "-m", "torch.distributed.run", "--standalone",
                 "--nproc-per-node=2", sys.argv[1], sys.argv[2]], check=True,
            )
        """)
    token = uuid4().hex
    with (tmp_path / "torchrun.log").open("w", encoding="utf-8") as output:
        worker = subprocess.Popen(  # noqa: S603 - real native launcher, task-owned rank script
            [sys.executable, "-c", worker_script, str(rank_script), str(tmp_path)],
            start_new_session=True,
            env={**os.environ, OWNER_ENV: token},
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        rank_pids: list[int] = []
        try:
            execution._attach_process_tree(worker, token)
            rank_pids.extend(int(_ready(tmp_path / f"rank-{rank}.pid")) for rank in range(2))
            assert all(os.getpgid(pid) != worker.pid for pid in rank_pids)

            execution.cancel_process(worker)

            assert worker.poll() is not None
            assert all(not _running(pid) for pid in rank_pids)
        finally:
            with suppress(ProcessLookupError):
                os.killpg(worker.pid, signal.SIGKILL)
            _kill(worker.pid)
            worker.wait(timeout=5)
            for path in tmp_path.glob("rank-*.pid"):
                _kill(int(path.read_text(encoding="utf-8")))


def test_unreadable_new_process_blocks_verification_without_being_killed(tmp_path: Path) -> None:
    from clearml_yolo.adapters.runtime import supervision as execution

    token = uuid4().hex
    worker = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
        env={**os.environ, OWNER_ENV: token},
    )
    opaque_script = dedent("""
        import ctypes, sys, time
        from pathlib import Path
        result = ctypes.CDLL(None).prctl(4, 0, 0, 0, 0)
        assert result == 0
        Path(sys.argv[1]).write_text("ready", encoding="utf-8")
        time.sleep(60)
        """)
    opaque = subprocess.Popen(  # noqa: S603 - task-owned non-dumpable control process
        [sys.executable, "-c", opaque_script, str(tmp_path / "opaque.ready")],
        start_new_session=True,
    )
    try:
        execution._attach_process_tree(worker, token)
        _ready(tmp_path / "opaque.ready")
        try:
            Path(f"/proc/{opaque.pid}/environ").read_bytes()
        except PermissionError:
            pass
        else:
            pytest.skip("Runner can inspect non-dumpable process environments")

        with pytest.raises(RuntimeError, match="Cannot verify model process cleanup"):
            execution.cancel_process(worker)

        assert worker.poll() is not None
        assert opaque.poll() is None, "Unknown process must not be treated as job-owned"
        assert worker in execution._LINUX_TREES, "Unverified ownership must remain registered"
        assert worker in execution._POSIX_GROUPS
    finally:
        _kill(worker.pid)
        worker.wait(timeout=5)
        _kill(opaque.pid)
        opaque.wait(timeout=5)


def test_release_retries_transient_denial_until_fresh_verified_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import supervision

    token = uuid4().hex
    worker = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
        env={**os.environ, OWNER_ENV: token},
    )
    control = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    scans: list[bool] = []
    try:
        supervision._attach_process_tree(worker, token)
        tree = supervision._LINUX_TREES[worker]
        original_running = tree.running
        original_read = Path.read_bytes

        def transient_denial(path: Path) -> bytes:
            if path == Path(f"/proc/{control.pid}/environ"):
                raise PermissionError("transient process exit visibility")
            return original_read(path)

        def running() -> bool:
            assert worker in supervision._LINUX_TREES
            assert worker in supervision._POSIX_GROUPS
            scans.append(True)
            if len(scans) == 1:
                with monkeypatch.context() as scan:
                    scan.setattr(Path, "read_bytes", transient_denial)
                    return original_running()
            return original_running()

        monkeypatch.setattr(tree, "running", running)
        supervision._release_process_tree(worker, deadline=time.monotonic() + 2)

        assert len(scans) >= 2
        assert worker not in supervision._LINUX_TREES
        assert worker not in supervision._POSIX_GROUPS
        assert control.poll() is None
        worker.wait(timeout=5)
    finally:
        _kill(worker.pid)
        worker.wait(timeout=5)
        _kill(control.pid)
        control.wait(timeout=5)


@pytest.mark.parametrize("after_denial", ["gone", "zombie", "live", "reused", "inaccessible"])
def test_environment_denial_rechecks_process_liveness(
    monkeypatch: pytest.MonkeyPatch, after_denial: str
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    # A process can exit after the table snapshot but before its environment is read.
    candidate = process_tree._Process(4242, 1, 4242, 123, "S")
    tree = process_tree.LinuxProcessTree(2**31 - 1, uuid4().hex)
    monkeypatch.setattr(tree, "_table", lambda: {candidate.pid: candidate})

    def deny_environment(path: Path) -> bytes:
        assert path == Path(f"/proc/{candidate.pid}/environ")
        raise PermissionError("environment became inaccessible after stat snapshot")

    def refreshed_process(pid: int) -> process_tree._Process | None:
        assert pid == candidate.pid
        if after_denial == "inaccessible":
            raise PermissionError("process state is still inaccessible")
        if after_denial == "gone":
            return None
        return process_tree._Process(
            candidate.pid,
            candidate.parent,
            candidate.session,
            candidate.born + (after_denial == "reused"),
            "Z" if after_denial == "zombie" else "S",
        )

    monkeypatch.setattr(Path, "read_bytes", deny_environment)
    monkeypatch.setattr(process_tree, "_read_process", refreshed_process)

    if after_denial in {"gone", "zombie"}:
        assert tree.running(), "An exit during discovery requires another scan"
        monkeypatch.setattr(tree, "_table", dict)
        assert not tree.running()
    else:
        with pytest.raises(RuntimeError, match="Cannot verify model process cleanup"):
            tree.running()


@pytest.mark.parametrize("association", ["parent", "session"])
def test_pid_reuse_after_snapshot_does_not_adopt_unmarked_processes(
    monkeypatch: pytest.MonkeyPatch, association: str
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    root = process_tree._Process(101, 1, 101, 10, "S")
    replacement = process_tree._Process(root.pid, 1, root.session, 20, "S")
    child = process_tree._Process(
        202, root.pid if association == "parent" else 1,
        root.session if association == "session" else 202, 21, "S",
    )
    monkeypatch.setattr(process_tree, "_read_process", lambda _pid: root)
    tree = process_tree.LinuxProcessTree(root.pid, uuid4().hex)
    monkeypatch.setattr(tree, "_table", lambda: {root.pid: root, child.pid: child})
    monkeypatch.setattr(
        process_tree, "_read_process",
        lambda pid: replacement if pid == root.pid else child,
    )
    monkeypatch.setattr(Path, "read_bytes", lambda _path: b"")
    signalled: list[int] = []
    monkeypatch.setattr(os, "pidfd_open", lambda pid: pid)
    monkeypatch.setattr(os, "close", lambda _descriptor: None)
    monkeypatch.setattr(
        signal, "pidfd_send_signal", lambda descriptor, _signum: signalled.append(descriptor),
    )

    tree.signal(signal.SIGKILL)

    assert signalled == [], "A numeric parent/session relationship adopted an unrelated process"
    assert child.pid not in tree._identities


@pytest.mark.parametrize("child_exits_during_next_scan", [False, True])
def test_empty_scan_does_not_release_a_late_forked_child(
    monkeypatch: pytest.MonkeyPatch, child_exits_during_next_scan: bool
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    root = process_tree._Process(101, 1, 101, 10, "S")
    parent = process_tree._Process(202, 1, 202, 11, "S")
    child = process_tree._Process(303, 1, 303, 12, "S")
    token = uuid4().hex
    monkeypatch.setattr(process_tree, "_read_process", lambda _pid: root)
    tree = process_tree.LinuxProcessTree(root.pid, token)
    tree._identities[parent.pid] = parent.born
    snapshots = iter(({parent.pid: parent}, {child.pid: child}, {child.pid: child}))
    monkeypatch.setattr(tree, "_table", lambda: next(snapshots))
    monkeypatch.setattr(
        process_tree, "_read_process",
        lambda pid: child if pid == child.pid and not child_exits_during_next_scan else None,
    )
    monkeypatch.setattr(Path, "read_bytes", lambda _path: f"{OWNER_ENV}={token}\0".encode())

    assert tree.running(), "An empty snapshot accepted cleanup before late descendants were checked"
    assert tree.running(), "A second generation must also be checked before release"

    monkeypatch.setattr(tree, "_table", dict)
    monkeypatch.setattr(process_tree, "_read_process", lambda _pid: None)
    assert not tree.running(), "Stable empty discovery must eventually release capacity"


def test_disappearing_enumerated_child_prevents_false_quiescence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    root = process_tree._Process(101, 1, 101, 10, "S")
    parent = process_tree._Process(202, 1, 202, 11, "Z")
    parent_path, child_path = Path("/proc/202"), Path("/proc/303")
    monkeypatch.setattr(process_tree, "_read_process", lambda _pid: root)
    tree = process_tree.LinuxProcessTree(root.pid, uuid4().hex)
    tree._identities[parent.pid] = parent.born
    # Parent forked before becoming a zombie. Its child forks again, then disappears
    # after enumeration but before stat; the grandchild is absent from that enumeration.
    enumerations = iter(((parent_path,), (parent_path, child_path)))
    original_iterdir, original_stat = Path.iterdir, Path.stat
    owned_stat = Path(f"/proc/{os.getpid()}").stat()

    def directories(path: Path) -> Iterator[Path]:
        return iter(next(enumerations)) if path == Path("/proc") else original_iterdir(path)

    def metadata(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if path in {parent_path, child_path}:
            return owned_stat
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "iterdir", directories)
    monkeypatch.setattr(Path, "stat", metadata)
    monkeypatch.setattr(process_tree, "_read_process", lambda pid: parent if pid == 202 else None)

    assert tree.running(), "Dropping a vanished enumerated child concealed a possible grandchild"

    monkeypatch.setattr(tree, "_table", dict)
    assert not tree.running()
