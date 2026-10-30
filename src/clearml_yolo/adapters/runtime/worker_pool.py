"""Supervise independent case processes with per-case descendant ownership."""

import os
import signal
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass
from types import TracebackType
from typing import BinaryIO, Literal, Self
from uuid import uuid4

from clearml_yolo.adapters.runtime.process_tree import (
    LinuxProcessTree,
    defer_interruptions,
    native_descendant_scope,
)
from clearml_yolo.adapters.runtime.workers import WorkerCommand

_CASE_OWNER = "CY_BATCH_CASE_OWNER"


@dataclass(frozen=True)
class WorkerCompletion:
    key: str
    exit_code: int
    cleanup_complete: bool
    diagnostic: str = ""


@dataclass
class _Worker:
    process: subprocess.Popen[bytes]
    token: str
    stream: BinaryIO
    tree: LinuxProcessTree | None = None
    reported: bool = False


def _tree(worker: _Worker) -> LinuxProcessTree:
    if worker.tree is None:
        worker.tree = LinuxProcessTree(worker.process.pid, worker.token, owner_env=_CASE_OWNER)
    return worker.tree


def _cleanup(worker: _Worker) -> list[Exception]:
    """Attempt every cleanup step; uncertain cases stay owned until pool exit."""
    failures: list[Exception] = []
    try:
        _tree(worker).terminate()
    except Exception as error:  # noqa: BLE001 - preserve failure while attempting wait/reap/close
        failures.append(error)
    try:
        worker.process.wait(timeout=2)
    except subprocess.TimeoutExpired as error:
        failures.append(error)
    try:
        if worker.tree is not None:
            worker.tree.reap_children()
    except Exception as error:  # noqa: BLE001 - still close this case's log
        failures.append(error)
    try:
        worker.stream.close()
    except OSError as error:
        failures.append(error)
    return failures


class IndependentWorkerPool:
    """Own one scope and many independent jobs, without a whole-case timeout.

    The caller chooses slots and admission. A completion permits slot reuse only
    when ``cleanup_complete`` is true. Failed cleanup is reported once, retained
    for exit-time retry, and never makes the corresponding key reusable.
    """

    def __init__(self) -> None:
        self._stack: ExitStack | None = None
        self._closed = False
        self._workers: dict[str, _Worker] = {}
        self._keys: set[str] = set()

    def __enter__(self) -> Self:
        if self._stack is not None or self._closed:
            raise RuntimeError("An independent worker pool cannot be reused")
        stack = ExitStack()
        stack.enter_context(native_descendant_scope())
        self._stack = stack
        return self

    def _require_context(self) -> None:
        if self._stack is None or self._closed:
            raise RuntimeError("Independent workers require an active pool context")

    def start(self, key: str, command: WorkerCommand) -> None:
        self._require_context()
        if not key or not command.argv or not command.argv[0]:
            raise ValueError("Worker key and command must be nonempty")
        if key in self._keys:
            raise ValueError(f"Worker key {key!r} was already used")
        self._keys.add(key)
        command.log_path.parent.mkdir(parents=True, exist_ok=True)
        stream = command.log_path.open("xb")
        token = uuid4().hex
        # Registration and process-tree construction must complete before a signal
        # can unwind start; subsequent cleanup then retains the concrete Popen.
        with defer_interruptions():
            try:
                process = subprocess.Popen(  # noqa: S603 - explicit internal worker argv
                    command.argv,
                    env=dict(os.environ) | dict(command.environment) | {_CASE_OWNER: token},
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except BaseException:
                stream.close()
                raise
            worker = _Worker(process, token, stream)
            self._workers[key] = worker
            try:
                _tree(worker)
            except Exception as error:
                failures = _cleanup(worker)
                if failures:
                    raise ExceptionGroup(
                        "Worker startup and cleanup failed", [error, *failures]
                    ) from None
                del self._workers[key]
                raise

    def poll(self) -> tuple[WorkerCompletion, ...]:
        self._require_context()
        completed = []
        for key, worker in tuple(self._workers.items()):
            if worker.reported:
                continue
            exit_code = worker.process.poll()
            if exit_code is None:
                continue
            failures = _cleanup(worker)
            worker.reported = True
            completed.append(
                WorkerCompletion(
                    key=key,
                    exit_code=exit_code,
                    cleanup_complete=not failures,
                    diagnostic="; ".join(f"{type(error).__name__}: {error}" for error in failures),
                )
            )
            if not failures:
                del self._workers[key]
        return tuple(completed)

    def _stop_all(self) -> list[BaseException]:
        failures: list[BaseException] = []
        # Signal every case before waiting, so one slow descendant cannot leave
        # its peers doing expensive work throughout another case's grace period.
        for worker in self._workers.values():
            try:
                _tree(worker).signal(signal.SIGTERM)
            except BaseException as error:  # noqa: BLE001 - cleanup must attempt all owned cases
                failures.append(error)
        for worker in self._workers.values():
            try:
                failures.extend(_cleanup(worker))
            except BaseException as error:  # noqa: BLE001 - preserve interruptions until all attempts
                failures.append(error)
        self._workers.clear()
        return failures

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        stack = self._stack
        if stack is None:
            raise RuntimeError("Independent workers require an active pool context")
        self._closed = True
        with defer_interruptions():
            failures = self._stop_all()
            try:
                stack.__exit__(exception_type, exception, traceback)
            except BaseException as error:  # noqa: BLE001 - retain scope and per-case cleanup failures
                failures.append(error)
            finally:
                self._stack = None
            if failures:
                if exception is not None:
                    failures.insert(0, exception)
                raise BaseExceptionGroup("Independent worker cleanup failed", failures)
        return False
