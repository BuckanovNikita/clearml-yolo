"""Changed-function mapping and exit statuses of scripts/mutation.py, without running mutmut."""

import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import tomllib
import types
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import ClassVar, Self

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
SAMPLE_TEST = "tests/test_sample.py"
SAMPLE_TEST_TEXT = "from clearml_yolo.core import (\n    other,\n    sample,\n)\n"
# The three pytest-testmon tables the driver joins, as testmon 2 creates them.
TESTMON_SCHEMA = (
    (
        "CREATE TABLE test_execution (id INTEGER PRIMARY KEY, environment_id INTEGER, test_name TEXT,"
        " duration FLOAT, failed BIT, forced BIT)"
    ),
    "CREATE TABLE file_fp (id INTEGER PRIMARY KEY, filename TEXT, method_checksums BLOB, mtime FLOAT, fsha TEXT)",
    (
        "CREATE TABLE test_execution_file_fp (test_execution_id INTEGER, fingerprint_id INTEGER,"
        " PRIMARY KEY (test_execution_id, fingerprint_id)) WITHOUT ROWID"
    ),
)


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
    _write(root, SAMPLE_TEST, SAMPLE_TEST_TEXT)
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


def _testmon(repo: Path, dependencies: Sequence[tuple[str, str]]) -> None:
    """Write a .testmondata recording (source file, test node id) dependencies."""
    connection = sqlite3.connect(repo / mutation.TESTMON_DATABASE)
    with connection:
        for statement in TESTMON_SCHEMA:
            connection.execute(statement)
        for number, (source, node_id) in enumerate(dependencies, start=1):
            connection.execute(
                "INSERT INTO test_execution (id, environment_id, test_name) VALUES (?, 1, ?)", (number, node_id)
            )
            connection.execute("INSERT INTO file_fp (id, filename) VALUES (?, ?)", (number, source))
            connection.execute("INSERT INTO test_execution_file_fp VALUES (?, ?)", (number, number))
    connection.close()


def _selection(pyproject: str) -> list[str]:
    selection: list[str] = tomllib.loads(pyproject)["tool"]["mutmut"]["pytest_add_cli_args_test_selection"]
    return selection


