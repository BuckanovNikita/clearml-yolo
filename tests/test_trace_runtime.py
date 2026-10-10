"""TRACE diagnostics preserve GPU and native lifecycle outcomes."""

import gc
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, get_ident
from types import SimpleNamespace
from typing import Any, cast, override

import pytest
from loguru import logger

from clearml_yolo.adapters.integrations import native_runtime as runtime_module
from clearml_yolo.adapters.integrations.native_ddp import NativeDDPRelay
from clearml_yolo.adapters.integrations.training import execute_training
from clearml_yolo.adapters.observability.tracing import trace_task
from clearml_yolo.adapters.runtime import gpu_resources, gpu_wait
from clearml_yolo.adapters.runtime.gpu_resources import GPUDevice, GPUInventory
from clearml_yolo.adapters.storage.filesystem import initialize_filesystem
from clearml_yolo.application.contracts import PreparedDataset


@pytest.fixture
def traces(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    monkeypatch.setenv("LOGURU_LEVEL", "TRACE")
    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(str(message)), level="TRACE")
    try:
        yield messages
    finally:
        logger.remove(sink)


class _Inventory(GPUInventory):
    @override
    def visible(self) -> tuple[str, ...]:
        return ("GPU-a", "GPU-b")

    @override
    def snapshot(self) -> tuple[GPUDevice, ...]:
        return (GPUDevice("GPU-a", True), GPUDevice("GPU-b", False))


def test_gpu_wait_traces_selection_without_exposing_inventory(traces: list[str]) -> None:
    assert gpu_wait.wait_for_available_gpus(1, inventory=_Inventory()) == (1,)
    text = "\n".join(traces)
    assert "START gpu.wait" in text
    assert "DONE gpu.wait" in text
    assert "START gpu.selected" in text
    assert "requested=1 selected=1" in text
    assert "GPU-a" not in text


def test_gpu_wait_invalid_request_preserves_exception(traces: list[str]) -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        gpu_wait.wait_for_available_gpus(-1)
    assert any("FAILED gpu.wait" in message for message in traces)


def test_probe_failure_diagnostics_do_not_echo_subprocess_payload(
    monkeypatch: pytest.MonkeyPatch, traces: list[str],
) -> None:
    result = SimpleNamespace(returncode=1, stderr="probe-secret", stdout="")
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: result)
    with pytest.raises(RuntimeError, match="failed"):
        gpu_resources.GPUInventory().visible()
    text = "\n".join(traces)
    assert "FAILED gpu.visibility_probe" in text
    assert "FAILED gpu.visibility" in text
    assert "probe-secret" not in text


@pytest.mark.parametrize("initialized", [False, True])
def test_gpu_memory_release_traces_actual_cleanup(
    monkeypatch: pytest.MonkeyPatch, traces: list[str], initialized: bool,
) -> None:
    calls: list[str] = []
    cuda = SimpleNamespace(
        is_initialized=lambda: initialized,
        synchronize=lambda: calls.append("synchronize"),
        empty_cache=lambda: calls.append("empty_cache"),
    )
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=cuda))
    monkeypatch.setattr(gc, "collect", lambda: calls.append("collect"))
    runtime_module.release_training_memory()
    assert calls == (["collect", "synchronize", "empty_cache"] if initialized else ["collect"])
    text = "\n".join(traces)
    assert "DONE native.import.torch" in text
    assert "DONE gpu.memory.collect" in text
    assert ("DONE gpu.memory.synchronize" in text) is initialized
    assert ("DONE gpu.memory.empty_cache" in text) is initialized


class _Model:
    def __init__(self) -> None:
        self.callbacks: dict[str, list[Any]] = {}
        self.trainer = SimpleNamespace(ddp=False)

    def add_callback(self, event: str, callback: Any) -> None:
        self.callbacks.setdefault(event, []).append(callback)


def test_ddp_relay_lifecycle_is_traced_and_callbacks_are_restored(
    tmp_path: Path, traces: list[str],
) -> None:
    model = _Model()
    relay = NativeDDPRelay(None, model, str(tmp_path))
    with relay:
        assert any(model.callbacks.values())
        relay.replay(model.trainer)
    assert not any(model.callbacks.values())
    text = "\n".join(traces)
    for operation in ("start", "replay", "join", "cleanup"):
        assert f"START ddp.relay.{operation}" in text
        assert f"DONE ddp.relay.{operation}" in text
    assert "ddp.callback" not in text


