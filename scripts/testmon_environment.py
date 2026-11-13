"""Print the affected-test environment fingerprint, run from the repository root."""

import hashlib
import platform
import subprocess
import sys
from pathlib import Path


def fingerprint() -> str:
    """Include non-Python inputs while leaving Python dependencies to testmon."""
    digest = hashlib.sha256()
    digest.update(repr((sys.version, sys.executable, platform.platform())).encode())
    listed = (
        subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"])
        .decode()
        .split("\0")
    )
    paths = {Path(name) for name in listed if name}
    # Ignored fixture assets and package data can also affect tests.
    paths.update(Path("tests/fixtures").rglob("*"))
    paths.update(Path("src/clearml_yolo").rglob("*"))
    configs = {
        "uv.lock",
        "Taskfile.yml",
        "Taskfile.ops.yml",
        ".pre-commit-config.yaml",
        ".python-version",
        ".importlinter",
        "ruff.toml",
    }
    for path in sorted(paths):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        in_tree = path.parts[0] in {"src", "tests", "scripts"}
        config = path.name in configs or path.suffix in {".toml", ".ini", ".cfg"}
        if not (in_tree or config):
            continue
        digest.update(path.as_posix().encode() + b"\0")
        # Python execution dependencies stay with testmon. Scripts are
        # orchestration inputs, so changes conservatively invalidate.
        if path.suffix != ".py" or path.parts[0] == "scripts":
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> None:
    print(fingerprint())


if __name__ == "__main__":
    main()
