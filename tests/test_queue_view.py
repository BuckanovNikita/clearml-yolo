"""The table cy-queue draws: held cards above the queue, pins, and times a person reads."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from clearml_yolo.queue_view import (
    CURSOR,
    EMPTY_MESSAGE,
    EXPIRED_STATE,
    NO_DURATION,
    PIN_MARKER,
    QueueState,
    RunningRow,
    WaitingRow,
    format_duration,
    render,
)

TABLE_WIDTH = 140


def rendered(state: QueueState) -> str:
    """The table as a person would see it, drawn into a string and not a terminal.

    Generously wide on purpose: rich truncates columns to fit, and a narrow console would
    make these assertions fail over a wrapped run id rather than over the behaviour.
    """
    buffer = StringIO()
    Console(file=buffer, width=TABLE_WIDTH).print(render(state))
    return buffer.getvalue()


def running(user: str, run_id: str, *gpu_indices: int, **fields: object) -> RunningRow:
    return RunningRow(user=user, run_id=run_id, gpu_indices=list(gpu_indices), **fields)  # type: ignore[arg-type]


def waiting(user: str, run_id: str, **fields: object) -> WaitingRow:
    return WaitingRow(user=user, run_id=run_id, **fields)  # type: ignore[arg-type]


def test_every_run_holding_cards_is_drawn_above_every_run_waiting_for_them() -> None:
    """The order of the two halves is the answer to "when do I start": a waiting list
    means nothing until you can see what has to finish first."""
    state = QueueState(
        queue_dir="/tmp/clearml-yolo/box",
        running=[running("ann", "hold-one", 0), running("bob", "hold-two", 1, 2)],
        waiting=[
            waiting("cid", "queued-one"),
            waiting("ann", "queued-two"),
            waiting("dee", "queued-three"),
        ],
    )

    drawn = rendered(state)

    positions = [
        drawn.index(name)
        for name in ("hold-one", "hold-two", "queued-one", "queued-two", "queued-three")
    ]
    assert positions == sorted(positions)


def test_a_run_holding_several_cards_names_all_of_them_on_one_line() -> None:
    """A multi-card run is one run, and drawing it as three rows would read as three
    separate holders of a machine that only has one of them."""
    state = QueueState(running=[running("bob", "hold-two", 1, 2, 3)])

    assert "1, 2, 3" in rendered(state)


def test_the_waiting_runs_are_numbered_in_the_order_they_will_be_served() -> None:
    """The number is the whole reason to open the viewer while queued: it is the place in
    line, and it has to count the queue rather than the table."""
    state = QueueState(
        running=[running("ann", "hold-one", 0)],
        waiting=[waiting("cid", "queued-one"), waiting("ann", "queued-two")],
    )

    drawn = rendered(state)

    assert "1" in drawn.split("queued-one")[0].splitlines()[-1]
    assert "2" in drawn.split("queued-two")[0].splitlines()[-1]


def test_an_empty_queue_says_so_instead_of_drawing_bare_column_headings() -> None:
    """A machine with nothing queued is the normal case, and a table of headings alone
    reads as a viewer that failed to find the queue."""
    assert EMPTY_MESSAGE in rendered(QueueState(queue_dir="/tmp/clearml-yolo/box"))


def test_a_queue_with_anything_in_it_does_not_claim_to_be_empty() -> None:
    """The reassurance is only useful while it is true."""
    state = QueueState(waiting=[waiting("cid", "queued-one")])

    assert EMPTY_MESSAGE not in rendered(state)


def test_a_pinned_entry_is_marked_so_a_manual_order_is_visible_as_manual() -> None:
    """A pin overrides the fair rotation, so anyone reading the queue has to be able to
    see that the order in front of them was set by hand rather than earned by waiting."""
    state = QueueState(
        waiting=[waiting("cid", "queued-one", priority=-2), waiting("ann", "queued-two")]
    )

    drawn = rendered(state)

    pinned_line = next(line for line in drawn.splitlines() if "queued-one" in line)
    unpinned_line = next(line for line in drawn.splitlines() if "queued-two" in line)
    assert f"{PIN_MARKER} -2" in pinned_line
    assert PIN_MARKER not in unpinned_line


def test_a_lease_nobody_heartbeats_is_drawn_as_expired_rather_than_hidden() -> None:
    """The whole point of showing a dead holder is that somebody can then reclaim its
    card; a viewer that dropped the row would leave the card stuck with no way back."""
    state = QueueState(running=[running("ann", "hold-one", 0, expired=True)])

    assert EXPIRED_STATE in rendered(state)


def test_the_selected_row_carries_the_cursor_and_no_other_row_does() -> None:
    """Every editing key acts on the selection, so a viewer that does not show which row
    is selected is a viewer where cancelling is a guess."""
    state = QueueState(
        running=[running("ann", "hold-one", 0)],
        waiting=[waiting("cid", "queued-one"), waiting("ann", "queued-two")],
        selected=2,
    )

    drawn = rendered(state)

    assert CURSOR in next(line for line in drawn.splitlines() if "queued-two" in line)
    assert CURSOR not in next(line for line in drawn.splitlines() if "queued-one" in line)
    assert CURSOR not in next(line for line in drawn.splitlines() if "hold-one" in line)


def test_a_selection_pointing_past_the_last_row_still_draws_the_queue() -> None:
    """Runs end between two redraws, and a cursor left on a row that has gone must cost a
    highlight and not the whole view."""
    state = QueueState(waiting=[waiting("cid", "queued-one")], selected=7)

    drawn = rendered(state)

    assert "queued-one" in drawn
    assert CURSOR not in drawn


def test_a_run_named_with_markup_characters_is_drawn_and_not_interpreted() -> None:
    """Run ids come from a task name the user chooses, and rich reads square brackets as
    style tags: an unlucky name would otherwise take the viewer down mid-redraw."""
    state = QueueState(waiting=[waiting("cid", "queued-[bold]-one")])

    assert "queued-[bold]-one" in rendered(state)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.0, "0s"),
        (9.7, "9s"),
        (75.0, "1m15s"),
        (3599.0, "59m59s"),
        (3600.0, "1h00m"),
        (9000.0, "2h30m"),
    ],
)
def test_a_duration_is_written_in_the_largest_unit_that_applies(
    seconds: float, expected: str
) -> None:
    """The queue is read at a glance, and a wait of two and a half hours printed as 9000
    seconds is a number the reader has to do arithmetic on before it means anything."""
    assert format_duration(seconds) == expected


@pytest.mark.parametrize("seconds", [None, -1.0])
def test_an_unknown_duration_says_nothing_rather_than_claiming_zero(
    seconds: float | None,
) -> None:
    """A run whose start this machine has no record of has not just started; printing 0s
    there would be a confident lie about a training that may be hours old."""
    assert format_duration(seconds) == NO_DURATION


def test_the_elapsed_and_wait_times_come_from_the_state_and_are_not_measured_here() -> None:
    """Rendering stays pure — no clock, no filesystem — which is the only reason a TUI can
    be checked at all; the caller decides both numbers and the table only formats them."""
    state = QueueState(
        running=[running("ann", "hold-one", 0, elapsed_seconds=4210.0)],
        waiting=[waiting("cid", "queued-one", waited_seconds=95.0)],
    )

    drawn = rendered(state)

    assert "1h10m" in drawn
    assert "1m35s" in drawn
