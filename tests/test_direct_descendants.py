"""Real Linux fork ownership regressions for direct native invocations."""

import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import pytest

from clearml_yolo.adapters.runtime.process_tree import _read_process

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux process ownership")


def _wait(path: Path, *, timeout: float = 8) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists() and (value := path.read_text(encoding="utf-8")):
            return value
        time.sleep(0.02)
    raise AssertionError(f"Missing subprocess observation: {path}")


def _alive(pid: int) -> bool:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return False
    return fields[0] != "Z"


@pytest.mark.parametrize("orphan", [False, True])
@pytest.mark.parametrize("native_fork", [False, True])
def test_fork_without_exec_is_owned_and_reaped(
    tmp_path: Path, orphan: bool, native_fork: bool
) -> None:
    script = """
import ctypes,os,signal,sys,time
from pathlib import Path
from clearml_yolo.adapters.runtime.process_tree import native_descendant_scope,OWNER_ENV
root=Path(sys.argv[1]); orphan=sys.argv[2]=='True'; native_fork=sys.argv[3]=='True'
libc=ctypes.CDLL(None); before=ctypes.c_int()
assert libc.prctl(37,ctypes.byref(before),0,0,0)==0
fork=libc.fork if native_fork else os.fork
os.environ[OWNER_ENV]='inherited-guardian'
try:
    with native_descendant_scope():
        assert os.environ[OWNER_ENV]=='inherited-guardian'
        child=fork()
        if child==0:
            if orphan:
                os.setsid()
                if fork(): os._exit(0)
            signal.signal(signal.SIGTERM,signal.SIG_IGN)
            (root/'child.pid').write_text(str(os.getpid()))
            time.sleep(60); os._exit(0)
        while not (root/'child.pid').exists(): time.sleep(.01)
        raise ValueError('original failure')
except ValueError as error:
    assert str(error)=='original failure'
after=ctypes.c_int(); assert libc.prctl(37,ctypes.byref(after),0,0,0)==0
assert after.value==before.value
assert os.environ[OWNER_ENV]=='inherited-guardian'
(root/'finished').write_text('done')
"""
    with (tmp_path / "errors").open("w") as errors:
        supervisor = subprocess.Popen(  # noqa: S603 - fixed, task-owned regression supervisor
            [sys.executable, "-c", script, str(tmp_path), str(orphan), str(native_fork)],
            stdout=subprocess.DEVNULL,
            stderr=errors,
            start_new_session=True,
        )
    child: int | None = None
    try:
        child = int(_wait(tmp_path / "child.pid"))
        supervisor.wait(timeout=15)
        assert supervisor.returncode == 0, (tmp_path / "errors").read_text(encoding="utf-8")
        assert (tmp_path / "finished").exists()
        assert _read_process(child) is None, "fork-only native child escaped cleanup/reaping"
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait(timeout=5)
        if child is not None and _alive(child):
            os.kill(child, signal.SIGKILL)


def test_existing_helper_and_its_later_fork_survive(tmp_path: Path) -> None:
    script = """
import os,signal,sys,time
from pathlib import Path
from clearml_yolo.adapters.runtime.process_tree import native_descendant_scope
root=Path(sys.argv[1]); reader,writer=os.pipe()
helper=os.fork()
if helper==0:
    os.close(writer); os.read(reader,1)
    child=os.fork()
    if child==0:
        os.setsid(); (root/'helper-child.pid').write_text(str(os.getpid()))
        time.sleep(60); os._exit(0)
    time.sleep(60); os._exit(0)
os.close(reader); (root/'helper.pid').write_text(str(helper))
with native_descendant_scope():
    os.write(writer,b'x')
    while not (root/'helper-child.pid').exists(): time.sleep(.01)
    native=os.fork()
    if native==0:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        (root/'native.pid').write_text(str(os.getpid()))
        time.sleep(60); os._exit(0)
    while not (root/'native.pid').exists(): time.sleep(.01)
(root/'finished').write_text('done')
"""
    with (tmp_path / "errors").open("w") as errors:
        supervisor = subprocess.Popen(  # noqa: S603 - fixed helper provenance regression
            [sys.executable, "-c", script, str(tmp_path)],
            stdout=subprocess.DEVNULL,
            stderr=errors,
            start_new_session=True,
        )
    pids: list[int] = []
    try:
        pids.extend(
            int(_wait(tmp_path / f"{name}.pid")) for name in ("helper", "helper-child", "native")
        )
        supervisor.wait(timeout=15)
        assert supervisor.returncode == 0, (tmp_path / "errors").read_text(encoding="utf-8")
        assert _alive(pids[0])
        assert _alive(pids[1])
        assert not _alive(pids[2])
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait(timeout=5)
        for pid in pids:
            if _alive(pid):
                os.kill(pid, signal.SIGKILL)


