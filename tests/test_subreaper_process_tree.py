"""Live supervisors discover their descendants without inspecting unrelated processes."""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

import pytest

from clearml_yolo.adapters.runtime import process_tree

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux subreaper ownership")


class ProcessTopology:
    """Model kernel identity/topology reads, including permission and exit races."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.supervisor = process_tree._Process(101, 1, 101, 10, "S")
        self.worker = process_tree._Process(202, 101, 202, 11, "S")
        self.processes = {101: self.supervisor, 202: self.worker}
        self.children: dict[int, dict[int, list[int]]] = {101: {101: [202]}, 202: {202: []}}
        self.denied_identity: set[int] = set()
        self.denied_topology: set[int] = set()
        self.denied_children: set[int] = set()
        def directories(path: Path) -> Iterator[Path]:
            return self.directories(path)

        def read_text(
            path: Path, encoding: str | None = None, errors: str | None = None,
        ) -> str:
            return self.read_text(path, encoding, errors)

        monkeypatch.setattr(process_tree, "_read_process", self.read_process)
        monkeypatch.setattr(Path, "iterdir", directories)
        monkeypatch.setattr(Path, "read_text", read_text)
        monkeypatch.setattr(Path, "read_bytes", self.read_environment)

    def read_process(self, pid: int) -> process_tree._Process | None:
        if pid in self.denied_identity:
            raise PermissionError("inaccessible identity")
        return self.processes.get(pid)

    def directories(self, path: Path) -> Iterator[Path]:
        assert path != Path("/proc"), "Live supervision scanned unrelated processes"
        assert path.name == "task", path
        pid = int(path.parent.name)
        if pid in self.denied_topology:
            raise PermissionError("inaccessible thread topology")
        return iter(path / str(tid) for tid in self.children.get(pid, {}))

    def read_text(self, path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        del encoding, errors
        assert path.name == "children", path
        pid, tid = int(path.parts[2]), int(path.parts[4])
        if pid in self.denied_children:
            raise PermissionError("inaccessible child topology")
        return " ".join(map(str, self.children[pid][tid]))

    @staticmethod
    def read_environment(path: Path) -> bytes:
        raise PermissionError(f"No readable environments, including unrelated process: {path}")

    def tree(self) -> process_tree.LinuxProcessTree:
        return process_tree.SubreaperProcessTree(202, "token", subreaper=101, born=11)


def test_live_scope_ignores_unrelated_process_permissions_and_churn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topology = ProcessTopology(monkeypatch)
    tree = topology.tree()
    topology.children[101][101] = []
    del topology.processes[202]
    topology.denied_identity.add(999)

    assert not tree.running()
    topology.processes[998] = process_tree._Process(998, 1, 998, 99, "S")
    assert not tree.running(), "An unrelated new process cannot keep the allocation owned"


@pytest.mark.parametrize("denial", ["identity", "topology", "children"])
def test_live_scope_inaccessible_descendant_blocks_release(
    monkeypatch: pytest.MonkeyPatch, denial: str,
) -> None:
    topology = ProcessTopology(monkeypatch)
    tree = topology.tree()
    if denial == "identity":
        topology.denied_identity.add(202)
    elif denial == "topology":
        topology.denied_topology.add(202)
    else:
        topology.denied_children.add(202)

    with pytest.raises(process_tree.UnverifiableProcessTreeError, match="access denied"):
        tree.running()


def test_live_scope_discovers_children_of_every_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    topology = ProcessTopology(monkeypatch)
    topology.processes[303] = process_tree._Process(303, 202, 303, 12, "S")
    topology.children[202][212] = [303]
    topology.children[303] = {303: []}
    tree = topology.tree()

    assert (303, 12) in tree.identities
    assert tree.running()


def test_live_scope_zombie_leader_cannot_hide_running_threads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topology = ProcessTopology(monkeypatch)
    topology.processes[202] = process_tree._Process(202, 101, 202, 11, "Z")
    topology.children[202][212] = []
    tree = topology.tree()

    assert tree.running(), "A zombie leader does not establish that all its threads have exited"


def test_live_scope_parent_replaced_during_topology_read_does_not_adopt_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topology = ProcessTopology(monkeypatch)
    tree = topology.tree()
    topology.children[202][202] = [303]
    topology.processes[303] = process_tree._Process(303, 202, 303, 51, "S")
    topology.children[303] = {303: []}
    original = topology.read_text

    def replace_parent(
        path: Path, encoding: str | None = None, errors: str | None = None,
    ) -> str:
        children = original(path, encoding, errors)
        if path == Path("/proc/202/task/202/children"):
            topology.processes[202] = process_tree._Process(202, 1, 202, 50, "S")
        return children

    monkeypatch.setattr(Path, "read_text", replace_parent)

    assert tree.running(), "Identity change during discovery requires a fresh scan"
    topology.children[101][101] = []
    assert (303, 51) not in tree.identities
    assert not tree.running()


def test_live_scope_does_not_adopt_known_pid_replacement(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_signal_target(pid: int, flags: int = 0) -> int:
        raise AssertionError(f"Recycled test PID must not be opened: {pid}, {flags}")

    monkeypatch.setattr(os, "pidfd_open", reject_signal_target)
    topology = ProcessTopology(monkeypatch)
    tree = topology.tree()
    topology.children[101][101] = []
    topology.processes[202] = process_tree._Process(202, 1, 202, 50, "S")
    topology.denied_topology.add(202)

    assert not tree.running(), "A recycled worker PID has no supervisor ancestry"
    tree.signal(signal.SIGKILL)


def test_live_scope_missing_enumerated_child_requires_fresh_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topology = ProcessTopology(monkeypatch)
    tree = topology.tree()
    topology.processes[202] = process_tree._Process(202, 101, 202, 11, "Z")
    topology.children[101][101] = [202, 303]

    assert tree.running(), "A disappearing child might have forked an adopted grandchild"
    topology.children[101][101] = [202]
    assert not tree.running()


def test_live_scope_second_scan_finds_late_adoption(monkeypatch: pytest.MonkeyPatch) -> None:
    topology = ProcessTopology(monkeypatch)
    tree = topology.tree()
    topology.children[101][101] = []
    del topology.processes[202]
    topology.processes[303] = process_tree._Process(303, 101, 303, 12, "S")
    topology.children[303] = {303: []}
    original = topology.read_text
    scans = 0

    def late_child(path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        nonlocal scans
        if path == Path("/proc/101/task/101/children"):
            scans += 1
            if scans > 1:
                return "303"
        return original(path, encoding, errors)

    monkeypatch.setattr(Path, "read_text", late_child)

    assert tree.running(), "One empty scan cannot establish cleanup before adoption settles"


def _wait(path: Path) -> str:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if path.exists() and (value := path.read_text(encoding="utf-8")):
            return value
        time.sleep(0.02)
    raise AssertionError(f"Missing process fixture observation: {path}")


@pytest.mark.parametrize("launch", ["fork", "orphan", "thread"])
def test_live_scope_cleans_fork_session_adoption_and_thread_children(
    tmp_path: Path, launch: str,
) -> None:
    script = r'''
import ctypes,os,signal,subprocess,sys,time
from pathlib import Path
from clearml_yolo.adapters.runtime.process_tree import SubreaperProcessTree,_read_process,_subreaper
directory=Path(sys.argv[1]); mode=sys.argv[2]
_subreaper(True)
worker_script=r"""
import ctypes,os,signal,subprocess,sys,threading,time
from pathlib import Path
directory=Path(sys.argv[1]); mode=sys.argv[2]
while not (directory/'go').exists(): time.sleep(.01)
def child():
    os.setsid()
    signal.signal(signal.SIGTERM,signal.SIG_IGN)
    (directory/'child.pid').write_text(str(os.getpid()))
    time.sleep(60)
    os._exit(0)
