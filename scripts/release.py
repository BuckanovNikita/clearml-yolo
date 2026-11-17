"""Prepare a release PR, then publish only its verified merged-source version tag."""

import argparse
import fcntl
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

TAG_PATTERN = r"v[0-9]+\.[0-9]+\.[0-9]+"
RELEASE_PATHS = {"pyproject.toml", "uv.lock", "CHANGELOG.md"}


class ReleaseError(RuntimeError):
    """An input or repository state cannot safely complete this release."""


class CommitIdentity(BaseModel):
    oid: str


class PullRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    number: int
    state: str
    url: str
    base: str = Field(alias="baseRefName")
    branch: str = Field(alias="headRefName")
    head: str = Field(alias="headRefOid")
    cross_repository: bool = Field(alias="isCrossRepository")
    merged_at: str | None = Field(alias="mergedAt")
    merged: CommitIdentity | None = Field(alias="mergeCommit")
    commits: list[CommitIdentity]


PR_FIELDS = "number,state,url,baseRefName,headRefName,headRefOid,isCrossRepository,mergedAt,mergeCommit,commits"


def output(*command: str) -> str:
    """Run a read operation and return its stripped output."""
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


def run(*command: str, environment: dict[str, str] | None = None) -> None:
    """Run one stage, preserving its failure status for the caller."""
    subprocess.run(command, check=True, env=environment)


def commit(reference: str) -> str:
    """Resolve a reference without permitting option injection."""
    return output("git", "rev-parse", "--verify", "--end-of-options", f"{reference}^{{commit}}")


def require_tip(expected: str, *, clean: bool = True) -> None:
    if commit("HEAD") != expected:
        raise ReleaseError(f"HEAD moved from expected commit {expected}")
    if clean and output("git", "status", "--porcelain", "--untracked-files=all"):
        raise ReleaseError("release requires a clean committed tree")


def branch_name() -> str:
    return output("git", "rev-parse", "--abbrev-ref", "HEAD")


def require_branch(branch: str, expected: str, *, clean: bool = True) -> None:
    require_tip(expected, clean=clean)
    if branch_name() != branch or commit(f"refs/heads/{branch}") != expected:
        raise ReleaseError(f"release branch {branch} moved or is no longer checked out")


def require_ancestor(ancestor: str, descendant: str) -> None:
    result = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], check=False)
    if result.returncode:
        raise ReleaseError(f"{ancestor} is not an ancestor of {descendant}")


def fetch_master() -> str:
    run("git", "fetch", "origin", "--tags", "refs/heads/master:refs/remotes/origin/master")
    return commit("refs/remotes/origin/master")


def remote_ref(reference: str) -> str:
    value = output("git", "ls-remote", "--refs", "origin", reference)
    return value.split("\t", 1)[0] if value else ""


def require_remote_master(expected: str) -> None:
    if remote_ref("refs/heads/master") != expected:
        raise ReleaseError("remote master moved; review evidence and restart on the new source")


def version(reference: str = "HEAD") -> str:
    return str(tomllib.loads(output("git", "show", f"{reference}:pyproject.toml"))["project"]["version"])


def code_tag(value: str) -> str:
    if not re.fullmatch(TAG_PATTERN, value):
        raise ReleaseError(f"invalid stable code release tag: {value!r}")
    return value


def exists(reference: str) -> bool:
    result = subprocess.run(["git", "show-ref", "--verify", "--quiet", reference], check=False)
    if result.returncode not in (0, 1):
        raise ReleaseError(f"cannot inspect {reference}")
    return result.returncode == 0