def test_unmarked_helper_orphan_is_preserved_and_cleanup_fails_closed(tmp_path: Path) -> None:
    script = """
import os,sys,time
from pathlib import Path
from clearml_yolo.adapters.runtime.process_tree import (
    native_descendant_scope,UnverifiableProcessTreeError)
root=Path(sys.argv[1]); reader,writer=os.pipe()
helper=os.fork()
if helper==0:
    os.close(writer); os.read(reader,1)
    child=os.fork()
    if child==0:
        os.setsid(); (root/'unknown.pid').write_text(str(os.getpid()))
        time.sleep(60); os._exit(0)
    os._exit(0)
os.close(reader)
try:
    with native_descendant_scope():
        os.write(writer,b'x')
        while not (root/'unknown.pid').exists(): time.sleep(.01)
        os.waitpid(helper,0)
except UnverifiableProcessTreeError as error:
    assert 'Cannot prove native ownership' in str(error)
    (root/'failed-closed').write_text('done')
else:
    raise AssertionError('Ambiguous helper offspring treated as safely cleaned')
"""
    with (tmp_path / "errors").open("w") as errors:
        supervisor = subprocess.Popen(  # noqa: S603 - fixed orphan ambiguity regression
            [sys.executable, "-c", script, str(tmp_path)],
            stdout=subprocess.DEVNULL,
            stderr=errors,
            start_new_session=True,
        )
    unknown: int | None = None
    try:
        unknown = int(_wait(tmp_path / "unknown.pid"))
        supervisor.wait(timeout=15)
        assert supervisor.returncode == 0, (tmp_path / "errors").read_text(encoding="utf-8")
        assert (tmp_path / "failed-closed").exists()
        assert _alive(unknown)
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait(timeout=5)
        if unknown is not None and _alive(unknown):
            os.kill(unknown, signal.SIGKILL)


def test_repeated_interrupts_preserve_original_error_until_fork_cleanup(tmp_path: Path) -> None:
    script = """
import os,signal,sys,time
from pathlib import Path
from clearml_yolo.adapters.runtime.process_tree import native_descendant_scope
root=Path(sys.argv[1])
try:
    with native_descendant_scope():
        child=os.fork()
        if child==0:
            signal.signal(signal.SIGTERM,signal.SIG_IGN)
            (root/'child.pid').write_text(str(os.getpid()))
            time.sleep(60); os._exit(0)
        time.sleep(60)
except KeyboardInterrupt:
    (root/'interrupted').write_text('done')
    raise SystemExit(130)
"""
    with (tmp_path / "errors").open("w") as errors:
        supervisor = subprocess.Popen(  # noqa: S603 - fixed repeated interruption fixture
            [sys.executable, "-c", script, str(tmp_path)],
            stdout=subprocess.DEVNULL,
            stderr=errors,
            start_new_session=True,
        )
    child: int | None = None
    try:
        child = int(_wait(tmp_path / "child.pid"))
        os.kill(supervisor.pid, signal.SIGINT)
        time.sleep(0.2)
        os.kill(supervisor.pid, signal.SIGINT)
        os.kill(supervisor.pid, signal.SIGTERM)
        supervisor.wait(timeout=15)
        assert supervisor.returncode == 130, (tmp_path / "errors").read_text(encoding="utf-8")
        assert (tmp_path / "interrupted").exists()
        assert _read_process(child) is None
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait(timeout=5)
        if child is not None and _alive(child):
            os.kill(child, signal.SIGKILL)


