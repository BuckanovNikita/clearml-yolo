"""Synchronize only the root lock version during semantic-release preparation."""

import os
import re
import subprocess
import tomllib
from pathlib import Path

from scripts.release_lock_guard import lock_problems


def main() -> None:
    version = os.environ["NEW_VERSION"]
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    if project["project"]["version"] != version or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("semantic-release version must match project.version and be a stable version")
    path = Path("uv.lock")
    original = path.read_text(encoding="utf-8")
    before = tomllib.loads(original)
    roots = [package for package in before["package"] if package["name"] == project["project"]["name"]]
    if len(roots) != 1:
        raise ValueError("lock must contain exactly one root package")
    pattern = r'(?m)(^\[\[package\]\]\nname = "clearml-yolo"\nversion = ")[^"]+("$)'
    updated, count = re.subn(pattern, lambda match: f"{match[1]}{version}{match[2]}", original)
    if count != 1:
        raise ValueError("cannot locate the root lock version unambiguously")
    problems = lock_problems(before, tomllib.loads(updated))
    if problems:
        raise ValueError("; ".join(problems))
    path.write_text(updated, encoding="utf-8")
    subprocess.run(["git", "add", "--", "uv.lock"], check=True)


if __name__ == "__main__":
    main()
