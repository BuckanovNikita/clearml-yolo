"""Validate a private queue snapshot, then exec the ordinary pipeline command."""

import argparse
import os
import stat
import sys
from pathlib import Path
from tempfile import mkdtemp

from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
from clearml_yolo.adapters.storage.filesystem import temporary_root
from clearml_yolo.core.queue import JobSnapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--devices", type=int, required=True)
    arguments = parser.parse_args()
    descriptor = os.open(arguments.snapshot, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise PermissionError("Queue snapshots must be regular files owned by the worker UID")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise PermissionError("Queue snapshots must be readable only by their owner")
        snapshot = JobSnapshot.model_validate_json(stream.read())
    if snapshot.owner_uid != os.geteuid():
        raise PermissionError("Workers execute only their own jobs")
    if len(os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",")) != arguments.devices:
        raise ValueError("Queue launch allocation does not match CUDA_VISIBLE_DEVICES")
    from clearml_yolo.entrypoints.hydra.queue_config import (
        validate_snapshot,
        write_execution_config,
    )

    validate_snapshot(snapshot)
    os.chdir(snapshot.cwd)
    os.environ["CY_HOME"] = snapshot.project_root
    os.environ["PYTHONUNBUFFERED"] = "1"
    initialize_runtime_environment()
    directory = Path(mkdtemp(prefix="queue-config-", dir=temporary_root()))
    configuration = write_execution_config(snapshot, arguments.devices, directory)
    os.execv(  # noqa: S606 - fixed pipeline target and validated current interpreter
        sys.executable,
        [
            sys.executable,
            "-u",
            "-m",
            "clearml_yolo.entrypoints.pipeline",
            "--config-dir",
            str(directory),
            "--config-name",
            configuration.stem,
        ],
    )


if __name__ == "__main__":
    main()
