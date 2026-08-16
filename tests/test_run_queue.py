"""The file-based run queue: leases, waiting entries, the fair order and the agent bypass."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from clearml_yolo import run_queue as run_queue_module
from clearml_yolo.run_queue import (
    AGENT_TASK_ID_ENV_VAR,
    DEFAULT_QUEUE_ROOT,
    QUEUE_DIR_ENV_VAR,
    UNKNOWN_HOLDER,
    Entry,
    QueueConfig,
    RunQueue,
    order,
    queue_active,
    queue_dir,
    running_under_agent,
)

STALE_AFTER = 120.0


def make_queue(
    tmp_path: Path, *, run_id: str = "run-a", user: str = "ann", **settings: object
) -> RunQueue:
    """A queue rooted in the test's own directory, with the machine identity pinned."""
    config = QueueConfig(dir=tmp_path / "queue", **settings)  # type: ignore[arg-type]
    return RunQueue(config, run_id=run_id, user=user, host="box", pid=4242)


def waiting(seq: int, user: str, priority: int | None = None) -> Entry:
    return Entry(seq=seq, run_id=f"{user}-{seq}", user=user, host="box", pid=seq, priority=priority)


def backdate(path: Path, seconds: float) -> None:
    """Push a heartbeat into the past, which is the only way a test can let a run die."""
    stamp = path.stat().st_mtime - seconds
    os.utime(path, (stamp, stamp))


def test_the_entries_of_three_users_are_served_in_rotation_and_not_in_arrival_order() -> None:
    """The whole point of the rotation: one user submitting a batch of runs must not push
    a colleague's single run behind all of them."""
    entries = [
        waiting(1, "ann"),
        waiting(2, "ann"),
        waiting(3, "ann"),
        waiting(4, "bob"),
        waiting(5, "cid"),
    ]

    ranked = order(entries, served={})

    assert [entry.seq for entry in ranked] == [1, 4, 5, 2, 3]


def test_a_user_who_has_never_run_goes_ahead_of_everyone_already_served() -> None:
    """Arriving on a machine somebody else has been using all day must not mean waiting
    behind them; the rotation is by last start, and never-started sorts oldest."""
    entries = [waiting(1, "ann"), waiting(2, "bob"), waiting(3, "cid")]

    ranked = order(entries, served={"ann": 100.0, "bob": 50.0})

    assert [entry.user for entry in ranked] == ["cid", "bob", "ann"]


def test_a_pinned_entry_runs_before_the_rotation_however_late_it_arrived() -> None:
    """Pinning from cy-queue is the manual override, so it has to beat the fair order
    rather than merely improve a place in it."""
    entries = [waiting(1, "ann"), waiting(2, "bob"), waiting(3, "cid", priority=0)]

    ranked = order(entries, served={})

    assert [entry.seq for entry in ranked] == [3, 1, 2]


def test_pinned_entries_run_by_priority_and_arrival_breaks_a_tie_between_them() -> None:
    """Pins are an order among themselves, smaller first, so pinning to the top means
    writing one less than the smallest pin already held."""
    entries = [
        waiting(1, "ann", priority=5),
        waiting(9, "bob", priority=-1),
        waiting(0, "cid", priority=5),
    ]

    ranked = order(entries, served={})

    assert [entry.seq for entry in ranked] == [9, 0, 1]


def test_the_sequence_breaks_a_tie_between_users_served_at_the_same_moment() -> None:
    """Two users whose last runs finished within one mtime tick must still get a stable
    order, or the queue would reshuffle itself between two polls."""
    entries = [waiting(2, "ann"), waiting(1, "bob")]

    ranked = order(entries, served={"ann": 10.0, "bob": 10.0})

    assert [entry.user for entry in ranked] == ["bob", "ann"]