def test_native_runtime_generator_traces_enter_and_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, traces: list[str],
) -> None:
    from ultralytics.utils import SETTINGS

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    monkeypatch.delenv(runtime_module.OWNER_PID_ENV, raising=False)
    monkeypatch.delenv(runtime_module.OWNER_TASK_ENV, raising=False)
    monkeypatch.setattr(runtime_module, "_enable_owner", lambda *_args: None)
    original = SETTINGS["clearml"]
    context = runtime_module.native_runtime()
    assert traces == []
    with context:
        assert any("DONE native.runtime.setup" in message for message in traces)
        assert not any("native.runtime.restore" in message for message in traces)
    assert SETTINGS["clearml"] is original
    assert any("DONE native.runtime.restore" in message for message in traces)


def test_gpu_trace_is_silent_without_opt_in(
    monkeypatch: pytest.MonkeyPatch, traces: list[str],
) -> None:
    monkeypatch.setenv("LOGURU_LEVEL", "INFO")
    assert gpu_wait.wait_for_available_gpus(0) == ()
    assert traces == []


def test_training_model_load_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch, traces: list[str],
) -> None:
    failure = RuntimeError("native-private-details")

    def load(_architecture: object) -> None:
        raise failure

    monkeypatch.setitem(sys.modules, "ultralytics.models", SimpleNamespace(YOLO=load))
    with pytest.raises(RuntimeError) as caught:
        execute_training(None, "yolo.pt", {}, cast(PreparedDataset, object()))
    assert caught.value is failure
    text = "\n".join(traces)
    assert "DONE native.import.yolo" in text
    assert "FAILED training.model.load" in text
    assert "native-private-details" not in text


def test_gpu_synchronize_failure_does_not_continue_cleanup(
    monkeypatch: pytest.MonkeyPatch, traces: list[str],
) -> None:
    failure = RuntimeError("cuda-private-details")
    calls: list[str] = []

    def synchronize() -> None:
        raise failure

    cuda = SimpleNamespace(
        is_initialized=lambda: True,
        synchronize=synchronize,
        empty_cache=lambda: calls.append("empty_cache"),
    )
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=cuda))
    monkeypatch.setattr(gc, "collect", lambda: None)
    with pytest.raises(RuntimeError) as caught:
        runtime_module.release_training_memory()
    assert caught.value is failure
    assert calls == []
    text = "\n".join(traces)
    assert "FAILED gpu.memory.synchronize" in text
    assert "gpu.memory.empty_cache" not in text
    assert "cuda-private-details" not in text


@pytest.mark.parametrize("fail_inside", [False, True])
def test_native_directory_cleanup_span_encloses_actual_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, traces: list[str], fail_inside: bool,
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    monkeypatch.delenv(runtime_module.OWNER_PID_ENV, raising=False)
    monkeypatch.delenv(runtime_module.OWNER_TASK_ENV, raising=False)
    monkeypatch.setattr(runtime_module, "_enable_owner", lambda *_args: None)
    original_cleanup = TemporaryDirectory.cleanup
    cleaned: list[str] = []
    failure = RuntimeError("caller failed")

    def observe_cleanup(directory: TemporaryDirectory[str]) -> None:
        text = "\n".join(traces)
        assert "DONE native.runtime.restore" in text
        assert "START native.runtime.directory.cleanup" in text
        assert "DONE native.runtime.directory.cleanup" not in text
        assert Path(directory.name).is_dir()
        original_cleanup(directory)
        assert not Path(directory.name).exists()
        cleaned.append(directory.name)

    monkeypatch.setattr(TemporaryDirectory, "cleanup", observe_cleanup)
    if fail_inside:
        with (
            pytest.raises(RuntimeError, match="caller failed") as caught,
            runtime_module.native_runtime(),
        ):
            raise failure
        assert caught.value is failure
    else:
        with runtime_module.native_runtime():
            pass
    assert len(cleaned) == 1
    assert any("DONE native.runtime.directory.cleanup" in message for message in traces)


def test_native_directory_cleanup_failure_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, traces: list[str],
) -> None:
    failure = OSError("cleanup failed")
    original_cleanup = TemporaryDirectory.cleanup

    def fail_cleanup(directory: TemporaryDirectory[str]) -> None:
        original_cleanup(directory)
        raise failure

    monkeypatch.setattr(TemporaryDirectory, "cleanup", fail_cleanup)
    directory = runtime_module._NativeTemporaryDirectory(dir=tmp_path)
    with pytest.raises(OSError, match="cleanup failed") as caught, directory:
        pass
    assert caught.value is failure
    assert not Path(directory.name).exists()
    assert any("FAILED native.runtime.directory.cleanup" in message for message in traces)


