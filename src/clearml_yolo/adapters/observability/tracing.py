"""Opt-in operation diagnostics with an independent, bounded process watchdog.

The monitor reads immutable snapshots without acquiring application or Loguru locks.
Only locations are sampled: no traceback formatting, source lookup or locals access.
"""

import os
import re
import sys
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from time import monotonic
from types import FrameType

from loguru import logger

from clearml_yolo.core.redaction import redact_text, sensitive_key

HEARTBEAT_SECONDS = 30.0
STACK_SECONDS = 60.0
MAX_STACK_GROUPS = 8
MAX_STACK_FRAMES = 12
_SHUTDOWN_SECONDS = 0.2
_TEXT_LIMIT = 180
_CONTEXT_KEYS = frozenset(
    {
        "stage",
        "split",
        "artifact",
        "destination",
        "path",
        "rows",
        "columns",
        "images",
        "count",
        "total",
        "classes",
        "devices",
        "device",
        "cache",
        "format",
        "role",
        "bytes",
        "epochs",
        "event",
        "worker",
        "requested",
        "selected",
        "task_id",
    }
)


def _text(value: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "?", redact_text(value))[:_TEXT_LIMIT]


def _context(context: Mapping[str, object] | None) -> str:
    if context is None:
        return ""
    parts = []
    for key, value in context.items():
        if key not in _CONTEXT_KEYS or sensitive_key(key):
            continue
        # Exact scalar types only: no arbitrary __str__, repr, rows or tensors.
        if type(value) in (str, int, float, bool) or value is None:
            parts.append(f"{key}={_text(str(value))}")
    return " ".join(parts[:12])


@dataclass(frozen=True)
class _Operation:
    name: str
    identity: str
    parent: str
    stage: str
    started: float
    thread: int
    task: str
    context: str


@dataclass
class _State:
    pid: int = field(default_factory=os.getpid)
    active: dict[int, tuple[_Operation, ...]] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    stop: threading.Event = field(default_factory=threading.Event)
    monitor: threading.Thread | None = None
    fd: int | None = None
    sequence: int = 0


_state = _State()
_task_id: ContextVar[tuple[int, str]] = ContextVar("trace_task_id", default=(0, "-"))
_cleanup_interruptions: ContextVar[tuple[int, list[BaseException]] | None] = ContextVar(
    "trace_cleanup_interruptions", default=None
)


def _deferred_interruptions() -> list[BaseException] | None:
    binding = _cleanup_interruptions.get()
    return binding[1] if binding is not None and binding[0] == os.getpid() else None


def _raise_deferred(interruptions: list[BaseException]) -> None:
    if interruptions:
        raise interruptions[0]


def _process_state() -> _State:
    global _state  # noqa: PLW0603 - replace all inherited process state after fork
    if _state.pid != os.getpid():
        # Never acquire inherited locks or join an inherited thread after fork.
        if _state.fd is not None:
            os.close(_state.fd)
        _state = _State()
    return _state


def _enabled() -> bool:
    return os.environ.get("LOGURU_LEVEL", "").upper() == "TRACE"


def _write_watchdog(state: _State, text: str) -> None:
    if state.fd is not None:
        # A closed diagnostic destination must not affect application work.
        with suppress(OSError):
            os.write(state.fd, (text + "\n").encode("utf-8", errors="replace"))


def _fields(operation: _Operation, now: float) -> str:
    return (
        f"op={operation.identity} parent={operation.parent} pid={os.getpid()} "
        f"thread={operation.thread} task={operation.task} "
        f"elapsed={max(0, now - operation.started):.3f}s"
    )


def _emit(event: str, operation: _Operation, *, preserve_exception: bool = False) -> None:
    # Nested failure finalizers have their own spans, but the outer error still wins.
    preserve_exception = preserve_exception or sys.exception() is not None
    try:
        logger.opt(exception=False).trace(
            "{} {} {} {}",
            event,
            operation.name,
            _fields(operation, monotonic()),
            operation.context,
        )
    except BaseException as error:
        # Signals can arrive inside a sink. Propagate termination unless an original
        # application exception is already unwinding and must retain precedence.
        if not preserve_exception and not isinstance(error, Exception):
            deferred = _deferred_interruptions()
            if deferred is None:
                raise
            if not deferred:
                deferred.append(error)
        _write_watchdog(_state, f"TRACE diagnostic emission failed pid={os.getpid()}")