def test_importing_test_files_are_selected_without_testmon_data(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    _stage(repo, "tests/test_unrelated.py", "from clearml_yolo.core import sample_extra\n")
    _stage(repo, "tests/test_dotted.py", "import clearml_yolo.core.sample as s\n")
    _stage(repo, "tests/integration/test_live.py", "from clearml_yolo.core import sample\n")
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    assert _selection(fake.pyproject) == ["tests/test_dotted.py", SAMPLE_TEST]


def test_testmon_node_ids_still_defined_in_staged_test_modules_are_selected(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    _testmon(repo, [
        (MODULE, "tests/test_indirect.py::test_renamed[a b-c]"),
        (MODULE, "tests/test_indirect.py::test_other"),
        (MODULE, "tests/test_indirect.py::test_case[a::b-c]"),
        (MODULE, "tests/test_indirect.py::TestGroup::test_method[1]"),
        (MODULE, "tests/test_indirect.py::TestRenamed::test_method"),
        (MODULE, "tests/test_indirect.py::test_method"),
        (MODULE, "tests/test_moved_away.py::test_gone"),
        (MODULE, "tests/integration/test_live.py::test_stand"),
        (MODULE, "tests/conftest.py::fixture_ghost"),
        ("src/clearml_yolo/__init__.py", "tests/test_init.py::test_version"),
    ])  # fmt: skip
    indirect = textwrap.dedent(
        """\
        import pytest
        def test_other() -> None:
            pass
        @pytest.mark.parametrize("value", ["a::b-c"])
        def test_case(value: str) -> None:
            pass
        class TestGroup:
            def test_method(self) -> None:
                pass
        """
    )
    _stage(repo, "tests/test_indirect.py", indirect)
    _stage(repo, "tests/integration/test_live.py", "def test_stand() -> None:\n    pass\n")
    _stage(repo, "tests/conftest.py", "def fixture_ghost() -> None:\n    pass\n")
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    # Stale, live and non-test ids are dropped and parameters cut; the importing test
    # module, which testmon has not recorded, is added whole.
    assert _selection(fake.pyproject) == [
        "tests/test_indirect.py::TestGroup::test_method",
        "tests/test_indirect.py::test_case",
        "tests/test_indirect.py::test_other",
        SAMPLE_TEST,
    ]
    assert "Selected 4 test(s) in 2 file(s)" in capsys.readouterr().out


def test_importing_module_with_selected_node_ids_is_not_added_whole(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    _testmon(repo, [(MODULE, f"{SAMPLE_TEST}::test_first")])
    _stage(
        repo,
        SAMPLE_TEST,
        SAMPLE_TEST_TEXT + "def test_first() -> None:\n    pass\ndef test_slow() -> None:\n    pass\n",
    )
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    assert _selection(fake.pyproject) == [f"{SAMPLE_TEST}::test_first"]


def test_node_ids_of_an_unparsable_test_module_select_the_whole_module(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    _testmon(repo, [(MODULE, "tests/test_broken.py::test_x"), (MODULE, "tests/test_broken.py::test_y")])
    _stage(repo, "tests/test_broken.py", "def test_x(:\n")
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    assert _selection(fake.pyproject) == ["tests/test_broken.py", SAMPLE_TEST]


def test_only_pytest_test_modules_are_selected(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    importing = "from clearml_yolo.core import sample\n"
    for helper in ("tests/conftest.py", "tests/env_isolation.py", "tests/ddp_cpu_harness.py", "tests/sample_worker.py"):
        _stage(repo, helper, importing)
    _stage(repo, "tests/core/sample_test.py", importing)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    assert _selection(fake.pyproject) == ["tests/core/sample_test.py", SAMPLE_TEST]


def test_unreadable_testmon_data_falls_back_to_imports(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    (repo / mutation.TESTMON_DATABASE).write_text("not a database", encoding="utf-8")
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    assert _selection(fake.pyproject) == [SAMPLE_TEST]


def test_committed_selection_is_replaced_not_duplicated(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    _stage(repo, "pyproject.toml", PYPROJECT + 'pytest_add_cli_args_test_selection = [\n    "tests/",\n]\nkeep = 1\n')
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 0
    table = tomllib.loads(fake.pyproject)["tool"]["mutmut"]
    assert table["pytest_add_cli_args_test_selection"] == [SAMPLE_TEST]
    assert table["keep"] == 1


@pytest.mark.parametrize(("strict", "expected"), [(False, 0), (True, 1)])
def test_change_no_test_selects_is_not_reached_without_running_mutmut(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], strict: bool, expected: int
) -> None:
    fake = FakeMutmut()
    fake.install(monkeypatch)
    ignoring = PYPROJECT + f'pytest_add_cli_args = ["-n", "0", "--ignore={SAMPLE_TEST}"]\n'
    _stage(repo, "pyproject.toml", ignoring)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main(["--strict"] if strict else []) == expected
    assert "Not reached by tests" in capsys.readouterr().out
    assert fake.run_args == []


def test_unexpected_failure_is_a_tool_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    FakeMutmut().install(monkeypatch)

    def broken(*_: object) -> str:
        msg = "database is gone"
        raise RuntimeError(msg)

    monkeypatch.setattr(mutation, "mutmut_results", broken)
    _stage(repo, MODULE, ORIGINAL.replace("value * 2", "value * 3"))
    assert mutation.main([]) == 2
    assert "ERROR: unexpected RuntimeError: database is gone" in capsys.readouterr().err


def _fake_proc(root: Path, processes: dict[int, tuple[str, int, str]]) -> Path:
    """Write ``<root>/<pid>/stat`` files: pid -> (command name, parent pid, start time)."""
    for pid, (name, parent, started) in processes.items():
        (root / str(pid)).mkdir(parents=True)
        fields = " ".join(["0"] * 17)  # pgrp .. itrealvalue
        (root / str(pid) / "stat").write_text(f"{pid} ({name}) S {parent} {fields} {started} 0\n", encoding="utf-8")
    (root / "self").mkdir()
    return root


def test_descendants_follow_the_parent_chain_across_sessions(tmp_path: Path) -> None:
    proc = _fake_proc(tmp_path, {
        10: ("mutmut", 1, "100"),
        11: ("python) S 1 (x", 10, "101"),  # a command name that mimics stat fields
        12: ("setsid child", 11, "102"),
        13: ("unrelated", 1, "103"),
        14: ("grandchild", 12, "104"),
    })  # fmt: skip
    assert mutation.proc_descendants(10, proc) == {11: "101", 12: "102", 14: "104"}
    assert mutation.proc_descendants(14, proc) == {}


class FakePsutilProcess:
    """psutil.Process over a fixed table: pid -> (parent pid, create time)."""

    table: ClassVar[dict[int, tuple[int, float]]] = {}

    def __init__(self, pid: int) -> None:
        if pid not in self.table:
            raise FakePsutilError(pid)
        self.pid = pid

    def create_time(self) -> float:
        return self.table[self.pid][1]

    def children(self, *, recursive: bool) -> list["FakePsutilProcess"]:
        direct = [type(self)(pid) for pid, (parent, _) in self.table.items() if parent == self.pid]
        if not recursive:
            return direct
        return [*direct, *(grandchild for child in direct for grandchild in child.children(recursive=True))]


class FakePsutilError(Exception):
    """psutil.Error stand-in (NoSuchProcess)."""


def _install_psutil(monkeypatch: pytest.MonkeyPatch, table: dict[int, tuple[int, float]] | None) -> None:
    """Install a fake ``psutil`` module; None makes every Process lookup fail."""
    module = types.ModuleType("psutil")

    class Process(FakePsutilProcess):
        pass

    Process.table = table if table is not None else {}
    module.Process = Process  # type: ignore[attr-defined]
    module.Error = FakePsutilError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psutil", module)


def test_descendants_come_from_psutil_and_are_killed_by_start_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_psutil(monkeypatch, {10: (1, 1.0), 11: (10, 2.0), 12: (11, 3.0), 13: (1, 4.0)})
    tree = mutation.descendants(10)
    assert tree == {11: "psutil:2.0", 12: "psutil:3.0"}
    killed: list[int] = []
    monkeypatch.setattr(os, "kill", lambda pid, _sig: killed.append(pid))
    _install_psutil(monkeypatch, {11: (1, 2.0), 12: (1, 9.0)})  # 12's pid was reused
    mutation._kill_known(tree)
    assert killed == [11]


def test_descendants_fall_back_to_proc_then_to_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_psutil(monkeypatch, None)
    proc = _fake_proc(tmp_path / "proc", {10: ("mutmut", 1, "100"), 11: ("child", 10, "101")})
    assert mutation.descendants(10, proc) == {11: "proc:101"}
    killed: list[int] = []
    monkeypatch.setattr(os, "kill", lambda pid, _sig: killed.append(pid))
    mutation._kill_known({11: "proc:101", 10: "proc:999"}, proc)
    assert killed == [11]
    assert mutation.descendants(10, tmp_path / "missing") == {}


class FakeGroupProcess:
    """The Popen surface _stop_group uses, for a process that exits on SIGINT."""

    pid = 424242

    def __init__(self) -> None:
        self.waited = False

    def wait(self, timeout: float) -> int:
        self.waited = timeout > 0
        return 0

    def poll(self) -> int | None:
        return 0


def test_failed_descendant_discovery_still_signals_the_group(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_: object) -> dict[int, str]:
        msg = "process table unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr(mutation, "psutil_descendants", broken)
    monkeypatch.setattr(mutation, "proc_descendants", broken)
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    monkeypatch.setattr(os, "kill", lambda *_: pytest.fail("no descendant was recorded"))
    process = FakeGroupProcess()
    spent = threading.Event()
    mutation._stop_group(process, spent)  # type: ignore[arg-type]
    assert signals == [(process.pid, signal.SIGINT), (process.pid, signal.SIGKILL)]
    assert process.waited
    assert spent.is_set()


def test_interrupted_grace_wait_still_kills_the_group(monkeypatch: pytest.MonkeyPatch) -> None:
    class ImpatientProcess:
        pid = 454545

        def wait(self, timeout: float) -> int:
            raise KeyboardInterrupt(timeout)  # a second Ctrl-C during the grace period

        def poll(self) -> int | None:
            return None

    monkeypatch.setattr(mutation, "descendants", lambda _pid: {77: "proc:1"})
    signals: list[tuple[int, int]] = []
    killed: list[set[int]] = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    monkeypatch.setattr(mutation, "_kill_known", lambda tree: killed.append(set(tree)))
    process = ImpatientProcess()
    with pytest.raises(KeyboardInterrupt):
        mutation._stop_group(process, threading.Event())  # type: ignore[arg-type]
    assert signals == [(process.pid, signal.SIGINT), (process.pid, signal.SIGKILL)]
    assert killed == [{77}]


class InterruptedPopen:
    """A Popen stand-in whose output stream is interrupted after one line."""

    def __init__(self, *_: object, **__: object) -> None:
        self.pid = 434343
        self.returncode: int | None = None
        self.stdout = self._lines()

    @staticmethod
    def _lines() -> Iterator[bytes]:
        yield b"mutating\n"
        raise KeyboardInterrupt

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_interrupted_run_stops_the_mutmut_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stopped: list[int] = []
    monkeypatch.setattr(subprocess, "Popen", InterruptedPopen)
    monkeypatch.setattr(mutation, "_stop_group", lambda process, _spent: stopped.append(process.pid))
    with pytest.raises(KeyboardInterrupt):
        mutation.run_mutmut(Path("/fake/mutmut"), tmp_path, {}, [], 60.0)
    assert stopped == [434343]
    assert "mutating" in capsys.readouterr().out


FAKE_MUTMUT = """\
#!{python}
import pathlib, subprocess, sys, time
# A descendant in a session of its own: the group signal misses it, and it holds stdout.
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
pathlib.Path(sys.argv[-1]).write_text(str(child.pid))
print("mutating", flush=True)
time.sleep(30)
"""


def _gone(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return True
    return stat.rpartition(")")[2].split()[0] == "Z"


@pytest.mark.skipif(not Path("/proc/self/stat").is_file(), reason="needs Linux /proc")
def test_spent_budget_stops_mutmut_and_descendants_in_other_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "mutmut"
    binary.write_text(FAKE_MUTMUT.format(python=sys.executable), encoding="utf-8")
    binary.chmod(0o755)
    pid_file = tmp_path / "child.pid"
    monkeypatch.setattr(mutation, "BUDGET_GRACE_SECONDS", 1)
    started = time.monotonic()
    status, tail = mutation.run_mutmut(binary, tmp_path, {"PATH": "/usr/bin:/bin"}, [str(pid_file)], 3.0)
    assert status is None
    assert "mutating" in tail
    assert time.monotonic() - started < 15
    child = int(pid_file.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 5
    while not _gone(child) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert _gone(child)
