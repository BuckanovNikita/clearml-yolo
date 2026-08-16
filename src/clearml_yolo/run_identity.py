"""What one run is called, and the directory that is only its own.

Two runs started in the same folder used to train into the same ``runs/detect/<task_name>``
with ultralytics' ``exist_ok: true`` set, which is not a confusing merge but a deletion: the
DDP launcher clears the save directory before it spawns its children, so one run's start
destroys a peer's in-flight checkpoints. A run therefore gets an identity first, and every
path it writes hangs off a directory named after that identity.

The id carries the host because a workspace on a shared mount can be driven from two
machines, and the pid because two runs on one machine must differ. Neither is enough on its
own and the pair is unique only among *live* runs: per-run directories are kept, pids are
recycled across a reboot, and ``exist_ok`` is still true, so a stamp is what stops a run
from quietly overwriting an old one. ``now`` is a parameter rather than read here so the
identity is decided by the caller and the tests are deterministic.
"""

from __future__ import annotations

import os
import socket
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from loguru import logger

# The symlink beside the run directories that always names the newest of them, so the
# documented habits stay one directory away: ``ls runs/latest/metrics``.
LATEST_LINK_NAME = "latest"


def _host_and_pid() -> tuple[str, int]:
    """The two facts that separate concurrent runs, behind one seam.

    Both are read through here rather than inline so a test can make an id reproducible by
    replacing this single function.
    """
    return socket.gethostname(), os.getpid()


def resolve_run_id(task_name: str, explicit: str | None, now: datetime) -> str:
    """Name this run, unless the caller already named it.

    An explicit id wins outright: it is how two stages of one pipeline, or a rerun that
    means to land beside an earlier one, share a directory on purpose.
    """
    if explicit:
        return explicit
    host, pid = _host_and_pid()
    return f"{task_name}-{host}-{now:%Y%m%d-%H%M%S}-{pid}"


def resolve_run_dir(root: Path, run_id: str, explicit: Path | None) -> Path:
    """Where this run writes, as an absolute path.

    Absolute because hydra is configured with ``chdir=False`` while ultralytics resolves
    its own project path against the process' working directory: a relative path handed to
    a stage would mean one thing when it was composed and another when it was used.
    """
    chosen = explicit if explicit is not None else root / run_id
    return chosen.expanduser().resolve()


def point_latest_at(root: Path, run_dir: Path) -> None:
    """Repoint ``root/latest`` at this run, and never fail the run over it.

    The replacement goes through a second symlink renamed over the first, so a reader
    following the link concurrently sees the old target or the new one and never a gap.
    Everything that can go wrong here — a filesystem without symlinks, a directory nobody
    may write, something that is not a symlink already sitting at the path — costs a
    convenience shortcut and nothing else, so it is logged rather than raised.
    """
    latest = root / LATEST_LINK_NAME
    if latest.exists() and not latest.is_symlink():
        logger.warning(
            "Leaving {} alone because it is not a symlink; this run is at {}", latest, run_dir
        )
        return
    host, pid = _host_and_pid()
    pending = root / f".{LATEST_LINK_NAME}-{host}-{pid}"
    try:
        root.mkdir(parents=True, exist_ok=True)
        pending.unlink(missing_ok=True)
        pending.symlink_to(run_dir)
        pending.replace(latest)
    except OSError as error:
        logger.warning("Could not point {} at {}: {}", latest, run_dir, error)
        with suppress(OSError):
            pending.unlink(missing_ok=True)
