"""What `cy-queue` draws and what its keys refuse, against a queue on the filesystem.

The app itself cannot be driven from a test — it holds the terminal in cbreak mode and
redraws until somebody presses `q` — but everything it decides happens in two functions
underneath that live table, and neither had a test. That is how a column that always drew
`-` and a call site left one argument behind both survived review.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from clearml_yolo.apps.queue import _repin, running_rows
from clearml_yolo.run_queue import Entry, QueueConfig, RunQueue

STALE_AFTER = 120.0


def make_queue(tmp_path: Path, *, run_id: str = "box-1", user: str = "ann") -> RunQueue:
    """A queue rooted in the test's own directory, with the machine identity pinned."""
    config = QueueConfig(dir=tmp_path / "queue", stale_after_seconds=STALE_AFTER)
    return RunQueue(config, run_id=run_id, user=user, host="box", pid=4242)


def backdate(path: Path, seconds: float) -> None:
    """Push a heartbeat into the past, which is the only way a test can let a run die."""
    stamp = path.stat().st_mtime - seconds
    os.utime(path, (stamp, stamp))


def test_a_run_holding_cards_is_shown_how_long_it_has_held_them(tmp_path: Path) -> None:
    """The elapsed column is the lease's own start against the queue's clock. Its earlier
    source was the timestamp inside the run id, which the ids the queue actually writes —
    `<host>-<pid>` — never carried, so the column drew `-` for every real run there is."""
    queue = make_queue(tmp_path)
    queue.claim_leases([0, 1])

    rows = running_rows(queue)

    assert [row.run_id for row in rows] == ["box-1"]
    assert rows[0].gpu_indices == [0, 1]
    assert rows[0].elapsed_seconds is not None
    assert 0.0 <= rows[0].elapsed_seconds < STALE_AFTER


def test_a_lease_from_before_the_queue_recorded_starts_shows_no_time(tmp_path: Path) -> None:
    """A payload written by an older release, and one claimed in the instant before it is
    written, both carry no start. An age counted from the epoch would read as decades."""
    queue = make_queue(tmp_path)
    queue.claim_lease(0)
    without_a_start = json.dumps(
        {"gpu_index": 0, "run_id": "box-1", "user": "ann", "host": "box", "pid": 4242}
    )
    queue.leases_dir.joinpath("gpu-0").write_text(without_a_start, encoding="utf-8")

    assert running_rows(queue)[0].elapsed_seconds is None


def test_a_card_nobody_heartbeats_stays_on_screen_marked_expired(tmp_path: Path) -> None:
    """`live_leases` hides an expired card so no run is offered one it would have to steal.
    This is the view where a person decides to steal it, so the row has to stay."""
    queue = make_queue(tmp_path)
    queue.claim_lease(0)
    backdate(queue.leases_dir / "gpu-0", STALE_AFTER * 2)

    rows = running_rows(queue)

    assert [(row.run_id, row.expired) for row in rows] == [("box-1", True)]


def test_a_reclaim_in_progress_is_never_drawn_as_a_held_card(tmp_path: Path) -> None:
    """A take-over leaves a marker beside the leases for as long as it runs. Counted as a
    card, it would put a run on screen holding a GPU index that does not exist."""
    queue = make_queue(tmp_path)
    queue.leases_dir.joinpath(".reclaim-gpu-0-12345-678").write_text("box-9", encoding="utf-8")

    assert running_rows(queue) == []


def test_pinning_a_run_that_already_took_its_cards_is_refused(tmp_path: Path) -> None:
    """The table on screen is up to one redraw old, and in that time the run under the
    cursor may have started. Writing its entry then raises a ghost at the head of the queue
    that every real waiter sits behind until it ages out."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(1)
    queue.claim_lease(0)
    queue.remove_entry(entry)

    message = _repin(queue, entry, priority=0)

    assert "running, not waiting" in message
    assert queue.live_entries() == []


def test_pinning_a_run_that_has_gone_is_refused(tmp_path: Path) -> None:
    """The same ghost, arrived at the other way: a run cancelled or started between the
    redraw and the keypress leaves no entry to rewrite."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(1)
    queue.remove_entry(entry)

    message = _repin(queue, entry, priority=0)

    assert "no longer waiting" in message
    assert queue.live_entries() == []


def test_pinning_a_run_that_is_still_waiting_writes_its_pin(tmp_path: Path) -> None:
    """The case the refusals must not swallow: a genuine waiter is pinned, and unpinned
    back into the fair rotation, by one write to its own entry file and nothing else."""
    queue = make_queue(tmp_path)
    entry = queue.enqueue(1)

    assert "pinned at 0" in _repin(queue, entry, priority=0)
    pinned = queue.live_entries()
    assert [(waiter.run_id, waiter.priority) for waiter in pinned] == [("box-1", 0)]

    assert "fair rotation" in _repin(queue, pinned[0], priority=None)
    assert [waiter.priority for waiter in queue.live_entries()] == [None]


def test_a_pin_moves_no_other_run(tmp_path: Path) -> None:
    """One entry file changes and nothing else is touched, which is why the pin lives
    inside each entry rather than in one shared order file every reorder would lock."""
    queue = make_queue(tmp_path)
    peer = Entry(seq=99, run_id="box-2", user="bob", host="box", pid=99)
    queue.write_entry(peer)
    entry = queue.enqueue(1)

    _repin(queue, entry, priority=0)

    assert {waiter.run_id: waiter.priority for waiter in queue.live_entries()} == {
        "box-1": 0,
        "box-2": None,
    }
