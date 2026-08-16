"""CLI: watch this machine's run queue live, and edit the order it will be served in.

Plain argparse rather than a Hydra app, for the same reason as ``cy-init-config``: there is
no config to compose here, and a Hydra app would open an output directory and a log file
just to draw a table.

``rich`` redraws the table on a timer but reads nothing, so the keys are read straight from
the terminal in cbreak mode. Every edit the keys make is a single file operation on a
single entry — the queue has no coordinator to ask, and one shared order file would have to
be locked against every waiting run that reads it.
"""

from __future__ import annotations

import argparse
import os
import select
import sys
import termios
import time
import tty
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from loguru import logger
from rich.console import Console
from rich.live import Live

from clearml_yolo.queue_view import QueueState, RunningRow, WaitingRow, render
from clearml_yolo.run_queue import (
    NO_PID,
    UNKNOWN_HOLDER,
    UNKNOWN_START,
    Entry,
    Lease,
    QueueConfig,
    RunQueue,
)

KEY_HELP = "j/k select  t pin to top  J/K move down/up  u unpin  c cancel  r reclaim  q quit"

LEASE_PREFIX = "gpu-"


def _lease_files(queue: RunQueue) -> dict[int, Path]:
    """Every card the queue has a file for, live or not.

    ``live_leases`` deliberately hides the expired ones — a run must not be offered a card
    it would have to steal — but this is the view where a person decides to steal it, so
    the files themselves are what it lists.
    """
    cards = {}
    for path in queue.leases_dir.iterdir():
        index = path.name.removeprefix(LEASE_PREFIX)
        if path.name.startswith(LEASE_PREFIX) and index.isdigit():
            cards[int(index)] = path
    return cards


def _abandoned_lease(path: Path, gpu_index: int) -> Lease:
    """Who left this card behind, as far as its file still says.

    A lease claimed but not yet written is a real claim with no payload, and one whose
    holder died mid-write may hold half of one; both name nobody rather than hide the card.
    """
    try:
        return Lease.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Lease(
            gpu_index=gpu_index,
            run_id=UNKNOWN_HOLDER,
            user=UNKNOWN_HOLDER,
            host=UNKNOWN_HOLDER,
            pid=NO_PID,
        )


def running_rows(queue: RunQueue) -> list[RunningRow]:
    """One row per run holding cards, however many cards it holds, expired ones marked.

    How long a run has held its cards is the lease's own ``started_at`` subtracted from the
    queue's clock, and never from this process's: the two readings have to come from the
    same clock the stamp was taken from, or a viewer on a workstation out of step with the
    file server draws an elapsed time that is out with it — hours off, or negative. That
    clock is ``RunQueue``'s, as the field's own documentation says, and reaching for it is
    what the private access below buys. It is read after the leases so that a card claimed
    during the redraw reads as just started rather than as unknown.

    A lease claimed but not yet written, and one written before the queue recorded starts
    at all, carry ``UNKNOWN_START``; those rows show no time rather than an age counted
    from the epoch.
    """
    live = {lease.gpu_index: lease for lease in queue.live_leases()}
    moment = queue._now()  # noqa: SLF001
    rows: dict[tuple[str, bool], RunningRow] = {}
    for gpu_index, path in sorted(_lease_files(queue).items()):
        held = live.get(gpu_index)
        expired = held is None
        lease = held if held is not None else _abandoned_lease(path, gpu_index)
        row = rows.get((lease.run_id, expired))
        if row is None:
            unknown_start = lease.started_at == UNKNOWN_START
            row = RunningRow(
                user=lease.user,
                run_id=lease.run_id,
                elapsed_seconds=None if unknown_start else moment - lease.started_at,
                expired=expired,
            )
            rows[(lease.run_id, expired)] = row
        row.gpu_indices.append(gpu_index)
    return list(rows.values())


