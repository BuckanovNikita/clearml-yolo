"""Stdlib-only project workspace and retained invocation scratch.

Library configuration, caches and temporary defaults remain library/user-owned.
Project temporary files receive an explicit directory without changing global
``tempfile`` settings or scanning existing directories.
"""

import os
import signal
import tempfile
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

_LOCK = threading.RLock()
_ARENA_ENV = "CY_RUNTIME_ARENA"


@dataclass
class _State:
    active: tuple[int, Path] | None = None


_STATE = _State()


def _capture_queue_root() -> None:
    """Keep GPU coordination user-wide across project workspace selections."""
    if os.environ.get("CY_GPU_QUEUE_ROOT"):
        return
    if os.name == "nt":
        state = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    else:
        state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    os.environ["CY_GPU_QUEUE_ROOT"] = str((state.expanduser() / "clearml-yolo/queue").resolve())


def _temporary_root(root: Path) -> Path:
    selected = Path(os.environ.get("CY_RUNTIME_TEMP_ROOT") or root / ".tmp").expanduser()
    return (selected if selected.is_absolute() else root / selected).resolve()


def initialize_runtime_environment() -> Path:
    """Freeze CY_HOME and create project scratch without configuring libraries."""
    with _LOCK:
        root = Path(os.environ.get("CY_HOME") or Path.cwd()).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        _temporary_root(root).mkdir(parents=True, exist_ok=True)
        _capture_queue_root()
        os.environ["CY_HOME"] = str(root)
        return root


def invocation_temporary_root() -> Path | None:
    """Return active or inherited scratch, with no ownership or recovery claims."""
    selected = os.environ.get(_ARENA_ENV)
    if selected:
        arena = Path(selected).expanduser().resolve()
        if arena.is_dir():
            return arena
    return None


@contextmanager
def runtime_environment() -> Iterator[Path]:
    """Provide explicit project scratch, retaining it after every exit outcome.

    Nested calls reuse the current process's arena. Spawned processes receive a
    fresh arena while inherited scratch stays available to late descendants.
    """
    with _LOCK:
        root = initialize_runtime_environment()
        if _STATE.active is not None and _STATE.active[0] == os.getpid():
            yield _STATE.active[1]
            return
        arena = Path(tempfile.mkdtemp(prefix="cy-runtime-", dir=_temporary_root(root)))
        previous_active = _STATE.active
        previous_arena = os.environ.get(_ARENA_ENV)
        previous_handler: int | Callable[[int, FrameType | None], object] | None = None
        try:
            os.environ[_ARENA_ENV] = str(arena)
            _STATE.active = (os.getpid(), arena)
            if threading.current_thread() is threading.main_thread():
                previous_handler = signal.getsignal(signal.SIGTERM)
                signal.signal(signal.SIGTERM, _terminate)
            yield arena
        finally:
            _STATE.active = previous_active
            if previous_arena is None:
                os.environ.pop(_ARENA_ENV, None)
            else:
                os.environ[_ARENA_ENV] = previous_arena
            if previous_handler is not None:
                signal.signal(signal.SIGTERM, previous_handler)


def _terminate(signum: int, _frame: FrameType | None) -> None:
    raise SystemExit(128 + signum)
