"""Classify one change set and execute an explicitly bounded test-only selection."""

import argparse
import ast
import io
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import redirect_stdout
from importlib.util import resolve_name
from pathlib import Path

PROSE = {".md", ".rst", ".txt", ".adoc"}
HEAVY = "not integration and not ddp_cpu and not process_capabilities and not gpu_controls and not severstal_gpu"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def changes(scope: str) -> tuple[str, set[str]]:
    if scope == "auto":
        if git("diff", "--cached", "--name-only", "-z"):
            scope = "staged"
        elif git("status", "--porcelain", "--untracked-files=all"):
            scope = "working"
        else:
            scope = "commit"
    # --no-renames emits deletion+addition and therefore retains both path names.
    match scope:
        case "staged":
            raw = git("diff", "--cached", "--no-renames", "--name-only", "-z")
        case "working":
            raw = git("diff", "HEAD", "--no-renames", "--name-only", "-z")
            raw += git("ls-files", "--others", "--exclude-standard", "-z")
        case _:
            raw = git("diff-tree", "--root", "--no-commit-id", "-m", "-r", "--no-renames", "--name-only", "-z", "HEAD")
    return scope, {name.decode() for name in raw.split(b"\0") if name}


def classify(paths: set[str]) -> str:
    code = {
        name
        for name in paths
        if Path(name).suffix.lower() not in PROSE
        and name != "tests/integration/lifecycle.py"
        and not name.startswith("tests/integration/environment/")
    }
    if any(name.startswith("src/") for name in code):
        return "product"
    if any(name.startswith("tests/") for name in code):
        return "tests"
    return "static"


def eligible_file(name: str) -> bool:
    path = Path(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and name.startswith("tests/")
        and not name.startswith("tests/integration/")
        and path.name.startswith("test_")
        and path.suffix == ".py"
        and path.is_file()
        and not path.is_symlink()
    )


def failed_ids() -> set[str]:
    cache = Path(".pytest_cache/v/cache/lastfailed")
    if not cache.is_file():
        return set()
    try:
        value = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Discarding unreadable failed-test cache: {exc}")
        return set()
    if not isinstance(value, dict):
        print("Discarding invalid failed-test cache")
        return set()
    return {node for node, failed in value.items() if failed and isinstance(node, str) and "::" in node}


def shared_test_modules(paths: set[str]) -> set[str]:
    """Find changed test modules used as helpers; imports never select tests by themselves."""
    if not paths:
        return set()
    modules = {
        alias: name
        for name in paths
        for parts in [Path(name).with_suffix("").parts]
        for alias in (".".join(parts), ".".join(parts[1:]))
    }
    shared: set[str] = set()
    for path in Path("tests").rglob("*.py"):
        if path.is_symlink() or path.is_relative_to("tests/integration"):
            continue
        package = ".".join(path.parent.parts)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            names: set[str] = set()
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = resolve_name("." * node.level + base, package)
                names.add(base)
                names.update(f"{base}.{alias.name}" for alias in node.names)
            for name in names | {f"{package}.{name}" for name in names}:
                if name in modules and modules[name] != path.as_posix():
                    shared.add(modules[name])
    return shared


def dependents(paths: set[str], required: set[str]) -> tuple[dict[str, set[str]], list[str]]:
    if not paths:
        return {}, []
    database = Path(os.environ.get("TESTMON_DATAFILE", ".testmondata"))
    selected: dict[str, set[str]] = {}
    gaps: list[str] = []
    query = (
        "SELECT DISTINCT t.test_name FROM test_execution t "
        "JOIN test_execution_file_fp tf ON tf.test_execution_id = t.id "
        "JOIN file_fp f ON f.id = tf.fingerprint_id WHERE f.filename = ?"
    )
    try:
        connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True, timeout=5)
        try:
            for path in sorted(paths):
                nodes = {str(row[0]) for row in connection.execute(query, (path,))}
                selected[path] = nodes
                if not nodes and path in required:
                    gaps.append(f"no recorded dependents for {path}")
        finally:
            connection.close()
    except sqlite3.Error as exc:
        if required:
            gaps.append(f"dependency history unavailable: {exc}")
    return selected, gaps


