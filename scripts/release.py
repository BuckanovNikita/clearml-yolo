"""Serialize explicit local releases and publication without persisting check receipts."""

import argparse
import fcntl
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class ReleaseError(RuntimeError):
    """An input or repository state cannot safely complete this release."""


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
    """Refuse moved refs or changed inputs at every stage boundary."""
    if commit("HEAD") != expected:
        raise ReleaseError(f"HEAD moved from expected commit {expected}")
    if clean and output("git", "status", "--porcelain", "--untracked-files=all"):
        raise ReleaseError("release requires a clean committed tree")


def require_ancestor(ancestor: str, descendant: str) -> None:
    """Require an actual fast-forward rather than rewriting either history."""
    result = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], check=False)
    if result.returncode:
        raise ReleaseError(f"{ancestor} is not an ancestor of {descendant}; fast-forward refused")


@contextmanager
def release_lock() -> Iterator[None]:
    """Hold the repository-wide lock across validation, versioning and optional push."""
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
    """Explicit stages run independently of automatic change classification."""
    environment = dict(os.environ)
    environment.pop("SKIP", None)
    environment.pop("PREK_SKIP", None)
    run("uv", "run", "--locked", "task", "--exit-code", name, environment=environment)


def check_pair(pairing: str) -> None:
    """Execute only the explicitly selected final-source compatibility check."""
    if pairing == "required":
        task("paired-check")
    elif pairing == "not-required":
        print("Pairing not required by the reviewed verification record")
    else:
        raise ReleaseError("pairing decision must be required or not-required")


def prepared(expected: str) -> None:
    """Recheck mutable release inputs immediately around final paired verification."""
    require_master(expected, clean=False)
    run("uv", "run", "--locked", "task", "--exit-code", "staging-check")
    paths = output("git", "diff", "--cached", "--name-only").splitlines()
    if set(paths) - {"pyproject.toml", "uv.lock", "CHANGELOG.md"}:
        raise ReleaseError("prepared release includes paths outside its version exception")
    run("uv", "run", "--locked", "python", "scripts/release_lock_guard.py")


def tag_object(tag: str, expected: str, *, allow_ancestor: bool = False) -> str:
    """Validate the source-version tag at the accepted tip or its release ancestor."""
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", tag):
        raise ReleaseError(f"invalid code release tag: {tag}")
    reference = f"refs/tags/{tag}"
    identity = output("git", "rev-parse", "--verify", reference)
    if output("git", "cat-file", "-t", identity) != "tag":
        raise ReleaseError(f"{tag} must be an annotated release tag")
    target = commit(identity)
    if allow_ancestor:
        require_ancestor(target, expected)
    elif target != expected:
        raise ReleaseError(f"{tag} must point at {expected}")
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if tag != f"v{version}":
        raise ReleaseError(f"tag {tag} differs from source version {version}")
    tagged_version = tomllib.loads(output("git", "show", f"{target}:pyproject.toml"))["project"]["version"]
    if tagged_version != version:
        raise ReleaseError(f"tag {tag} has tagged source version {tagged_version}, expected {version}")
    return identity


def require_master(expected: str, *, clean: bool = True) -> None:
    """Keep the checked-out branch and its ref bound to the intended release."""
    require_tip(expected, clean=clean)
    if output("git", "symbolic-ref", "--short", "HEAD") != "master" or commit("refs/heads/master") != expected:
        raise ReleaseError("master moved or is no longer checked out")


def publish(expected: str, tag: tuple[str, str]) -> None:
    """Push exact intended refs atomically and verify their remote identities."""
    require_master(expected)
    require_ancestor("refs/remotes/origin/master", expected)
    refs = {"refs/heads/master": expected}
    refspecs = [f"{expected}:refs/heads/master"]
    name, identity = tag
    reference = f"refs/tags/{name}"
    if tag_object(name, expected, allow_ancestor=True) != identity:
        raise ReleaseError(f"tag {name} moved after validation")
    refs[reference] = identity
    refspecs.append(f"{identity}:{reference}")
    run("git", "push", "--atomic", "origin", *refspecs)
    remote = output("git", "ls-remote", "origin", *refs)
    observed = dict(line.split("\t", 1)[::-1] for line in remote.splitlines())
    if observed != refs:
        raise ReleaseError(f"remote confirmation failed for {', '.join(refs)}")
    print(f"Confirmed remote refs: {', '.join(refs)}")


