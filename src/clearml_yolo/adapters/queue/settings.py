"""Read one shared queue configuration without creating storage or runtime state."""

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

_MOUNTPOINT_FIELD = 4

# These Linux filesystems provide local inode/flock coordination. Remote and
# userspace filesystems need verified locking semantics before they can be used.
_LOCAL_FILESYSTEMS = frozenset(
    {
        "btrfs",
        "ext2",
        "ext3",
        "ext4",
        "f2fs",
        "jfs",
        "nilfs2",
        "ntfs3",
        "overlay",
        "ramfs",
        "reiserfs",
        "rootfs",
        "tmpfs",
        "ubifs",
        "xfs",
        "zfs",
    }
)


@dataclass(frozen=True)
class QueueSettings:
    name: str
    root: Path
    coordination_root: Path
    config_path: Path
    root_source: Literal["config", "--root"]


class _QueueConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str
    root: str
    coordination_root: str

    @field_validator("name")
    @classmethod
    def readable_name(cls, value: str) -> str:
        value = value.strip()
        if not value or not value.isprintable():
            raise ValueError("Queue name must be nonempty printable text")
        return value


class _ConfigurationFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    queue: _QueueConfiguration


def _absolute_path(value: str | Path, source: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{source} must be an absolute path")
    return path.resolve()


def _require_local_filesystem(path: Path) -> None:
    mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    selected: tuple[int, str] | None = None
    for line in mountinfo.splitlines():
        before, separator, after = line.partition(" - ")
        fields, filesystem = before.split(), after.split()
        if not separator or len(fields) <= _MOUNTPOINT_FIELD or not filesystem:
            raise RuntimeError("Cannot determine the queue coordination filesystem")
        mount = Path(
            re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[_MOUNTPOINT_FIELD])
        )
        if path.is_relative_to(mount) and (selected is None or len(mount.parts) >= selected[0]):
            selected = (len(mount.parts), filesystem[0])
    if selected is None or selected[1] not in _LOCAL_FILESYSTEMS:
        raise ValueError(
            "Queue coordination_root requires a supported host-local Linux filesystem; "
            "keep network storage in queue.root"
        )


def load_queue_settings(
    root_override: Path | None = None, *, environ: Mapping[str, str] | None = None
) -> QueueSettings:
    """Resolve explicit settings once; callers inject them into every queue effect."""
    environment = os.environ if environ is None else environ
    configured = environment.get("CY_QUEUE_CONFIG")
    if not configured:
        raise ValueError("Set CY_QUEUE_CONFIG to an absolute shared TOML configuration path")
    config_path = _absolute_path(configured, "CY_QUEUE_CONFIG")
    try:
        with config_path.open("rb") as source:
            config = _ConfigurationFile.model_validate(tomllib.load(source)).queue
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise ValueError(
            "Invalid queue configuration: expected [queue] with name, root and coordination_root"
        ) from error
    configured_root = _absolute_path(config.root, "queue.root")
    coordination_root = _absolute_path(config.coordination_root, "queue.coordination_root")
    root = configured_root if root_override is None else _absolute_path(root_override, "--root")
    legacy = environment.get("CY_QUEUE_ROOT")
    if legacy and _absolute_path(legacy, "CY_QUEUE_ROOT") != root:
        raise ValueError(
            "CY_QUEUE_ROOT conflicts with the selected queue root; remove the legacy variable "
            "and configure CY_QUEUE_CONFIG or --root"
        )
    for directory in (root, coordination_root):
        if directory.exists() and not directory.is_dir():
            raise ValueError("Queue configuration paths must name directories")
    _require_local_filesystem(coordination_root)
    return QueueSettings(
        name=config.name,
        root=root,
        coordination_root=coordination_root,
        config_path=config_path,
        root_source="config" if root_override is None else "--root",
    )