def test_a_stale_entry_is_dropped_from_the_order(tmp_path: Path) -> None:
    """A waiter killed with SIGKILL leaves its file behind; if that file kept its place,
    the head of the queue would be a run that no longer exists and nobody would start."""
    queue = make_queue(tmp_path)
    dead = queue.enqueue(num_gpus=1)
    alive = queue.enqueue(num_gpus=1)
    backdate(queue.entry_path(dead), STALE_AFTER + 1)

    assert [entry.seq for entry in queue.dispatch_order()] == [alive.seq]


def test_an_entry_that_keeps_beating_keeps_its_place(tmp_path: Path) -> None:
    """Waiting entries heartbeat for the same reason holders do, so a long wait must not
    look like a death."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(num_gpus=1)
    backdate(queue.entry_path(entry), STALE_AFTER + 1)

    assert queue.heartbeat_entry(entry) is True
    assert [ranked.seq for ranked in queue.dispatch_order()] == [entry.seq]


def test_a_cancelled_entry_tells_its_run_to_stop(tmp_path: Path) -> None:
    """Cancelling from cy-queue deletes the file, and the missing file is the only signal
    the waiting cy process gets."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(num_gpus=1)

    queue.remove_entry(entry)

    assert queue.heartbeat_entry(entry) is False
    assert queue.live_entries() == []


def test_a_stale_lease_is_reclaimed_while_a_fresh_one_is_not(tmp_path: Path) -> None:
    """Recovering a card from a run that died without releasing it is what keeps the
    machine usable; doing it to a run that is merely slow would evict a live training."""
    holder = make_queue(tmp_path, run_id="run-holder")
    waiter = make_queue(tmp_path, run_id="run-waiter", user="bob")
    assert holder.claim_lease(0) is not None

    assert waiter.claim_lease(0) is None

    backdate(waiter._lease_path(0), STALE_AFTER + 1)
    reclaimed = waiter.claim_lease(0)

    assert reclaimed is not None
    assert [lease.run_id for lease in waiter.live_leases()] == ["run-waiter"]


def test_only_one_of_two_runs_claiming_the_same_card_wins(tmp_path: Path) -> None:
    """The lease file, not the NVML survey, decides who gets the card — this is the
    check-then-act window that made two runs OOM on the same device."""
    first = make_queue(tmp_path, run_id="run-first")
    second = make_queue(tmp_path, run_id="run-second", user="bob")

    claims = [first.claim_lease(0), second.claim_lease(0)]

    assert [claim is not None for claim in claims].count(True) == 1


def test_the_loser_of_a_claim_race_releases_nothing_of_the_winner(tmp_path: Path) -> None:
    """A loser that unlinked the file it failed to create would hand the card to a third
    run while the winner is already training on it."""
    winner = make_queue(tmp_path, run_id="run-winner")
    loser = make_queue(tmp_path, run_id="run-loser", user="bob")
    winner.claim_lease(0)

    assert loser.claim_lease(0) is None
    loser.release_lease(0)

    assert [lease.run_id for lease in winner.live_leases()] == ["run-winner"]


def test_a_run_that_cannot_get_all_its_cards_keeps_none_of_them(tmp_path: Path) -> None:
    """Holding a partial set while waiting for the rest is how two runs deadlock each
    other, each sitting on what the other needs."""
    peer = make_queue(tmp_path, run_id="run-peer", user="bob")
    peer.claim_lease(1)
    asking = make_queue(tmp_path, run_id="run-asking")

    assert asking.claim_leases([0, 1]) == []
    assert [(lease.gpu_index, lease.run_id) for lease in asking.live_leases()] == [(1, "run-peer")]


def test_a_lease_claimed_but_not_yet_written_still_counts_as_held(tmp_path: Path) -> None:
    """Creating the file and writing its payload are two steps, and a peer looking in
    between must read the card as taken rather than as free."""
    queue = make_queue(tmp_path)
    (queue.leases_dir / "gpu-0").write_text("", encoding="utf-8")

    assert [lease.run_id for lease in queue.live_leases()] == [UNKNOWN_HOLDER]
    assert queue.claim_lease(0) is None


