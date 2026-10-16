"""Human queue views remain useful while machine identities stay exact."""

import json
import re
import subprocess
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest

from clearml_yolo.core.queue import PublicJob, QueueView, ResourceRequest
from queue_cli_helpers import queue_command, queue_environment


def _job() -> PublicJob:
    return PublicJob(
        id=str(uuid4()),
        owner_uid=7,
        host_id="a" * 64,
        boot_id=str(uuid4()),
        command="pipeline",
        request=ResourceRequest(gpus=1),
        label="Training experiment",
        submitted_at=0,
        submission_sequence=17,
        clearml_url="https://clearml.example/projects/project/experiments/" + "b" * 32,
    )


def test_default_listing_names_job_and_json_retains_identity(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from clearml_yolo.entrypoints.queue import _show

    job = _job()
    view = QueueView(host_id=job.host_id, revision=2, jobs=(job,))
    _show(view)
    text = capsys.readouterr().out
    assert "Job 17" in text
    assert "Training experiment" in text
    assert job.id not in text
    assert job.host_id not in text
    _show(view, as_json=True)
    document = json.loads(capsys.readouterr().out)
    assert document["host_id"] == job.host_id
    assert document["jobs"][0]["id"] == job.id
    assert document["jobs"][0]["boot_id"] == job.boot_id
    assert document["jobs"][0]["clearml_url"] == job.clearml_url
    assert document["jobs"][0]["reference"] == "job-17"


@pytest.mark.parametrize("action", ["archive", "restore"])
def test_archive_commands_accept_multiple_readable_references(action: str) -> None:
    from clearml_yolo.entrypoints.queue import _parser

    arguments = _parser().parse_args([action, "job-17", "job-18", "--json"])
    assert arguments.job_ids == ["job-17", "job-18"]
    assert arguments.json is True


def test_listing_modes_and_submit_label_are_explicit() -> None:
    from clearml_yolo.entrypoints.queue import _parser

    parser = _parser()
    assert parser.parse_args(["list", "--archived"]).visibility == "archived"
    assert parser.parse_args(["list", "--all"]).visibility == "all"
    assert parser.parse_args(["list"]).visibility == "main"
    with pytest.raises(SystemExit):
        parser.parse_args(["list", "--all", "--archived"])
    arguments = parser.parse_args(["submit", "--gpus", "1", "--label", "Experiment", "--json"])
    assert arguments.label == "Experiment"
    assert arguments.json is True


def test_fallback_gpu_labels_are_words_not_hashes() -> None:
    from clearml_yolo.core.gpu_identity import identity_label

    first = "GPU-" + str(uuid4())
    second = "GPU-" + str(uuid4())
    label = identity_label(first)
    assert re.fullmatch(r"gpu-(?:[a-z]+-)+[a-z]+", label)
    assert label == identity_label(first)
    assert label != identity_label(second)


def test_config_inspection_is_read_only_and_help_needs_no_config(tmp_path: Path) -> None:
    environment = queue_environment(tmp_path)
    command = queue_command(tmp_path)
    inspected = subprocess.run(  # noqa: S603 - isolated real CLI
        [*command, "config", "--json"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert inspected.returncode == 0, inspected.stderr
    values = json.loads(inspected.stdout)
    assert values["root"] == str(tmp_path / "queue")
    assert values["coordination_root"] == str(tmp_path / "locks")
    assert values["root_source"] == "config"
    assert {p.name for p in tmp_path.iterdir()} == {"queue.toml"}
    environment.pop("CY_QUEUE_CONFIG")
    for arguments, expected in ((["--help"], 0), (["list"], 1)):
        result = subprocess.run(  # noqa: S603 - isolated real CLI
            [*command, *arguments],
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == expected
        if expected:
            assert "CY_QUEUE_CONFIG" in result.stderr


def test_real_cli_readable_submit_archive_restore(tmp_path: Path) -> None:
    environment = queue_environment(tmp_path)
    command = queue_command(tmp_path)

    def run(*arguments: str) -> str:
        result = subprocess.run(  # noqa: S603 - isolated real CLI
            [*command, *arguments],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    submitted = run(
        "submit", "--gpus", "1", "--label", "Old experiment", "--", "ground_truth=input.csv"
    )
    assert submitted == "Submitted Job 1 · Old experiment\n"
    original = json.loads(run("list", "--json"))["jobs"][0]
    assert original["id"] not in submitted
    assert "Job 1 · Old experiment: cancelled" in run("cancel", "job-1")
    assert "Archived 1 job" in run("archive", "job-1", original["id"])
    main = json.loads(run("list", "--json"))
    assert main["jobs"] == []
    assert main["archived_count"] == 1
    archived = json.loads(run("list", "--archived", "--json"))["jobs"]
    assert archived[0]["id"] == original["id"]
    assert archived[0]["archived"] is True
    all_jobs = run("list", "--all")
    assert "Job 1 · Old experiment" in all_jobs
    assert "cancelled (archived)" in all_jobs
    assert "Restored 1 job" in run("restore", "job-1")
    restored = json.loads(run("list", "--json"))["jobs"][0]
    assert restored["id"] == original["id"]
    assert restored["archived"] is False


def test_tui_task_links_preserve_targets_and_reject_malformed_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("textual")
    from clearml_yolo.application.queue import QueueService
    from clearml_yolo.core.queue import WorkerIdentity
    from clearml_yolo.entrypoints import queue_tui

    class Service:
        identity = WorkerIdentity(owner_uid=7, host_id="host", boot_id="boot")

    app = queue_tui.QueueApp(cast(QueueService, Service()))
    job = _job()
    monkeypatch.setattr(app, "_selected", lambda: job)
    opened: list[str] = []

    def open_browser(url: str) -> bool:
        opened.append(url)
        return True

    notices: list[str] = []
    monkeypatch.setattr("webbrowser.open", open_browser)
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notices.append(message))
    app.action_open_task()
    assert opened == [job.clearml_url]
    for target in ("http://[", "javascript:alert(1)", "https:"):
        job = job.model_copy(update={"clearml_url": target})
        app.action_open_task()
    assert len(opened) == 1
    assert notices == ["Task link is unavailable"] * 3
