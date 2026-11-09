#!/usr/bin/env python3
"""Mutation-test only the functions a change touches, in a throwaway workspace.

    uv run python scripts/mutation.py                          # staged change vs HEAD
    uv run python scripts/mutation.py --base master            # staged tree vs master
    uv run python scripts/mutation.py src/clearml_yolo/x.py    # every function of a file
    uv run python scripts/mutation.py --keep --strict          # keep it; fail on survivors
    uv run python scripts/mutation.py --budget-seconds 0 --max-functions 0  # no limits

Changed lines of staged ``src/clearml_yolo/**/*.py`` files, compared with the merge
base of ``--base`` (default ``HEAD``), are mapped to the top-level functions and
methods that contain them, and mutmut runs only their mutants. The run is budgeted:
at most ``--max-functions`` (default 8) changed functions are mutated and the rest
are listed; mutmut stops after ``--budget-seconds`` (default 300), and mutants it did
not reach by then count as "not run", not as survivors. Zero lifts either limit.

The budget covers mutmut's whole run, including its stats pass, which executes every
selected test once before any mutant. Running the whole unit suite there takes about
1000 s, so each run selects test files per change instead (``select_tests``): the
test files ``.testmondata`` records as depending on each changed file, or, for a file
it knows nothing about, the test files whose text imports the changed module. Live
suites (``tests/integration``) and files ``[tool.mutmut]`` ignores are never selected,
and the committed ``pytest_add_cli_args`` deselect the host-wide markers. With that
selection the stats pass takes seconds to a few minutes, so 300 s leaves room for
mutants of the default 8 functions; widen ``--budget-seconds`` for a thorough run.
When no test file is selected, mutmut is not run and the functions are reported as
not reached by tests.

The verdict is advisory: surviving mutants are printed (the first few with diffs) and
the run passes, unless ``--strict`` is given. Mutants no unit test reaches are counted
separately. Exit statuses: 0 success (survivors are advisory), 1 survivors or
unreached functions under ``--strict``, 2 a tool, configuration or clean-test failure,
including any unexpected error of the driver itself.

Nothing is shared between runs. Each run exports the *staged* tree with
``git checkout-index`` into a fresh temporary directory, links the repository's
``external/`` dependency copies into it, narrows that copy's ``[tool.mutmut]`` to the
changed files and selected tests and runs the repository venv's ``mutmut`` there in
its own session. When the budget expires, that process group and every descendant
that started a session of its own are stopped. No mutmut cache or
pytest temp root outlives the run, so concurrent runs from other worktrees or agents
cannot corrupt each other, and a stale verdict cannot be reused.

mutmut only mutates code inside undecorated top-level functions and methods (a lone
``@staticmethod``/``@classmethod`` is allowed), never f-strings, and skips lines
matched by ``do_not_mutate_patterns``. A change outside those produces no mutants,
and a change no unit test reaches cannot be tested; both are reported and pass.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import tomllib
from collections import deque
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = "src"
PACKAGE = "clearml_yolo"
PACKAGE_DIR = f"{SOURCE_ROOT}/{PACKAGE}"
# `mutmut results` statuses that mean the mutant did not escape.
BENIGN_STATUSES = frozenset({"killed", "skipped", "caught by type check"})
# Statuses of mutants that were never judged: the budget ran out first, or no unit
# test reaches the line. Reported as counts, never as survivors.
UNRUN_STATUSES = frozenset({"not checked"})
UNREACHED_STATUSES = frozenset({"no tests"})
# mutmut asserts when a name filter matches no generated mutant.
NOTHING_MATCHES = "Filtered for specific mutants, but nothing matches"
# mutmut stops when no unit test reaches any mutated function at all.
NO_TESTS = "could not find any test case for any mutant"
# Live-stand and run variables a shell may still export. The unit suite must never
# see them; git's hook variables (GIT_INDEX_FILE) point at the real repository.
SCRUBBED_PREFIXES = ("CLEARML_", "INFRA_", "CY_RUN_", "MINIO_", "GIT_")
CLASS_SEPARATOR = "ǁ"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
MAX_DIFFS = 5
DEFAULT_MAX_FUNCTIONS = 8
DEFAULT_BUDGET_SECONDS = 300.0
BUDGET_GRACE_SECONDS = 15
# pytest-testmon's dependency database in the repository (the worktree) root.
TESTMON_DATABASE = ".testmondata"
TESTS_DIR = "tests"
LIVE_TESTS_DIR = "tests/integration"
PROC_ROOT = Path("/proc")


class MutationError(Exception):
    """A tool or configuration failure: the run cannot produce a verdict."""


@dataclass(frozen=True)
class Options:
    """Parsed command line."""

    files: tuple[str, ...]
    base: str
    keep: bool
    strict: bool
    max_children: int | None
    max_functions: int
    budget_seconds: float


@dataclass(frozen=True)
class Target:
    """One mutable function and the mutmut names that select its mutants.

    ``name`` is mutmut's mangled function name (``pkg.mod.x_func``). The run filter
    is ``<name>*`` rather than ``<name>__mutmut_*``: mutmut also matches the filter
    against mangled function names to pick the clean-run tests, and a pattern with
    the ``__mutmut_`` suffix matches none of them, which silently makes the clean run
    execute the whole suite. The wider glob can also run mutants of a function whose
    name extends this one; the report counts exact names only.
    """

    path: str
    qualname: str
    name: str

    @property
    def glob(self) -> str:
        """The ``mutmut run`` filter for this function."""
        return f"{self.name}*"


def git(*args: str) -> str:
    """Run git in the repository and return stdout; a failure is a tool error."""
    completed = subprocess.run(["git", *args], cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        msg = f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        raise MutationError(msg)
    return completed.stdout


def changed_lines(base: str) -> dict[str, set[int]]:
    """Return staged package Python files and their changed lines.

    The index is compared with the merge base of *base* and ``HEAD``, so a moving
    ``master`` does not count its own changes as this branch's. A deletion-only hunk
    marks the lines on both sides of the gap. Prefixes, quoting and external-diff
    options are pinned so that user git configuration cannot change the format.
    """
    diff = git(
        "-c", "core.quotePath=false",
        "diff", "--cached", "--merge-base", "--unified=0", "--no-color",
        "--no-renames", "--no-ext-diff", "--no-textconv",
        "--src-prefix=a/", "--dst-prefix=b/",
        "--diff-filter=AM", base, "--", f"{PACKAGE_DIR}/*.py",
    )  # fmt: skip
    files: dict[str, set[int]] = {}
    current: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            if not target.startswith("b/"):
                msg = f"unexpected diff header {line!r}"
                raise MutationError(msg)
            current = target[2:]
            files.setdefault(current, set())
        elif current is not None and (match := HUNK.match(line)):
            start, count = int(match.group(1)), int(match.group(2) or "1")
            if count == 0:
                # `-U0` numbers a pure deletion by the line before the gap.
                files[current].update({max(start, 1), start + 1})
            else:
                files[current].update(range(start, start + count))
    return {path: lines for path, lines in files.items() if lines}


def module_name(path: str) -> str:
    """Return mutmut's module name for a repository path (``src.`` and ``__init__`` dropped)."""
    parts = list(Path(path).with_suffix("").parts)
    if parts and parts[0] == SOURCE_ROOT:
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _decorated_out(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Tell whether mutmut skips *node*: decorated, bar one static/classmethod."""
    if not node.decorator_list:
        return False
    if len(node.decorator_list) > 1:
        return True
    decorator = node.decorator_list[0]
    return not (isinstance(decorator, ast.Name) and decorator.id in {"staticmethod", "classmethod"})


def _span(node: ast.FunctionDef | ast.AsyncFunctionDef) -> range:
    first = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
    return range(first, (node.end_lineno or node.lineno) + 1)


def _functions(tree: ast.Module) -> Iterator[tuple[str, str, range]]:
    """Yield (qualname, mangled mutmut name, line span) of every mutable function."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if not _decorated_out(node):
                yield node.name, f"x_{node.name}", _span(node)
        elif isinstance(node, ast.ClassDef) and not node.decorator_list:
            for member in node.body:
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef) and not _decorated_out(member):
                    yield (
                        f"{node.name}.{member.name}",
                        f"x{CLASS_SEPARATOR}{node.name}{CLASS_SEPARATOR}{member.name}",
                        _span(member),
                    )