def test_a_run_does_not_release_a_lease_a_peer_has_only_just_claimed(tmp_path: Path) -> None:
    """A run whose expired lease was reclaimed while it was suspended reaches its own
    release last: reading the peer's not-yet-written payload as nobody's would delete a
    claim the peer is already training on."""
    queue = make_queue(tmp_path)
    reclaimed = queue.leases_dir / "gpu-0"
    reclaimed.write_text("", encoding="utf-8")

    queue.release_lease(0)

    assert reclaimed.exists()


def test_a_lease_nobody_can_parse_is_reclaimed_once_it_stops_beating(tmp_path: Path) -> None:
    """An unreadable lease must not become a card no run can ever have again."""
    queue = make_queue(tmp_path)
    abandoned = queue.leases_dir / "gpu-0"
    abandoned.write_text("{not json", encoding="utf-8")
    backdate(abandoned, STALE_AFTER + 1)

    assert queue.claim_lease(0) is not None


def test_the_leases_a_run_holds_are_released_however_the_run_ends(tmp_path: Path) -> None:
    """The release in the finally is the fast path back to a free card; the heartbeat
    timeout is only the recovery for a run that never reaches it."""
    queue = make_queue(tmp_path, heartbeat_seconds=0.01)
    queue.claim_leases([0, 1])

    with pytest.raises(RuntimeError), queue.holding([0, 1]):
        raise RuntimeError("training failed")

    assert queue.live_leases() == []


def test_a_held_lease_is_heartbeated_while_the_run_uses_it(tmp_path: Path) -> None:
    """Without the beat a long training would age past stale_after_seconds and have its
    card reclaimed out from under it."""
    queue = make_queue(tmp_path, heartbeat_seconds=0.01)
    queue.claim_lease(0)
    lease = queue._lease_path(0)
    backdate(lease, STALE_AFTER + 1)
    aged = lease.stat().st_mtime

    with queue.holding([0]):
        deadline = time.monotonic() + 5.0
        while lease.stat().st_mtime == aged and time.monotonic() < deadline:
            time.sleep(0.01)
        beaten = lease.stat().st_mtime

    assert beaten > aged


def test_the_sequence_never_hands_out_the_same_number_twice(tmp_path: Path) -> None:
    """Two runs enqueueing at the same moment must not share a place in the order, and a
    shared counter file could only be incremented under a lock this queue refuses to use."""
    queues = [make_queue(tmp_path, run_id=f"run-{index}") for index in range(5)]

    numbers = [queue.next_sequence() for queue in queues] + [queues[0].next_sequence()]

    assert sorted(numbers) == [1, 2, 3, 4, 5, 6]


def test_a_number_already_handed_out_is_never_reused(tmp_path: Path) -> None:
    """The sequence files are the counter's whole memory: an entry that left the queue
    must not free its number for a later run to arrive under."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(num_gpus=1)
    queue.remove_entry(entry)

    assert queue.next_sequence() == entry.seq + 1


def test_an_entry_is_readable_by_every_user_of_the_machine(tmp_path: Path) -> None:
    """An entry the second user cannot read is an entry their queue silently drops, and
    they then jump a queue they never saw. The temp file it is written through is 0o600."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(num_gpus=1)

    assert queue.entry_path(entry).stat().st_mode & 0o044 == 0o044


def test_every_queue_directory_is_writable_by_every_user_of_the_machine(tmp_path: Path) -> None:
    """The umask strips the group and other bits from a new directory, and the second
    user on the box then gets EACCES on a queue they are supposed to share."""
    queue = make_queue(tmp_path)

    directories = [
        queue.dir,
        queue.leases_dir,
        queue.entries_dir,
        queue.served_dir,
        queue.sequence_dir,
    ]

    assert [path.stat().st_mode & 0o777 for path in directories] == [0o777] * len(directories)