def _repin(queue: RunQueue, entry: Entry, priority: int | None) -> str:
    """Rewrite this one entry's pin, which is the whole of a reorder.

    The table on screen is up to one redraw old, and in that time the run under the cursor
    may have taken its cards and deleted its entry. Writing the file then would not move a
    run, it would raise a ghost: a freshly heartbeated entry belonging to nobody, sitting
    at the head of the queue if it was pinned there, with every real waiter behind it
    seeing someone else at the head until the ghost ages out.

    The two checks below **narrow that window; they do not close it.** Publishing an entry
    is a rename, which recreates the path whatever became of it in between, so a run that
    deletes its entry after the checks and before the rename is resurrected anyway. Closing
    it would mean writing entries in place, where a reader can catch a half-written one —
    and an entry that will not parse is silently skipped, which makes a live waiter briefly
    invisible and lets the run behind it jump the queue. A ghost is the better failure, and
    it is visible and curable: it is a row nobody is behind for long, ``c`` removes it at
    once, and left alone it ages out after ``stale_after_seconds``.

    A run that already holds live leases is refused outright rather than narrowly: it is
    running, so it cannot also be waiting, and its entry file is the one the queue is about
    to delete.
    """
    holders = {lease.run_id for lease in queue.live_leases()}
    if entry.run_id in holders:
        return f"{entry.run_id} has already taken its cards; it is running, not waiting."
    if not queue.entry_path(entry).exists():
        return f"{entry.run_id} is no longer waiting; it has started or been cancelled."
    queue.write_entry(entry.model_copy(update={"priority": priority}))
    if priority is None:
        return f"{entry.run_id} is back in the fair rotation."
    return f"{entry.run_id} is pinned at {priority}."


def _shift_pin(queue: RunQueue, entries: Sequence[Entry], index: int, direction: int) -> str:
    """Move a pinned run one place, past the neighbour it swaps with.

    The new priority is one step beyond that neighbour's, which always lands the run on the
    far side of it. Where several pins share a number the move can carry a run past more
    than one of them at once; the next redraw shows where it went. The alternative is a
    global order file, rewritten under a lock that every waiting run would have to take to
    read its own position — a far worse trade for a queue whose order is edited by hand.
    """
    entry = entries[index]
    if entry.priority is None:
        return f"{entry.run_id} is not pinned; press t to pin it first."
    neighbour_index = index + direction
    if not 0 <= neighbour_index < len(entries):
        end = "top" if direction < 0 else "bottom"
        return f"{entry.run_id} is already at the {end} of the queue."
    neighbour = entries[neighbour_index]
    if neighbour.priority is None:
        return f"{entry.run_id} is the last pinned run; press u to unpin it."
    return _repin(queue, entry, neighbour.priority + direction)


def _edit_entry(queue: RunQueue, entries: Sequence[Entry], index: int, key: str) -> str:
    """Apply a key that acts on a waiting run to the one under the cursor."""
    if not 0 <= index < len(entries):
        return "That key acts on a waiting run; the rows above the queue are already running."
    entry = entries[index]
    if key == "c":
        queue.remove_entry(entry)
        return f"Cancelled {entry.run_id}; the run itself will say so and stop waiting."
    if key == "t":
        pins = [queued.priority for queued in entries if queued.priority is not None]
        return _repin(queue, entry, min(pins, default=1) - 1)
    if key == "u":
        return _repin(queue, entry, None)
    return _shift_pin(queue, entries, index, -1 if key == "K" else 1)


def _reclaim(queue: RunQueue, row: RunningRow) -> str:
    """Free the cards of a run nothing has heartbeated for the timeout.

    Taking the lease and giving it straight back is what makes this safe to press by
    mistake: the claim is refused outright while the holder is still beating, so a running
    training cannot be evicted from the viewer.
    """
    reclaimed = []
    for gpu_index in row.gpu_indices:
        if queue.claim_lease(gpu_index) is None:
            continue
        queue.release_lease(gpu_index)
        reclaimed.append(gpu_index)
    if not reclaimed:
        return f"{row.run_id} is still heartbeating its cards; there is nothing to reclaim."
    return f"Reclaimed GPU {', '.join(str(index) for index in reclaimed)} from {row.run_id}."


def apply_key(
    queue: RunQueue,
    key: str,
    running: Sequence[RunningRow],
    entries: Sequence[Entry],
    selected: int,
) -> tuple[int, str]:
    """What a keypress does, as the new cursor position and the line under the table."""
    last = max(len(running) + len(entries) - 1, 0)
    if key == "j":
        return min(selected + 1, last), KEY_HELP
    if key == "k":
        return max(selected - 1, 0), KEY_HELP
    if key == "r":
        if not 0 <= selected < len(running):
            return selected, "Reclaiming acts on a card that is held; select a running run."
        return selected, _reclaim(queue, running[selected])
    if key in {"c", "t", "u", "J", "K"}:
        return selected, _edit_entry(queue, entries, selected - len(running), key)
    return selected, KEY_HELP


