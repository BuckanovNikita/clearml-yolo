"""The pre-commit guard tolerates only the documented [tool.uv.sources] override."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(ROOT))
    from scripts import source_override

PYPROJECT = b"""[project]
name = "demo"
version = "1.0.0"

# Release settings stay byte-exact.
[tool.semantic_release]
tag_format = "v{version}"
"""
OVERRIDE = b"""
[tool.uv.sources]
digital-metrics = { path = "external/digital-metrics", editable = true }
"""
LOCK = b'version = 1\n\n[[package]]\nname = "demo"\nversion = "1.0.0"\n'


def _git(root: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - fixed Git arguments in a test-owned repository
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )


def _script(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - this repository's script under the test interpreter
        [sys.executable, ROOT / "scripts" / "source_override.py"], cwd=cwd, capture_output=True, text=True, check=False
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "master")
    (tmp_path / "pyproject.toml").write_bytes(PYPROJECT)
    (tmp_path / "uv.lock").write_bytes(LOCK)
    (tmp_path / "module.py").write_text("VALUE = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_clean_tree_is_tolerated(repo: Path) -> None:
    assert source_override.refusal(repo) is None


def test_appended_sources_override_is_tolerated(repo: Path) -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT + OVERRIDE)

    assert source_override.refusal(repo) is None


def test_override_between_tables_and_lockfile_are_tolerated(repo: Path) -> None:
    project, settings = PYPROJECT.split(b"\n# Release")
    (repo / "pyproject.toml").write_bytes(project + OVERRIDE + b"\n# Release" + settings)
    (repo / "uv.lock").write_bytes(LOCK + b'source = { editable = "." }\n')

    assert source_override.refusal(repo) is None


def test_source_subtable_is_part_of_the_override(repo: Path) -> None:
    subtable = b'\n[tool.uv.sources.report-generator]\npath = "external/report-generator"\n'
    (repo / "pyproject.toml").write_bytes(PYPROJECT + OVERRIDE + subtable)

    assert source_override.refusal(repo) is None


def test_edit_outside_sources_is_refused(repo: Path) -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT.replace(b"1.0.0", b"1.0.1") + OVERRIDE)

    assert source_override.refusal(repo) == "pyproject.toml differs from the index outside [tool.uv.sources]"


def test_comment_edit_outside_sources_is_refused(repo: Path) -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT.replace(b"byte-exact", b"exact"))

    assert source_override.refusal(repo) is not None


def test_invalid_toml_override_is_refused(repo: Path) -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT + b"\n[tool.uv.sources]\nbroken = {\n")

    assert source_override.refusal(repo) is not None


def test_other_unstaged_path_is_refused(repo: Path) -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT + OVERRIDE)
    (repo / "module.py").write_text("VALUE = 2\n")

    assert source_override.refusal(repo) == "not a source override: module.py"


def test_lockfile_without_pyproject_override_is_refused(repo: Path) -> None:
    (repo / "uv.lock").write_bytes(LOCK + b"\n")

    assert source_override.refusal(repo) == "uv.lock changed without a pyproject.toml source override"


def test_deleted_pyproject_is_refused(repo: Path) -> None:
    (repo / "pyproject.toml").unlink()

    assert source_override.refusal(repo) == "pyproject.toml is deleted in the working tree"


def test_staged_override_leaves_nothing_to_tolerate(repo: Path) -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT + OVERRIDE)
    _git(repo, "add", "pyproject.toml")

    assert source_override.refusal(repo) is None


def test_comparison_uses_the_index_not_head(repo: Path) -> None:
    staged = PYPROJECT.replace(b"1.0.0", b"1.1.0")
    (repo / "pyproject.toml").write_bytes(staged)
    _git(repo, "add", "pyproject.toml")
    (repo / "pyproject.toml").write_bytes(staged + OVERRIDE)

    assert source_override.refusal(repo) is None


def test_command_exit_status_reports_the_decision(repo: Path) -> None:
    (repo / "pyproject.toml").write_bytes(PYPROJECT + OVERRIDE)
    tolerated = _script(repo)
    (repo / "module.py").write_text("VALUE = 3\n")
    refused = _script(repo)

    assert (tolerated.returncode, refused.returncode) == (0, 1)
    assert "module.py" in refused.stderr