def test_a_user_who_just_started_a_run_goes_to_the_back(tmp_path: Path) -> None:
    """served/<user> is the rotation's only memory, and it is the start of a run that
    counts — waiting for a card is not being served."""
    ann = make_queue(tmp_path, run_id="run-ann")
    bob = make_queue(tmp_path, run_id="run-bob", user="bob")
    ann.mark_served()
    ann.enqueue(num_gpus=1)
    bob.enqueue(num_gpus=1)

    assert [entry.user for entry in bob.dispatch_order()] == ["bob", "ann"]


def test_the_clock_that_decides_staleness_comes_from_the_filesystem(tmp_path: Path) -> None:
    """Comparing a file's mtime against the reader's own clock is what breaks when the
    queue lives on a mount whose server is minutes out of step with this host."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(num_gpus=1)

    stamped = queue._filesystem_now()

    assert stamped >= queue.entry_path(entry).stat().st_mtime
    assert list(queue.dir.glob("now-*")) == []


def test_an_injected_clock_decides_what_is_stale(tmp_path: Path) -> None:
    """The clock is a parameter so the whole liveness policy is checkable without waiting
    two minutes for anything."""
    queue = make_queue(tmp_path)
    queue.enqueue(num_gpus=1)
    queue.claim_lease(0)
    much_later = RunQueue(
        queue.config,
        run_id="run-later",
        user="bob",
        now=lambda: time.time() + STALE_AFTER + 1,
    )

    assert much_later.live_entries() == []
    assert much_later.live_leases() == []


def test_running_under_agent_reads_the_environment_as_it_was_at_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """clearml_session.init_task sets CLEARML_TASK_ID itself, after Task.init, so that DDP
    children attach to the right experiment — reading it lazily would make every run look
    agent-managed and switch the queue off for all of them."""
    monkeypatch.setattr(run_queue_module, "_TASK_ID_AT_IMPORT", None)
    monkeypatch.setenv(AGENT_TASK_ID_ENV_VAR, "task-written-by-this-run")

    assert running_under_agent() is False

    monkeypatch.setattr(run_queue_module, "_TASK_ID_AT_IMPORT", "task-from-the-agent")

    assert running_under_agent() is True


@pytest.mark.parametrize(
    ("enabled", "snapshot", "expected"),
    [
        (True, None, True),
        (True, "task-from-the-agent", False),
        (False, None, False),
        (False, "task-from-the-agent", False),
    ],
)
def test_the_queue_is_off_under_an_agent_and_off_when_it_is_turned_off(
    monkeypatch: pytest.MonkeyPatch, enabled: bool, snapshot: str | None, expected: bool
) -> None:
    """An agent already schedules, so queueing underneath one would make a run wait twice;
    an explicit enabled=false wins over the detection either way."""
    monkeypatch.setattr(run_queue_module, "_TASK_ID_AT_IMPORT", snapshot)

    assert queue_active(QueueConfig(enabled=enabled)) is expected


@pytest.mark.parametrize(
    "settings",
    [
        {"heartbeat_seconds": 200.0},
        {"poll_seconds": 130.0},
        {"stale_after_seconds": 10.0},
    ],
)
def test_a_timeout_no_heartbeat_can_outrun_is_refused(settings: dict[str, Any]) -> None:
    """With the timeout at or under the beat, every holder and every waiter expires between
    two of its own heartbeats: leases are stolen from live trainings and the order dissolves."""
    with pytest.raises(ValidationError):
        QueueConfig(**settings)


def test_the_queue_directory_comes_from_the_config_then_the_environment_then_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A path named on the command line has to win over one inherited from a shell, and
    the default is per machine so two hosts sharing a home directory never share a queue."""
    monkeypatch.setenv(QUEUE_DIR_ENV_VAR, str(tmp_path / "from-environment"))

    assert queue_dir(QueueConfig(dir=tmp_path / "explicit")) == tmp_path / "explicit"
    assert queue_dir(QueueConfig()) == tmp_path / "from-environment"

    monkeypatch.delenv(QUEUE_DIR_ENV_VAR)

    assert queue_dir(QueueConfig()).parent == DEFAULT_QUEUE_ROOT
