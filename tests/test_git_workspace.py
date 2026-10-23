"""Real Git membership and experiment startup diagnostics."""

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from loguru import logger

_WARNING = "Git working tree could not be verified"
_COMMANDS = (
    "cy",
    "cy-train",
    "cy-predict",
    "cy-val",
    "cy-metrics",
    "cy-report",
    "cy-compare",
    "cy-export",
    "cy-ground-truth",
)


def _environment(root: Path) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "CY_"))
    }
    environment["CY_HOME"] = str(root)
    return environment


def _run(
    arguments: list[str], cwd: Path, *, root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed commands and test-owned paths, no shell
        arguments,
        cwd=cwd,
        env=_environment(root or cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
    )


def _git(root: Path, *arguments: str) -> None:
    executable = shutil.which("git")
    assert executable is not None, "Git is required for real working-tree fixtures"
    result = _run(
        [
            executable,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            *arguments,
        ],
        root,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def messages() -> Iterator[list[str]]:
    captured: list[str] = []
    sink = logger.add(captured.append, format="{message}", level="WARNING")
    try:
        yield captured
    finally:
        logger.remove(sink)


@pytest.mark.parametrize("command", _COMMANDS)
@pytest.mark.parametrize("arguments", [("--help",), ("--cfg", "job")])
def test_experiment_inspection_warns_once_without_changing_stdout_or_status(
    tmp_path: Path, command: str, arguments: tuple[str, ...]
) -> None:
    executable = str(Path(sys.executable).with_name(command))
    outside = _run([executable, *arguments], tmp_path)
    assert outside.returncode == 0, outside.stderr
    assert outside.stderr.count(_WARNING) == 1
    assert _WARNING not in outside.stdout
    assert "git init" in outside.stderr
    assert "Continuing" in outside.stderr
    assert not (tmp_path / ".git").exists()

    _git(tmp_path, "init", "--quiet")
    inside = _run([executable, *arguments], tmp_path)
    assert inside.returncode == outside.returncode, inside.stderr
    assert _WARNING not in inside.stderr
    assert inside.stdout == outside.stdout


@pytest.mark.parametrize("kind", ["unborn", "nested", "worktree", "submodule"])
def test_valid_working_trees_are_quiet(
    tmp_path: Path, kind: str, messages: list[str]
) -> None:
    from clearml_yolo.adapters.runtime.git_workspace import warn_if_unversioned_launch

    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    directory = repository
    if kind == "nested":
        directory = repository / "nested" / "directory"
        directory.mkdir(parents=True)
    elif kind in {"worktree", "submodule"}:
        _git(repository, "commit", "--quiet", "--allow-empty", "-m", "fixture")
        directory = tmp_path / kind
        if kind == "worktree":
            _git(repository, "worktree", "add", "--quiet", "--detach", str(directory))
        else:
            directory = repository / "submodule"
            _git(
                repository,
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "--quiet",
                str(repository),
                str(directory),
            )
        assert (directory / ".git").is_file()
    warn_if_unversioned_launch(directory)
    assert messages == []


@pytest.mark.parametrize("bare", [False, True])
def test_non_working_tree_warns_without_writing_git(
    tmp_path: Path, bare: bool, messages: list[str]
) -> None:
    from clearml_yolo.adapters.runtime.git_workspace import warn_if_unversioned_launch

    if bare:
        _git(tmp_path, "init", "--quiet", "--bare")
    before = set(tmp_path.rglob("*"))
    warn_if_unversioned_launch(tmp_path)
    assert len(messages) == 1
    assert _WARNING in messages[0]
    assert str(tmp_path) in messages[0]
    assert set(tmp_path.rglob("*")) == before


@pytest.mark.parametrize("inside", [False, True])
def test_launch_cwd_wins_over_cy_home_and_git_overrides(
    tmp_path: Path, inside: bool, monkeypatch: pytest.MonkeyPatch, messages: list[str]
) -> None:
    from clearml_yolo.adapters.runtime.git_workspace import warn_if_unversioned_launch

    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    directory, other = (repository, tmp_path) if inside else (tmp_path, repository)
    monkeypatch.setenv("CY_HOME", str(other))
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(repository))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    warn_if_unversioned_launch(directory)
    assert len(messages) == (0 if inside else 1)


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError("fixture"),
        PermissionError("fixture"),
        subprocess.TimeoutExpired("git", 5),
        subprocess.CompletedProcess(["git"], 128, b"", b"private diagnostic"),
        subprocess.CompletedProcess(["git"], 0, b"unexpected\xff", b""),
    ],
)
def test_git_failures_remain_advisory(
    tmp_path: Path,
    failure: OSError | subprocess.TimeoutExpired | subprocess.CompletedProcess[bytes],
    messages: list[str],
) -> None:
    from clearml_yolo.adapters.runtime import git_workspace

    with patch.object(shutil, "which", return_value="/git"), patch.object(
        subprocess, "run"
    ) as probe:
        if isinstance(failure, subprocess.CompletedProcess):
            probe.return_value = failure
        else:
            probe.side_effect = failure
        git_workspace.warn_if_unversioned_launch(tmp_path)
    assert probe.call_args.kwargs["timeout"] == 5
    assert len(messages) == 1
    assert _WARNING in messages[0]
    assert "private diagnostic" not in messages[0]
    assert "Continuing" in messages[0]


def test_missing_git_warns_without_spawning(tmp_path: Path, messages: list[str]) -> None:
    from clearml_yolo.adapters.runtime import git_workspace

    with patch.object(shutil, "which", return_value=None), patch.object(
        subprocess, "run"
    ) as probe:
        git_workspace.warn_if_unversioned_launch(tmp_path)
    probe.assert_not_called()
    assert len(messages) == 1
    assert "Git is unavailable" in messages[0]


def test_multirun_warns_once_before_hydra_chdir_and_continues(tmp_path: Path) -> None:
    workspace = tmp_path / "outputs"
    workspace.mkdir()
    _git(workspace, "init", "--quiet")
    script = """
from clearml_yolo.entrypoints.hydra import common
from pathlib import Path
common.execute_owned = lambda *args: print('WORKFLOW_STARTED ' + str(Path.cwd()), flush=True)
common.launch('pipeline', lambda: None)
"""
    result = _run(
        [
            sys.executable,
            "-c",
            script,
            "-m",
            "ultralytics.epochs=1,2",
            "hydra.job.chdir=true",
        ],
        tmp_path,
        root=workspace,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr.count(_WARNING) == 1
    assert result.stdout.count("WORKFLOW_STARTED") == 2
    assert str(tmp_path) in result.stderr
    assert _WARNING not in result.stdout


@pytest.mark.parametrize("command", ["cy-init-config", "cy-dedup"])
def test_administration_help_does_not_warn(tmp_path: Path, command: str) -> None:
    result = _run([str(Path(sys.executable).with_name(command)), "--help"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert _WARNING not in result.stderr
