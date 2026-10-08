"""Exercise the local command without importing application startup side effects."""

import os
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path

import pytest


def _run(
    directory: Path, *arguments: str, cy_home: str | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.pop("CY_HOME", None)
    if cy_home is not None:
        environment["CY_HOME"] = cy_home
    return subprocess.run(  # noqa: S603 -- fixed interpreter/module and test-owned arguments
        [sys.executable, "-m", "clearml_yolo.entrypoints.dedup", *arguments],
        cwd=directory, env=environment, capture_output=True, text=True, check=False,
    )


def test_help_creates_no_application_directories(tmp_path: Path) -> None:
    result = _run(tmp_path, "--help")
    assert result.returncode == 0, result.stderr
    assert "--dry-run" in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_missing_default_cache_is_an_error_without_creation(tmp_path: Path) -> None:
    result = _run(tmp_path, "--dry-run")
    assert result.returncode == 2
    assert ".cache" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_dry_run_uses_relative_workspace_without_replacing_files(tmp_path: Path) -> None:
    cache = tmp_path / "workspace" / ".cache"
    (cache / "a").mkdir(parents=True)
    (cache / "b").mkdir()
    first, second = cache / "a" / "image.jpg", cache / "b" / "image.jpg"
    first.write_bytes(b"identical image")
    second.write_bytes(b"identical image")
    inodes = (first.stat().st_ino, second.stat().st_ino)
    result = _run(tmp_path, "--dry-run", cy_home="workspace")
    assert result.returncode == 0, result.stderr
    assert "duplicates=1" in result.stdout
    assert "reflinked=0" in result.stdout
    assert "Dry run" in result.stdout
    assert (first.stat().st_ino, second.stat().st_ino) == inodes
    assert sorted(path.name for path in (tmp_path / "workspace").iterdir()) == [".cache"]


def test_explicit_directory_overrides_workspace(tmp_path: Path) -> None:
    cache = tmp_path / "chosen"
    cache.mkdir()
    result = _run(tmp_path, str(cache), cy_home="nonexistent")
    assert result.returncode == 0, result.stderr
    assert "scanned=0" in result.stdout
    assert not (tmp_path / "nonexistent").exists()


def test_installed_command_has_lightweight_entrypoint() -> None:
    entrypoints = [
        item for item in distribution("clearml-yolo").entry_points
        if item.group == "console_scripts" and item.name == "cy-dedup"
    ]
    assert len(entrypoints) == 1
    assert entrypoints[0].load().__module__ == "clearml_yolo.entrypoints.dedup"


def test_operational_failure_reports_nonzero_and_preserves_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from clearml_yolo.adapters.storage import dedup
    from clearml_yolo.entrypoints.dedup import main

    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    source, destination = tmp_path / "a" / "image.png", tmp_path / "b" / "image.png"
    source.write_bytes(b"same bytes")
    destination.write_bytes(b"same bytes")
    inode = destination.stat().st_ino

    def denied(_source: int, _destination: int) -> None:
        raise PermissionError("clone denied")

    monkeypatch.setattr(dedup, "_clone", denied)
    monkeypatch.setattr(sys, "argv", ["cy-dedup", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "failures=1" in output.out
    assert "clone denied" in output.err
    assert destination.stat().st_ino == inode
    assert destination.read_bytes() == b"same bytes"


def test_command_does_not_import_execution_dependencies(tmp_path: Path) -> None:
    script = (
        "import sys; from clearml_yolo.entrypoints.dedup import main; main(); "
        "assert not {'clearml', 'torch', 'ultralytics', 'hydra', "
        "'clearml_yolo.entrypoints.hydra', 'clearml_yolo.entrypoints.composition', "
        "'clearml_yolo.application'} "
        ".intersection(sys.modules)"
    )
    result = subprocess.run(  # noqa: S603 -- fixed script and test-owned directory
        [sys.executable, "-c", script, str(tmp_path), "--dry-run"],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []
