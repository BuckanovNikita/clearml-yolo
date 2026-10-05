"""FIFO GPU reservations and supervisor/worker liveness."""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from clearml_yolo.gpu_queue import GPUQueue, queue_root
from clearml_yolo.gpu_resources import GPUDevice


class MutableInventory:
    def __init__(self, *devices: GPUDevice) -> None:
        self.devices = devices

    def snapshot(self) -> tuple[GPUDevice, ...]:
        return tuple(self.devices)


class FailingInventory:
    def snapshot(self) -> tuple[GPUDevice, ...]:
        raise OSError("telemetry unavailable")


@pytest.fixture
def child_processes() -> Iterator[list[subprocess.Popen[str]]]:
    processes: list[subprocess.Popen[str]] = []
    yield processes
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _write_inventory(path: Path, *, busy: tuple[str, ...] = ()) -> None:
    values = [
        {"uuid": uuid, "busy": uuid in busy}
        for uuid in ("GPU-a", "GPU-b", "GPU-c")
    ]
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values), encoding="utf-8")
    temporary.replace(path)


def _start(
    child_processes: list[subprocess.Popen[str]],
    mode: str,
    root: Path,
    inventory: Path,
    *arguments: str,
    secret: str | None = None,
) -> tuple[subprocess.Popen[str], dict[str, object]]:
    command = [
        sys.executable,
        str(Path(__file__).with_name("gpu_queue_worker.py")),
        mode,
        "--root",
        str(root),
        "--inventory",
        str(inventory),
        *arguments,
    ]
    environment = dict(os.environ)
    if secret is not None:
        environment["GPU_QUEUE_TEST_SECRET"] = secret
    process = subprocess.Popen(  # noqa: S603 - fixed test helper and task-owned arguments
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    child_processes.append(process)
    return process, _read(process)


def _read(process: subprocess.Popen[str]) -> dict[str, object]:
    assert process.stdout is not None
    line = process.stdout.readline()
    if not line:
        assert process.stderr is not None
        pytest.fail(f"queue child exited {process.poll()}: {process.stderr.read()}")
    value = json.loads(line)
    assert isinstance(value, dict)
    return value


def _command(process: subprocess.Popen[str], command: str) -> dict[str, object]:
    assert process.stdin is not None
    process.stdin.write(f"{command}\n")
    process.stdin.flush()
    return _read(process)


def _stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    assert process.stdin is not None
    process.stdin.write("exit\n")
    process.stdin.flush()
    process.wait(timeout=5)


def _idle_inventory() -> MutableInventory:
    return MutableInventory(
        GPUDevice(uuid="GPU-a", busy=False),
        GPUDevice(uuid="GPU-b", busy=False),
        GPUDevice(uuid="GPU-c", busy=False),
    )


def test_queue_root_uses_user_state_and_ignores_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))

    assert queue_root() == state / "clearml-yolo" / "queue"


def test_register_validates_count_without_leaving_a_waiter(tmp_path: Path) -> None:
    queue = GPUQueue(root=tmp_path, inventory=_idle_inventory())
    with pytest.raises(ValueError, match="positive"):
        queue.register(0, ("GPU-a",))
    with pytest.raises(ValueError, match="visible"):
        queue.register(2, ("GPU-a",))

    ticket = queue.register(1, ("GPU-a",))
    try:
        assert ticket.position() == 1
    finally:
        ticket.close()


def test_closed_ticket_number_is_never_reused_and_registry_lock_remains(tmp_path: Path) -> None:
    queue = GPUQueue(root=tmp_path, inventory=_idle_inventory())
    first = queue.register(1, ("GPU-a",))
    first_number = int(first.id)
    first.close()

    second = queue.register(1, ("GPU-a",))
    try:
        assert int(second.id) == first_number + 1
    finally:
        second.close()
    assert (tmp_path / "registry.lock").is_file()


def test_ticket_reports_latest_devices_and_closed_ticket_is_missing(tmp_path: Path) -> None:
    ticket = GPUQueue(root=tmp_path, inventory=_idle_inventory()).register(
        2, ("GPU-a", "GPU-b", "GPU-c")
    )
    assert not ticket.devices
    assert ticket.try_acquire() == ("GPU-a", "GPU-b")
    assert list(ticket.devices) == ["GPU-a", "GPU-b"]
    assert ticket.position() == 0

    ticket.close()

    with pytest.raises(ValueError, match="ticket"):
        ticket.position()
    with pytest.raises(ValueError, match="ticket"):
        _ = ticket.devices


def test_external_compute_occupancy_is_excluded_atomically(tmp_path: Path) -> None:
    inventory = MutableInventory(
        GPUDevice(uuid="GPU-a", busy=True),
        GPUDevice(uuid="GPU-b", busy=False),
        GPUDevice(uuid="GPU-c", busy=False),
    )
    first = GPUQueue(root=tmp_path, inventory=inventory).register(
        1, ("GPU-a", "GPU-b", "GPU-c")
    )
    second = GPUQueue(root=tmp_path, inventory=inventory).register(
        1, ("GPU-a", "GPU-b", "GPU-c")
    )
    try:
        assert first.try_acquire() == ("GPU-b",)
        assert second.try_acquire() == ("GPU-c",)
        assert set(first.devices).isdisjoint(second.devices)
    finally:
        first.close()
        second.close()


