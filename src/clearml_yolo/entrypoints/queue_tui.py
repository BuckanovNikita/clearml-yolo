"""Optional Textual view; every mutation crosses the queue application interface."""

import webbrowser
from typing import ClassVar, override
from urllib.parse import urlsplit

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Select, Static

from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import MoveDirection, PublicJob, QueueView, QueueVisibility
from clearml_yolo.entrypoints.queue_presentation import QueuePresentation


class QueueApp(App[None]):
    TITLE: str | None = "cy-queue"
    BINDINGS: ClassVar = [
        Binding("q", "quit", "Close"),
        Binding("u", "move_up", "Move up"),
        Binding("d", "move_down", "Move down"),
        Binding("t", "move_top", "Top"),
        Binding("g", "move_bottom", "Bottom"),
        Binding("b", "move_before", "Move before"),
        Binding("a", "move_after", "Move after"),
        Binding("c", "cancel_job", "Cancel"),
        Binding("r", "recover_job", "Recover"),
        Binding("x", "archive_job", "Archive"),
        Binding("s", "restore_job", "Restore"),
        Binding("v", "cycle_view", "Change view"),
        Binding("o", "open_task", "Open task"),
        Binding("escape", "dismiss_move", "Back", show=False),
    ]

    def __init__(
        self, service: QueueService, *, presentation: QueuePresentation | None = None
    ) -> None:
        super().__init__()
        self.service = service
        self.presentation = presentation or QueuePresentation()
        self.view = QueueView(host_id=service.identity.host_id, revision=0, jobs=())
        self.relative_move: tuple[str, MoveDirection, int] | None = None
        self.visibility: QueueVisibility = "main"

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading queue", id="status")
        yield DataTable[str](id="jobs", cursor_type="row")
        yield Select[str]([], prompt="Choose target job", id="relative")
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
            "Status diagnostic",
        )
        self.query_one("#relative", Select).display = False
        self.refresh_queue()
        self.set_interval(2, self.refresh_queue)

    def _selected(self) -> PublicJob | None:
        row = self.query_one("#jobs", DataTable).cursor_row
        return self.view.jobs[row] if 0 <= row < len(self.view.jobs) else None

    def refresh_queue(self) -> None:
        selected = self._selected()
        try:
            view = self.service.list(visibility=self.visibility)
        except (OSError, ValueError, RuntimeError) as error:
            self.query_one("#status", Static).update(
                self.presentation.text(f"Queue unavailable: {error}")
            )
            return
        self.view = view
        messages = self.presentation.refresh_messages(view)
        table = self.query_one("#jobs", DataTable)
        table.clear()
        for position, job in enumerate(view.jobs, 1):
            request = self.presentation.request(job.request, job.host_id)
            table.add_row(
                str(position),
                self.presentation.job_title(job),
                str(job.owner_uid),
                job.state + (" (archived)" if job.id in view.archived_job_ids else ""),
                request,
                ",".join(self.presentation.devices(job.devices, job.host_id)) or "-",
                self.presentation.text(job.waiting_reason or "", job.host_id),
                (
                    f"{job.progress:.0%}"
                    if isinstance(job.progress, float)
                    else self.presentation.text(job.progress or "", job.host_id)
                ),
                "Open task (o)" if job.clearml_url else "",
                messages.get(job.id, ""),
                key=job.id,
            )
            if selected is not None and selected.id == job.id:
                table.move_cursor(row=position - 1)
        self.query_one("#status", Static).update(
            f"{self.presentation.queue_name} | {self.presentation.host(view.host_id)} | "
            f"{self.visibility.title()} | archived {len(view.archived_job_ids)} | "
            f"warnings {len(messages)} | "
            f"revision {view.revision} | "
            "Closing this view leaves workers running"
        )

    def _move(self, direction: MoveDirection) -> None:
        job = self._selected()
        if job is None:
            return
        if direction in {"before", "after"}:
            self.relative_move = job.id, direction, self.view.revision
            targets = [
                (self.presentation.job_title(target), target.id)
                for target in self.view.jobs
                if target.id != job.id and target.state == "pending"
            ]
            if job.state != "pending" or not targets:
                self.relative_move = None
                self.notify("Choose a pending job with another pending target", severity="error")
                return
            field = self.query_one("#relative", Select)
            field.set_options(targets)
            field.display = True
            field.focus()
            return
        try:
            self.service.move(job.id, direction, self.view.revision)
        except (OSError, ValueError, RuntimeError) as error:
            self.notify(self.presentation.text(str(error)), severity="error")
        self.refresh_queue()

    def on_select_changed(self, event: Select.Changed) -> None:
        if self.relative_move is not None and isinstance(event.value, str):
            identifier, direction, revision = self.relative_move
            try:
                self.service.move(identifier, direction, revision, relative_job_id=event.value)
            except (OSError, ValueError, RuntimeError) as error:
                self.notify(self.presentation.text(str(error)), severity="error")
            self.action_dismiss_move()
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
        field = self.query_one("#relative", Select)
        field.clear()
        field.display = False
        self.query_one("#jobs", DataTable).focus()

    def action_cancel_job(self) -> None:
        self._owned_action(recover=False)

    def action_recover_job(self) -> None:
        self._owned_action(recover=True)

    def action_cycle_view(self) -> None:
        self.action_dismiss_move()
        modes: tuple[QueueVisibility, ...] = ("main", "archived", "all")
        self.visibility = modes[(modes.index(self.visibility) + 1) % len(modes)]
        self.refresh_queue()

    def action_archive_job(self) -> None:
        self._archive(restore=False)

    def action_restore_job(self) -> None:
        self._archive(restore=True)

    def _archive(self, *, restore: bool) -> None:
        job = self._selected()
        if job is None:
            return
        try:
            if restore:
                self.service.restore((job.id,))
            else:
                self.service.archive((job.id,))
        except (OSError, ValueError, RuntimeError) as error:
            self.notify(self.presentation.text(str(error)), severity="error")
        self.refresh_queue()

    def action_open_task(self) -> None:
        job = self._selected()
        if job is None or job.clearml_url is None:
            return
        try:
            target = urlsplit(job.clearml_url)
            valid = target.scheme in {"http", "https"} and bool(target.netloc)
        except ValueError:
            valid = False
        if not valid:
            self.notify("Task link is unavailable", severity="error")
            return
        if not webbrowser.open(job.clearml_url):
            self.notify("No browser is available to open the task", severity="warning")

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
            self.notify(self.presentation.text(str(error)), severity="error")
        self.refresh_queue()