def _frames(frame: FrameType) -> tuple[tuple[str, ...], bool]:
    result: list[str] = []
    current: FrameType | None = frame
    while current is not None and len(result) < MAX_STACK_FRAMES:
        code = current.f_code
        result.append(f"{_text(code.co_filename)}:{current.f_lineno} in {_text(code.co_name)}")
        current = current.f_back
    return tuple(result), current is not None


def _stack_snapshot(
    active: dict[int, tuple[_Operation, ...]],
    monitor_id: int | None,
) -> tuple[tuple[tuple[str, ...], tuple[int, ...], bool], ...]:
    groups: dict[tuple[tuple[str, ...], bool], list[int]] = {}
    frames = sys._current_frames()  # noqa: SLF001 - Python's location-only sampling API
    # Active threads are considered first, even when SDK helper threads outnumber them.
    diagnostic_ids = {
        thread.ident for thread in threading.enumerate() if thread.name.startswith("cy-trace-")
    }
    for thread_id in sorted(frames, key=lambda key: (key not in active, key)):
        if thread_id == monitor_id or thread_id in diagnostic_ids:
            continue
        locations = _frames(frames[thread_id])
        groups.setdefault(locations, []).append(thread_id)
    return tuple(
        (locations, tuple(ids), truncated) for (locations, truncated), ids in groups.items()
    )


def _render_snapshot(snapshot: tuple[tuple[tuple[str, ...], tuple[int, ...], bool], ...]) -> str:
    lines = [f"TRACE STACK snapshot pid={os.getpid()} groups={len(snapshot)}"]
    for locations, ids, truncated in snapshot[:MAX_STACK_GROUPS]:
        lines.append(f"  threads={','.join(map(str, ids))}")
        lines.extend(f"    {location}" for location in locations)
        if truncated:
            lines.append(f"    frames truncated at {MAX_STACK_FRAMES}")
    if len(snapshot) > MAX_STACK_GROUPS:
        lines.append(f"  groups truncated: omitted={len(snapshot) - MAX_STACK_GROUPS}")
    return "\n".join(lines)


def _monitor(state: _State) -> None:
    heartbeat = monotonic() + HEARTBEAT_SECONDS
    stacks = monotonic() + STACK_SECONDS
    previous: object = None
    try:
        while not state.stop.wait(max(0.001, min(heartbeat, stacks) - monotonic())):
            now = monotonic()
            active = state.active.copy()
            if now >= heartbeat:
                for operations in active.values():
                    operation = operations[-1]
                    _write_watchdog(
                        state,
                        (
                            f"TRACE ACTIVE {operation.name} {_fields(operation, now)} "
                            f"parent_stage={operation.stage} {operation.context}"
                        ),
                    )
                heartbeat = now + HEARTBEAT_SECONDS
            if now >= stacks:
                snapshot = _stack_snapshot(active, threading.get_ident())
                if snapshot != previous:
                    _write_watchdog(state, _render_snapshot(snapshot))
                    previous = snapshot
                stacks = now + STACK_SECONDS
    except Exception:  # noqa: BLE001 - isolate diagnostic-thread failures from application work
        _write_watchdog(state, f"TRACE watchdog unavailable pid={state.pid}")
    finally:
        if state.fd is not None:
            os.close(state.fd)
            state.fd = None


def _start_monitor(state: _State) -> None:
    state.stop = threading.Event()
    try:
        try:
            state.fd = os.dup(sys.stderr.fileno())
        except (AttributeError, OSError, ValueError):
            state.fd = None
        state.monitor = threading.Thread(
            target=_monitor,
            args=(state,),
            name="cy-trace-watchdog",
            daemon=True,
        )
        state.monitor.start()
    except Exception:  # noqa: BLE001 - unavailable diagnostics must leave no owned resources
        _write_watchdog(state, f"TRACE watchdog startup unavailable pid={state.pid}")
        if state.fd is not None:
            with suppress(OSError):
                os.close(state.fd)
        state.fd = None
        state.monitor = None


