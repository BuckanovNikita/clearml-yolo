"""Required result publication runs before the invocation completion barrier."""

from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.adapters.clearml import session
from test_clearml_session import FakeTask
from test_clearml_session import fake_clearml as owner_fixture

owner = owner_fixture


def test_finalizer_uploads_before_expectations_are_checked(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    path = tmp_path / "durable.csv"
    path.write_text("value\n1\n")
    with session.invocation(session.ClearMLConfig(), "pipeline"):
        session.expect_artifacts(task, ["predicts_csv"])
        session.register_finalizer(
            task, lambda: session.upload_artifact(task, "predicts_csv", path)
        )
        assert not task.uploads
    assert task.completed
    assert [item["name"] for item in task.uploads] == ["predicts_csv"]


def test_failed_finalizer_preserves_diagnostics_and_fails_task(
    owner: tuple[type[Any], FakeTask], tmp_path: Path
) -> None:
    _, task = owner
    path = tmp_path / "durable.csv"
    path.write_text("value\n1\n")
    task.upload_result = False
    with (
        pytest.raises(session.ArtifactUploadError),
        session.invocation(session.ClearMLConfig(), "pipeline"),
    ):
        session.register_finalizer(
            task, lambda: session.upload_artifact(task, "predicts_csv", path)
        )
    assert path.is_file()
    assert task.failed
    assert not task.completed


def test_resources_are_shared_only_within_one_invocation(
    owner: tuple[type[Any], FakeTask],
) -> None:
    _, task = owner
    with session.invocation(session.ClearMLConfig(), "pipeline"):
        first = session.invocation_resource(task, "bundle", list[str])
        first.append("context")
        with session.invocation(session.ClearMLConfig(), "metrics"):
            assert session.invocation_resource(task, "bundle", list[str]) == ["context"]
    with session.invocation(session.ClearMLConfig(), "pipeline"):
        assert session.invocation_resource(task, "bundle", list[str]) == []
