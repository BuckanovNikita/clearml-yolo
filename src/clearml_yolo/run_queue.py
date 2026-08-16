"""A per-machine run queue and GPU leases, built out of nothing but the filesystem.

Two runs started in one folder used to fight over the same cards: the survey said "free",
and minutes passed before the memory was actually held, so a second run selected the very
devices the first was about to take. A lease closes that window — the card is claimed
before it is returned, and the claim is a file.

Only two filesystem primitives are used, and both are chosen because they are the ones
that still decide a race when this directory sits on a shared mount: ``O_CREAT | O_EXCL``
to claim, and a rename within one directory to publish a rewrite. There is deliberately no
``flock`` (unreliable on NFSv3, lease-dependent on v4).

Liveness is a file's ``st_mtime`` and never a timestamp written inside a file, because the
filesystem's clock is the only clock every participant shares — a workstation minutes out
of step with the file server would otherwise declare live leases dead. Holders heartbeat,
and so do *waiting* entries: a waiter killed with SIGKILL that never aged out would sit at
the head of the queue forever and the rotation would keep skipping to a user who is gone.

The tree, one per machine::

    <queue_dir>/leases/gpu-<index>          one file per card; the file IS the lock
    <queue_dir>/entries/<seq>-<run_id>.json one file per waiting run
    <queue_dir>/served/<user>               mtime = when that user last started a run
    <queue_dir>/seq/<n>                     one file per number handed out
"""

from __future__ import annotations

import getpass
import json
import os
import socket
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from itertools import zip_longest
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, ValidationError, model_validator

# An absolute path in the environment wins over the shipped default but not over an
# explicit ``auto_gpu.queue.dir``, so a command line always says what it means.
QUEUE_DIR_ENV_VAR = "CLEARML_YOLO_QUEUE_DIR"
# /tmp because a queue must not survive a reboot: every lease in it names a pid that died
# with the machine. S108 is exactly the property wanted here.
DEFAULT_QUEUE_ROOT = Path("/tmp/clearml-yolo")  # noqa: S108

# The queue is shared by every user of the machine, so every directory in it has to be
# writable by all of them and every file readable by all of them. The process umask strips
# the group and other bits from anything created here, which is why the modes are applied
# again by hand afterwards; without that the second user on the box gets EACCES.
SHARED_DIR_MODE = 0o777
SHARED_FILE_MODE = 0o644

# What a lease says when its file has been claimed but not yet written — the O_EXCL create
# and the payload are two steps, and a peer is allowed to look in between.
UNKNOWN_HOLDER = "?"
NO_PID = 0

# Read once, at import, because ``clearml_session.init_task`` sets this same variable after
# ``Task.init`` so that DDP children attach to the right experiment. Reading it lazily
# would therefore make every single run look agent-managed and switch the queue off. The
# snapshot is also precisely how ``clearml.config.running_remotely()`` decides the same
# question, which is the definition being matched here.
AGENT_TASK_ID_ENV_VAR = "CLEARML_TASK_ID"
_TASK_ID_AT_IMPORT = os.environ.get(AGENT_TASK_ID_ENV_VAR)

# A user nobody has ever served sorts ahead of one who ran a moment ago.
NEVER_SERVED = float("-inf")


def running_under_agent() -> bool:
    """Whether this process was launched by a ClearML agent rather than by a person.

    An agent already schedules; queueing underneath it would make a run wait twice.
    """
    return bool(_TASK_ID_AT_IMPORT)


def current_user() -> str:
    """The identity the queue rotates between: the OS username."""
    try:
        return getpass.getuser()
    except (KeyError, OSError):
        return f"uid-{os.getuid()}"


