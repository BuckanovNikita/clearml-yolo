"""Supervise fresh cooperating workers without signalling unrelated processes."""

import math
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Literal
from uuid import uuid4

from clearml_yolo.adapters.runtime.process_tree import LinuxProcessTree, native_descendant_scope

_WORKER_OWNER = "CY_TRAINING_WORKER_OWNER"


@dataclass(frozen=True)
class WorkerCommand:
    argv: tuple[str, ...]
    environment: Mapping[str, str]
    log_path: Path


@dataclass(frozen=True)
class WorkerOutcome:
    status: Literal["success", "crash", "timeout"]
    exit_codes: tuple[int, ...]


def _await_workers(
    processes: Sequence[subprocess.Popen[bytes]],
    trees: Sequence[LinuxProcessTree],
    deadline: float,
    monitor: Callable[[Callable[[], tuple[int, ...]]], None] | None,
) -> Literal["success", "crash", "timeout"]:
    def owned_pids() -> tuple[int, ...]:
        return tuple(sorted({pid for tree in trees for pid in tree.live_pids()}))

    while True:
        codes = [process.poll() for process in processes]
        if any(code is not None and code != 0 for code in codes):
            return "crash"
        if all(code == 0 for code in codes):
            return "success"
        if monitor is not None:
            monitor(owned_pids)
        if time.monotonic() >= deadline:
            return "timeout"
        time.sleep(0.05)


def _stop_workers(
    processes: Sequence[subprocess.Popen[bytes]], trees: Sequence[LinuxProcessTree]
) -> None:
    failures: list[Exception] = []
    for tree in trees:
        try:
            tree.signal(signal.SIGTERM)
        except Exception as error:  # noqa: BLE001 - still signal remaining owned peers
            failures.append(error)
    for tree in trees:
        try:
            tree.terminate()
        except Exception as error:  # noqa: BLE001 - cleanup must attempt every owned rank
            failures.append(error)
    for process in processes:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired as error:
            failures.append(error)
    for tree in trees:
        try:
            tree.reap_children()
        except Exception as error:  # noqa: BLE001 - still reap other confirmed rank descendants
            failures.append(error)
    if failures:
        raise ExceptionGroup("Training worker cleanup failed", failures)


def run_workers(
    commands: Sequence[WorkerCommand],
    *,
    timeout_seconds: float,
    monitor: Callable[[Callable[[], tuple[int, ...]]], None] | None = None,
) -> WorkerOutcome:
    """Return only after all ranks and owned descendants exit, including on interruption.

    A nonzero rank or deadline terminates peers immediately. The caller interprets
    typed receipts: a nonzero exit alone never establishes CUDA OOM or usable capacity.
    Logs are retained at caller-owned paths and the monitor may forward scalar events.
    Monitors receive a fresh ownership callable to invoke after collecting telemetry,
    so children born during a slow query can be verified without trusting old PIDs.
    """
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("Worker timeout must be finite and positive")
    if not commands or any(not command.argv for command in commands):
        raise ValueError("At least one nonempty worker command is required")
    processes: list[subprocess.Popen[bytes]] = []
    trees: list[LinuxProcessTree] = []
    with ExitStack() as stack, native_descendant_scope():
        try:
            for command in commands:
                token = uuid4().hex
                command.log_path.parent.mkdir(parents=True, exist_ok=True)
                stream: BinaryIO = stack.enter_context(command.log_path.open("xb"))
                process = subprocess.Popen(  # noqa: S603 - explicit internal worker argv
                    command.argv,
                    env=dict(os.environ) | dict(command.environment) | {_WORKER_OWNER: token},
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                processes.append(process)
                trees.append(LinuxProcessTree(process.pid, token, owner_env=_WORKER_OWNER))
            status = _await_workers(processes, trees, time.monotonic() + timeout_seconds, monitor)
        finally:
            primary = sys.exception()
            try:
                _stop_workers(processes, trees)
            except Exception as cleanup_error:
                if primary is not None:
                    raise BaseExceptionGroup(
                        "Worker execution and cleanup failed", [primary, cleanup_error]
                    ) from None
                raise
    return WorkerOutcome(
        status=status, exit_codes=tuple(process.returncode for process in processes)
    )