def targets_for(path: str, source: str, lines: set[int] | None) -> list[Target]:
    """Return the mutable functions of *source* that contain any of *lines* (None: all)."""
    tree = ast.parse(source, filename=path)
    module = module_name(path)
    return [
        Target(path, qualname, f"{module}.{mangled}")
        for qualname, mangled, span in _functions(tree)
        if lines is None or any(line in span for line in lines)
    ]


def export_staged_tree(workspace: Path) -> None:
    """Write the index (exactly what a commit would contain) into *workspace*."""
    git("checkout-index", "--all", "--force", f"--prefix={workspace}{os.sep}")


def link_external(workspace: Path) -> None:
    """Expose the repository's ``external/`` dependency copies inside *workspace*."""
    external = (REPO_ROOT / "external").resolve()
    if not external.is_dir():
        msg = f"{external} is missing; populate external sources first (docs/development.md)."
        raise MutationError(msg)
    (workspace / "external").symlink_to(external, target_is_directory=True)


def _mutmut_table(pyproject: Path) -> dict[str, object]:
    """Return the parsed ``[tool.mutmut]`` table of *pyproject*; invalid TOML is a tool error."""
    try:
        document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = f"{pyproject.name} is not valid TOML: {exc}"
        raise MutationError(msg) from exc
    table = document.get("tool", {}).get("mutmut")
    if not isinstance(table, dict):
        msg = "pyproject.toml has no [tool.mutmut] table."
        raise MutationError(msg)
    return table