@contextmanager
def release_lock() -> Iterator[None]:
    common = Path(output("git", "rev-parse", "--path-format=absolute", "--git-common-dir"))
    with (common / "clearml-yolo-release.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ReleaseError("release lock is held; no changes made") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def task(name: str) -> None:
    environment = dict(os.environ)
    environment.pop("SKIP", None)
    environment.pop("PREK_SKIP", None)
    run("uv", "run", "--locked", "task", "--exit-code", name, environment=environment)


def check_pair(pairing: str) -> None:
    if pairing == "required":
        task("paired-check")
    else:
        print("Pairing not required by the reviewed verification record")


def prepared(expected: str) -> None:
    """Validate the staged version exception around the selected pairing check."""
    branch = f"release/v{tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version']}"
    require_branch(branch, expected, clean=False)
    task("staging-check")
    if set(output("git", "diff", "--cached", "--name-only").splitlines()) - RELEASE_PATHS:
        raise ReleaseError("prepared release includes paths outside its version exception")
    run("uv", "run", "--locked", "python", "scripts/release_lock_guard.py")


def release_delta(base: str, head: str) -> None:
    """Validate actual committed version-only content, not PR labels or titles."""
    paths = set(output("git", "diff", "--name-only", base, head).splitlines())
    if not {"pyproject.toml", "uv.lock"} <= paths or paths - RELEASE_PATHS:
        raise ReleaseError("release changes must be limited to version, lock and changelog")
    if tuple(map(int, version(head).split("."))) <= tuple(map(int, version(base).split("."))):
        raise ReleaseError("release version must increase")
    run("uv", "run", "--locked", "python", "scripts/release_lock_guard.py", "--base", base, "--target", head)


def tag_object(tag: str, expected: str) -> str:
    reference = f"refs/tags/{code_tag(tag)}"
    identity = output("git", "rev-parse", "--verify", reference)
    if output("git", "cat-file", "-t", identity) != "tag" or commit(identity) != expected:
        raise ReleaseError(f"{tag} must be an annotated tag at {expected}")
    if tag != f"v{version(expected)}":
        raise ReleaseError("tag differs from the merged source version")
    return identity


def predicted_tag() -> str:
    return code_tag(output("uv", "run", "--locked", "semantic-release", "version", "--print-tag"))


@contextmanager
def calculation_branch(expected: str) -> Iterator[None]:
    """Give semantic-release a configured branch without moving existing branches."""
    previous = branch_name()
    temporary = f"release/preparing-{expected}"
    run("git", "switch", "--create", temporary, expected)
    try:
        yield
    finally:
        # Preserve an interrupted attempt's changed files or new commit for inspection.
        if branch_name() == temporary and commit("HEAD") == expected and not output("git", "status", "--porcelain"):
            if previous != "HEAD" and commit(f"refs/heads/{previous}") != expected:
                raise ReleaseError("original checkout branch moved; temporary release branch retained")
            run("git", "switch", "--detach", expected) if previous == "HEAD" else run("git", "switch", previous)
            run("git", "branch", "--delete", temporary)


def github_repository() -> str:
    """Bind GitHub API operations to the same origin receiving Git pushes."""
    fetch_urls = output("git", "remote", "get-url", "--all", "origin").splitlines()
    push_urls = output("git", "remote", "get-url", "--push", "--all", "origin").splitlines()
    if len(fetch_urls) != 1 or push_urls != fetch_urls:
        raise ReleaseError("origin must have one identical effective fetch and push destination")
    origin = fetch_urls[0]
    match = re.fullmatch(
        r"(?:git@github\.com:|https://github\.com/|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?",
        origin,
    )
    if match is None:
        raise ReleaseError("origin must be a GitHub SSH or HTTPS repository URL")
    return match[1]


def inspect_pr(number: str) -> PullRequest:
    return PullRequest.model_validate_json(
        output("gh", "pr", "view", number, "--repo", github_repository(), "--json", PR_FIELDS)
    )


def open_pr(branch: str, head: str, base: str, record: Path) -> None:
    """Push only the release branch and reuse its existing PR on retries."""
    require_branch(branch, head)
    require_remote_master(base)
    remote = remote_ref(f"refs/heads/{branch}")
    if remote and remote != head:
        raise ReleaseError("remote release branch differs; refusing to overwrite it")
    github_repository()
    run("git", "push", "--no-follow-tags", "origin", f"{head}:refs/heads/{branch}")
    if remote_ref(f"refs/heads/{branch}") != head:
        raise ReleaseError("release branch push could not be confirmed")
    require_branch(branch, head)
    require_remote_master(base)
    existing = output(
        "gh",
        "pr",
        "list",
        "--repo",
        github_repository(),
        "--head",
        branch,
        "--base",
        "master",
        "--state",
        "all",
        "--json",
        "number",
        "--jq",
        ".[].number",
    )
    if existing:
        if len(existing.splitlines()) != 1:
            raise ReleaseError("multiple release PRs match; resolve their ownership before retrying")
        pr = inspect_pr(existing)
        if (
            pr.state != "OPEN"
            or pr.head != head
            or pr.cross_repository
            or pr.base != "master"
            or pr.branch != branch
            or len(pr.commits) != 1
            or pr.commits[0].oid != head
        ):
            raise ReleaseError("existing release PR is closed, merged or has different source")
        require_branch(branch, head)
        require_remote_master(base)
        print(f"Release PR: {pr.url}")
        return
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8") as body:
        body.write(
            f"Prepare {branch.removeprefix('release/')} from `{base}`.\n\n"
            "## Verification evidence\n\n"
            f"{record.read_text(encoding='utf-8').strip()}\n\n"
            "Human merge required. Tag publication is a separate authorized command "
            "after merged-source verification.\n"
        )
        body.flush()
        run(
            "gh",
            "pr",
            "create",
            "--repo",
            github_repository(),
            "--base",
            "master",
            "--head",
            branch,
            "--title",
            f"chore(release): {version(head)}",
            "--body-file",
            body.name,
        )
    created = inspect_pr(branch)
    require_branch(branch, head)
    require_remote_master(base)
    if created.state != "OPEN" or created.head != head or created.base != "master" or created.cross_repository:
        raise ReleaseError("new PR identity could not be confirmed")
    print(f"Release PR: {created.url}")


def prepare_release(expected: str, pairing: str, record: Path) -> None:
    require_tip(expected)
    github_repository()
    base = fetch_master()
    require_tip(expected)
    branch = branch_name()
    if re.fullmatch(f"release/{TAG_PATTERN}", branch):
        parent = commit("HEAD^")
        if parent != base or output("git", "rev-list", "--parents", "-n", "1", expected).count(" ") != 1:
            raise ReleaseError("retry needs exactly one release commit on current origin/master")
        release_delta(base, expected)
        if branch != f"release/v{version(expected)}":
            raise ReleaseError("release branch name differs from version")
        check_pair(pairing)
        open_pr(branch, expected, base, record)
        return
    if expected != base:
        raise ReleaseError("preparation must start at current origin/master")
    with calculation_branch(expected):
        tag = predicted_tag()
        require_tip(expected)
        require_remote_master(base)
        if exists(f"refs/tags/{tag}"):
            target = commit(f"refs/tags/{tag}")
            identity = tag_object(tag, target)
            require_ancestor(target, expected)
            if tag != f"v{version(expected)}":
                raise ReleaseError("source version differs from existing release")
            check_pair(pairing)
            require_tip(expected)
            require_remote_master(base)
            if tag_object(tag, target) != identity:
                raise ReleaseError("existing version tag moved during verification")
            print(f"No new version; accepted source {expected}")
            return
        branch = f"release/{tag}"
        run("git", "branch", "--move", branch)
        environment = {
            **os.environ,
            "CY_RELEASE_CHECK": "1",
            "CY_RELEASE_EXPECTED_TIP": expected,
            "CY_RELEASE_PAIRING": pairing,
            "SKIP": "verify",
        }
        environment.pop("PREK_SKIP", None)
        run(
            "uv",
            "run",
            "--locked",
            "semantic-release",
            "version",
            "--no-tag",
            "--no-push",
            "--no-vcs-release",
            environment=environment,
        )
        released = commit("HEAD")
        if commit("HEAD^") != expected:
            raise ReleaseError("semantic-release must create exactly one version commit")
        require_branch(branch, released)
        release_delta(expected, released)
        if version(released) != tag.removeprefix("v") or exists(f"refs/tags/{tag}"):
            raise ReleaseError("prepared version differs from prediction or a premature tag appeared")
        open_pr(branch, released, base, record)


def merged_release(number: int, expected: str) -> PullRequest:
    pr = inspect_pr(str(number))
    if pr.state != "MERGED" or not pr.merged_at or pr.merged is None or pr.merged.oid != expected:
        raise ReleaseError("expected tip must be the GitHub-confirmed merged release PR commit")
    if pr.base != "master" or pr.cross_repository or pr.branch != f"release/v{version(expected)}":
        raise ReleaseError("release PR must target master from the matching repository release branch")
    run("git", "fetch", "origin", f"refs/pull/{number}/head")
    head = commit("FETCH_HEAD")
    if head != pr.head:
        raise ReleaseError("release PR head changed during validation")
    if output("git", "rev-list", "--parents", "-n", "1", head).count(" ") != 1:
        raise ReleaseError("release PR head must be a single-parent version commit")
    parent = commit(f"{head}^")
    require_ancestor(parent, expected)
    release_delta(parent, head)
    if output("git", "diff", head, expected, "--", *sorted(RELEASE_PATHS)):
        raise ReleaseError("merged release files differ from the reviewed PR head")
    if len(pr.commits) != 1 or pr.commits[0].oid != head:
        raise ReleaseError("release PR must contain exactly one version commit")
    return pr


def require_checkout(branch: str, expected: str) -> None:
    require_tip(expected)
    if branch_name() != branch:
        raise ReleaseError("checked-out branch changed during publication")
    if branch != "HEAD":
        require_branch(branch, expected)


def publish_release(expected: str, number: int, pairing: str) -> None:
    original = branch_name()
    require_checkout(original, expected)
    base = fetch_master()
    require_ancestor(expected, base)
    pr = merged_release(number, expected)
    tag = code_tag(f"v{version(expected)}")
    existing_tag = tag_object(tag, expected) if exists(f"refs/tags/{tag}") else None
    check_pair(pairing)
    require_checkout(original, expected)
    require_remote_master(base)
    if existing_tag is not None and tag_object(tag, expected) != existing_tag:
        raise ReleaseError("release tag moved during verification")
    if inspect_pr(str(number)) != pr:
        raise ReleaseError("release PR metadata changed during verification")
    tag = code_tag(f"v{version(expected)}")
    if not exists(f"refs/tags/{tag}"):
        with calculation_branch(expected):
            if predicted_tag() != tag:
                raise ReleaseError("semantic-release prediction differs from merged source version")
            require_tip(expected)
            require_remote_master(base)
            run(
                "uv",
                "run",
                "--locked",
                "semantic-release",
                "version",
                "--no-commit",
                "--no-changelog",
                "--skip-build",
                "--no-push",
                "--no-vcs-release",
            )
            require_tip(expected)
    identity = tag_object(tag, expected)
    require_checkout(original, expected)
    require_remote_master(base)
    remote = remote_ref(f"refs/tags/{tag}")
    if remote and remote != identity:
        raise ReleaseError("remote tag differs; refusing to replace it")
    github_repository()
    run("git", "push", "--no-follow-tags", "origin", f"{identity}:refs/tags/{tag}")
    if remote_ref(f"refs/tags/{tag}") != identity:
        raise ReleaseError("tag publication could not be confirmed")
    print(f"Published {tag} at merged release source {expected}; master was not pushed")


def expected_commit(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        raise ReleaseError("--expected-tip must be a full immutable commit SHA")
    return commit(value)


def verification_record(path: Path) -> Path:
    record = path.resolve()
    if not record.is_file() or not record.read_text(encoding="utf-8").strip():
        raise ReleaseError("verification record must be an existing nonempty UTF-8 file")
    print(f"Reviewed verification record: {record} (attestation, not machine-validated proof)")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparing = commands.add_parser("prepare")
    publishing = commands.add_parser("publish")
    publishing.add_argument("--pr", required=True, type=int)
    publishing.add_argument(
        "--publish", required=True, action="store_true", help="attest separate tag publishing authorization"
    )
    check = commands.add_parser("check-prepared")
    for operation in (preparing, publishing, check):
        operation.add_argument("--expected-tip", required=True)
        operation.add_argument("--pairing", choices=("required", "not-required"), required=True)
    for operation in (preparing, publishing):
        operation.add_argument("--verification-record", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command != "check-prepared":
            arguments.verification_record = arguments.verification_record.resolve()
        os.chdir(output("git", "rev-parse", "--show-toplevel"))
        expected = expected_commit(arguments.expected_tip)
        if arguments.command == "check-prepared":
            prepared(expected)
            return 0
        record = verification_record(arguments.verification_record)
        with release_lock():
            github_repository()
            if arguments.command == "prepare":
                prepare_release(expected, arguments.pairing, record)
            else:
                publish_release(expected, arguments.pr, arguments.pairing)
    except (ReleaseError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