def _begin(name: str, context: Mapping[str, object] | None) -> tuple[_State, _Operation]:
    state = _process_state()
    with state.lock:
        thread_id = threading.get_ident()
        parents = state.active.get(thread_id, ())
        task_pid, task_id = _task_id.get()
        state.sequence += 1
        operation = _Operation(
            _text(name),
            f"{state.sequence:x}",
            parents[-1].identity if parents else "-",
            next(
                (
                    parent.name
                    for parent in reversed(parents)
                    if parent.name.startswith("workflow.")
                ),
                parents[-1].name if parents else _text(name),
            ),
            monotonic(),
            thread_id,
            task_id if task_pid == state.pid else "-",
            _context(context),
        )
        state.active[thread_id] = (*parents, operation)
        if state.monitor is None or not state.monitor.is_alive():
            _start_monitor(state)
    return state, operation


def _end(state: _State, operation: _Operation) -> None:
    if state.pid != os.getpid():
        return
    with state.lock:
        remaining = tuple(
            item for item in state.active.get(operation.thread, ()) if item != operation
        )
        if remaining:
            state.active[operation.thread] = remaining
        else:
            state.active.pop(operation.thread, None)
        if not state.active and state.monitor is not None:
            state.stop.set()
            state.monitor.join(_SHUTDOWN_SECONDS)
            if not state.monitor.is_alive():
                state.monitor = None


@contextmanager
def trace_operation(
    name: str,
    *,
    context: Mapping[str, object] | None = None,
    cleanup: bool = False,
) -> Iterator[None]:
    """Measure a boundary; cleanup spans defer sink interruptions until cleanup runs."""
    if not _enabled():
        yield
        return
    try:
        state, operation = _begin(name, context)
    except Exception:  # noqa: BLE001 - setup is diagnostic only
        yield
        return
    interruptions: list[BaseException] = []
    token = (
        _cleanup_interruptions.set((os.getpid(), interruptions))
        if cleanup and _deferred_interruptions() is None
        else None
    )
    try:
        try:
            _emit("START", operation)
            yield
            _raise_deferred(interruptions)
            _emit("DONE", operation)
            _raise_deferred(interruptions)
        except BaseException as error:
            event = "FAILED" if isinstance(error, Exception) else "INTERRUPTED"
            if isinstance(error, SystemExit) and error.code in (None, 0):
                event = "DONE"
            _emit(event, operation, preserve_exception=True)
            raise
    finally:
        if token is not None:
            _cleanup_interruptions.reset(token)
        try:
            _end(state, operation)
        except Exception:  # noqa: BLE001 - cleanup must preserve the application exception
            _write_watchdog(state, f"TRACE diagnostic cleanup failed pid={state.pid}")


@contextmanager
def trace_task(task_id: str) -> Iterator[None]:
    """Bind the invocation-owned task in this context and explicitly copied contexts."""
    if not _enabled():
        yield
        return
    # A copied thread context keeps ownership; a fork must not inherit that ownership.
    token = _task_id.set((os.getpid(), _text(task_id)))
    try:
        yield
    finally:
        _task_id.reset(token)


def trace_command[**P, R](name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Cover a command's entire cleanup lifetime and report its final return boundary."""

    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def run(*args: P.args, **kwargs: P.kwargs) -> R:
            failed = False
            try:
                with trace_operation(f"command.{name}"):
                    return function(*args, **kwargs)
            except BaseException:
                failed = True
                raise
            finally:
                if _enabled():
                    operation = _Operation(
                        "command.return",
                        "-",
                        "-",
                        name,
                        monotonic(),
                        threading.get_ident(),
                        "-",
                        f"stage={_text(name)}",
                    )
                    _emit("DONE", operation, preserve_exception=failed)

        return run

    return decorate
