"""An opaque stage handoff to the process that supervises this invocation."""

import os
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

CHANNEL_FD_ENV = "CY_EXECUTION_CHANNEL_FD"
OWNER_PID_ENV = "CY_EXECUTION_OWNER_PID"
TRAINING_FINISHED = b"training-finished-v1"
ACKNOWLEDGED = b"ok-v1"
_HANDOFF_TIMEOUT_SECONDS = 30.0
_CHANNEL: ContextVar[tuple[int, socket.socket] | None] = ContextVar(
    "execution_lifecycle_channel", default=None
)


@contextmanager
def execution_lifecycle() -> Iterator[bool]:
    """Own the inherited channel through finalization, without exposing scheduling.

    The launch gate supplies the original PID across exec. Forked model workers
    cannot notify, and later execs cannot inherit the descriptor or its selectors.
    Direct invocations have no channel and keep their own descendant supervision.
    """
    active = _CHANNEL.get()
    if active is not None and active[0] == os.getpid():
        yield True
        return
    descriptor = os.environ.get(CHANNEL_FD_ENV)
    owner = os.environ.get(OWNER_PID_ENV)
    if descriptor is None and owner is None:
        yield False
        return
    if descriptor is None or owner is None:
        raise RuntimeError("Incomplete execution supervisor channel")
    if int(owner) != os.getpid():
        yield False
        return
    with socket.socket(fileno=int(descriptor)) as channel:
        if channel.family != socket.AF_UNIX or channel.type != socket.SOCK_SEQPACKET:
            raise RuntimeError("Execution supervision requires a local packet channel")
        channel.getpeername()
        channel.set_inheritable(False)
        channel.settimeout(_HANDOFF_TIMEOUT_SECONDS)
        os.environ.pop(CHANNEL_FD_ENV)
        os.environ.pop(OWNER_PID_ENV)
        token = _CHANNEL.set((os.getpid(), channel))
        try:
            yield True
        finally:
            _CHANNEL.reset(token)


def notify_training_finished() -> None:
    """Wait for the supervisor after training has returned and freed unused memory."""
    active = _CHANNEL.get()
    if active is None or active[0] != os.getpid():
        return
    try:
        active[1].sendall(TRAINING_FINISHED)
        response = active[1].recv(64)
    except OSError as error:
        raise RuntimeError("Training completion handoff to supervisor failed") from error
    if response != ACKNOWLEDGED:
        raise RuntimeError("Training completion handoff was not acknowledged by supervisor")