def test_telemetry_failure_keeps_head_ticket_pending(tmp_path: Path) -> None:
    ticket = GPUQueue(root=tmp_path, inventory=FailingInventory()).register(1, ("GPU-a",))
    try:
        with pytest.raises(OSError, match="telemetry unavailable"):
            ticket.try_acquire()
        assert ticket.position() == 1
        assert ticket.devices == ()
    finally:
        ticket.close()


def test_processes_share_fifo_and_oldest_blocked_waiter_stops_smaller_request(
    tmp_path: Path, child_processes: list[subprocess.Popen[str]]
) -> None:
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory)
    root = tmp_path / "queue"
    first, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "2", "--visible", "GPU-a", "GPU-b", "GPU-c",
    )
    second, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "2", "--visible", "GPU-a", "GPU-b", "GPU-c",
    )
    third, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "1", "--visible", "GPU-a", "GPU-b", "GPU-c",
    )
    try:
        assert _command(second, "position")["position"] == 2
        assert _command(second, "acquire")["devices"] is None
        assert _command(first, "acquire")["devices"] == ["GPU-a", "GPU-b"]
        assert _command(second, "acquire")["devices"] is None
        assert _command(third, "acquire")["devices"] is None
        assert _command(first, "close")["event"] == "close"
        assert _command(second, "acquire")["devices"] == ["GPU-a", "GPU-b"]
        assert _command(third, "acquire")["devices"] == ["GPU-c"]
    finally:
        _stop(first)
        _stop(second)
        _stop(third)


def test_cancelled_and_abandoned_waiters_do_not_block_followers(
    tmp_path: Path, child_processes: list[subprocess.Popen[str]]
) -> None:
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory)
    root = tmp_path / "queue"
    cancelled, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "3", "--visible", "GPU-a", "GPU-b", "GPU-c",
    )
    abandoned, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "3", "--visible", "GPU-a", "GPU-b", "GPU-c",
    )
    follower, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "1", "--visible", "GPU-a", "GPU-b", "GPU-c",
    )
    _write_inventory(inventory, busy=("GPU-a",))
    try:
        assert _command(cancelled, "acquire")["devices"] is None
        assert _command(cancelled, "close")["event"] == "close"
        abandoned.terminate()
        abandoned.wait(timeout=5)
        assert _command(follower, "acquire")["devices"] == ["GPU-b"]
    finally:
        _stop(cancelled)
        _stop(follower)


def test_live_worker_keeps_reservation_after_supervisor_closes(
    tmp_path: Path, child_processes: list[subprocess.Popen[str]]
) -> None:
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory)
    root = tmp_path / "queue"
    supervisor, registration = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "1", "--visible", "GPU-a",
    )
    assert _command(supervisor, "acquire")["devices"] == ["GPU-a"]
    worker, claim = _start(
        child_processes, "worker", root, inventory,
        "--ticket-id", str(registration["ticket_id"]),
    )
    assert claim["devices"] == ["GPU-a"]
    assert _command(supervisor, "close")["event"] == "close"
    follower, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "1", "--visible", "GPU-a",
    )
    try:
        assert _command(follower, "acquire")["devices"] is None
        _stop(worker)
        assert _command(follower, "acquire")["devices"] == ["GPU-a"]
    finally:
        _stop(supervisor)
        _stop(worker)
        _stop(follower)


def test_worker_cannot_revive_ticket_after_supervisor_closes_before_claim(
    tmp_path: Path, child_processes: list[subprocess.Popen[str]]
) -> None:
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory)
    root = tmp_path / "queue"
    supervisor, registration = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "1", "--visible", "GPU-a",
    )
    assert _command(supervisor, "acquire")["devices"] == ["GPU-a"]
    assert _command(supervisor, "close")["event"] == "close"

    worker, first_output = _start(
        child_processes, "worker", root, inventory,
        "--ticket-id", str(registration["ticket_id"]),
    )

    assert first_output["event"] != "claimed"
    worker.wait(timeout=5)
    assert worker.returncode != 0


def test_shrink_releases_only_idle_surplus_devices(
    tmp_path: Path, child_processes: list[subprocess.Popen[str]]
) -> None:
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory)
    root = tmp_path / "queue"
    supervisor, registration = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "3", "--visible", "GPU-a", "GPU-b", "GPU-c",
    )
    assert _command(supervisor, "acquire")["devices"] == ["GPU-a", "GPU-b", "GPU-c"]
    worker, _ = _start(
        child_processes, "worker", root, inventory,
        "--ticket-id", str(registration["ticket_id"]),
    )
    follower, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "2", "--visible", "GPU-b", "GPU-c",
    )
    try:
        _write_inventory(inventory, busy=("GPU-c",))
        refused = _command(worker, "shrink")
        assert refused["error"] == "RuntimeError"
        assert _command(follower, "acquire")["devices"] is None

        _write_inventory(inventory)
        assert _command(worker, "shrink")["devices"] == ["GPU-a"]
        assert _command(supervisor, "devices")["devices"] == ["GPU-a"]
        assert _command(worker, "shrink")["devices"] == ["GPU-a"]
        assert _command(follower, "acquire")["devices"] == ["GPU-b", "GPU-c"]
    finally:
        _stop(worker)
        _stop(supervisor)
        _stop(follower)


