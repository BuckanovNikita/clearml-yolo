"""Write the release version into the root ``uv.lock`` entry without resolving.

semantic-release rewrites ``project.version`` in ``pyproject.toml`` and then runs this
script from its ``build_command``. The committed ``pyproject.toml`` cannot be re-locked
without the uncommitted ``[tool.uv.sources]`` override for ``external/`` (see
``scripts/lock_check.py``), so ``uv lock`` is never run here. Instead the single
``version`` token of the ``clearml-yolo`` package in ``uv.lock`` is replaced, keeping
every other byte. The script refuses unless ``pyproject.toml`` differs from ``HEAD`` only
by that same version token and ``uv.lock`` is still the ``HEAD`` content (or already
carries exactly this patch).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

RELEASE_VERSION = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")
_SECTION_START = re.compile(rb"(?m)(?=^\[)")
_VERSION_LINE = re.compile(rb"(?m)^[ \t]*version[ \t]*=[ \t]*[\"'](?P<version>[^\"']+)[\"']")


class ReleaseVersionError(Exception):
    """The release files are not in the state this step expects."""


def _git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def version_bytes(content: bytes, version: str, *, lock: bool, name: str) -> bytes:
    """Replace exactly one root version token without normalizing other file bytes.

    With ``lock`` the token is the ``version`` of the ``[[package]]`` named ``name``;
    otherwise it is ``version`` in the ``[project]`` table.
    """
    sections = _SECTION_START.split(content)
    matches: list[tuple[int, re.Match[bytes]]] = []
    for index, section in enumerate(sections):
        if lock:
            selected = (
                section.startswith(b"[[package]]")
                and tomllib.loads(section.decode()).get("package", [{}])[0].get("name") == name
            )
        else:
            selected = section.startswith(b"[project]")
        if selected:
            matches.extend((index, match) for match in _VERSION_LINE.finditer(section))
    if len(matches) != 1:
        raise ReleaseVersionError(f"cannot identify exactly one root version token for {name}")
    index, match = matches[0]
    start, end = match.span("version")
    sections[index] = sections[index][:start] + version.encode() + sections[index][end:]
    return b"".join(sections)


def root_lock_package(lock: bytes, name: str) -> dict[str, object]:
    """Return the single ``[[package]]`` entry of the project in ``lock``."""
    packages = [package for package in tomllib.loads(lock.decode()).get("package", []) if package.get("name") == name]
    if len(packages) != 1:
        raise ReleaseVersionError(f"uv.lock must contain exactly one {name} package, found {len(packages)}")
    package: dict[str, object] = packages[0]
    return package


def patch_lock(root: Path, expected_version: str | None = None) -> bool:
    """Patch the root ``uv.lock`` version to the working ``pyproject.toml`` version.

    Return whether ``uv.lock`` was written; an already patched lock is left as is.
    """
    head_pyproject = _git_bytes(root, "show", "HEAD:pyproject.toml")
    project = tomllib.loads(head_pyproject.decode())["project"]
    name: str = project["name"]
    old: str = project["version"]
    working_pyproject = (root / "pyproject.toml").read_bytes()
    new: str = tomllib.loads(working_pyproject.decode())["project"]["version"]
    if not RELEASE_VERSION.fullmatch(new):
        raise ReleaseVersionError(f"unexpected release version {new!r}")
    if expected_version is not None and new != expected_version:
        raise ReleaseVersionError(f"pyproject.toml has {new}, semantic-release announced {expected_version}")
    if working_pyproject != version_bytes(head_pyproject, new, lock=False, name=name):
        raise ReleaseVersionError(
            "pyproject.toml differs from HEAD beyond project.version; "
            "releases carry no local source overrides or other edits"
        )
    head_lock = _git_bytes(root, "show", "HEAD:uv.lock")
    package = root_lock_package(head_lock, name)
    if package.get("source") != {"editable": "."}:
        raise ReleaseVersionError(f"uv.lock {name} entry must have source editable '.'")
    if package.get("version") != old:
        raise ReleaseVersionError(f"uv.lock {name} version {package.get('version')} differs from HEAD {old}")
    expected = version_bytes(head_lock, new, lock=True, name=name)
    path = root / "uv.lock"
    current = path.read_bytes()
    if current == expected:
        return False
    if current != head_lock:
        raise ReleaseVersionError("uv.lock differs from HEAD; restore it before releasing")
    path.write_bytes(expected)
    return True


def main() -> int:
    """Patch ``uv.lock`` for the version semantic-release just wrote."""
    root = Path(_git_bytes(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
    try:
        written = patch_lock(root, os.environ.get("NEW_VERSION") or None)
    except (ReleaseVersionError, KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"release_version: {exc}", file=sys.stderr)
        return 1
    print("release_version: uv.lock root version " + ("updated" if written else "already current"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
