"""Refuse a staged release commit that changes more than the root version.

Run inside the semantic-release ``build_command`` (``task release-commit-check``) after
the release files are staged. It compares the index with ``HEAD``:

* ``uv.lock``: every top-level key and every ``[[package]]`` entry is identical, except
  the single ``clearml-yolo`` entry whose only change is ``version``;
* ``pyproject.toml``: identical apart from ``project.version`` and free of
  ``[tool.uv.sources]`` overrides;
* the staged lock root version equals the staged ``project.version``.

Exit status: 0 when the release changes only the version, 1 with one line per problem.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PACKAGE = "clearml-yolo"

type Document = dict[str, Any]


def _load(root: Path, revision: str, path: str) -> Document:
    content = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"], check=True, capture_output=True
    ).stdout
    document: Document = tomllib.loads(content.decode())
    return document


def _split_root(lock: Mapping[str, Any], side: str, problems: list[str]) -> tuple[Document | None, list[Any]]:
    packages: list[Any] = list(lock.get("package", []))
    roots = [package for package in packages if package.get("name") == PACKAGE]
    if len(roots) != 1:
        problems.append(f"{side} uv.lock must contain exactly one {PACKAGE} package, found {len(roots)}")
        return None, packages
    return roots[0], [package for package in packages if package.get("name") != PACKAGE]


def _describe(package: Mapping[str, Any]) -> str:
    return f"{package.get('name')} {package.get('version')}"


def lock_problems(head: Document, staged: Document) -> list[str]:
    """Return why the staged lock is not a root-version-only change of ``head``."""
    problems = [
        f"uv.lock top-level key {key!r} changed"
        for key in sorted((set(head) | set(staged)) - {"package"})
        if head.get(key) != staged.get(key)
    ]
    head_root, head_others = _split_root(head, "HEAD", problems)
    staged_root, staged_others = _split_root(staged, "staged", problems)
    if head_others != staged_others:
        head_names = [_describe(package) for package in head_others]
        staged_names = [_describe(package) for package in staged_others]
        added = [name for name in staged_names if name not in head_names]
        removed = [name for name in head_names if name not in staged_names]
        changed = sorted(
            name
            for name in set(head_names) & set(staged_names)
            if [package for package in head_others if _describe(package) == name]
            != [package for package in staged_others if _describe(package) == name]
        )
        problems.extend(f"uv.lock package added: {name}" for name in added)
        problems.extend(f"uv.lock package removed: {name}" for name in removed)
        problems.extend(f"uv.lock package changed: {name}" for name in changed)
        if not (added or removed or changed):
            problems.append("uv.lock package order changed")
    if head_root is not None and staged_root is not None:
        before = {key: value for key, value in head_root.items() if key != "version"}
        after = {key: value for key, value in staged_root.items() if key != "version"}
        problems.extend(
            f"uv.lock {PACKAGE} field {key!r} changed"
            for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key)
        )
    return problems


def pyproject_problems(head: Document, staged: Document) -> list[str]:
    """Return why the staged project is not a version-only change of ``head``."""
    problems: list[str] = []
    if "sources" in staged.get("tool", {}).get("uv", {}):
        problems.append("staged pyproject.toml contains [tool.uv.sources]; releases carry no local overrides")
    before = {**head, "project": {**head.get("project", {}), "version": None}}
    after = {**staged, "project": {**staged.get("project", {}), "version": None}}
    if before != after:
        keys = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
        problems.append(f"staged pyproject.toml differs from HEAD beyond project.version in: {', '.join(keys)}")
    return problems


def check(root: Path) -> list[str]:
    """Compare ``HEAD`` with the index and return every release-policy violation."""
    lock_head = _load(root, "HEAD", "uv.lock")
    lock_staged = _load(root, "", "uv.lock")
    project_staged = _load(root, "", "pyproject.toml")
    problems = lock_problems(lock_head, lock_staged)
    problems.extend(pyproject_problems(_load(root, "HEAD", "pyproject.toml"), project_staged))
    version = project_staged.get("project", {}).get("version")
    roots = [package for package in lock_staged.get("package", []) if package.get("name") == PACKAGE]
    if len(roots) == 1 and roots[0].get("version") != version:
        problems.append(f"staged uv.lock {PACKAGE} version {roots[0].get('version')} differs from project {version}")
    return problems


def main() -> int:
    """Report release-policy violations of the staged release commit."""
    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
        ).stdout.strip()
    )
    try:
        problems = check(root)
    except (subprocess.CalledProcessError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        problems = [f"cannot read release files: {exc}"]
    for problem in problems:
        print(f"release_lock_guard: {problem}", file=sys.stderr)
    if problems:
        return 1
    print("release_lock_guard: staged release changes only the root version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
