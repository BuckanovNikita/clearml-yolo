"""Bound SDK finalization in its owning thread, without detached status writes."""

import atexit
import signal
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from types import FrameType
from typing import Any


class TaskFinalizationError(RuntimeError):
    """Required task finalization cannot finish safely within its deadline."""


class _DeadlineInterrupt(BaseException):
    """Bypass SDK catch-Exception blocks; convert after leaving the SDK boundary."""


def _interrupt(_signum: int, _frame: FrameType | None) -> None:
    raise _DeadlineInterrupt


def detach_sdk_exit_callback(task: Any) -> None:
    """Prevent a failed explicit close from repeating unbounded SDK work at exit.

    The installed ClearML Task.init registers task._at_exit through ExitHooks.hook;
    Task.close removes it only after __shutdown succeeds. That callback retries an
    interrupted shutdown once. Unregister exactly this owner-bound callback through
    the standard library, without mutating SDK task state or another caller's hooks.
    The existing owner reporter independently registers an unbounded drain callback;
    detach that exact cached instance too, without invoking its lazy SDK getter.
    """
    callback = getattr(task, "_at_exit", None)
    if callable(callback):
        atexit.unregister(callback)
    # This opaque SDK compatibility field holds only an already-created reporter.
    # task._reporter would create reporting work while handling incomplete shutdown.
    reporter = getattr(task, "_Task__reporter", None)
    reporter_callback = getattr(reporter, "_handle_program_exit", None)
    if callable(reporter_callback):
        atexit.unregister(reporter_callback)


@contextmanager
def sdk_deadline(seconds: float) -> Iterator[None]:
    """Require a Unix main-thread alarm slot; never override an embedding timer."""
    if (
        not hasattr(signal, "setitimer")
        or threading.current_thread() is not threading.main_thread()
    ):
        raise TaskFinalizationError("Bounded ClearML finalization requires a Unix main thread")
    timer = signal.getitimer(signal.ITIMER_REAL)
    if timer != (0.0, 0.0):
        raise TaskFinalizationError("Bounded ClearML finalization conflicts with an existing alarm")
    previous = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _interrupt)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except _DeadlineInterrupt as error:
        raise TaskFinalizationError("ClearML task finalization deadline expired") from error
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