class QueueConfig(BaseModel):
    """How long a heartbeat lasts, how often it is written, and where all of it lives."""

    enabled: bool = True
    # Unset means the environment, and failing that ``/tmp/clearml-yolo/<hostname>``.
    dir: Path | None = None
    poll_seconds: float = Field(default=5.0, gt=0)
    heartbeat_seconds: float = Field(default=10.0, gt=0)
    # Wide on purpose: NFS attribute caching can hold a stale mtime for tens of seconds,
    # so a timeout close to the heartbeat would declare live runs dead over the network.
    stale_after_seconds: float = Field(default=120.0, gt=0)

    @model_validator(mode="after")
    def _a_heartbeat_must_outrun_the_timeout(self) -> QueueConfig:
        """Refuse a timeout no heartbeat can keep up with, rather than expire every run.

        With ``stale_after_seconds`` at or below the heartbeat or the poll interval, every
        holder and every waiter ages out between one beat and the next: leases are stolen
        from running trainings and the queue order dissolves. It is unrecoverable at
        runtime and obvious here.
        """
        slowest = max(self.heartbeat_seconds, self.poll_seconds)
        if slowest >= self.stale_after_seconds:
            raise ValueError(
                f"auto_gpu.queue.stale_after_seconds={self.stale_after_seconds} is not "
                f"above heartbeat_seconds={self.heartbeat_seconds} and "
                f"poll_seconds={self.poll_seconds}, so every run would expire between two "
                "of its own heartbeats. Raise stale_after_seconds well above both."
            )
        return self


def queue_dir(config: QueueConfig) -> Path:
    """Where this machine's queue lives: the config, then the environment, then /tmp."""
    if config.dir is not None:
        return Path(config.dir)
    from_environment = os.environ.get(QUEUE_DIR_ENV_VAR)
    if from_environment:
        return Path(from_environment)
    return DEFAULT_QUEUE_ROOT / socket.gethostname()


def queue_active(config: QueueConfig) -> bool:
    """Whether this run should queue at all — an explicit ``enabled=false`` always wins."""
    return config.enabled and not running_under_agent()


class Entry(BaseModel):
    """One run waiting for cards, as it sits in ``entries/``.

    ``priority`` is the pin: ``None`` leaves the entry in the fair rotation, and any
    number takes it out of the rotation and ahead of every unpinned entry, **smaller
    first** — pinning to the top writes one less than the smallest pin currently held.
    """

    seq: int
    run_id: str
    user: str
    host: str
    pid: int
    num_gpus: int = 1
    priority: int | None = None
    # Display only — how long the TUI says a run has been waiting. Liveness is the file's
    # mtime and nothing else; this number is never compared against anybody's clock.
    enqueued_at: float = 0.0


class Lease(BaseModel):
    """One card held by one run, as it sits in ``leases/gpu-<index>``.

    ``pid`` is what makes a peer's VRAM and its ``/dev/dxg`` handles attributable, so a
    reader may subtract the holder's whole process group. ``NO_PID`` means the file was
    claimed but not yet written and there is no process to name.
    """

    gpu_index: int
    run_id: str
    user: str
    host: str
    pid: int


def order(entries: Sequence[Entry], served: Mapping[str, float]) -> list[Entry]:
    """Rank waiting runs: pins first, then a fair rotation between users, then arrival.

    Pure, and taking ``served`` as a plain mapping of user to mtime, because this is the
    whole fairness policy and it must be checkable without a filesystem behind it.

    The rotation is what makes several users on one machine take turns: users are ordered
    by the last time each of them *started* a run, oldest first and never-served first,
    then everybody's earliest entry goes out before anybody's second. A user who submits
    ten jobs therefore does not push a colleague's single job to the back. Only the head
    of this list may claim cards, so a large request is never starved by a stream of small
    ones; head-of-line blocking is the price, and cancelling is the escape hatch.
    """
    pinned = sorted(
        (entry for entry in entries if entry.priority is not None),
        key=lambda entry: (entry.priority or 0, entry.seq),
    )
    by_user: dict[str, list[Entry]] = {}
    for entry in entries:
        if entry.priority is None:
            by_user.setdefault(entry.user, []).append(entry)
    for queued in by_user.values():
        queued.sort(key=lambda entry: entry.seq)
    users = sorted(
        by_user,
        key=lambda user: (served.get(user, NEVER_SERVED), by_user[user][0].seq),
    )
    rotation = [
        entry
        for round_ in zip_longest(*(by_user[user] for user in users))
        for entry in round_
        if entry is not None
    ]
    return pinned + rotation


def _open_up(path: Path, mode: int) -> None:
    """Hand back the access the umask just took away, so the next user is not locked out."""
    try:
        path.chmod(mode)
    except (PermissionError, FileNotFoundError) as error:
        logger.debug("Leaving the mode of {} as it is ({})", path, error)