if mode=='thread':
    def launch():
        subprocess.Popen([sys.executable,'-c',
            'import os,signal,sys,time; from pathlib import Path; os.setsid(); '
            'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
            'Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)',
            str(directory/'child.pid')])
        time.sleep(60)
    thread=threading.Thread(target=launch); thread.start()
else:
    pid=ctypes.CDLL(None).fork()
    if pid==0:
        if mode=='orphan':
            if ctypes.CDLL(None).fork(): os._exit(0)
        child()
    if mode=='orphan': os._exit(0)
time.sleep(60)
"""
worker=subprocess.Popen([sys.executable,'-c',worker_script,str(directory),mode],
    start_new_session=True)
(directory/'worker.pid').write_text(str(worker.pid))
tree=SubreaperProcessTree(worker.pid,'unused-native-token',subreaper=os.getpid())
(directory/'go').write_text('go')
deadline=time.monotonic()+8
while not (directory/'child.pid').exists() and time.monotonic()<deadline: time.sleep(.01)
child=int((directory/'child.pid').read_text())
if mode=='orphan': worker.wait(timeout=5)
assert any(pid==child for pid,born in tree.identities), 'Descendant absent from live ownership'
tree.terminate(adopted_parent=os.getpid())
worker.wait(timeout=5)
while True:
    try:
        pid,status=os.waitpid(-1,os.WNOHANG)
    except ChildProcessError:
        break
    if not pid: break
assert _read_process(child) is None, 'Descendant survived verified cleanup'
(directory/'finished').write_text('done')
'''
    supervisor = subprocess.Popen(  # noqa: S603 - isolated, task-owned supervision fixture
        [sys.executable, "-c", script, str(tmp_path), launch],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    child: int | None = None
    try:
        child = int(_wait(tmp_path / "child.pid"))
        _, errors = supervisor.communicate(timeout=16)
        assert supervisor.returncode == 0, errors
        assert (tmp_path / "finished").exists()
    finally:
        if supervisor.poll() is None:
            with suppress(ProcessLookupError):
                os.killpg(supervisor.pid, signal.SIGKILL)
        supervisor.wait(timeout=5)
        if supervisor.stderr is not None:
            supervisor.stderr.close()
        pids = [child] if child is not None else []
        worker_file = tmp_path / "worker.pid"
        if worker_file.exists() and (worker_pid := worker_file.read_text(encoding="utf-8")):
            pids.append(int(worker_pid))
        for pid in pids:
            with suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
