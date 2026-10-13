"""Linux host-local short transactions independent of NFS paths and aliases."""

import fcntl
import json
import os
import re
import stat
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from uuid import uuid4


def host_directory(host_id: str, root: Path | None = None) -> Path:
    if sys.platform != "linux" or not re.fullmatch(r"[A-Za-z0-9_-]+", host_id):
        raise RuntimeError("Shared queue requires a supported Linux host identity")
    base = Path("/tmp/clearml-yolo-queue") if root is None else root  # noqa: S108 - explicit host-global namespace
    directory = base / host_id
    for path in (base, directory):
        try:
            path.mkdir(mode=0o1777, parents=True)
        except FileExistsError:
            pass
        else:
            path.chmod(0o1777)
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError("Host-local queue namespace is invalid")
    _validate_namespace(directory, host_id)
    return directory


def _validate_namespace(directory: Path, host_id: str) -> None:
    boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    # A new kernel boot invalidates PID identities, not durable GPU quarantine.
    # Keep previous boot metadata and claims untouched for explicit owner recovery.
    path = directory / f"namespace-{boot}.json"
    namespace = str(Path("/proc/self/ns/pid").readlink())
    if not path.exists():
        temporary = directory / f".namespace-{uuid4().hex}.tmp"
        record = {
            "protocol": 1,
            "owner_uid": os.geteuid(),
            "host_id": host_id,
            "boot_id": boot,
            "pid_namespace": namespace,
        }
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                # Cross-user discovery cannot depend on the first actor's umask.
                os.fchmod(output.fileno(), 0o644)
                output.write(json.dumps(record))
                output.flush()
                os.fsync(output.fileno())
            with suppress(FileExistsError):
                os.link(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    status = path.lstat()
    if not stat.S_ISREG(status.st_mode) or stat.S_IMODE(status.st_mode) & 0o022:
        raise RuntimeError("Local namespace metadata is not a protected regular record")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(record, dict)
        or set(record) != {"protocol", "owner_uid", "host_id", "boot_id", "pid_namespace"}
        or type(record["protocol"]) is not int
        or record["protocol"] != 1
        or record["owner_uid"] != status.st_uid
        or record["host_id"] != host_id
    ):
        raise RuntimeError("Local namespace protocol/ownership is corrupt")
    if record["boot_id"] != boot or record["pid_namespace"] != namespace:
        raise RuntimeError("Shared host boot/PID namespace differs; GPU admission is unsupported")


def shared_descriptor(path: Path) -> int:
    try:
        descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    except FileNotFoundError:
        try:
            descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666)
        except FileExistsError:
            descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode):
        os.close(descriptor)
        raise RuntimeError("Host-local queue coordination requires regular lock files")
    if status.st_uid == os.geteuid():
        os.fchmod(descriptor, 0o666)
    return descriptor


@contextmanager
def host_transaction(
    host_id: str, *, name: str = "nfs-transaction.lock", root: Path | None = None
) -> Iterator[None]:
    descriptor = shared_descriptor(host_directory(host_id, root) / name)
    deadline = time.monotonic() + 10
    acquired = False
    try:
        while not acquired:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Host-local queue transaction timed out") from None
                time.sleep(0.02)
        yield
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
