"""Advisory launch-directory Git inspection, independent of package provenance."""

import os
import shutil
import subprocess
from pathlib import Path

from clearml_yolo.adapters.observability.diagnostics import log


def warn_if_unversioned_launch(directory: Path) -> None:
    """Warn once if Git cannot confirm the supplied directory is in a working tree."""
    executable = shutil.which("git")
    reason = "Git is unavailable"
    if executable is not None:
        try:
            result = subprocess.run(  # noqa: S603 - fixed read-only Git command, no shell
                [executable, "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
                # Hooks and parent processes may select a different repository or index.
                env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
                capture_output=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            reason = f"Git inspection failed ({type(error).__name__})"
        else:
            if result.returncode == 0 and result.stdout.strip() == b"true":
                return
            reason = "Git did not confirm working-tree membership"
    log(
        "WARNING",
        "Git working tree could not be verified for launch directory '{}': {}. "
        "To version experiment configuration, launch from a Git checkout or deliberately "
        "run 'git init' in this directory. Continuing.",
        directory,
        reason,
    )