def test_ddp_consumer_span_parents_callback_and_identifies_training(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, traces: list[str],
) -> None:
    model = _Model()
    model.trainer.ddp = True
    relay = NativeDDPRelay(None, model, str(tmp_path))
    waits = iter([False, True])
    monkeypatch.setattr(relay, "_stop", SimpleNamespace(wait=lambda _delay: next(waits)))
    monkeypatch.setattr(relay, "_args", SimpleNamespace())
    monkeypatch.setattr(
        relay, "_callbacks", lambda: {"on_train_epoch_end": lambda _trainer: None}
    )
    monkeypatch.setattr(relay, "_consume", lambda: relay._dispatch({"event": "on_train_epoch_end"}))
    relay._consume_live()
    consumer = next(message for message in traces if "START ddp.consumer" in message)
    callback = next(message for message in traces if "START ddp.callback" in message)
    match = re.search(r"op=([0-9a-f]+)", consumer)
    assert match is not None
    assert f"parent={match.group(1)} " in callback
    assert "stage=train" in consumer
    assert "stage=train" in callback
    assert sum("START ddp.consumer" in message for message in traces) == 1
    assert any("DONE ddp.consumer" in message for message in traces)


def test_actual_ddp_consumer_callback_inherits_task_context_at_thread_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, traces: list[str],
) -> None:
    model = _Model()
    model.trainer.ddp = True
    relay = NativeDDPRelay(None, model, str(tmp_path))
    release_callback = Event()
    callback_finished = Event()
    monkeypatch.setattr(relay, "_args", SimpleNamespace())
    monkeypatch.setattr(
        relay, "_callbacks", lambda: {"on_train_epoch_end": lambda _trainer: None}
    )

    def consume() -> None:
        if not release_callback.wait(3):
            raise RuntimeError("test did not release consumer callback")
        relay._dispatch({"event": "on_train_epoch_end"})
        relay._stop.set()
        callback_finished.set()

    monkeypatch.setattr(relay, "_consume", consume)
    with trace_task("owner-task-context"):
        relay.__enter__()
    try:
        # The consumer keeps creation-time context after the owner's binding exits.
        with trace_task("different-caller-context"):
            release_callback.set()
            assert callback_finished.wait(3)
    finally:
        release_callback.set()
        model.trainer.ddp = False
        relay.__exit__(None, None, None)
    callback = next(message for message in traces if "START ddp.callback" in message)
    assert "task=owner-task-context " in callback
    assert "different-caller-context" not in callback
    assert f"thread={get_ident()} " not in callback
    assert any(
        "DONE ddp.consumer" in message and "task=owner-task-context " in message
        for message in traces
    )


def _interrupting_sink(marker: str, failure: BaseException) -> Callable[[object], None]:
    def sink(message: object) -> None:
        if marker in str(message):
            raise failure
    return sink


def test_ddp_start_terminal_sink_interruption_rolls_back_live_resources(
    tmp_path: Path, traces: list[str],
) -> None:
    model = _Model()
    relay = NativeDDPRelay(None, model, str(tmp_path))
    failure = KeyboardInterrupt("sink interrupted relay startup")
    sink = logger.add(
        _interrupting_sink("DONE ddp.relay.start", failure), level="TRACE", catch=False
    )
    try:
        with pytest.raises(KeyboardInterrupt, match="relay startup") as caught:
            relay.__enter__()
        assert caught.value is failure
        assert not any(model.callbacks.values())
        assert relay._thread is not None
        assert not relay._thread.is_alive()
    finally:
        logger.remove(sink)
    assert any("DONE ddp.relay.join" in message for message in traces)


@pytest.mark.parametrize("operation", ["ddp.relay.cleanup", "ddp.relay.join"])
@pytest.mark.parametrize("event", ["START", "DONE"])
def test_ddp_cleanup_sink_interruption_finishes_join_and_callback_removal(
    tmp_path: Path, traces: list[str], operation: str, event: str,
) -> None:
    model = _Model()
    relay = NativeDDPRelay(None, model, str(tmp_path))
    failure = KeyboardInterrupt("sink interrupted relay cleanup")
    sink = logger.add(
        _interrupting_sink(f"{event} {operation}", failure), level="TRACE", catch=False
    )
    try:
        with pytest.raises(KeyboardInterrupt, match="relay cleanup") as caught, relay:
            pass
        assert caught.value is failure
        assert not any(model.callbacks.values())
        assert relay._thread is not None
        assert not relay._thread.is_alive()
    finally:
        logger.remove(sink)
    assert any("DONE ddp.relay.join" in message for message in traces)


