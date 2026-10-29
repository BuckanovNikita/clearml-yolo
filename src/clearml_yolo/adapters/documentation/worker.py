"""Bounded ownership of disposable documentation preview subprocesses."""

import os
import selectors
import signal
import subprocess
import sys
from collections.abc import Sequence
from contextlib import suppress
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore, Lock
from time import monotonic, sleep

from pydantic import ValidationError

from clearml_yolo.adapters.documentation.files import MAX_REQUEST_BYTES
from clearml_yolo.core.documentation import PreviewRequest, PreviewResult

WORKER_TIMEOUT = 15
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_DIAGNOSTIC_BYTES = 32 * 1024
_READ_CHUNK = 64 * 1024


class PreviewWorkers:
    def __init__(self, command: Sequence[str]) -> None:
        if not command:
            raise ValueError("Preview worker command must not be empty")
        self.command = tuple(command)
        self._lock = Lock()
        self._slots = BoundedSemaphore(2)
        self._processes: dict[subprocess.Popen[bytes], TemporaryDirectory[str]] = {}
        self._closed = False

    def __call__(self, request: PreviewRequest) -> PreviewResult:
        if not self._slots.acquire(blocking=False):
            return PreviewResult(errors=["Preview workers are busy; try again shortly"])
        try:
            return self._run(request)
        finally:
            self._slots.release()

    def _run(self, request: PreviewRequest) -> PreviewResult:
        payload = request.model_dump_json().encode("utf-8")
        if len(payload) > MAX_REQUEST_BYTES:
            return PreviewResult(errors=["Preview request exceeds 1 MiB"])
        with self._lock:
            if self._closed:
                return PreviewResult(errors=["Documentation server is shutting down"])
            try:
                process, directory = _start_worker(self.command)
            except OSError as error:
                return PreviewResult(errors=[f"Cannot start preview worker: {error}"])
            self._processes[process] = directory
        try:
            return _worker_result(process, payload, self._lock)
        finally:
            self._release(process)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()

    def _release(self, process: subprocess.Popen[bytes]) -> None:
        _stop(process, self._lock)
        # close() must finish cleanup even when daemon request threads cannot run
        # their finally blocks. Serialize competing owners after the group stops.
        with self._lock:
            directory = self._processes.get(process)
            if directory is not None:
                directory.cleanup()
                del self._processes[process]

    def close(self) -> None:
        with self._lock:
            self._closed = True
            processes = tuple(self._processes)
        for process in processes:
            self._release(process)


def _start_worker(
    command: Sequence[str],
) -> tuple[subprocess.Popen[bytes], TemporaryDirectory[str]]:
    directory = TemporaryDirectory(prefix="cy-docs-worker-")
    # The parent retains ownership when SIGKILL bypasses the child's file cleanup.
    environment = os.environ | dict.fromkeys(("TMPDIR", "TMP", "TEMP"), directory.name)
    try:
        process = subprocess.Popen(  # noqa: S603 - composition root supplies the fixed command
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=environment,
        )
    except OSError:
        directory.cleanup()
        raise
    return process, directory


def _worker_result(process: subprocess.Popen[bytes], payload: bytes, lock: Lock) -> PreviewResult:
    try:
        output, diagnostic = _communicate_bounded(process, payload, lock)
        if process.returncode:
            message = (
                f"Preview worker failed ({process.returncode}): "
                f"{diagnostic.decode('utf-8', errors='replace')[-2000:]}"
            )
            return PreviewResult(errors=[message])
        return PreviewResult.model_validate_json(output)
    except TimeoutError:
        return PreviewResult(errors=["Preview exceeded its 15-second deadline"])
    except (OSError, ValueError, ValidationError) as error:
        return PreviewResult(errors=[f"Invalid preview worker response: {error}"])


def _stop(process: subprocess.Popen[bytes], lock: Lock) -> None:
    # Before reaping the leader, its PID and process group remain owned. Serialize
    # reaping with close() so a finished/reused PID can never be signalled here.
    with lock:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=WORKER_TIMEOUT)


def _communicate_bounded(
    process: subprocess.Popen[bytes], payload: bytes, lock: Lock
) -> tuple[bytes, bytes]:
    if process.stdin is None or process.stdout is None or process.stderr is None:
        raise RuntimeError("Preview worker streams are unavailable")
    deadline = monotonic() + WORKER_TIMEOUT
    output, diagnostic = bytearray(), bytearray()
    offset = 0
    with selectors.DefaultSelector() as selector:
        for stream, event in (
            (process.stdin, selectors.EVENT_WRITE),
            (process.stdout, selectors.EVENT_READ),
            (process.stderr, selectors.EVENT_READ),
        ):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, event)
        while selector.get_map():
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError("Preview deadline exceeded")
            for key, event in selector.select(remaining):
                if event == selectors.EVENT_WRITE:
                    offset = _write_input(selector, process, payload, offset)
                else:
                    chunk = os.read(key.fd, _READ_CHUNK)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    destination = output if key.fileobj is process.stdout else diagnostic
                    destination.extend(chunk)
                    _check_output_limits(output, diagnostic)
    _wait_worker(process, deadline, lock)

    return bytes(output), bytes(diagnostic)


def _wait_worker(process: subprocess.Popen[bytes], deadline: float, lock: Lock) -> None:
    while (remaining := deadline - monotonic()) > 0:
        # Observe exit without reaping the leader: its PID still owns this process
        # group while descendants are stopped, including children that closed pipes.
        with lock:
            if process.returncode is not None:
                return
            outcome = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG)
            if outcome is not None:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=remaining)
                return
        sleep(min(0.05, remaining))
    raise TimeoutError("Preview deadline exceeded")


def _write_input(
    selector: selectors.BaseSelector, process: subprocess.Popen[bytes], payload: bytes, offset: int
) -> int:
    if process.stdin is None:
        raise RuntimeError("Preview worker input is unavailable")
    try:
        offset += os.write(process.stdin.fileno(), payload[offset : offset + _READ_CHUNK])
    except BrokenPipeError:
        offset = len(payload)
    if offset == len(payload):
        selector.unregister(process.stdin)
        process.stdin.close()
    return offset


def _check_output_limits(output: bytearray, diagnostic: bytearray) -> None:
    if len(output) > MAX_RESPONSE_BYTES:
        raise ValueError("Preview result exceeds 8 MiB; reduce the sweep")
    if len(diagnostic) > MAX_DIAGNOSTIC_BYTES:
        raise ValueError("Preview worker diagnostic exceeds 32 KiB")


def worker_command(module: str) -> tuple[str, ...]:
    return sys.executable, "-I", "-m", module