def _ignored_paths(workspace: Path) -> tuple[str, ...]:
    """Return the paths ``[tool.mutmut].pytest_add_cli_args`` passes to ``--ignore=``."""
    args = _mutmut_table(workspace / "pyproject.toml").get("pytest_add_cli_args", [])
    if not isinstance(args, list):
        return ()
    return tuple(arg.removeprefix("--ignore=").rstrip("/") for arg in args if str(arg).startswith("--ignore="))


def _eligible_test_file(workspace: Path, path: str, ignored: Sequence[str]) -> bool:
    """Tell whether *path* is a unit test file present in the staged *workspace*."""
    if not path.startswith(f"{TESTS_DIR}/") or not path.endswith(".py"):
        return False
    if any(path == skip or path.startswith(f"{skip}/") for skip in (LIVE_TESTS_DIR, *ignored)):
        return False
    return (workspace / path).is_file()


def testmon_dependents(database: Path, sources: Sequence[str]) -> dict[str, set[str]]:
    """Return, per source file, the test files *database* records as depending on it.

    The database is pytest-testmon's ``.testmondata``, opened read-only; a missing or
    unreadable database yields no dependents. Node ids are cut to their test files:
    stale ids (renamed tests, parameters) would make pytest refuse the selection.
    """
    if not database.is_file() or not sources:
        return {}
    query = (
        "SELECT DISTINCT t.test_name FROM test_execution t "
        "JOIN test_execution_file_fp tf ON tf.test_execution_id = t.id "
        "JOIN file_fp f ON f.id = tf.fingerprint_id "
        "WHERE f.filename = ?"
    )
    dependents: dict[str, set[str]] = {}
    try:
        connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True, timeout=5)
        try:
            for source in sources:
                node_ids = connection.execute(query, (source,)).fetchall()
                dependents[source] = {str(node_id).partition("::")[0] for (node_id,) in node_ids}
        finally:
            connection.close()
    except sqlite3.Error as exc:
        print(f"Test selection: {database} is unreadable ({exc}); falling back to imports.")
        return {}
    return dependents


def _import_pattern(module: str) -> re.Pattern[str]:
    """Match ``pkg.mod`` anywhere or ``from pkg import (..., mod, ...)`` in test source."""
    parent, _, leaf = module.rpartition(".")
    dotted = rf"\b{re.escape(module)}\b"
    if not parent:
        return re.compile(dotted)
    from_import = rf"\bfrom\s+{re.escape(parent)}\s+import\s+(?:\([^)]*|[^\n]*)\b{re.escape(leaf)}\b"
    return re.compile(f"{dotted}|{from_import}")