@pytest.mark.parametrize("failure", ["subreaper", "close"])
@pytest.mark.parametrize("cleanup_failed", [False, True])
def test_restoration_failure_retains_original_error_and_restores_resources(
    monkeypatch: pytest.MonkeyPatch, failure: str, cleanup_failed: bool
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    descriptors: list[int] = []
    original_pipe = os.pipe2
    original_close = os.close

    def pipe(flags: int) -> tuple[int, int]:
        result = original_pipe(flags)
        descriptors.extend(result)
        return result

    def subreaper(enabled: bool | None = None) -> bool:
        if enabled is False and failure == "subreaper":
            raise OSError("injected subreaper restoration failure")
        return False

    def close(descriptor: int) -> None:
        original_close(descriptor)
        if descriptors and descriptor == descriptors[0] and failure == "close":
            raise OSError("injected close restoration failure")

    def terminate(_self: process_tree._NativeProcessTree) -> None:
        if cleanup_failed:
            raise RuntimeError("injected descendant cleanup failure")

    monkeypatch.setenv(process_tree.DIRECT_OWNER_ENV, "previous-scope")
    monkeypatch.setattr(os, "pipe2", pipe)
    monkeypatch.setattr(os, "close", close)
    monkeypatch.setattr(process_tree, "_subreaper", subreaper)
    monkeypatch.setattr(process_tree._NativeProcessTree, "terminate", terminate)
    original = ValueError("original invocation failure")
    try:
        with pytest.raises(BaseExceptionGroup) as captured, process_tree.native_descendant_scope():
            raise original
        assert captured.value.exceptions[0] is original
        assert len(captured.value.exceptions) == 2 + int(cleanup_failed)
        assert isinstance(captured.value.exceptions[-1], OSError)
        assert os.environ[process_tree.DIRECT_OWNER_ENV] == "previous-scope"
        for descriptor in descriptors:
            with pytest.raises(OSError, match="Bad file descriptor"):
                os.fstat(descriptor)
    finally:
        for descriptor in descriptors:
            with suppress(OSError):
                original_close(descriptor)


def test_native_scope_checks_second_empty_scan_for_late_fork(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    current = process_tree._Process(101, 1, 101, 10, "S")
    child = process_tree._Process(202, current.pid, 202, 11, "S")
    reader, writer = os.pipe2(os.O_NONBLOCK)
    monkeypatch.setattr(process_tree, "_read_process", lambda _pid: current)
    monkeypatch.setattr(process_tree.LinuxProcessTree, "_table", lambda _self: {101: current})
    try:
        tree = process_tree._NativeProcessTree(current, "direct-token", reader)
        snapshots = iter(({101: current}, {101: current, 202: child}))
        monkeypatch.setattr(tree, "_table", lambda: next(snapshots))
        monkeypatch.setattr(Path, "read_bytes", lambda _path: b"")
        monkeypatch.setattr(
            process_tree, "_read_process", lambda pid: current if pid == current.pid else child
        )

        assert tree.running(), "Native scope released before checking a late fork"
        assert tree._identities == {101: 10, 202: 11}
    finally:
        os.close(reader)
        os.close(writer)


def test_native_scope_fork_record_after_table_requires_new_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.adapters.runtime import process_tree

    current = process_tree._Process(101, 1, 101, 10, "S")
    reader, writer = os.pipe2(os.O_NONBLOCK)
    monkeypatch.setattr(process_tree, "_read_process", lambda _pid: current)
    monkeypatch.setattr(process_tree.LinuxProcessTree, "_table", lambda _self: {101: current})
    monkeypatch.setattr(Path, "read_bytes", lambda _path: b"")
    try:
        tree = process_tree._NativeProcessTree(current, "direct-token", reader)
        os.write(writer, b"202 11\n")

        assert tree.running(), "A fork identity absent from the snapshot requires rediscovery"
        assert not tree.running(), "Stable empty scans must eventually establish native cleanup"
    finally:
        os.close(reader)
        os.close(writer)
