"""Read required queue settings without creating storage or runtime state."""

import os
import pwd
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

_MOUNTPOINT_FIELD = 4
_SUPERBLOCK_FIELD = 2

# These Linux filesystems provide local inode/flock coordination. NFS additionally
# needs effective mount options preserving the same host-local lock lifetime.
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


def _require_coordination_filesystem(path: Path) -> None:
    mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    selected: tuple[int, str, frozenset[str]] | None = None
    for line in mountinfo.splitlines():
        before, separator, after = line.partition(" - ")
        fields, filesystem = before.split(), after.split()
        if (
            not separator
            or len(fields) <= _MOUNTPOINT_FIELD
            or len(filesystem) <= _SUPERBLOCK_FIELD
        ):
            raise RuntimeError("Cannot determine the queue coordination filesystem")
        mount = Path(
            re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[_MOUNTPOINT_FIELD])
        )
        if path.is_relative_to(mount) and (selected is None or len(mount.parts) >= selected[0]):
            selected = (
                len(mount.parts),
                filesystem[0],
                frozenset(filesystem[_SUPERBLOCK_FIELD].split(",")),
            )
    if selected is not None and selected[1] in {"nfs", "nfs4"}:
        _require_nfs_options(selected[2])
        return
    if selected is None or selected[1] not in _LOCAL_FILESYSTEMS:
        raise ValueError(
            "Queue coordination_root requires a supported host-local Linux filesystem "
            "or NFS with hard,local_lock=flock and shared cache"
        )


def _require_nfs_options(options: frozenset[str]) -> None:
    # Remote NFS locks can be lost while a guardian keeps its descriptor open.
    # Effective superblock options, unlike requested mount options, reflect the
    # shared NFS client's actual locking mode. All participants must share it.
    locking = {option for option in options if option.startswith("local_lock=")}
    if (
        "hard" not in options
        or options & {"soft", "softerr", "nosharecache"}
        or locking not in ({"local_lock=flock"}, {"local_lock=all"})
    ):
        raise ValueError(
            "NFS coordination requires effective hard and local_lock=flock or local_lock=all "
            "with shared cache (no soft, softerr or nosharecache); check the mount options "
            "with your administrator"
        )


def _configuration_path(environment: Mapping[str, str]) -> Path:
    if configured := environment.get("CY_QUEUE_CONFIG"):
        return _absolute_path(configured, "CY_QUEUE_CONFIG")
    config_home = environment.get("XDG_CONFIG_HOME")
    if config_home and Path(config_home).is_absolute():
        return (Path(config_home) / "clearml-yolo" / "queue.toml").resolve()
    home = environment.get("HOME")
    user_home = _absolute_path(home or pwd.getpwuid(os.getuid()).pw_dir, "HOME")
    return (user_home / ".config" / "clearml-yolo" / "queue.toml").resolve()


def load_queue_settings(
    root_override: Path | None = None, *, environ: Mapping[str, str] | None = None
) -> QueueSettings:
    """Resolve explicit settings once; callers inject them into every queue effect."""
    environment = os.environ if environ is None else environ
    config_path = _configuration_path(environment)
    try:
        with config_path.open("rb") as source:
            config = _ConfigurationFile.model_validate(tomllib.load(source)).queue
    except FileNotFoundError as error:
        raise ValueError(
            f"Queue configuration is missing: {config_path}. Create and fill [queue] with "
            "name, root and coordination_root before using the queue; "
            "set CY_QUEUE_CONFIG to use a different configuration file"
        ) from error
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
    _require_coordination_filesystem(coordination_root)
    return QueueSettings(
        name=config.name,
        root=root,
        coordination_root=coordination_root,
        config_path=config_path,
        root_source="config" if root_override is None else "--root",
    )
