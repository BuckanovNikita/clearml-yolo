"""Recognize the documented uncommitted ``[tool.uv.sources]`` override.

The pre-commit guard refuses unstaged tracked changes. The one tolerated exception is a
local dependency-source override: ``pyproject.toml`` whose working copy differs from the
index only inside ``[tool.uv.sources]`` tables, optionally with ``uv.lock`` beside it.
Every other nonblank line must stay identical to the index, so value, formatting or
comment edits elsewhere still count as unstaged inputs.

Exit status: 0 when every unstaged tracked path is such an override, 1 otherwise. Only
the standard library is used, so the guard can run it with any Python 3.11+ interpreter.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

PYPROJECT = "pyproject.toml"
LOCKFILE = "uv.lock"
SOURCES_TABLE = "tool.uv.sources"
_HEADER = re.compile(rb"^\[\[?\s*(?P<name>[^\]]+?)\s*\]\]?")
_SECTION_START = re.compile(rb"(?m)(?=^\[)")


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def _is_sources_section(section: bytes) -> bool:
    match = _HEADER.match(section)
    if match is None:
        return False
    name = re.sub(rb"\s*\.\s*", b".", match.group("name")).decode(errors="replace")
    return name == SOURCES_TABLE or name.startswith(f"{SOURCES_TABLE}.")


def _trailing_comments(section: bytes) -> list[bytes]:
    lines = section.splitlines()
    tail: list[bytes] = []
    while lines and (not lines[-1].strip() or lines[-1].lstrip().startswith(b"#")):
        tail.insert(0, lines.pop())
    return tail


def without_sources(content: bytes) -> list[bytes]:
    """Return the file's nonblank lines outside ``[tool.uv.sources]`` tables.

    Comment lines that follow the last entry of a source table introduce the next
    table, so they are kept. Blank lines carry no meaning and are dropped, so inserting
    or removing an override table does not count as a change of its neighbours.
    """
    lines: list[bytes] = []
    for section in _SECTION_START.split(content):
        lines.extend(_trailing_comments(section) if _is_sources_section(section) else section.splitlines())
    return [line for line in lines if line.strip()]


def is_sources_only_change(staged: bytes, working: bytes) -> bool:
    """Return whether ``working`` differs from ``staged`` only inside source tables."""
    try:
        tomllib.loads(working.decode())
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    return without_sources(staged) == without_sources(working)


def unstaged_paths(root: Path) -> list[str]:
    """Return tracked paths whose working copy differs from the index."""
    output = _git(root, "diff", "--name-only", "-z", "--ignore-submodules=none")
    return [path for path in output.decode().split("\0") if path]


def refusal(root: Path) -> str | None:
    """Explain why unstaged changes are not a pure source override, or return None."""
    paths = unstaged_paths(root)
    if not paths:
        return None
    others = sorted(set(paths) - {PYPROJECT, LOCKFILE})
    if others:
        return f"not a source override: {', '.join(others)}"
    if PYPROJECT not in paths:
        return f"{LOCKFILE} changed without a {PYPROJECT} source override"
    working = root / PYPROJECT
    if not working.is_file():
        return f"{PYPROJECT} is deleted in the working tree"
    if not is_sources_only_change(_git(root, "show", f":{PYPROJECT}"), working.read_bytes()):
        return f"{PYPROJECT} differs from the index outside [{SOURCES_TABLE}]"
    return None


def main() -> int:
    """Report whether the guard may tolerate the current unstaged changes."""
    root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
    reason = refusal(root)
    if reason is not None:
        print(f"source_override: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