@contextmanager
def single_keypresses(stream: TextIO) -> Iterator[None]:
    """Read keys as they are pressed, and hand the terminal back however this ends.

    Without cbreak the loop would see nothing until the user pressed enter; without the
    restore in the ``finally`` an exception anywhere in the view would leave the shell with
    no echo and no line editing, which is a broken terminal the user has to reset by hand.
    """
    descriptor = stream.fileno()
    saved = termios.tcgetattr(descriptor)
    try:
        tty.setcbreak(descriptor)
        yield
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, saved)


def _pressed_key(stream: TextIO, timeout: float) -> str | None:
    """One keypress, or None because the redraw is due.

    Read from the descriptor rather than the stream: a buffered reader can pull a whole
    escape sequence out of the terminal while ``select`` then reports nothing to read, and
    the view would sit still until the next key.
    """
    ready, _, _ = select.select([stream], [], [], timeout)
    if not ready:
        return None
    return os.read(stream.fileno(), 1).decode(errors="ignore") or None


def watch(queue: RunQueue, *, console: Console, refresh_seconds: float) -> None:
    """Draw the queue until the user quits, applying every key to it as it is pressed.

    Each of the two times on screen is subtracted from the clock its stamp was taken from,
    and they are not the same clock. A lease's start is stamped from the queue's own, which
    ``running_rows`` reads for itself; an entry stamps ``enqueued_at`` from the wall clock
    of the run that wrote it, so the wait below is what this process's wall clock makes of
    it. Crossing the two would draw a wait that is out by whatever the two disagree by.
    """
    selected = 0
    message = KEY_HELP
    live_table = Live(console=console, screen=True, auto_refresh=False)
    with single_keypresses(sys.stdin), live_table as live:
        while True:
            now = time.time()
            running = running_rows(queue)
            entries = queue.dispatch_order()
            selected = min(selected, max(len(running) + len(entries) - 1, 0))
            state = QueueState(
                queue_dir=str(queue.dir),
                running=running,
                waiting=[
                    WaitingRow(
                        user=entry.user,
                        run_id=entry.run_id,
                        num_gpus=entry.num_gpus,
                        waited_seconds=now - entry.enqueued_at if entry.enqueued_at > 0 else None,
                        priority=entry.priority,
                    )
                    for entry in entries
                ],
                selected=selected,
                message=message,
            )
            live.update(render(state), refresh=True)
            key = _pressed_key(sys.stdin, refresh_seconds)
            if key == "q":
                return
            if key is not None:
                selected, message = apply_key(queue, key, running, entries, selected)


def _refuse_without_a_terminal() -> None:
    """Stop before drawing, rather than painting control codes into a pipe or a log."""
    if sys.stdout.isatty() and sys.stdin.isatty():
        return
    unusable = "stdout" if not sys.stdout.isatty() else "stdin"
    logger.error(
        "cy-queue draws a live table and reads single keypresses, so it needs a terminal, "
        "but {} is not one. Run it in a terminal of its own, without redirecting it.",
        unusable,
    )
    raise SystemExit(2)


def _quiet_the_log() -> None:
    """Keep loguru out of the drawing.

    Reclaiming an expired lease logs a warning from ``run_queue``, and a line written to
    stderr while the alternate screen is up lands in the middle of the table. The caption
    under the table is this app's channel for saying what happened; only something serious
    enough to end the view is worth breaking the picture for.
    """
    logger.remove()
    logger.add(sys.stderr, level="ERROR")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", help="the queue directory to watch, if not the default one")
    parser.add_argument(
        "--refresh-seconds",
        type=float,
        default=1.0,
        help="how often the table is redrawn while no key is pressed",
    )
    arguments = parser.parse_args()
    _refuse_without_a_terminal()
    queue = RunQueue(
        QueueConfig(dir=Path(arguments.dir) if arguments.dir else None),
        run_id=f"cy-queue-{os.getpid()}",
    )
    _quiet_the_log()
    watch(queue, console=Console(), refresh_seconds=arguments.refresh_seconds)


if __name__ == "__main__":
    main()
