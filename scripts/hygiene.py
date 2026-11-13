"""Tracked-input hygiene and pre-stash staging safeguards, dispatched by Task."""

import argparse
import ast
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from scripts.verification import changes


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def staging_check() -> int:
    """Refuse every unstaged tracked or nonignored untracked input before prek."""
    dirty = git("diff", "--name-only", "--ignore-submodules=none", "-z")
    untracked = git("ls-files", "--others", "--exclude-standard", "-z")
    if dirty or untracked:
        print("Stage or ignore all inputs before committing; the guard never stashes:", file=sys.stderr)
        for path in (dirty + untracked).split(b"\0"):
            if path:
                print(f"  {path.decode()}", file=sys.stderr)
        return 1
    return 0


def syntax_problem(path: Path, text: str) -> str | None:
    try:
        match path.suffix:
            case ".py":
                ast.parse(text, filename=str(path))
            case ".toml":
                tomllib.loads(text)
            case ".yaml" | ".yml":
                YAML(typ="safe").load(text)
            case _:
                pass
    except (SyntaxError, tomllib.TOMLDecodeError, YAMLError) as exc:
        return f"{path}: {exc}"
    return None


def check_file(path: Path, max_bytes: int, sized: set[Path]) -> list[str]:
    """Binary files get the size check; text also gets syntax and safe fixes."""
    content = path.read_bytes()
    problems = []
    if path in sized and len(content) > max_bytes:
        problems.append(f"{path}: exceeds {max_bytes // 1024} KB")
    if b"\0" in content:
        return problems
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return problems
    if re.search(r"^(?:<<<<<<< |=======$|>>>>>>> )", text, re.MULTILINE):
        problems.append(f"{path}: merge conflict marker")
    problem = syntax_problem(path, text)
    if problem:
        problems.append(problem)
    fixed = re.sub(rb"[ \t]+(?=\r?$)", b"", content, flags=re.MULTILINE)
    if fixed:
        newline = b"\r\n" if b"\r\n" in fixed else b"\n"
        fixed = fixed.rstrip(b"\r\n")
        if fixed:
            fixed += newline
    if fixed != content:
        path.write_bytes(fixed)
        problems.append(f"{path}: whitespace/final newline fixed; inspect and stage")
    return problems


def added_files() -> set[Path]:
    """Preserve check-added-large-files eligibility, also on the committed tip."""
    scope, _ = changes(os.environ.get("CY_VERIFY_SCOPE", "auto"))
    if scope == "commit":
        raw = git("diff-tree", "--root", "--no-commit-id", "-m", "-r", "--diff-filter=A", "--name-only", "-z", "HEAD")
    else:
        args = ["--cached"] if scope == "staged" else ["HEAD"]
        raw = git("diff", *args, "--diff-filter=A", "--name-only", "-z")
    names = [name for name in raw.split(b"\0") if name]
    if not names:
        return set()
    attrs = subprocess.run(
        ["git", "check-attr", "filter", "-z", "--stdin"],
        input=b"\0".join(names),
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    return {Path(attrs[index].decode()) for index in range(0, len(attrs) - 1, 3) if attrs[index + 2] != b"lfs"}


def hygiene(max_kb: int, required: list[str]) -> int:
    problems = [f"Required input missing: {name}" for name in required if not Path(name).is_file()]
    sized = added_files()
    paths = [Path(name.decode()) for name in git("ls-files", "-z").split(b"\0") if name]
    for path in paths:
        # Deleted files and symlinks are not regular-file hook inputs. In particular,
        # never follow an instruction symlink out of this checkout while fixing text.
        if path.is_file() and not path.is_symlink():
            problems.extend(check_file(path, max_kb * 1024, sized))
    for problem in problems:
        print(problem, file=sys.stderr)
    return int(bool(problems))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "staging"))
    parser.add_argument("--max-kb", type=int, required=False)
    parser.add_argument("--required", nargs="*", default=[])
    args = parser.parse_args()
    if args.action == "staging":
        return staging_check()
    if args.max_kb is None:
        parser.error("check requires --max-kb from Task")
    return hygiene(args.max_kb, args.required)


if __name__ == "__main__":
    sys.exit(main())