def importing_tests(workspace: Path, source: str, ignored: Sequence[str]) -> set[str]:
    """Return the unit test files of *workspace* whose text imports *source*'s module."""
    pattern = _import_pattern(module_name(source))
    found: set[str] = set()
    for test_file in sorted((workspace / TESTS_DIR).rglob("*.py")):
        relative = test_file.relative_to(workspace).as_posix()
        if _eligible_test_file(workspace, relative, ignored) and pattern.search(
            test_file.read_text(encoding="utf-8", errors="replace")
        ):
            found.add(relative)
    return found


def select_tests(workspace: Path, sources: Sequence[str], database: Path) -> list[str]:
    """Return the unit test files that can kill mutants of *sources*.

    Per source file, testmon's recorded dependents that still exist in the staged tree
    are used; a source file testmon does not know (new, renamed, or no database) falls
    back to the test files that import its module.
    """
    ignored = _ignored_paths(workspace)
    recorded = testmon_dependents(database, sources)
    selected: set[str] = set()
    for source in sources:
        known = {path for path in recorded.get(source, set()) if _eligible_test_file(workspace, path, ignored)}
        selected |= known or importing_tests(workspace, source, ignored)
    return sorted(selected)


def _toml_array(values: Sequence[str]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def narrow_scope(pyproject: Path, files: Sequence[str], tests: Sequence[str]) -> None:
    """Point the workspace's ``[tool.mutmut]`` at *files* and the selected *tests*."""
    if "only_mutate" in _mutmut_table(pyproject):
        msg = "pyproject.toml sets [tool.mutmut].only_mutate; the scope is derived from the change, remove the setting."
        raise MutationError(msg)
    text = pyproject.read_text(encoding="utf-8")
    header = re.search(r"^\[tool\.mutmut\]\s*$", text, flags=re.MULTILINE)
    if header is None:
        msg = "pyproject.toml has no plain [tool.mutmut] header line."
        raise MutationError(msg)
    head, body = text[: header.end()], text[header.end() :]
    # The committed selection is replaced: a second assignment is a TOML error.
    body = re.sub(r"^pytest_add_cli_args_test_selection\s*=\s*\[[^\]]*\][^\n]*\n?", "", body, flags=re.MULTILINE)
    # Git change detection would compare against a repository this copy is not.
    addition = (
        f"\nonly_mutate = {_toml_array(files)}\nuse_git_change_detection = false\n"
        f"pytest_add_cli_args_test_selection = {_toml_array(tests)}\n"
    )
    pyproject.write_text(head + addition + body, encoding="utf-8")
    table = _mutmut_table(pyproject)
    if table.get("only_mutate") != list(files) or table.get("pytest_add_cli_args_test_selection") != list(tests):
        msg = "could not narrow [tool.mutmut] in the workspace copy of pyproject.toml."
        raise MutationError(msg)


def child_env(workspace: Path) -> dict[str, str]:
    """Build mutmut's environment: no stand, run or git variables, a private temp root."""
    env = {key: value for key, value in os.environ.items() if not key.startswith(SCRUBBED_PREFIXES)}
    temproot = workspace / ".pytest-temproot"
    temproot.mkdir(parents=True, exist_ok=True)
    # A shared /tmp/pytest-of-$USER lets a concurrent session delete this run's
    # `pytest-current` link, which kills a mutant for unrelated reasons.
    env["PYTEST_DEBUG_TEMPROOT"] = str(temproot)
    return env


def mutmut_binary() -> Path:
    """Locate the repo venv's mutmut (``uv run`` in the copy would build a new venv)."""
    binary = Path(sys.executable).with_name("mutmut")
    if not binary.is_file():
        msg = f"{binary} not found; run this script with `uv run python`."
        raise MutationError(msg)
    return binary


def _proc_stat(proc: Path, pid: int) -> tuple[int, str] | None:
    """Return (parent pid, start time) of *pid* from ``<proc>/<pid>/stat``; None when gone."""
    try:
        stat = (proc / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    # The command name is parenthesized and may itself contain spaces and parentheses.
    fields = stat.rpartition(")")[2].split()
    if len(fields) < 20:  # noqa: PLR2004 - field 22 (starttime) is index 19 after the name
        return None
    return int(fields[1]), fields[19]


def descendants(pid: int, proc: Path = PROC_ROOT) -> dict[int, str]:
    """Return every live descendant of *pid* by parent-pid chain, with its start time.

    This includes descendants that started a session (or group) of their own, which a
    signal to the process group misses. A process orphaned before the scan is not seen.
    """
    children: dict[int, list[tuple[int, str]]] = {}
    for entry in proc.iterdir():
        if entry.name.isdigit() and (stat := _proc_stat(proc, int(entry.name))) is not None:
            children.setdefault(stat[0], []).append((int(entry.name), stat[1]))
    found: dict[int, str] = {}
    pending = [pid]
    while pending:
        for child, started in children.get(pending.pop(), []):
            if child not in found:
                found[child] = started
                pending.append(child)
    return found


def _kill_known(processes: dict[int, str], proc: Path = PROC_ROOT) -> None:
    """SIGKILL each recorded process that still runs with the same start time."""
    for pid, started in processes.items():
        stat = _proc_stat(proc, pid)
        if stat is None or stat[1] != started:  # gone, or the pid was reused
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            continue


def _stop_group(process: subprocess.Popen[bytes], spent: threading.Event) -> None:
    """Interrupt mutmut's whole process group, then kill what is left.

    mutmut forks one child per mutant and stops them only on KeyboardInterrupt, so the
    group gets SIGINT first; after the grace period the group and every descendant
    recorded before the interrupt (including ones in sessions of their own, which may
    hold the output pipe) get SIGKILL. Descendants are recorded first because they
    lose their parent chain once mutmut exits.
    """
    spent.set()
    tree = descendants(process.pid)
    with contextlib.suppress(subprocess.TimeoutExpired, ProcessLookupError):
        os.killpg(process.pid, signal.SIGINT)
        process.wait(timeout=BUDGET_GRACE_SECONDS)
    if process.poll() is None:  # a reaped pid may already belong to another process
        tree |= descendants(process.pid)
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    _kill_known(tree)


def run_mutmut(
    binary: Path,
    workspace: Path,
    env: dict[str, str],
    args: Sequence[str],
    budget_seconds: float = 0,
) -> tuple[int | None, str]:
    """Stream ``mutmut run``; return its status (None: budget spent) and output tail.

    Only what a terminal would have left on each line is printed, so captured output
    does not hold every spinner redraw. mutmut runs in its own session; with a budget,
    a timer interrupts that process group once the budget is spent, and the mutants
    judged so far keep their results.
    """
    tail: deque[str] = deque(maxlen=40)
    spent = threading.Event()
    with subprocess.Popen(
        [str(binary), "run", *args],
        cwd=workspace,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    ) as process:
        timer = threading.Timer(budget_seconds, _stop_group, (process, spent)) if budget_seconds > 0 else None
        if timer is not None:
            timer.start()
        try:
            stdout = process.stdout
            if stdout is None:
                msg = "mutmut output pipe is unavailable."
                raise MutationError(msg)
            for raw in stdout:
                line = raw.decode("utf-8", errors="replace").rsplit("\r", 1)[-1]
                tail.append(line)
                sys.stdout.write(line)
                sys.stdout.flush()
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
    if spent.is_set() and process.returncode != 0:
        return None, "".join(tail)
    return process.returncode, "".join(tail)


def mutmut_results(binary: Path, workspace: Path, env: dict[str, str]) -> str:
    """Return ``mutmut results --all true`` output; a failure is a tool error."""
    completed = subprocess.run(
        [str(binary), "results", "--all", "true"],
        cwd=workspace,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        msg = f"mutmut results exited with status {completed.returncode}: {completed.stderr.strip()}"
        raise MutationError(msg)
    return completed.stdout


def parse_results(text: str) -> dict[str, str]:
    """Return the ``name: status`` lines of ``mutmut results`` as a mapping."""
    statuses: dict[str, str] = {}
    for line in text.splitlines():
        name, separator, status = line.strip().partition(": ")
        if separator and name and not name.startswith("#"):
            statuses[name] = status
    return statuses


def _selected(mutant: str, functions: Iterable[str]) -> bool:
    return mutant.partition("__mutmut_")[0] in functions


class ShowFn:
    """``mutmut show`` in the workspace, as a callable."""

    def __init__(self, binary: Path, workspace: Path, env: dict[str, str]) -> None:
        """Bind the mutmut binary, workspace and environment of this run."""
        self.binary, self.workspace, self.env = binary, workspace, env

    def __call__(self, name: str) -> str:
        """Return the diff of mutant *name*."""
        completed = subprocess.run(
            [str(self.binary), "show", name],
            cwd=self.workspace,
            env=self.env,
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.stdout or f"# {name}: (no diff available)"


def report(statuses: dict[str, str], functions: Sequence[str], show: ShowFn) -> list[str]:
    """Print the verdict; return the names of mutants that escaped."""
    selected = {name: status for name, status in statuses.items() if _selected(name, functions)}
    if not selected:
        print("The changed functions produce no mutants; nothing to do.")
        return []
    judged = BENIGN_STATUSES | UNRUN_STATUSES | UNREACHED_STATUSES
    escaped = sorted(name for name, status in selected.items() if status not in judged)
    killed = sum(1 for status in selected.values() if status == "killed")
    unrun = sum(1 for status in selected.values() if status in UNRUN_STATUSES)
    unreached = sum(1 for status in selected.values() if status in UNREACHED_STATUSES)
    print(f"Mutants in changed functions: {len(selected)}, killed: {killed}, "
          f"survived: {len(escaped)}, not reached by tests: {unreached}, "
          f"not run (budget): {unrun}")  # fmt: skip
    if not escaped:
        print("No judged mutant of the changed functions survived.")
    for name in escaped[:MAX_DIFFS]:
        print()
        print(show(name).rstrip())
    if len(escaped) > MAX_DIFFS:
        print(f"... and {len(escaped) - MAX_DIFFS} more:")
        for name in escaped[MAX_DIFFS:]:
            print(f"    {name}: {selected[name]}")
    return escaped


def _package_file(name: str) -> str:
    """Return the repository-relative path of a package Python file named on the command line."""
    resolved = Path(name).resolve()
    relative = resolved.relative_to(REPO_ROOT).as_posix() if resolved.is_relative_to(REPO_ROOT) else ""
    if not relative.startswith(f"{PACKAGE_DIR}/") or not relative.endswith(".py"):
        msg = f"{name} is not a {PACKAGE_DIR}/ Python file."
        raise MutationError(msg)
    return relative


def collect_targets(workspace: Path, base: str, files: Sequence[str]) -> list[Target]:
    """Return targets from explicit *files* (whole files) or the staged diff against *base*."""
    scope: dict[str, set[int] | None] = dict.fromkeys(map(_package_file, files)) if files else dict(changed_lines(base))
    targets: list[Target] = []
    for path, lines in sorted(scope.items()):
        source_file = workspace / path
        if not source_file.is_file():
            msg = f"{path} is not in the index; stage it first."
            raise MutationError(msg)
        targets.extend(targets_for(path, source_file.read_text("utf-8"), lines))
    return targets


def limit_targets(targets: list[Target], limit: int) -> list[Target]:
    """Keep the first *limit* targets (0 keeps all) and list the others."""
    if not 0 < limit < len(targets):
        return targets
    print(f"Budget: mutating {limit} of {len(targets)} changed functions (--max-functions); not mutated:")
    for target in targets[limit:]:
        print(f"    {target.path}: {target.qualname}")
    return targets[:limit]


def _advisory(strict: bool) -> int:
    return 1 if strict else 0


def mutate(workspace: Path, targets: Sequence[Target], options: Options) -> int:
    """Run mutmut on *targets* inside the prepared *workspace* and report the verdict."""
    files = sorted({target.path for target in targets})
    print(f"Mutating {len(targets)} function(s) in {len(files)} file(s):")
    for target in targets:
        print(f"    {target.path}: {target.qualname}")
    tests = select_tests(workspace, files, REPO_ROOT / TESTMON_DATABASE)
    if not tests:
        print("Not reached by tests: no unit test file depends on or imports the changed modules; mutmut not run.")
        print("Advisory: add tests that call them.")
        return _advisory(options.strict)
    print(f"Selected {len(tests)} test file(s): {' '.join(tests)}")
    link_external(workspace)
    narrow_scope(workspace / "pyproject.toml", files, tests)
    binary = mutmut_binary()
    env = child_env(workspace)
    children = ["--max-children", str(options.max_children)] if options.max_children else []
    status, tail = run_mutmut(
        binary, workspace, env, [*children, *(target.glob for target in targets)], options.budget_seconds
    )
    if status is None:
        print(f"Budget: mutmut stopped after {options.budget_seconds} s (--budget-seconds); "
              "unjudged mutants count as not run.")  # fmt: skip
    elif status != 0:
        if NOTHING_MATCHES in tail:
            print("The changed functions produce no mutants; nothing to do.")
            return 0
        if NO_TESTS in tail:
            print("No unit test exercises the changed functions.")
            print("Advisory: add tests that call them.")
            return _advisory(options.strict)
        msg = f"mutmut run exited with status {status} (output above)."
        raise MutationError(msg)
    statuses = parse_results(mutmut_results(binary, workspace, env))
    escaped = report(statuses, [target.name for target in targets], ShowFn(binary, workspace, env))
    if not escaped:
        return 0
    print()
    print("Advisory: strengthen a test that should observe these mutations,")
    print("or leave them when the mutation cannot change observable behaviour.")
    return _advisory(options.strict)


def run(options: Options) -> int:
    """Export, narrow, mutate, report. Returns the process exit status."""
    workspace = Path(tempfile.mkdtemp(prefix="clearml-yolo-mutation-"))
    try:
        export_staged_tree(workspace)
        targets = collect_targets(workspace, options.base, options.files)
        if not targets:
            print(f"No changed {PACKAGE} function can be mutated; nothing to do.")
            return 0
        return mutate(workspace, limit_targets(targets, options.max_functions), options)
    finally:
        if options.keep:
            print(f"Workspace kept: {workspace}")
            print(f"    cd there; {Path(sys.executable).with_name('mutmut')} show <name>  (or browse)")
        else:
            shutil.rmtree(workspace, ignore_errors=True)


def _non_negative_int(text: str) -> int:
    value = int(text)
    if value < 0:
        msg = f"{text} is negative"
        raise argparse.ArgumentTypeError(msg)
    return value


def _non_negative_float(text: str) -> float:
    value = float(text)
    if value < 0:
        msg = f"{text} is negative"
        raise argparse.ArgumentTypeError(msg)
    return value


def parse_options(argv: Sequence[str] | None) -> Options:
    """Parse the command line into typed options."""
    parser = argparse.ArgumentParser(description="Mutation-test the functions a change touches (advisory).")
    parser.add_argument("files", nargs="*", help=f"{PACKAGE_DIR}/ files to mutate whole instead of the diff")
    parser.add_argument(
        "--base",
        default="HEAD",
        help="diff the staged tree against the merge base with REV (default HEAD)",
    )
    parser.add_argument("--keep", action="store_true", help="keep the workspace")
    parser.add_argument("--strict", action="store_true", help="exit 1 when a mutant survives")
    parser.add_argument("--max-children", type=_non_negative_int, help="mutmut worker count")
    parser.add_argument(
        "--max-functions",
        type=_non_negative_int,
        default=DEFAULT_MAX_FUNCTIONS,
        help="mutate at most N changed functions, 0 for all (default %(default)s)",
    )
    parser.add_argument(
        "--budget-seconds",
        type=_non_negative_float,
        default=DEFAULT_BUDGET_SECONDS,
        help="stop mutmut after N seconds, 0 for no limit (default %(default)s)",
    )
    namespace = parser.parse_args(argv)
    return Options(
        files=tuple(namespace.files),
        base=str(namespace.base),
        keep=bool(namespace.keep),
        strict=bool(namespace.strict),
        max_children=namespace.max_children,
        max_functions=int(namespace.max_functions),
        budget_seconds=float(namespace.budget_seconds),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the driver; argparse usage errors and unexpected failures also exit 2."""
    options = parse_options(argv)
    try:
        return run(options)
    except (MutationError, SyntaxError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - any driver failure is a tool error (2), not a verdict (1)
        print(f"ERROR: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
