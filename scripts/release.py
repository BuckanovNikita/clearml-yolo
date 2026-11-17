"""Publish a metadata-only semantic release from the merged master branch.

The GitHub workflow owns merge authorization and serialization. This runner never
merges branches or overwrites remote history; its only push is an atomic commit/tag pair.
"""

import subprocess
import sys
import tomllib
from pathlib import Path

from scripts.release_lock_guard import check

RELEASE_PATHS = {"pyproject.toml", "uv.lock", "CHANGELOG.md"}
MASTER = "refs/heads/master"


def output(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def remote_ref(ref: str) -> str:
    rows = output("git", "ls-remote", "--refs", "origin", ref).splitlines()
    if len(rows) > 1:
        raise ValueError(f"ambiguous remote ref: {ref}")
    return rows[0].split()[0] if rows else ""


def require_clean() -> None:
    if output("git", "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("release requires a clean checkout")
    if output("git", "symbolic-ref", "HEAD") != MASTER:
        raise ValueError("release requires master checked out")


def validate_release(base: str, released: str) -> tuple[str, str]:
    if output("git", "rev-list", "--parents", "-n", "1", released) != f"{released} {base}":
        raise ValueError("semantic-release must create exactly one commit on the selected source")
    changed = set(output("git", "diff", "--name-only", base, released).splitlines())
    if not changed <= RELEASE_PATHS or "pyproject.toml" not in changed:
        raise ValueError(f"unexpected release paths: {sorted(changed)}")
    problems = check(Path.cwd(), base, released)
    if problems:
        raise ValueError("; ".join(problems))
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    tag = f"v{version}"
    if output("git", "cat-file", "-t", f"refs/tags/{tag}") != "tag":
        raise ValueError("release tag must be annotated")
    if output("git", "rev-parse", f"refs/tags/{tag}^{{commit}}") != released:
        raise ValueError("release tag must target the release commit")
    return tag, output("git", "rev-parse", f"refs/tags/{tag}")


def release() -> None:
    if len(sys.argv) != 1:
        raise ValueError("local release subcommands are retired; releases run in GitHub Actions")
    require_clean()
    # Refuse configuration that could publish to a different or multiple destinations.
    destination = output("git", "remote", "get-url", "origin")
    if output("git", "remote", "get-url", "--push", "--all", "origin").splitlines() != [destination]:
        raise ValueError("origin must have one identical fetch and push destination")
    run("git", "fetch", "--tags", "origin", f"{MASTER}:refs/remotes/origin/master")
    base = output("git", "rev-parse", "HEAD")
    if remote_ref(MASTER) != base:
        raise ValueError("checkout differs from remote master; rerun with a fresh checkout")
    run("semantic-release", "version", "--no-push", "--no-vcs-release")
    require_clean()
    released = output("git", "rev-parse", "HEAD")
    if remote_ref(MASTER) != base:
        raise ValueError("remote master moved during preparation; rerun with a fresh checkout")
    if released == base:
        print(f"No new version at {base}")
        return
    tag, identity = validate_release(base, released)
    if remote_ref(f"refs/tags/{tag}"):
        raise ValueError(f"remote tag {tag} already exists; refusing to replace it")
    run("git", "push", "--atomic", "--no-follow-tags", "origin", f"{released}:{MASTER}", f"{identity}:refs/tags/{tag}")
    if remote_ref(MASTER) != released or remote_ref(f"refs/tags/{tag}") != identity:
        raise ValueError("publication identity could not be confirmed; inspect remote refs before retrying")
    print(f"Published {tag}: commit {released}, annotated tag {identity}")


def main() -> int:
    try:
        release()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
