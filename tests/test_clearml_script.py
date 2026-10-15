"""Exercise source metadata against real disposable Git repositories."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.clearml import script
from test_clearml_session import FakeTask


def _git(root: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    return subprocess.check_output(  # noqa: S603 - fixed commands in test-owned repos
        [executable, "-C", str(root), *arguments],
        env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        | {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "source"
    source = root / "src/clearml_yolo/adapters/clearml/script.py"
    source.parent.mkdir(parents=True)
    source.write_text("# source identity fixture\n")
    _git(root, "init", "-b", "experiment")
    _git(root, "config", "user.name", "Metadata Test")
    _git(root, "config", "user.email", "metadata@example.test")
    _git(root, "add", "src")
    _git(root, "commit", "-m", "fixture")
    _git(root, "remote", "add", "origin", "https://example.test/team/detector.git")
    monkeypatch.setattr(script, "__file__", str(source))
    return root


def test_source_metadata_ignores_launch_directory_arguments_and_dirty_contents(
    checkout: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_commit = _git(checkout, "rev-parse", "HEAD")
    (checkout / "src/clearml_yolo/adapters/clearml/script.py").write_text(
        "password = 'uncommitted-secret'\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["/outside/bin/cy-ground-truth", "token=argument-secret"])
    task = FakeTask()
    script.publish_script(task, "ground_truth")

    assert task.script == {
        "repository": "https://example.test/team/detector.git",
        "branch": "experiment",
        "version_num": expected_commit,
        "entry_point": "-m clearml_yolo.entrypoints.ground_truth",
        "working_dir": ".",
        "diff": "",
    }


def test_git_worktree_and_detached_head_preserve_exact_commit(
    checkout: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = _git(checkout, "rev-parse", "HEAD")
    worktree = tmp_path / "linked"
    _git(checkout, "worktree", "add", "--detach", str(worktree), commit)
    source = worktree / "src/clearml_yolo/adapters/clearml/script.py"
    monkeypatch.setattr(script, "__file__", str(source))
    task = FakeTask()
    script.publish_script(task, "pipeline")
    assert task.script["version_num"] == commit
    assert task.script["branch"] == "HEAD"
    assert task.script["entry_point"] == "-m clearml_yolo.entrypoints.pipeline"


def test_inherited_git_environment_cannot_override_source_checkout(
    checkout: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-b", "other-branch")
    _git(other, "remote", "add", "origin", "https://example.test/other.git")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git/index"))
    task = FakeTask()
    script.publish_script(task, "train")
    assert task.script["repository"] == "https://example.test/team/detector.git"
    assert task.script["version_num"] == _git(checkout, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://user:private-token@example.test/repo.git", "https://example.test/repo.git"),
        ("https://private-token@example.test/repo.git", "https://example.test/repo.git"),
        ("ssh://git@example.test/repo.git", "ssh://git@example.test/repo.git"),
        ("ssh://git:private-token@example.test/repo.git", "ssh://git@example.test/repo.git"),
        ("git+ssh://git@example.test/repo.git", "git+ssh://git@example.test/repo.git"),
        ("ssh://git@[2001:db8::1]:2222/repo.git", "ssh://git@[2001:db8::1]:2222/repo.git"),
        ("https://user:secret@[2001:db8::1]/repo.git", "https://[2001:db8::1]/repo.git"),
        ("git@example.test:team/repo.git", "git@example.test:team/repo.git"),
        (
            "https://user:secret@example.test/repo.git?token=secret&ref=main",
            "https://example.test/repo.git?token=%3Credacted%3E&ref=main",
        ),
    ],
)
def test_origin_preserves_transport_and_removes_credentials(
    checkout: Path, origin: str, expected: str
) -> None:
    _git(checkout, "remote", "set-url", "origin", origin)
    task = FakeTask()
    script.publish_script(task, "train")
    assert task.script["repository"] == expected


def test_missing_origin_does_not_invent_repository(checkout: Path) -> None:
    _git(checkout, "remote", "remove", "origin")
    task = FakeTask()
    script.publish_script(task, "predict")
    assert task.script["repository"] == ""
    assert task.script["version_num"] == _git(checkout, "rev-parse", "HEAD")


def test_wheel_inside_unrelated_checkout_does_not_claim_its_git_identity(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = checkout / ".venv/lib/python3.12/site-packages/clearml_yolo/adapters/clearml/script.py"
    module.parent.mkdir(parents=True)
    module.write_text("# installed wheel\n")
    monkeypatch.setattr(script, "__file__", str(module))
    task = FakeTask()
    script.publish_script(task, "metrics")
    assert task.script == {
        "entry_point": "-m clearml_yolo.entrypoints.metrics",
        "working_dir": ".",
        "diff": "",
    }


def test_unavailable_git_does_not_prevent_module_publication(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("clearml_yolo.adapters.clearml.script.shutil.which", lambda _name: None)
    task = FakeTask()
    script.publish_script(task, "report")
    assert task.script["repository"] == task.script["branch"] == task.script["version_num"] == ""
    assert task.script["entry_point"] == "-m clearml_yolo.entrypoints.report"


def test_remote_replay_does_not_read_local_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden() -> dict[str, str]:
        pytest.fail("Remote replay must preserve its existing script metadata")

    monkeypatch.setattr(script, "_source_identity", forbidden)
    task = FakeTask()
    task.local = False
    task.script = {"repository": "remote-repo", "entry_point": "remote.py"}
    script.publish_script(task, "train")
    assert task.script == {"repository": "remote-repo", "entry_point": "remote.py"}


def test_rejected_script_write_is_detected_by_readback(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = FakeTask()
    monkeypatch.setattr(task, "set_script", lambda **_kwargs: None)
    with pytest.raises(RuntimeError, match="did not retain script metadata field"):
        script.publish_script(task, "val")


def test_readback_failure_cannot_validate_cached_script(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = FakeTask()

    def unavailable(_field: str) -> None:
        raise RuntimeError("Fresh script read unavailable")

    monkeypatch.setattr(task, "_reload_field", unavailable)
    with pytest.raises(RuntimeError, match="Fresh script read unavailable"):
        script.publish_script(task, "train")
    assert task.script["version_num"] == _git(checkout, "rev-parse", "HEAD")


def test_persisted_script_must_match_even_when_cached_script_is_correct(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = FakeTask()
    saved = SimpleNamespace(to_dict=lambda: {"repository": "previous-repository"})
    monkeypatch.setattr(task, "_reload_field", lambda _field: saved)
    with pytest.raises(RuntimeError, match="did not retain script metadata field 'repository'"):
        script.publish_script(task, "predict")
    assert task.script["repository"] == "https://example.test/team/detector.git"


@pytest.mark.parametrize("error", [OSError("private-error"), subprocess.TimeoutExpired("git", 5)])
def test_git_failures_leave_identity_unavailable(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> None:
        raise error

    monkeypatch.setattr("clearml_yolo.adapters.clearml.script.subprocess.run", fail)
    task = FakeTask()
    script.publish_script(task, "export")
    assert task.script["repository"] == task.script["branch"] == task.script["version_num"] == ""
