"""Stable Linux host/boot and non-reusable process identity evidence."""

import hashlib
import os
import sys
from pathlib import Path

from clearml_yolo.adapters.runtime.process_tree import (
    process_ticks as process_ticks,  # noqa: PLC0414 - public compatibility export
)
from clearml_yolo.core.queue import WorkerIdentity


def current_identity() -> WorkerIdentity:
    if sys.platform != "linux":
        raise RuntimeError("Shared cy-queue currently requires Linux")
    machine = Path("/etc/machine-id").read_text(encoding="ascii").strip()
    boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    if not machine or not boot:
        raise RuntimeError("Stable host and boot identities are unavailable")
    return WorkerIdentity(
        owner_uid=os.geteuid(), host_id=hashlib.sha256(machine.encode()).hexdigest(), boot_id=boot
    )


def process_birth(pid: int) -> int | None:
    try:
        parts = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").rsplit(")", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return None if parts[0] == "Z" else int(parts[19])
