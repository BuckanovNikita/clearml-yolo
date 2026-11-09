"""Changed-function mapping and exit statuses of scripts/mutation.py, without running mutmut."""

import subprocess
import tempfile
import textwrap
from collections.abc import Sequence
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(ROOT))
    from scripts import mutation

MODULE = "src/clearml_yolo/core/sample.py"
ORIGINAL = textwrap.dedent(
    """\
    def first(value: int) -> int:
        return value + 1


    def second(value: int) -> int:
        return value * 2


    class Box:
        def size(self) -> int:
            return 3

        @staticmethod
        def make() -> "Box":
            return Box()

        @property
        def label(self) -> str:
            return "box"
    """
)
PYPROJECT = '[project]\nname = "sample"\n\n[tool.mutmut]\nsource_paths = ["src/clearml_yolo"]\n'


GIT_IDENTITY = (
    "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
    "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
)  # fmt: skip


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed program in a throwaway repository
        ["git", *GIT_IDENTITY, *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A committed repository with one package module, pointed at by the driver."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "master")
    _write(root, "pyproject.toml", PYPROJECT)
    _write(root, MODULE, ORIGINAL)
    _write(root, "src/clearml_yolo/__init__.py", "def version() -> str:\n    return '0'\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "initial")
    (root / "external").mkdir()
    monkeypatch.setattr(mutation, "REPO_ROOT", root)
    return root


def _stage(repo: Path, path: str, text: str) -> None:
    _write(repo, path, text)
    _git(repo, "add", path)


class FakeMutmut:
    """Replace the mutmut process boundary and record how it was driven."""

    def __init__(self, status: int | None = 0, tail: str = "", results: str = "") -> None:
        self.status, self.tail, self.results = status, tail, results
        self.run_args: list[str] = []
        self.pyproject = ""
        self.env: dict[str, str] = {}
        self.external_linked = False

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(mutation, "mutmut_binary", lambda: Path("/fake/mutmut"))
        monkeypatch.setattr(mutation, "run_mutmut", self.run)
        monkeypatch.setattr(mutation, "mutmut_results", lambda *_: self.results)
        monkeypatch.setattr(mutation.ShowFn, "__call__", lambda _self, name: f"diff of {name}")

    def run(
        self, binary: Path, workspace: Path, env: dict[str, str], args: Sequence[str], budget_seconds: float = 0
    ) -> tuple[int | None, str]:
        self.run_args = list(args)
        self.pyproject = (workspace / "pyproject.toml").read_text(encoding="utf-8")
        self.env = env
        self.external_linked = (workspace / "external").is_symlink()
        return self.status, self.tail


def test_module_names_follow_mutmut_src_layout() -> None:
    assert mutation.module_name("src/clearml_yolo/core/policy.py") == "clearml_yolo.core.policy"
    assert mutation.module_name("src/clearml_yolo/core/__init__.py") == "clearml_yolo.core"


def test_targets_map_changed_lines_to_mutable_top_level_functions_and_methods() -> None:
    every = mutation.targets_for(MODULE, ORIGINAL, None)
    assert [(target.qualname, target.name) for target in every] == [
        ("first", "clearml_yolo.core.sample.x_first"),
        ("second", "clearml_yolo.core.sample.x_second"),
        ("Box.size", "clearml_yolo.core.sample.xǁBoxǁsize"),
        ("Box.make", "clearml_yolo.core.sample.xǁBoxǁmake"),
    ]
    changed = mutation.targets_for(MODULE, ORIGINAL, {6, 14})
    assert [target.qualname for target in changed] == ["second", "Box.make"]
    assert changed[0].glob == "clearml_yolo.core.sample.x_second*"
    assert mutation.targets_for(MODULE, ORIGINAL, {18, 19}) == []


def test_package_init_functions_use_the_package_name() -> None:
    (target,) = mutation.targets_for("src/clearml_yolo/__init__.py", "def version():\n    return '0'\n", {2})
    assert target.name == "clearml_yolo.x_version"


def test_changed_lines_compare_the_index_with_head(repo: Path) -> None:
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    _write(repo, MODULE, ORIGINAL.replace("value + 1", "value + 5"))  # unstaged: ignored
    _stage(repo, "scripts/tool.py", "def other():\n    return 1\n")
    assert mutation.changed_lines("HEAD") == {MODULE: {6}}


def test_pure_deletion_marks_both_sides_of_the_gap(repo: Path) -> None:
    _stage(repo, MODULE, ORIGINAL.replace("    return value * 2\n", ""))
    assert mutation.changed_lines("HEAD") == {MODULE: {5, 6}}


def test_base_uses_the_merge_base_not_the_moving_branch(repo: Path) -> None:
    _git(repo, "switch", "-q", "-c", "feature")
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    _git(repo, "commit", "-q", "-m", "feature change")
    _git(repo, "switch", "-q", "master")
    _stage(repo, MODULE, ORIGINAL.replace("value + 1", "value + 7"))
    _git(repo, "commit", "-q", "-m", "master moves on")
    _git(repo, "switch", "-q", "feature")
    assert mutation.changed_lines("master") == {MODULE: {6}}


def test_no_changed_function_succeeds_with_nothing_to_do(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    _stage(repo, MODULE, ORIGINAL.replace('return "box"', 'return "crate"'))
    assert mutation.main([]) == 0
    assert "nothing to do" in capsys.readouterr().out
    assert fake.run_args == []


def test_run_narrows_the_copy_and_scrubs_the_child_environment(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("CLEARML_API_HOST", "INFRA_RUN_TAG", "CY_RUN_TAG", "MINIO_ROOT_USER", "GIT_TEST_SCRUB"):
        monkeypatch.setenv(name, "leak")
    monkeypatch.setenv("KEEP_ME", "1")
    results = (
        "clearml_yolo.core.sample.x_second__mutmut_1: killed\n"
        "clearml_yolo.core.sample.x_second__mutmut_2: not checked\n"
        "clearml_yolo.core.sample.x_first__mutmut_1: survived\n"
    )
    fake = FakeMutmut(results=results)
    fake.install(monkeypatch)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main(["--strict", "--max-children", "2"]) == 0
    assert fake.run_args == ["--max-children", "2", "clearml_yolo.core.sample.x_second*"]
    assert f'only_mutate = ["{MODULE}"]\nuse_git_change_detection = false\n' in fake.pyproject
    assert fake.external_linked
    assert fake.env["KEEP_ME"] == "1"
    assert not [name for name in fake.env if name.startswith(mutation.SCRUBBED_PREFIXES)]
    assert fake.env["PYTEST_DEBUG_TEMPROOT"].endswith(".pytest-temproot")
    assert "killed: 1, survived: 0, not reached by tests: 0, not run (budget): 1" in capsys.readouterr().out


@pytest.mark.parametrize(("strict", "expected"), [(False, 0), (True, 1)])
def test_survivors_are_advisory_unless_strict(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], strict: bool, expected: int
) -> None:
    FakeMutmut(results="clearml_yolo.core.sample.x_second__mutmut_1: survived\n").install(monkeypatch)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main(["--strict"] if strict else []) == expected
    assert "diff of clearml_yolo.core.sample.x_second__mutmut_1" in capsys.readouterr().out


@pytest.mark.parametrize(("strict", "expected"), [(False, 0), (True, 1)])
def test_unreached_functions_are_advisory_unless_strict(
    repo: Path, monkeypatch: pytest.MonkeyPatch, strict: bool, expected: int
) -> None:
    FakeMutmut(status=1, tail=f"Stopping early, because we {mutation.NO_TESTS}.").install(monkeypatch)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main(["--strict"] if strict else []) == expected


def test_unmatched_filter_means_no_mutants(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    FakeMutmut(status=1, tail=f"AssertionError: {mutation.NOTHING_MATCHES}").install(monkeypatch)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main(["--strict"]) == 0


def test_clean_test_failure_is_a_tool_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    FakeMutmut(status=1, tail="failed to run clean test\n").install(monkeypatch)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 2
    assert "mutmut run exited with status 1" in capsys.readouterr().err


def test_spent_budget_reports_unjudged_mutants_as_not_run(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    FakeMutmut(status=None, results="clearml_yolo.core.sample.x_second__mutmut_1: not checked\n").install(monkeypatch)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main(["--strict"]) == 0
    assert "Budget: mutmut stopped" in capsys.readouterr().out


def test_function_budget_mutates_the_first_targets_and_lists_the_rest(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    assert mutation.main([str(repo / MODULE), "--max-functions", "1"]) == 0
    assert fake.run_args == ["clearml_yolo.core.sample.x_first*"]
    assert "Budget: mutating 1 of 4 changed functions" in capsys.readouterr().out


def test_configured_only_mutate_is_refused(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    _stage(repo, "pyproject.toml", PYPROJECT + 'only_mutate = ["src/clearml_yolo/core/sample.py"]\n')
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 2
    assert fake.run_args == []


def test_file_outside_the_package_is_a_usage_error(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    FakeMutmut().install(monkeypatch)
    _write(repo, "scripts/tool.py", "def other():\n    return 1\n")
    assert mutation.main([str(repo / "scripts/tool.py")]) == 2


def test_missing_external_copies_are_a_tool_error(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    FakeMutmut().install(monkeypatch)
    (repo / "external").rmdir()
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 2


def test_unknown_base_is_a_tool_error(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    FakeMutmut().install(monkeypatch)
    assert mutation.main(["--base", "no-such-ref"]) == 2


def test_negative_budget_is_rejected() -> None:
    with pytest.raises(SystemExit) as stopped:
        mutation.parse_options(["--budget-seconds", "-1"])
    assert stopped.value.code == 2


def test_workspace_is_removed_unless_kept(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    FakeMutmut().install(monkeypatch)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    assert list(scratch.iterdir()) == []
    assert mutation.main(["--keep"]) == 0
    (kept,) = scratch.iterdir()
    assert f"Workspace kept: {kept}" in capsys.readouterr().out
