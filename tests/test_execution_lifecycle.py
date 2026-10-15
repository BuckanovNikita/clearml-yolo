"""Jobs report stage completion without owning queue allocation or cleanup."""

import os
import socket
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from omegaconf import OmegaConf

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux supervisor channel")


def test_supervised_success_does_not_enter_native_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from clearml_yolo.entrypoints.hydra import common

    outcomes: list[str] = []

    @contextmanager
    def runtime() -> Iterator[None]:
        yield

    @contextmanager
    def invocation(*_args: Any, **_kwargs: Any) -> Iterator[Any]:
        try:
            yield SimpleNamespace(running_locally=lambda: True)
        except BaseException:
            outcomes.append("failed")
            raise
        else:
            outcomes.append("completed")

    @contextmanager
    def inaccessible_native_cleanup() -> Iterator[None]:
        from clearml_yolo.adapters.runtime.process_tree import UnverifiableProcessTreeError

        yield
        raise UnverifiableProcessTreeError("/proc access denied for unrelated PIDs")

    def workload(ultralytics_predict: dict[str, Any], clearml: dict[str, Any]) -> None:
        (tmp_path / "artifact").write_text("finished", encoding="utf-8")

    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    descriptor = child.detach()
    monkeypatch.setenv("CY_EXECUTION_CHANNEL_FD", str(descriptor))
    monkeypatch.setenv("CY_EXECUTION_OWNER_PID", str(os.getpid()))
    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "native_descendant_scope", inaccessible_native_cleanup)
    monkeypatch.setattr(common, "replay_configuration", lambda _task, values: values)
    monkeypatch.setattr(common, "initialize_naming", lambda _task: None)
    monkeypatch.setattr(common, "release_training_memory", lambda: None)
    config = OmegaConf.create({"ultralytics_predict": {"device": 0}, "clearml": {}})
    try:
        common.execute_owned("predict", config, workload)
        assert outcomes == ["completed"]
        assert (tmp_path / "artifact").read_text(encoding="utf-8") == "finished"
        parent.settimeout(1)
        assert parent.recv(64) == b"", "The job must close its lifecycle channel"
    finally:
        parent.close()
        try:
            os.fstat(descriptor)
        except OSError:
            pass
        else:
            os.close(descriptor)


def test_training_cleanup_precedes_acknowledged_handoff(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.adapters.runtime import execution_lifecycle as lifecycle
    from clearml_yolo.entrypoints import composition

    observations: list[str] = []
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    monkeypatch.setenv(lifecycle.CHANNEL_FD_ENV, str(child.detach()))
    monkeypatch.setenv(lifecycle.OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setattr(
        composition, "_resources_training_finished", lambda: observations.append("memory-free")
    )

    def guardian() -> None:
        parent.settimeout(3)
        assert parent.recv(64) == lifecycle.TRAINING_FINISHED
        assert observations == ["memory-free"]
        observations.append("reservations-released")
        parent.sendall(lifecycle.ACKNOWLEDGED)

    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            result = workers.submit(guardian)
            with lifecycle.execution_lifecycle() as supervised:
                assert supervised
                composition._ExecutionResources.training_finished()
                observations.append("inference")
            result.result(timeout=3)
        assert observations == ["memory-free", "reservations-released", "inference"]
    finally:
        parent.close()


@pytest.mark.parametrize("reply", [b"", b"invalid"])
def test_failed_handoff_cannot_start_inference(
    monkeypatch: pytest.MonkeyPatch, reply: bytes
) -> None:
    from clearml_yolo.adapters.runtime import execution_lifecycle as lifecycle

    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    monkeypatch.setenv(lifecycle.CHANNEL_FD_ENV, str(child.detach()))
    monkeypatch.setenv(lifecycle.OWNER_PID_ENV, str(os.getpid()))

    def guardian() -> None:
        parent.settimeout(3)
        assert parent.recv(64) == lifecycle.TRAINING_FINISHED
        if reply:
            parent.sendall(reply)
        parent.close()

    with ThreadPoolExecutor(max_workers=1) as workers:
        result = workers.submit(guardian)
        with lifecycle.execution_lifecycle(), pytest.raises(RuntimeError, match="handoff"):
            lifecycle.notify_training_finished()
        result.result(timeout=3)


def test_unsupervised_training_notification_is_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.adapters.runtime import execution_lifecycle as lifecycle

    monkeypatch.delenv(lifecycle.CHANNEL_FD_ENV, raising=False)
    monkeypatch.delenv(lifecycle.OWNER_PID_ENV, raising=False)
    with lifecycle.execution_lifecycle() as supervised:
        assert not supervised
        lifecycle.notify_training_finished()


def test_unresponsive_supervisor_handoff_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.adapters.runtime import execution_lifecycle as lifecycle

    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    monkeypatch.setenv(lifecycle.CHANNEL_FD_ENV, str(child.detach()))
    monkeypatch.setenv(lifecycle.OWNER_PID_ENV, str(os.getpid()))
    monkeypatch.setattr(lifecycle, "_HANDOFF_TIMEOUT_SECONDS", 0.01)
    try:
        with (
            lifecycle.execution_lifecycle(),
            pytest.raises(RuntimeError, match="handoff") as raised,
        ):
            lifecycle.notify_training_finished()
        assert isinstance(raised.value.__cause__, TimeoutError)
    finally:
        parent.close()


def test_channel_is_not_available_to_forked_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.adapters.runtime import execution_lifecycle as lifecycle

    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    descriptor = child.detach()
    monkeypatch.setenv(lifecycle.CHANNEL_FD_ENV, str(descriptor))
    monkeypatch.setenv(lifecycle.OWNER_PID_ENV, str(os.getpid()))
    try:
        with lifecycle.execution_lifecycle():
            assert not os.get_inheritable(descriptor)
            pid = os.fork()
            if pid == 0:
                lifecycle.notify_training_finished()
                os._exit(0)
            assert os.waitpid(pid, 0) == (pid, 0)
            parent.setblocking(False)
            with pytest.raises(BlockingIOError):
                parent.recv(64)
    finally:
        parent.close()
