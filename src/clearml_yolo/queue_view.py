"""The table ``cy-queue`` draws: who holds the cards, who is waiting, and in what order.

Rendering is a pure function of a state object — no filesystem, no clock, no terminal.
That is what makes a TUI checkable at all: the mocked suite builds a state by hand, renders
it into a string console and asserts on what a person would read, with nothing to stub. It
also draws the line between the two halves of the feature — everything the table shows,
including the elapsed and wait times, is decided by the caller and handed in, so the rules
about *what* a run is doing never leak into the drawing of it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from rich.table import Table
from rich.text import Text

TITLE = "clearml-yolo queue"
# Which row the keys act on. A marker rather than colour alone, because the selection has
# to survive being read out of a plain string, both in a test and over a dumb terminal.
CURSOR = ">"
PIN_MARKER = "*"
EMPTY_MESSAGE = "Nothing is running and nothing is waiting."
NO_DURATION = "-"
RUNNING_STATE = "running"
EXPIRED_STATE = "expired"
WAITING_STATE = "waiting"


def format_duration(seconds: float | None) -> str:
    """How long, in the units a person waiting actually thinks in.

    A queue is read at a glance to answer "is this nearly done" and "have I been skipped",
    so the largest unit that applies wins and the rest is dropped. ``None`` is not zero: it
    is a run whose start this machine has no record of, and a confident ``0s`` there would
    be a lie about a run that may have been going for hours.
    """
    if seconds is None or seconds < 0:
        return NO_DURATION
    hours, rest = divmod(int(seconds), 3600)
    minutes, whole_seconds = divmod(rest, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{whole_seconds:02d}s"
    return f"{whole_seconds}s"


class RunningRow(BaseModel):
    """One run that already holds cards, with every card it holds on the same line.

    ``expired`` is a lease nothing has heartbeated for the timeout: the run behind it is
    almost certainly gone, and the row stays visible precisely so somebody can reclaim it.
    """

    user: str
    run_id: str
    gpu_indices: list[int] = Field(default_factory=list)
    elapsed_seconds: float | None = None
    expired: bool = False


class WaitingRow(BaseModel):
    """One run still queued, already placed by the dispatch order it will be served in."""

    user: str
    run_id: str
    num_gpus: int = 1
    waited_seconds: float | None = None
    priority: int | None = None


class QueueState(BaseModel):
    """Everything the table needs, as one value the caller assembles.

    ``selected`` counts through the running rows first and then the waiting ones, so a
    single index addresses every row a key can act on. It is allowed to point nowhere —
    the queue shrinks between two polls whenever a run ends — and that draws a table with
    no cursor rather than raising in the middle of a redraw.
    """

    queue_dir: str = ""
    running: list[RunningRow] = Field(default_factory=list)
    waiting: list[WaitingRow] = Field(default_factory=list)
    selected: int = 0
    message: str = ""


def render(state: QueueState) -> Table:
    """The whole queue as one table: what is running, above what is waiting for it.

    Held cards come first because they are the answer to "when do I start" — the waiting
    list only means something once you can see what has to finish. Free text goes through
    ``Text`` so a run named with square brackets is drawn rather than parsed as markup.
    """
    table = Table(title=f"{TITLE} — {state.queue_dir}", caption=_caption(state))
    table.add_column("", width=len(CURSOR))
    table.add_column("#", justify="right")
    table.add_column("state")
    table.add_column("user")
    table.add_column("run")
    table.add_column("cards", justify="right")
    table.add_column("time", justify="right")
    table.add_column("pin")
    for position, running in enumerate(state.running):
        table.add_row(
            CURSOR if position == state.selected else "",
            "",
            EXPIRED_STATE if running.expired else RUNNING_STATE,
            Text(running.user),
            Text(running.run_id),
            ", ".join(str(index) for index in running.gpu_indices),
            format_duration(running.elapsed_seconds),
            "",
            style="reverse" if position == state.selected else None,
        )
    for place, waiting in enumerate(state.waiting, start=1):
        position = len(state.running) + place - 1
        table.add_row(
            CURSOR if position == state.selected else "",
            str(place),
            WAITING_STATE,
            Text(waiting.user),
            Text(waiting.run_id),
            str(waiting.num_gpus),
            format_duration(waiting.waited_seconds),
            "" if waiting.priority is None else f"{PIN_MARKER} {waiting.priority}",
            style="reverse" if position == state.selected else None,
        )
    return table


def _caption(state: QueueState) -> str | None:
    """What is written under the table: why it is empty, and what the last key did."""
    empty = EMPTY_MESSAGE if not state.running and not state.waiting else ""
    notes = [note for note in (empty, state.message) if note]
    return "  ".join(notes) if notes else None
