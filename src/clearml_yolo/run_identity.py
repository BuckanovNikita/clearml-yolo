"""Filesystem-only output identities and the workspace's latest-run shortcut."""

import os
import socket
from contextlib import suppress
from pathlib import Path
from urllib.parse import quote

from loguru import logger

from clearml_yolo.diagnostics import log_exception
from clearml_yolo.filesystem import write_path

# The symlink beside the run directories that always names the newest of them, so the
# documented habits stay one directory away: ``ls runs/latest/metrics``.
LATEST_LINK_NAME = "latest"


def safe_path_component(value: str) -> str:
    """Encode names reversibly as portable single components, including Windows devices."""
    if not value:
        raise ValueError("Task identity components must be nonempty")
    encoded = quote(value, safe="-_", encoding="utf-8").replace(".", "%2E").replace("~", "%7E")
    reserved = {
        LATEST_LINK_NAME.upper(),
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(10)),
        *(f"LPT{i}" for i in range(10)),
    }
    if encoded.upper() in reserved:
        encoded = f"%{ord(encoded[0]):02X}{encoded[1:]}"
    return encoded


def task_run_dir(root: Path, project_name: str, task_name: str, task_id: str) -> Path:
    """Resolve an implicit root from plain identity values, independent of tracking SDKs."""
    return (
        root
        / safe_path_component(project_name)
        / f"{safe_path_component(task_name)}-{safe_path_component(task_id)}"
    ).resolve()


def _host_and_pid() -> tuple[str, int]:
    """Identify concurrent latest-link updates and displaced destinations."""
    return socket.gethostname(), os.getpid()


def resolve_run_dir(root: Path, run_id: str, explicit: Path | None) -> Path:
    """Where this run writes, as an absolute path.

    Absolute because hydra is configured with ``chdir=False`` while ultralytics resolves
    its own project path against the process' working directory: a relative path handed to
    a stage would mean one thing when it was composed and another when it was used.
    """
    chosen = explicit if explicit is not None else root / run_id
    return write_path(chosen).resolve()


def point_latest_at(root: Path, run_dir: Path) -> None:
    """Repoint ``root/latest`` at this run, and never fail the run over it.

    Only a run inside the workspace the root lives in is pointed at. The link is the
    workspace's shortcut to its own newest run, and a run written elsewhere — an agent's in
    a scratch directory that its cleanup deletes — is not one of those: pointing at it would
    leave the link dangling and the next standalone stage reading a checkpoint through it
    finding nothing. Such a run is left alone and the link keeps naming the last run that
    did land here.

    The replacement goes through a second symlink renamed over the first, so a reader
    following the link concurrently sees the old target or the new one and never a gap.

    Anything that is not a symlink sitting at the name is moved aside rather than written
    over or left in place. A standalone stage whose default output path runs *through* the
    link creates the name as an ordinary directory the first time it is used in a fresh
    workspace, and leaving that alone would freeze the link for every later run while
    nothing ever wrote into what it holds; deleting it would take a directory a user may
    have put there on purpose. The move keeps the contents, names the run that displaced
    them, and lets the next run take the name back on its own.

    A filesystem without symlinks, a directory nobody may write, a displaced name already
    taken — each costs a convenience shortcut and nothing else, so it is logged rather than
    raised, and the next run tries again under a different pid.
    """
    latest = root / LATEST_LINK_NAME
    workspace = root.resolve().parent
    target = run_dir.resolve()
    if target != workspace and workspace not in target.parents:
        logger.info(
            "Leaving {} alone: {} is outside {}, and the link names only this workspace's runs",
            latest,
            run_dir,
            workspace,
        )
        return
    host, pid = _host_and_pid()
    pending = root / f".{LATEST_LINK_NAME}-{host}-{pid}"
    displaced = root / f"{LATEST_LINK_NAME}-displaced-{host}-{pid}"
    try:
        root.mkdir(parents=True, exist_ok=True)
        if latest.exists() and not latest.is_symlink():
            latest.rename(displaced)
            logger.warning(
                "Moved {} to {} because it was not a symlink, and kept everything it held;"
                " {} now points at {}",
                latest,
                displaced,
                latest,
                run_dir,
            )
        pending.unlink(missing_ok=True)
        pending.symlink_to(run_dir)
        pending.replace(latest)
    except OSError as error:
        log_exception(
            "Could not update latest run link", error, context={"link": latest, "target": run_dir}
        )
        with suppress(OSError):
            pending.unlink(missing_ok=True)