def validate_and_integrate(expected: str, branch: str | None) -> None:
    """Accept unchanged branch inputs before advancing the unchanged master ref."""
    require_tip(expected)
    checked_out = output("git", "symbolic-ref", "--short", "HEAD")
    selected = branch or checked_out
    if commit(f"refs/heads/{selected}") != expected:
        raise ReleaseError(f"branch {selected} moved from {expected}")
    run("git", "fetch", "origin", "--tags", "refs/heads/master:refs/remotes/origin/master")
    require_ancestor("refs/remotes/origin/master", expected)
    master_tip = commit("refs/heads/master")
    require_ancestor(master_tip, expected)
    tag_refs = output("git", "for-each-ref", "--format=%(refname) %(objectname)", "refs/tags/v*")
    require_tip(expected)
    if output("git", "symbolic-ref", "--short", "HEAD") != checked_out:
        raise ReleaseError("checked-out branch changed during validation")
    if commit(f"refs/heads/{selected}") != expected:
        raise ReleaseError(f"branch {selected} moved during validation")
    if commit("refs/heads/master") != master_tip:
        raise ReleaseError("master moved during validation")
    if output("git", "for-each-ref", "--format=%(refname) %(objectname)", "refs/tags/v*") != tag_refs:
        raise ReleaseError("version tags changed during validation")
    run("git", "switch", "master")
    require_master(master_tip)
    run("git", "merge", "--ff-only", expected)
    require_master(expected)


def local_release(expected: str, branch: str | None, *, push: bool, pairing: str) -> None:
    """Integrate the accepted tip and let semantic-release alone create a version."""
    validate_and_integrate(expected, branch)
    predicted = output("uv", "run", "--locked", "semantic-release", "version", "--print-tag")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", predicted):
        raise ReleaseError(f"unexpected semantic-release tag output: {predicted!r}")
    exists = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{predicted}"], check=False
    ).returncode
    if exists == 0:
        identity = tag_object(predicted, expected, allow_ancestor=True)
        check_pair(pairing)
        require_master(expected)
        if tag_object(predicted, expected, allow_ancestor=True) != identity:
            raise ReleaseError(f"tag {predicted} moved during paired verification")
        print(f"No new version; accepted tip {expected}")
        released_tag = (predicted, identity)
    elif exists == 1:
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
            "--no-push",
            "--no-vcs-release",
            environment=environment,
        )
        released = commit("HEAD")
        if commit("HEAD^") != expected:
            raise ReleaseError("semantic-release did not create exactly one commit on the accepted tip")
        identity = tag_object(predicted, released)
        require_master(released)
        released_tag = (predicted, identity)
        print(f"Local release: {predicted} at {released}")
    else:
        raise ReleaseError("cannot inspect the predicted release tag")
    if push:
        publish(commit("HEAD"), released_tag)


def publish_existing(expected: str, tag: str | None, *, pairing: str) -> None:
    """Publish an existing version with reviewed evidence and the selected pairing check."""
    require_tip(expected)
    if output("git", "symbolic-ref", "--short", "HEAD") != "master":
        raise ReleaseError("later publication requires the expected tip checked out on master")
    if tag is None:
        version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        tag = f"v{version}"
    selected_tag = (tag, tag_object(tag, expected, allow_ancestor=True))
    run("git", "fetch", "origin", "--tags", "refs/heads/master:refs/remotes/origin/master")
    require_ancestor("refs/remotes/origin/master", expected)
    check_pair(pairing)
    require_tip(expected)
    publish(expected, selected_tag)


def expected_commit(value: str) -> str:
    """Require immutable identity rather than a branch that can move during checks."""
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        raise ReleaseError("--expected-tip must be a full immutable commit SHA")
    return commit(value)


def verification_record(path: Path, pairing: str) -> None:
    """Require an evidence file without pretending to validate its reviewed contents."""
    record = path.resolve()
    if not record.is_file():
        raise ReleaseError(f"verification record must be an existing regular file: {record}")
    print(f"Reviewed verification record: {record} (attestation, not machine-validated proof)")
    print(f"Pairing decision: {pairing}")


def main() -> int:
    """Expose explicit local and publish operations with mandatory expected identity."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    local = commands.add_parser("local")
    local.add_argument("--expected-tip", required=True)
    local.add_argument("--branch")
    local.add_argument("--publish", action="store_true", help="publish now; requires separate push authorization")
    publishing = commands.add_parser("publish")
    publishing.add_argument("--expected-tip", required=True)
    publishing.add_argument("--tag")
    check = commands.add_parser("check-prepared")
    check.add_argument("--expected-tip", required=True)
    for operation in (local, publishing):
        operation.add_argument(
            "--verification-record",
            type=Path,
            required=True,
            help="existing reviewed evidence file; its contents are not validated as proof",
        )
        operation.add_argument("--pairing", choices=("required", "not-required"), required=True)
    check.add_argument("--pairing", choices=("required", "not-required"), required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command != "check-prepared":
            verification_record(arguments.verification_record, arguments.pairing)
        os.chdir(output("git", "rev-parse", "--show-toplevel"))
        expected = expected_commit(arguments.expected_tip)
        if arguments.command == "check-prepared":
            prepared(expected)
            return 0
        with release_lock():
            if arguments.command == "local":
                local_release(expected, arguments.branch, push=arguments.publish, pairing=arguments.pairing)
            else:
                publish_existing(expected, arguments.tag, pairing=arguments.pairing)
    except (ReleaseError, OSError, subprocess.CalledProcessError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return exc.returncode if isinstance(exc, subprocess.CalledProcessError) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