def test_corrupt_registry_fails_closed_without_replacing_it(tmp_path: Path) -> None:
    queue = GPUQueue(root=tmp_path, inventory=_idle_inventory())
    ticket = queue.register(1, ("GPU-a",))
    ticket.close()
    registry = next(path for path in tmp_path.iterdir() if path.suffix == ".json")
    corrupt = b'{"tickets": ['
    registry.write_bytes(corrupt)

    with pytest.raises(RuntimeError, match="registry"):
        queue.register(1, ("GPU-a",))

    assert registry.read_bytes() == corrupt


def test_private_registry_never_captures_process_arguments_or_environment(
    tmp_path: Path, child_processes: list[subprocess.Popen[str]]
) -> None:
    inventory = tmp_path / "inventory.json"
    _write_inventory(inventory)
    root = tmp_path / "queue"
    marker = "do-not-persist-this-value"
    supervisor, _ = _start(
        child_processes, "supervisor", root, inventory,
        "--count", "1", "--visible", "GPU-a", "--untrusted-label", marker, secret=marker,
    )
    try:
        contents = b"\n".join(path.read_bytes() for path in root.iterdir() if path.is_file())
        assert marker.encode() not in contents
    finally:
        _stop(supervisor)


def test_concurrent_registry_writer_waits_for_short_transaction(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from filelock import FileLock

    queue = GPUQueue(root=tmp_path)
    with ThreadPoolExecutor(max_workers=1) as executor:
        with FileLock(tmp_path / "registry.lock", preserve_lock_file=True):
            future = executor.submit(queue.register, 1, ("GPU-a",))
            with pytest.raises(TimeoutError):
                future.result(timeout=0.1)
        ticket = future.result(timeout=5)
        executor.submit(ticket.close).result(timeout=5)


def test_stalled_telemetry_does_not_hold_registry_lock(tmp_path: Path) -> None:
    import concurrent.futures
    import threading

    started = threading.Event()
    release = threading.Event()

    class BlockingInventory:
        def snapshot(self) -> tuple[GPUDevice, ...]:
            started.set()
            assert release.wait(timeout=5)
            return (GPUDevice("GPU-a", False),)

    queue = GPUQueue(tmp_path, BlockingInventory())
    ticket = queue.register(1, ("GPU-a",))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        admission = pool.submit(ticket.try_acquire)
        try:
            assert started.wait(timeout=2)
            position = pool.submit(ticket.position)
            assert position.result(timeout=0.5) == 1
        finally:
            release.set()
            admission.result(timeout=2)
            ticket.close()


def test_admission_rereads_registry_after_telemetry(tmp_path: Path) -> None:
    import concurrent.futures
    import threading

    started = threading.Event()
    release = threading.Event()

    class BlockingInventory:
        def snapshot(self) -> tuple[GPUDevice, ...]:
            started.set()
            assert release.wait(timeout=5)
            return (GPUDevice("GPU-a", False),)

    queue = GPUQueue(tmp_path, BlockingInventory())
    ticket = queue.register(1, ("GPU-a",))
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        admission = pool.submit(ticket.try_acquire)
        try:
            assert started.wait(timeout=2)
            ticket.close()
        finally:
            release.set()
        with pytest.raises(ValueError, match="closed or missing"):
            admission.result(timeout=2)
    assert json.loads((tmp_path / "registry.json").read_text())["requests"] == []


def test_stalled_contraction_does_not_hold_registry_lock(tmp_path: Path) -> None:
    import concurrent.futures
    import threading

    started = threading.Event()
    release = threading.Event()

    class BlockingInventory:
        block = False

        def snapshot(self) -> tuple[GPUDevice, ...]:
            if self.block:
                started.set()
                assert release.wait(timeout=5)
            return (GPUDevice("GPU-a", False), GPUDevice("GPU-b", False))

    inventory = BlockingInventory()
    queue = GPUQueue(tmp_path, inventory)
    ticket = queue.register(2, ("GPU-a", "GPU-b"))
    assert ticket.try_acquire() == ("GPU-a", "GPU-b")
    with queue.claim_worker(ticket.id) as claim:
        inventory.block = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            contraction = pool.submit(claim.shrink)
            try:
                assert started.wait(timeout=2)
                assert pool.submit(ticket.position).result(timeout=0.5) == 0
            finally:
                release.set()
            assert contraction.result(timeout=2) == ("GPU-a",)
    ticket.close()
