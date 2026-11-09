"""The release commit guard accepts only a root-version change of the staged files."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(ROOT))
    from scripts import release_lock_guard

PYPROJECT = """[project]
name = "clearml-yolo"
version = "{version}"
dependencies = ["digital-metrics"]
"""
ROOT_ENTRY = """[[package]]
name = "clearml-yolo"
version = "{version}"
source = {{ editable = "." }}
dependencies = [{{ name = "digital-metrics" }}]
"""
METRICS_ENTRY = """[[package]]
name = "digital-metrics"
version = "0.1.0"
source = {{ editable = "external/digital-metrics" }}
"""
EXTRA_ENTRY = """[[package]]
name = "extra"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }
"""


def _lock(version: str, *, metrics: str = METRICS_ENTRY, extra: bool = False) -> str:
    entries = [ROOT_ENTRY.format(version=version), metrics.format()]
    if extra:
        entries.append(EXTRA_ENTRY)
    return "version = 1\nrevision = 3\n\n" + "\n".join(entries)


def _git(root: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - fixed Git arguments in a test-owned repository
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )


def _script(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - this repository's script under the test interpreter
        [sys.executable, ROOT / "scripts" / "release_lock_guard.py"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _stage(root: Path, *, pyproject: str, lock: str) -> None:
    (root / "pyproject.toml").write_text(pyproject)
    (root / "uv.lock").write_text(lock)
    _git(root, "add", "pyproject.toml", "uv.lock")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "master")
    _stage(tmp_path, pyproject=PYPROJECT.format(version="0.4.0"), lock=_lock("0.4.0", extra=True))
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_root_version_change_passes(repo: Path) -> None:
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0", extra=True))

    assert release_lock_guard.check(repo) == []


def test_external_revision_change_fails(repo: Path) -> None:
    moved = METRICS_ENTRY.replace("0.1.0", "0.2.0")
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0", metrics=moved, extra=True))

    assert release_lock_guard.check(repo) == [
        "uv.lock package added: digital-metrics 0.2.0",
        "uv.lock package removed: digital-metrics 0.1.0",
    ]


def test_changed_package_source_fails(repo: Path) -> None:
    moved = METRICS_ENTRY.replace("external/digital-metrics", "../digital-metrics")
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0", metrics=moved, extra=True))

    assert release_lock_guard.check(repo) == ["uv.lock package changed: digital-metrics 0.1.0"]


def test_added_package_fails(repo: Path) -> None:
    _stage(repo, pyproject=PYPROJECT.format(version="0.4.0"), lock=_lock("0.4.0"))
    _git(repo, "commit", "-q", "-m", "without extra")
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0", extra=True))

    assert release_lock_guard.check(repo) == ["uv.lock package added: extra 2.0.0"]


def test_removed_package_fails(repo: Path) -> None:
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0"))

    assert release_lock_guard.check(repo) == ["uv.lock package removed: extra 2.0.0"]


def test_root_dependency_change_fails(repo: Path) -> None:
    lock = _lock("0.5.0", extra=True).replace('dependencies = [{ name = "digital-metrics" }]', "dependencies = []")
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=lock)

    assert release_lock_guard.check(repo) == ["uv.lock clearml-yolo field 'dependencies' changed"]


def test_lock_header_change_fails(repo: Path) -> None:
    lock = _lock("0.5.0", extra=True).replace("revision = 3", "revision = 4")
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=lock)

    assert release_lock_guard.check(repo) == ["uv.lock top-level key 'revision' changed"]


def test_lock_version_must_match_project(repo: Path) -> None:
    _stage(repo, pyproject=PYPROJECT.format(version="0.6.0"), lock=_lock("0.5.0", extra=True))

    assert release_lock_guard.check(repo) == ["staged uv.lock clearml-yolo version 0.5.0 differs from project 0.6.0"]


def test_staged_source_override_fails(repo: Path) -> None:
    override = '\n[tool.uv.sources]\ndigital-metrics = { path = "external/digital-metrics" }\n'
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0") + override, lock=_lock("0.5.0", extra=True))

    assert release_lock_guard.check(repo) == [
        "staged pyproject.toml contains [tool.uv.sources]; releases carry no local overrides",
        "staged pyproject.toml differs from HEAD beyond project.version in: tool",
    ]


def test_pyproject_dependency_change_fails(repo: Path) -> None:
    pyproject = PYPROJECT.format(version="0.5.0").replace('["digital-metrics"]', '["digital-metrics>=1"]')
    _stage(repo, pyproject=pyproject, lock=_lock("0.5.0", extra=True))

    assert release_lock_guard.check(repo) == [
        "staged pyproject.toml differs from HEAD beyond project.version in: project"
    ]


def test_unstaged_changes_are_not_inspected(repo: Path) -> None:
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0", extra=True))
    (repo / "uv.lock").write_text(_lock("0.5.0"))

    assert release_lock_guard.check(repo) == []


def test_command_exit_status_and_messages(repo: Path) -> None:
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0", extra=True))
    passed = _script(repo)
    _stage(repo, pyproject=PYPROJECT.format(version="0.5.0"), lock=_lock("0.5.0"))
    failed = _script(repo)

    assert (passed.returncode, failed.returncode) == (0, 1)
    assert failed.stderr == "release_lock_guard: uv.lock package removed: extra 2.0.0\n"
