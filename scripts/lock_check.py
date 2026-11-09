"""Check lock freshness for the staged project, independent of local source overrides.

The committed ``pyproject.toml`` declares ``digital-metrics`` and ``report-generator``
by version only; the committed ``uv.lock`` records them as editable copies under
``external/``. Contributors may keep the matching ``[tool.uv.sources]`` override
uncommitted, so the working copy cannot represent what is being committed. This check
copies the index versions of the lock inputs into a temporary directory, adds the
canonical external sources when the staged project does not declare them, links
``external/`` and runs ``uv lock --check`` there. It never resolves into the worktree.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

LOCK_INPUTS = ("pyproject.toml", "uv.lock", "README.md")
EXTERNAL_SOURCES = {
    "digital-metrics": "external/digital-metrics",
    "report-generator": "external/report-generator",
}


def staged_bytes(root: Path, path: str) -> bytes:
    """Return the index content of ``path``."""
    return subprocess.run(
        ["git", "-C", str(root), "show", f":{path}"],
        check=True,
        capture_output=True,
    ).stdout


def with_external_sources(pyproject: bytes) -> bytes:
    """Append canonical editable external sources unless the project declares sources."""
    document = tomllib.loads(pyproject.decode())
    if "sources" in document.get("tool", {}).get("uv", {}):
        return pyproject
    lines = ["", "[tool.uv.sources]"]
    lines.extend(f'{name} = {{ path = "{path}", editable = true }}' for name, path in EXTERNAL_SOURCES.items())
    return pyproject.rstrip(b"\n") + b"\n" + "\n".join(lines).encode() + b"\n"


def main() -> int:
    """Run ``uv lock --check`` on the staged lock inputs."""
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    missing = [path for path in EXTERNAL_SOURCES.values() if not (root / path).is_dir()]
    if missing:
        print(f"lock_check: populate external sources first: {', '.join(missing)}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="clearml-yolo-lock-check-") as scratch:
        directory = Path(scratch)
        for path in LOCK_INPUTS:
            content = staged_bytes(root, path)
            if path == "pyproject.toml":
                content = with_external_sources(content)
            (directory / path).write_bytes(content)
        (directory / "external").symlink_to(root / "external", target_is_directory=True)
        return subprocess.run(["uv", "lock", "--check", "--directory", str(directory)], check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
