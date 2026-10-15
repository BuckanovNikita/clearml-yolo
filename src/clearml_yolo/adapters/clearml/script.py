"""Publish source identity without capturing checkout contents or command arguments."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from loguru import logger

from clearml_yolo.core.redaction import sanitize_url


def _git(root: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        logger.warning("Git is unavailable; ClearML source identity may be incomplete")
        return ""
    try:
        result = subprocess.run(  # noqa: S603 - fixed read-only Git commands, no shell
            [executable, "-C", str(root), *arguments],
            # Git hooks can export another repository/index despite explicit -C.
            env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        logger.warning("Git source identity read failed ({})", type(error).__name__)
        return ""
    if result.returncode:
        logger.warning("Git source identity is unavailable for {}", arguments[0])
        return ""
    return result.stdout.strip()


def _source_identity() -> dict[str, str]:
    package = Path(__file__).resolve().parents[2]
    root = package.parent.parent
    # An installed wheel inside another checkout's .venv is not that checkout's code.
    if package.parent.name != "src" or not (root / ".git").exists():
        logger.warning("No source checkout; ClearML Git identity is unavailable")
        return {}
    repository = _git(root, "config", "--get", "remote.origin.url")
    if repository:
        parts = urlsplit(repository)
        # Strip credentials before generic sanitization, preserving bracketed hosts.
        authority = parts.netloc.rsplit("@", 1)[-1]
        safe = urlsplit(sanitize_url(urlunsplit(parts._replace(netloc=authority))))
        if parts.scheme in {"ssh", "git+ssh"} and parts.username is not None:
            # SSH login names select the transport user; passwords never belong here.
            safe = safe._replace(netloc=f"{parts.username}@{safe.netloc}")
        repository = urlunsplit(safe)
    return {
        "repository": repository,
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git(root, "rev-parse", "--verify", "HEAD"),
    }


def publish_script(task: Any, stage: str) -> None:
    """Fill the owner's execution fields and verify SDK publication by fresh readback.

    The SDK task remains opaque at this outer adapter boundary. Remote agents retain
    their supplied script; local queue workers publish the same module as direct runs.
    """
    if not task.running_locally():
        return
    fields = {
        **_source_identity(),
        "entry_point": f"-m clearml_yolo.entrypoints.{stage}",
        "working_dir": ".",
        "diff": "",
    }
    if task.data.script is None:
        from clearml.backend_api.services import tasks

        # SDK offline tasks omit this object; set_script assumes it already exists.
        task._update_script(tasks.Script())  # noqa: SLF001 - SDK offline initialization gap
    task.set_script(**fields)
    # Public reload suppresses read errors and can leave the setter's mutated cache.
    recorded = task._reload_field("script").to_dict()  # noqa: SLF001 - require fresh SDK read
    for key, expected in fields.items():
        saved_key = "version_num" if key == "commit" else key
        if recorded.get(saved_key, "") != expected:
            raise RuntimeError(f"ClearML did not retain script metadata field {saved_key!r}")