@pytest.mark.parametrize(
    "operation", ["native.runtime.restore", "native.runtime.directory.cleanup"]
)
@pytest.mark.parametrize("fail_inside", [False, True])
def test_native_cleanup_sink_interruption_restores_globals_and_removes_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, traces: list[str],
    operation: str, fail_inside: bool,
) -> None:
    from ultralytics import utils
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.callbacks import clearml as integration

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    monkeypatch.delenv(runtime_module.OWNER_PID_ENV, raising=False)
    monkeypatch.delenv(runtime_module.OWNER_TASK_ENV, raising=False)
    initialize_filesystem()
    previous_directory = os.environ.get("YOLO_CONFIG_DIR")
    previous_setting = SETTINGS["clearml"]
    previous_callbacks = integration.callbacks
    previous_runs = utils.RUNS_DIR

    def enable(_integration: object, settings: Any) -> None:
        dict.__setitem__(settings, "clearml", not previous_setting)
        integration.callbacks = {"test": lambda _trainer: None}

    monkeypatch.setattr(runtime_module, "_enable_owner", enable)
    interruption = KeyboardInterrupt("sink interrupted native cleanup")
    failure = ValueError("caller failed before cleanup")
    sink = logger.add(
        _interrupting_sink(f"START {operation}", interruption), level="TRACE", catch=False
    )
    temporary: list[Path] = []

    def run_native() -> None:
        with runtime_module.native_runtime():
            temporary.append(Path(os.environ["YOLO_CONFIG_DIR"]))
            if fail_inside:
                raise failure

    try:
        if fail_inside:
            with pytest.raises(ValueError, match="caller failed") as caller_error:
                run_native()
            assert caller_error.value is failure
        else:
            with pytest.raises(KeyboardInterrupt, match="native cleanup") as caught:
                run_native()
            assert caught.value is interruption
    finally:
        logger.remove(sink)
    assert len(temporary) == 1
    assert not temporary[0].exists()
    assert os.environ.get("YOLO_CONFIG_DIR") == previous_directory
    assert SETTINGS["clearml"] is previous_setting
    assert integration.callbacks is previous_callbacks
    assert previous_runs == utils.RUNS_DIR
    assert any(
        terminal in message
        for message in traces
        for terminal in (
            "DONE native.runtime.directory.cleanup", "INTERRUPTED native.runtime.directory.cleanup"
        )
    )


@pytest.mark.parametrize("event", ["START", "DONE"])
def test_gpu_cleanup_sink_interruption_finishes_all_memory_release_phases(
    monkeypatch: pytest.MonkeyPatch, traces: list[str], event: str,
) -> None:
    calls: list[str] = []
    cuda = SimpleNamespace(
        is_initialized=lambda: True,
        synchronize=lambda: calls.append("synchronize"),
        empty_cache=lambda: calls.append("empty_cache"),
    )
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=cuda))
    monkeypatch.setattr(gc, "collect", lambda: calls.append("collect"))
    failure = KeyboardInterrupt("sink interrupted memory release")
    sink = logger.add(
        _interrupting_sink(f"{event} gpu.memory.collect", failure), level="TRACE", catch=False
    )
    try:
        with pytest.raises(KeyboardInterrupt, match="memory release") as caught:
            runtime_module.release_training_memory()
        assert caught.value is failure
    finally:
        logger.remove(sink)
    assert calls == ["collect", "synchronize", "empty_cache"]
    assert any("DONE gpu.memory.empty_cache" in message for message in traces)


@pytest.mark.parametrize("operation", ["ddp.relay.cleanup", "ddp.relay.join"])
def test_ddp_cleanup_sink_interruption_preserves_pending_caller_exception(
    tmp_path: Path, traces: list[str], operation: str,
) -> None:
    model = _Model()
    relay = NativeDDPRelay(None, model, str(tmp_path))
    interruption = KeyboardInterrupt("sink interrupted pending cleanup")
    failure = ValueError("caller failed during relay")
    sink = logger.add(
        _interrupting_sink(f"START {operation}", interruption), level="TRACE", catch=False
    )
    try:
        with pytest.raises(ValueError, match="caller failed") as caught, relay:
            raise failure
        assert caught.value is failure
        assert not any(model.callbacks.values())
        assert relay._thread is not None
        assert not relay._thread.is_alive()
    finally:
        logger.remove(sink)
    assert any("DONE ddp.relay.join" in message for message in traces)