def _create_exclusive(path: Path, text: str) -> bool:
    """Create the file and write ``text``, or lose the race and say so.

    This is the claim primitive: the kernel decides, exactly once, which of two processes
    creating the same path at the same moment gets the file.
    """
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, SHARED_FILE_MODE)
    except FileExistsError:
        return False
    os.fchmod(descriptor, SHARED_FILE_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
    return True


def _read_payload(path: Path) -> dict[str, Any] | None:
    """The JSON in a lease or entry file, or None when there is nothing usable to read."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        logger.debug("Ignoring the unreadable queue file {} ({})", path, error)
        return None
    return loaded if isinstance(loaded, dict) else None


def _touch(path: Path) -> bool:
    """Heartbeat the file, reporting False when it is gone — cancelled, or reclaimed."""
    try:
        os.utime(path, None)
    except FileNotFoundError:
        return False
    return True


class RunQueue:
    """The queue as one run sees it: its own leases, its own entry, everyone's order.

    The waiting run is the whole scheduler — there is no daemon — so every method here is
    called from an ordinary ``cy`` process and every one of them tolerates a peer dying
    mid-write. Constructing this creates the directory tree.
    """

    def __init__(
        self,
        config: QueueConfig,
        *,
        run_id: str,
        user: str | None = None,
        host: str | None = None,
        pid: int | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.config = config
        self.run_id = run_id
        self.user = user or current_user()
        self.host = host or socket.gethostname()
        self.pid = os.getpid() if pid is None else pid
        self.dir = queue_dir(config)
        self.leases_dir = self.dir / "leases"
        self.entries_dir = self.dir / "entries"
        self.served_dir = self.dir / "served"
        self.sequence_dir = self.dir / "seq"
        self._now = now or self._filesystem_now
        self._prepare()

    def _prepare(self) -> None:
        """Build the tree so that every user of the machine can write in it."""
        directories = [
            self.dir,
            self.leases_dir,
            self.entries_dir,
            self.served_dir,
            self.sequence_dir,
        ]
        # The shipped root holds one directory per machine and is created by whoever runs
        # first; left at the umask's mode, the second user could not create theirs in it.
        if self.dir.parent == DEFAULT_QUEUE_ROOT:
            directories.insert(0, DEFAULT_QUEUE_ROOT)
        for path in directories:
            path.mkdir(parents=True, exist_ok=True)
            _open_up(path, SHARED_DIR_MODE)

    def _filesystem_now(self) -> float:
        """Read the current time from the filesystem's clock, by making it stamp a file.

        Every staleness decision compares two numbers that came from here, so a reader
        whose own clock disagrees with the file server still reaches the same verdict
        about a lease as the run holding it.
        """
        with NamedTemporaryFile(dir=self.dir, prefix="now-", delete=False) as handle:
            probe = Path(handle.name)
        stamp = probe.stat().st_mtime
        probe.unlink(missing_ok=True)
        return stamp

    def _live(self, path: Path, moment: float) -> bool:
        try:
            heartbeat = path.stat().st_mtime
        except FileNotFoundError:
            return False
        return moment - heartbeat < self.config.stale_after_seconds

    def _lease_path(self, gpu_index: int) -> Path:
        return self.leases_dir / f"gpu-{gpu_index}"

    def entry_path(self, entry: Entry) -> Path:
        return self.entries_dir / f"{entry.seq}-{entry.run_id}.json"

    def live_leases(self) -> list[Lease]:
        """Every card currently held, with the ones nobody heartbeats any more left out.

        A held card that cannot be parsed is still reported as held, under
        ``UNKNOWN_HOLDER``: between the O_EXCL create and the write of its payload a lease
        is a real claim with nothing in it yet, and treating that as free would hand the
        card to two runs.
        """
        moment = self._now()
        leases = []
        for path in sorted(self.leases_dir.iterdir()):
            index = _gpu_index_of(path.name)
            if index is None or not self._live(path, moment):
                continue
            leases.append(_lease_of(index, _read_payload(path)))
        return sorted(leases, key=lambda lease: lease.gpu_index)

    def claim_lease(self, gpu_index: int) -> Lease | None:
        """Take the card, or return None because a live peer holds it.

        The lease file, not the NVML survey, is the arbiter: whoever creates it wins, and
        the loser re-polls rather than assuming the survey it did seconds ago still holds.
        """
        path = self._lease_path(gpu_index)
        lease = Lease(
            gpu_index=gpu_index,
            run_id=self.run_id,
            user=self.user,
            host=self.host,
            pid=self.pid,
        )
        payload = lease.model_dump_json()
        if _create_exclusive(path, payload):
            return lease
        if not self._reclaim_if_stale(path):
            return None
        return lease if _create_exclusive(path, payload) else None

    def claim_leases(self, gpu_indices: Sequence[int]) -> list[Lease]:
        """Take every one of these cards or none of them.

        A run that got two cards out of three and then lost the third would hold the two
        for as long as it kept waiting, which is how two runs deadlock each other. The
        empty list says the caller should release nothing, survey again and retry.
        """
        taken: list[Lease] = []
        for index in gpu_indices:
            lease = self.claim_lease(index)
            if lease is None:
                self.release_leases([held.gpu_index for held in taken])
                return []
            taken.append(lease)
        return taken

    def _reclaim_if_stale(self, path: Path) -> bool:
        """Remove a lease nobody has heartbeated for ``stale_after_seconds``.

        Unlink first and create second, never the reverse: two runs may both unlink, but
        only one of them can then create the file. The window in which this could remove a
        lease that revived between the check and the unlink is bounded by the gap between
        the heartbeat and the timeout, which is why the two are set an order of magnitude
        apart — and a holder whose lease is taken anyway finds out at its next beat.
        """
        if self._live(path, self._now()):
            return False
        logger.warning(
            "Reclaiming {}: nothing has heartbeated it for {}s (it was held by {})",
            path.name,
            self.config.stale_after_seconds,
            _read_payload(path),
        )
        path.unlink(missing_ok=True)
        return True

    def release_lease(self, gpu_index: int) -> None:
        """Give the card back, unless the file stopped being this run's lease.

        A payload that cannot be read is somebody else's too: this run's own lease always
        carries one by the time it can be released, so an unreadable file is a peer that
        reclaimed the expired lease and has not written its own payload yet.
        """
        path = self._lease_path(gpu_index)
        payload = _read_payload(path)
        if payload is None or payload.get("run_id") != self.run_id:
            logger.warning(
                "Not releasing GPU {}: this run no longer holds it (the lease says {})",
                gpu_index,
                payload.get("run_id", UNKNOWN_HOLDER) if payload else UNKNOWN_HOLDER,
            )
            return
        path.unlink(missing_ok=True)

    def release_leases(self, gpu_indices: Sequence[int]) -> None:
        for index in gpu_indices:
            self.release_lease(index)

    @contextmanager
    def holding(self, gpu_indices: Sequence[int]) -> Iterator[None]:
        """Heartbeat these leases on a daemon thread, and release them however the run ends.

        The release in the ``finally`` is the fast path; the heartbeat running out is what
        recovers the cards when the process never reaches it, which is every SIGKILL and
        every machine that goes down mid-training. A daemon thread so that the beating can
        never be the reason an exiting process stays alive.
        """
        stop = threading.Event()
        beating = threading.Thread(
            target=self._beat_until,
            args=(list(gpu_indices), stop),
            name="clearml-yolo-leases",
            daemon=True,
        )
        beating.start()
        try:
            yield
        finally:
            stop.set()
            beating.join(timeout=self.config.heartbeat_seconds)
            self.release_leases(gpu_indices)

    def _beat_until(self, gpu_indices: list[int], stop: threading.Event) -> None:
        while not stop.wait(self.config.heartbeat_seconds):
            for index in gpu_indices:
                if not _touch(self._lease_path(index)):
                    logger.warning(
                        "The lease on GPU {} is gone while this run is still using it; "
                        "another run has reclaimed the card",
                        index,
                    )

    def next_sequence(self) -> int:
        """Hand out a number no other run can also be holding.

        One file per number, claimed with O_EXCL and never deleted: the files are the
        counter's memory, and a counter kept in a single file would need a lock to
        increment. They cost a directory entry each and go away with the reboot that
        wipes the queue.
        """
        taken = [int(path.name) for path in self.sequence_dir.iterdir() if path.name.isdigit()]
        candidate = max(taken, default=0) + 1
        while not _create_exclusive(self.sequence_dir / str(candidate), self.run_id):
            candidate += 1
        return candidate

    def enqueue(self, num_gpus: int, *, priority: int | None = None) -> Entry:
        """Take a place in the queue for ``num_gpus`` cards."""
        entry = Entry(
            seq=self.next_sequence(),
            run_id=self.run_id,
            user=self.user,
            host=self.host,
            pid=self.pid,
            num_gpus=num_gpus,
            priority=priority,
            enqueued_at=time.time(),
        )
        self.write_entry(entry)
        return entry

    def write_entry(self, entry: Entry) -> None:
        """Publish the entry in one step, so a reader sees the old file or the new one.

        Also how ``cy-queue`` rewrites a pin: one entry file changes and nothing else is
        touched, which is why the pin lives inside each entry rather than in one shared
        order file that every reorder would have to lock.
        """
        with NamedTemporaryFile(
            "w", dir=self.entries_dir, prefix=".entry-", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(entry.model_dump_json(indent=2))
            written = Path(handle.name)
        # The temp file is created 0o600, and an entry no other user can read is an entry
        # their queue silently drops — which is exactly the queue-jumping this prevents.
        _open_up(written, SHARED_FILE_MODE)
        written.replace(self.entry_path(entry))

    def heartbeat_entry(self, entry: Entry) -> bool:
        """Say this waiter is still alive; False means it was cancelled and must stop.

        Waiters heartbeat for the same reason holders do: one that died without deleting
        its file would keep the head of the queue and stall everybody behind it.
        """
        return _touch(self.entry_path(entry))

    def remove_entry(self, entry: Entry) -> None:
        """Take the entry out of the queue — either it got its cards, or it was cancelled."""
        self.entry_path(entry).unlink(missing_ok=True)

    def live_entries(self) -> list[Entry]:
        """Every run still waiting, unranked, with the ones that stopped beating dropped.

        Dropped rather than deleted: a run stalled on a slow filesystem may yet come back
        and heartbeat its file, and deletion is the one thing it could not recover from.
        """
        moment = self._now()
        entries = []
        for path in sorted(self.entries_dir.iterdir()):
            if path.name.startswith(".") or not self._live(path, moment):
                continue
            payload = _read_payload(path)
            if payload is None:
                continue
            try:
                entries.append(Entry.model_validate(payload))
            except ValidationError as error:
                logger.debug("Ignoring the malformed queue entry {} ({})", path, error)
        return entries

    def served_mtimes(self) -> dict[str, float]:
        """When each user of this machine last started a run, for the rotation to read."""
        mtimes = {}
        for path in self.served_dir.iterdir():
            try:
                mtimes[path.name] = path.stat().st_mtime
            except FileNotFoundError:
                continue
        return mtimes

    def mark_served(self) -> None:
        """Record that this user has just started a run, which sends them to the back."""
        path = self.served_dir / self.user
        path.touch(exist_ok=True)
        _open_up(path, SHARED_FILE_MODE)

    def dispatch_order(self) -> list[Entry]:
        """The queue as it stands: who runs next, and who is behind them."""
        return order(self.live_entries(), self.served_mtimes())


def _gpu_index_of(name: str) -> int | None:
    """The card a lease file names, or None for anything else living in ``leases/``."""
    index = name.removeprefix("gpu-")
    return int(index) if name.startswith("gpu-") and index.isdigit() else None


def _lease_of(gpu_index: int, payload: Mapping[str, Any] | None) -> Lease:
    """A lease from what its file held, falling back to a claim whose holder is unnamed."""
    if payload is not None:
        try:
            return Lease.model_validate({**payload, "gpu_index": gpu_index})
        except ValidationError as error:
            logger.debug("Lease gpu-{} holds no usable payload ({})", gpu_index, error)
    return Lease(
        gpu_index=gpu_index,
        run_id=UNKNOWN_HOLDER,
        user=UNKNOWN_HOLDER,
        host=UNKNOWN_HOLDER,
        pid=NO_PID,
    )
