"""Monitoring diagnostics retain readable queue summaries across output formats."""

import asyncio
import json
from typing import cast

import pytest

from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import (
    PublicJob,
    QueueRefreshIssue,
    QueueView,
    QueueVisibility,
    ResourceRequest,
    WorkerIdentity,
)
from clearml_yolo.entrypoints.queue import _show
from clearml_yolo.entrypoints.queue_presentation import QueuePresentation

_DIAGNOSTIC = "Status unavailable; showing last recorded state"


def _mixed_view() -> QueueView:
    healthy = PublicJob(
        id="healthy-private-id",
        owner_uid=7,
        host_id="host",
        boot_id="boot",
        command="train",
        label="Healthy training",
        request=ResourceRequest(gpus=1),
        submitted_at=0,
        submission_sequence=1,
        state="running",
        progress=0.25,
    )
    pending = healthy.model_copy(
        update={
            "id": "pending-private-id",
            "label": "Older training",
            "submission_sequence": 2,
            "state": "pending",
            "progress": None,
            "waiting_reason": "Waiting for GPU capacity",
        }
    )
    archived = healthy.model_copy(
        update={
            "id": "archived-private-id",
            "label": "Archived training",
            "submission_sequence": 3,
            "state": "completed",
            "progress": 1.0,
        }
    )
    return QueueView(
        host_id="host",
        revision=4,
        jobs=(healthy, pending, archived),
        archived_job_ids=(archived.id,),
        refresh_issues=(
            QueueRefreshIssue(job_id=pending.id),
            QueueRefreshIssue(job_id=archived.id),
        ),
    )


def test_text_listing_shows_each_warning_with_its_readable_job(
    capsys: pytest.CaptureFixture[str],
) -> None:
    view = _mixed_view()
    _show(view)
    rendered = capsys.readouterr().out
    lines = rendered.splitlines()
    assert "warnings 2" in lines[0]
    assert "Job 1 · Healthy training" in lines[1]
    assert _DIAGNOSTIC not in lines[1]
    assert "Job 2 · Older training" in lines[2]
    assert "Waiting for GPU capacity" in lines[2]
    assert _DIAGNOSTIC in lines[2]
    assert "Job 3 · Archived training" in lines[3]
    assert "completed (archived)" in lines[3]
    assert _DIAGNOSTIC in lines[3]
    assert all(job.id not in rendered for job in view.jobs)


def test_json_listing_keeps_refresh_diagnostics_separate_from_job_outcomes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    view = _mixed_view()
    _show(view, as_json=True)
    result = json.loads(capsys.readouterr().out)
    assert result["warning_count"] == 2
    assert result["refresh_issues"] == [
        {"job_id": "pending-private-id", "reference": "job-2", "message": _DIAGNOSTIC},
        {"job_id": "archived-private-id", "reference": "job-3", "message": _DIAGNOSTIC},
    ]
    assert [job["state"] for job in result["jobs"]] == ["running", "pending", "completed"]
    assert all(job["error"] is None for job in result["jobs"])
    assert result["jobs"][2]["archived"] is True
    _show(view.model_copy(update={"refresh_issues": ()}), as_json=True)
    repaired = json.loads(capsys.readouterr().out)
    assert repaired["warning_count"] == 0
    assert repaired["refresh_issues"] == []


def test_refresh_diagnostics_use_existing_output_redaction(
    capsys: pytest.CaptureFixture[str],
) -> None:
    gpu = "GPU-12345678-1234-1234-1234-123456789abc"
    claim = "e" * 64
    view = _mixed_view()
    issue = QueueRefreshIssue(
        job_id=view.jobs[1].id,
        message=f"{_DIAGNOSTIC}; device={gpu}; claim-token={claim}",
    )
    view = view.model_copy(update={"refresh_issues": (issue,)})
    presentation = QueuePresentation({gpu: 2}, host_id="host")
    for as_json in (False, True):
        _show(view, as_json=as_json, presentation=presentation)
        rendered = capsys.readouterr().out
        assert _DIAGNOSTIC in rendered
        assert gpu not in rendered
        assert claim not in rendered


class _ViewService:
    identity = WorkerIdentity(owner_uid=7, host_id="host", boot_id="boot")

    def __init__(self) -> None:
        self.view = _mixed_view()
        self.failure = False

    def list(self, *, visibility: QueueVisibility = "main") -> QueueView:
        if self.failure:
            raise RuntimeError("Shared queue manifest is invalid")
        return self.view


def test_tui_warnings_clear_after_refresh_without_losing_selection() -> None:
    pytest.importorskip("textual")
    from textual.widgets import DataTable, Static

    from clearml_yolo.entrypoints.queue_tui import QueueApp

    service = _ViewService()

    async def exercise() -> None:
        application = QueueApp(cast(QueueService, service))
        application.visibility = "all"
        async with application.run_test() as pilot:
            table = application.query_one("#jobs", DataTable)
            rows = [table.get_row_at(index) for index in range(table.row_count)]
            assert len(rows) == 3
            assert _DIAGNOSTIC not in rows[0]
            assert _DIAGNOSTIC in rows[1]
            assert _DIAGNOSTIC in rows[2]
            assert "Waiting for GPU capacity" in rows[1]
            assert "completed (archived)" in rows[2]
            assert "warnings 2" in str(application.query_one("#status", Static).render())
            table.move_cursor(row=1)
            await pilot.pause()
            healthy, pending, archived = service.view.jobs
            service.view = service.view.model_copy(
                update={
                    "revision": 5,
                    "jobs": (
                        pending,
                        healthy.model_copy(update={"progress": 0.75}),
                        archived,
                    ),
                    "refresh_issues": (),
                }
            )
            application.refresh_queue()
            assert table.cursor_row == 0
            assert "Job 2 · Older training" in table.get_row_at(table.cursor_row)
            assert "75%" in table.get_row_at(1)
            assert all(
                _DIAGNOSTIC not in table.get_row_at(index) for index in range(table.row_count)
            )
            assert "warnings 0" in str(application.query_one("#status", Static).render())

    asyncio.run(exercise())


def test_tui_queue_wide_failure_preserves_previously_displayed_rows() -> None:
    pytest.importorskip("textual")
    from textual.widgets import DataTable, Static

    from clearml_yolo.entrypoints.queue_tui import QueueApp

    service = _ViewService()

    async def exercise() -> None:
        application = QueueApp(cast(QueueService, service))
        async with application.run_test() as pilot:
            table = application.query_one("#jobs", DataTable)
            table.move_cursor(row=1)
            await pilot.pause()
            rows = [table.get_row_at(index) for index in range(table.row_count)]
            service.failure = True
            application.refresh_queue()
            assert table.cursor_row == 1
            assert [table.get_row_at(index) for index in range(table.row_count)] == rows
            assert "Queue unavailable" in str(application.query_one("#status", Static).render())

    asyncio.run(exercise())
