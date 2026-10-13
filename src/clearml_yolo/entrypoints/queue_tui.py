"""Optional Textual view; every mutation crosses the queue application interface."""

from typing import ClassVar, override

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Input, Static

from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import MoveDirection, PublicJob, QueueView


class QueueApp(App[None]):
    TITLE: str | None = "cy-queue"
    BINDINGS: ClassVar = [
        Binding("q", "quit", "Close"),
        Binding("u", "move_up", "Move up"),
        Binding("d", "move_down", "Move down"),
        Binding("t", "move_top", "Top"),
        Binding("g", "move_bottom", "Bottom"),
        Binding("b", "move_before", "Before ID"),
        Binding("a", "move_after", "After ID"),
        Binding("c", "cancel_job", "Cancel"),
        Binding("r", "recover_job", "Recover"),
        Binding("escape", "dismiss_move", "Back", show=False),
    ]

    def __init__(self, service: QueueService) -> None:
        super().__init__()
        self.service = service
        self.view = QueueView(host_id=service.identity.host_id, revision=0, jobs=())
        self.relative_move: tuple[str, MoveDirection, int] | None = None

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading queue", id="status")
        yield DataTable[str](id="jobs", cursor_type="row")
        yield Input(
            placeholder="Target job ID; Enter applies, Escape returns to jobs", id="relative"
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#jobs", DataTable)
        table.add_columns(
            "Position",
            "Job",
            "Owner",
            "State",
            "Request",
            "Allocation",
            "Waiting reason",
            "Progress",
            "ClearML",
        )
        self.query_one("#relative", Input).display = False
        self.refresh_queue()
        self.set_interval(2, self.refresh_queue)

    def _selected(self) -> PublicJob | None:
        row = self.query_one("#jobs", DataTable).cursor_row
        return self.view.jobs[row] if 0 <= row < len(self.view.jobs) else None

    def refresh_queue(self) -> None:
        selected = self._selected()
        try:
            view = self.service.list()
        except (OSError, ValueError, RuntimeError) as error:
            self.query_one("#status", Static).update(f"Queue unavailable: {error}")
            return
        self.view = view
        table = self.query_one("#jobs", DataTable)
        table.clear()
        for position, job in enumerate(view.jobs, 1):
            request = ",".join(job.request.devices or ()) or str(job.request.count)
            table.add_row(
                str(position),
                job.id,
                str(job.owner_uid),
                job.state,
                request,
                ",".join(job.devices) or "-",
                job.waiting_reason or "",
                (
                    f"{job.progress:.0%}"
                    if isinstance(job.progress, float)
                    else job.progress or ""
                ),
                job.clearml_url or "",
                key=job.id,
            )
            if selected is not None and selected.id == job.id:
                table.move_cursor(row=position - 1)
        self.query_one("#status", Static).update(
            f"Host {view.host_id} | revision {view.revision} | "
            "Closing this view leaves workers running"
        )

    def _move(self, direction: MoveDirection) -> None:
        job = self._selected()
        if job is None:
            return
        if direction in {"before", "after"}:
            self.relative_move = job.id, direction, self.view.revision
            field = self.query_one("#relative", Input)
            field.display = True
            field.focus()
            return
        try:
            self.service.move(job.id, direction, self.view.revision)
        except (OSError, ValueError, RuntimeError) as error:
            self.notify(str(error), severity="error")
        self.refresh_queue()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.relative_move is not None:
            identifier, direction, revision = self.relative_move
            try:
                self.service.move(
                    identifier, direction, revision, relative_job_id=event.value.strip()
                )
            except (OSError, ValueError, RuntimeError) as error:
                self.notify(str(error), severity="error")
        self.relative_move = None
        event.input.value = ""
        event.input.display = False
        self.query_one("#jobs", DataTable).focus()
        self.refresh_queue()

    def action_move_up(self) -> None:
        self._move("up")

    def action_move_down(self) -> None:
        self._move("down")

    def action_move_top(self) -> None:
        self._move("top")

    def action_move_bottom(self) -> None:
        self._move("bottom")

    def action_move_before(self) -> None:
        self._move("before")

    def action_move_after(self) -> None:
        self._move("after")

    def action_dismiss_move(self) -> None:
        self.relative_move = None
        field = self.query_one("#relative", Input)
        field.value = ""
        field.display = False
        self.query_one("#jobs", DataTable).focus()

    def action_cancel_job(self) -> None:
        self._owned_action(recover=False)

    def action_recover_job(self) -> None:
        self._owned_action(recover=True)

    def _owned_action(self, *, recover: bool) -> None:
        job = self._selected()
        if job is None:
            return
        try:
            if recover:
                self.service.recover(job.id)
            else:
                self.service.cancel(job.id)
        except (OSError, ValueError, RuntimeError) as error:
            self.notify(str(error), severity="error")
        self.refresh_queue()