def pytest_command() -> list[str]:
    # Override selection-capable inherited options. testmon remains entirely disabled:
    # every execution argument below is a validated current node ID, never an implicit root.
    # Execution retains pytest's failed-test cache; collection disables that plugin below.
    return [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:testmon",
        "-o",
        "addopts=--strict-markers --strict-config -p tests.env_isolation",
        "-n",
        "0",
        "-m",
        HEAVY,
    ]


def collect(files: set[str], environment: dict[str, str]) -> tuple[set[str], set[str]]:
    # Collection must resolve parametrization and marker inheritance, but an empty
    # selection must never launch a pytest process. Collect inside this verifier and
    # restore environment changes made by the test isolation plugin before execution.
    import pytest

    from scripts.verification_collection import BoundedCollection

    collector = BoundedCollection()
    original_environment = dict(os.environ)
    original_path = list(sys.path)
    original_cwd = Path.cwd()
    captured = io.StringIO()
    try:
        os.environ.clear()
        os.environ.update(environment)
        with redirect_stdout(captured):
            result = pytest.main(
                [*pytest_command()[3:], "-p", "no:cacheprovider", "--collect-only", "-q", *sorted(files)],
                plugins=[collector],
            )
    finally:
        os.environ.clear()
        os.environ.update(original_environment)
        sys.path[:] = original_path
        os.chdir(original_cwd)
    if result not in {0, 5}:
        print(captured.getvalue())
        raise RuntimeError(f"Bounded collection failed with exit {result}")
    return collector.nodes, collector.all_nodes


def test_selection(paths: set[str]) -> int:
    changed = {name for name in paths if eligible_file(name)}
    helpers = {
        name
        for name in paths
        if name.startswith("tests/")
        and Path(name).suffix not in PROSE
        and not Path(name).name.startswith("test_")
        and not name.startswith("tests/integration/")
    }
    test_modules = {
        name
        for name in paths
        if name.startswith("tests/")
        and not name.startswith("tests/integration/")
        and Path(name).name.startswith("test_")
        and Path(name).suffix == ".py"
    }
    required = helpers | shared_test_modules(test_modules)
    recorded, gaps = dependents(helpers | test_modules, required)
    candidates = set().union(*recorded.values()) | failed_ids()
    candidates = {node for node in candidates if eligible_file(node.split("::", 1)[0])}
    files = changed | {node.split("::", 1)[0] for node in candidates}
    environment = {key: value for key, value in os.environ.items() if key != "PYTEST_ADDOPTS"}
    current, collected = collect(files, environment) if files else (set(), set())
    for source, nodes in recorded.items():
        unit_nodes = {node for node in nodes if not node.startswith("tests/integration/")}
        if source in required and unit_nodes and not unit_nodes.intersection(collected):
            gaps.append(f"no current unit dependents remain for {source}")
    for gap in gaps:
        print(f"TARGETED VERIFICATION GAP: {gap}", file=sys.stderr)
    selected = sorted(node for node in current if node in candidates or node.split("::", 1)[0] in changed)
    print(f"Bounded selection: {len(selected)} tests; {len(candidates - current)} stale/ineligible IDs discarded.")
    if not selected:
        print("Empty selection; no pytest process launched.")
        return 3 if gaps else 0
    result = subprocess.run([*pytest_command(), *selected], env=environment, check=False)
    return result.returncode or (3 if gaps else 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("classify", "run"))
    parser.add_argument("--scope", choices=("auto", "staged", "working", "commit"), default="auto")
    parser.add_argument("--task", default="task")
    args = parser.parse_args()
    scope, paths = changes(args.scope)
    route = classify(paths)
    if args.action == "classify":
        print(json.dumps({"scope": scope, "route": route, "paths": sorted(paths)}))
        return 0
    print(f"Automatic verification: {route} ({scope})", flush=True)
    if route == "static":
        print("Static route complete; no product tests or live infrastructure launched.")
        return 0
    if route == "product":
        return subprocess.run([args.task, "--exit-code", "test"], check=False).returncode
    try:
        return test_selection(paths)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"Targeted verification error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
