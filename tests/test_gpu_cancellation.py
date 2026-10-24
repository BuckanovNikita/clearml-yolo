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

from clearml_yolo.adapters.runtime import process_tree
from clearml_yolo.adapters.runtime.process_tree import OWNER_ENV, LinuxProcessTree
from test_direct_descendants import _alive, _wait

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="requires Linux /proc")


def _kill(pid: int) -> None:
    with suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not _alive(pid), f"Task-owned process {pid} survived test teardown"


def test_cleanup_defers_first_interrupt_and_restores_handlers() -> None:
    previous = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}
    events: list[str] = []

    def cleanup() -> None:
        with process_tree.defer_interruptions():
            signal.raise_signal(signal.SIGINT)
            with process_tree.defer_interruptions():
                signal.raise_signal(signal.SIGTERM)
                events.append("inner cleanup finished")
            events.append("outer cleanup finished")

    with pytest.raises(KeyboardInterrupt):
        cleanup()
    assert events == ["inner cleanup finished", "outer cleanup finished"]
    assert {signum: signal.getsignal(signum) for signum in previous} == previous


def test_inaccessible_owned_process_prevents_verified_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            tree = LinuxProcessTree(worker.pid, token)
            rank_pids.extend(
                int(_wait(tmp_path / f"rank-{rank}.pid", timeout=10)) for rank in range(2)
            )
            assert all(os.getpgid(pid) != worker.pid for pid in rank_pids)

            tree.terminate()
            worker.wait(timeout=5)

            assert worker.poll() is not None
            assert all(not _alive(pid) for pid in rank_pids)
        finally:
            with suppress(ProcessLookupError):
                os.killpg(worker.pid, signal.SIGKILL)
            _kill(worker.pid)
            worker.wait(timeout=5)
            for path in tmp_path.glob("rank-*.pid"):
                _kill(int(path.read_text(encoding="utf-8")))


def test_unreadable_new_process_blocks_verification_without_being_killed(tmp_path: Path) -> None:
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
        tree = LinuxProcessTree(worker.pid, token)
        _wait(tmp_path / "opaque.ready", timeout=10)
        try:
            Path(f"/proc/{opaque.pid}/environ").read_bytes()
        except PermissionError:
            pass
        else:
            pytest.skip("Runner can inspect non-dumpable process environments")

        with pytest.raises(RuntimeError, match="Cannot verify model process cleanup"):
            tree.terminate()
        worker.wait(timeout=5)

        assert worker.poll() is not None
        assert opaque.poll() is None, "Unknown process must not be treated as job-owned"
        assert worker.pid in dict(tree.identities), "Unverified cleanup retains recovery identity"
    finally:
        _kill(worker.pid)
        worker.wait(timeout=5)
        _kill(opaque.pid)
        opaque.wait(timeout=5)


@pytest.mark.parametrize("after_denial", ["gone", "zombie", "live", "reused", "inaccessible"])
def test_environment_denial_rechecks_process_liveness(
    monkeypatch: pytest.MonkeyPatch, after_denial: str
) -> None:
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
