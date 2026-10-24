"""Run repository checks once per verified input view; keep evidence private to Git."""

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any, NoReturn
from urllib.parse import unquote, urlsplit

RELEASE_FILES = {"pyproject.toml", "uv.lock", "CHANGELOG.md"}
NOISE = {
    "_", "SHLVL", "OLDPWD", "PRE_COMMIT",
    "CLEARML_YOLO_RELEASE_ACTIVE", "UV_RUN_RECURSION_DEPTH", "CODEX_TOOL_CALL_ID",
}
CACHES = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".hypothesis",
    ".grimp_cache",
    ".import_linter_cache",
}
GENERATED = CACHES | {
    ".venv",
    ".cache",
    ".tmp",
    ".cy",
    ".cy-queue",
    "mutants",
    "build",
    "dist",
    "outputs",
    "runs",
    "multirun",
}


class VerificationError(Exception):
    """Checks or their input/evidence boundary could not be verified."""


@dataclass(frozen=True)
class Fingerprint:
    content: str
    stability: str
    physical: str


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(  # noqa: S603 - fixed Git arguments, never a shell
        ["git", "-C", str(root), *args],  # noqa: S607 - required repository tool
        check=True,
        capture_output=True,
    ).stdout


def private_directory(root: Path) -> Path:
    path = git(root, "rev-parse", "--path-format=absolute", "--git-path", "verification")
    return Path(os.fsdecode(path).strip())


def environment(root: Path) -> dict[str, str]:
    # Git's temporary index belongs to the hook view, not nested test repositories.
    # These values are removed from the actual checking environment as well as its hash.
    result = {
        key: value
        for key, value in os.environ.items()
        if key not in NOISE and not key.startswith("GIT_")
    }
    # Git prepends its private helper directory when launching hooks. It is not
    # needed to locate public tools and must not distinguish manual checks.
    git_helpers = os.fsdecode(git(root, "--exec-path")).strip()
    # Nested uv adds its bin directory again; retain the first lookup position.
    entries = result.get("PATH", os.defpath).split(os.pathsep)
    result["PATH"] = os.pathsep.join(dict.fromkeys(item for item in entries if item != git_helpers))
    result["PWD"] = str(root)
    return result


def governed(path: str) -> bool:
    parts = Path(path).parts
    if not parts or parts[0] in GENERATED:
        return False
    return parts[0] not in {
        "docs", "specs", ".specify", ".agents", ".claude", ".codex", ".superpowers",
        "README.md", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "TECH_DETAILS.md",
    } and Path(path).suffix not in {".pyc", ".pyo"}


def repository_files(root: Path) -> list[str]:
    paths = set(os.fsdecode(git(
        root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"
    )).split("\0")) - {""}
    paths.update(path.name for path in root.iterdir() if not path.is_dir())
    for area in root.iterdir():
        if area.is_dir() and governed(area.name):
            paths.update(str(path.relative_to(root)) for path in tree_files(area))
    return sorted(paths)


def tree_files(root: Path, *, editable: bool = False) -> Iterator[Path]:
    """Include editable source and package data, including untracked local edits."""
    pending, seen = [root], set[tuple[int, int]]()
    while pending:
        directory = pending.pop()
        if directory.is_symlink():
            yield directory
        if not directory.is_dir():
            continue
        info = directory.stat()
        identity = info.st_dev, info.st_ino
        if identity in seen:
            continue
        seen.add(identity)
        for path in sorted(directory.iterdir()):
            if path.is_dir():
                if path.name not in CACHES and not (
                    editable and directory == root and path.name == ".venv"
                ):
                    pending.append(path)
            elif path.suffix not in {".pyc", ".pyo"}:
                yield path


def dependency_files(root: Path) -> Iterator[Path]:  # noqa: C901 - installed files, owned trees and editable roots need distinct inventories
    trees: set[tuple[Path, bool]] = set()
    for distribution in importlib.metadata.distributions():
        if distribution.files is None:
            raise VerificationError(f"Missing installed file inventory: {distribution.name}")
        for item in distribution.files:
            path = Path(str(distribution.locate_file(item))).absolute()
            if path.suffix not in {".pyc", ".pyo"}:
                yield path
            if len(item.parts) > 1 and not item.is_absolute() and item.parts[0] != "..":
                trees.add((Path(str(distribution.locate_file(item.parts[0]))).absolute(), False))
        direct = json.loads(distribution.read_text("direct_url.json") or "{}")
        if direct.get("dir_info", {}).get("editable"):
            url = urlsplit(direct["url"])
            if url.scheme != "file" or url.netloc not in {"", "localhost"}:
                raise VerificationError("An editable dependency has no local source inventory")
            source = Path(unquote(url.path)).resolve()
            if source != root:
                if not source.is_dir():
                    raise VerificationError(f"Missing editable dependency: {source}")
                trees.add((source, True))
    for tree, editable in sorted(trees):
        yield from tree_files(tree, editable=editable)


def file_stamp(path: Path) -> tuple[int, ...] | None:
    try:
        link = path.lstat()
    except FileNotFoundError:
        return None
    try:
        info = path.stat()
    except FileNotFoundError:
        info = link
    if stat.S_ISDIR(info.st_mode):
        info = link  # Directory contents are inventoried; generated cache mtimes are not inputs.
    return (
        info.st_mode,
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        link.st_ino,
        link.st_ctime_ns,
    )


def file_identity(path: Path) -> tuple[str, str]:
    """Hash bytes, not RECORD claims or mtimes; detect edits during the read itself."""
    before = file_stamp(path)
    if before is None:
        return "missing", repr(before)
    link = str(path.readlink()) if path.is_symlink() else ""
    if link and not path.exists():
        digest = "missing-target"
    elif path.is_dir():
        digest = "directory"
    else:
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if before != file_stamp(path):
        raise VerificationError(f"Input changed while reading: {path}")
    return f"{stat.S_IMODE(before[0])}:{link}:{digest}", repr(before)


def version_bytes(content: bytes, version: str, *, lock: bool, name: str) -> bytes:
    """Replace exactly one root version token without normalizing other file bytes."""
    sections = re.split(rb"(?m)(?=^\[)", content)
    matches: list[tuple[int, re.Match[bytes]]] = []
    root_package = False
    for index, section in enumerate(sections):
        if lock and section.startswith(b"[[package]]"):
            root_package = (
                tomllib.loads(section.decode()).get("package", [{}])[0].get("name") == name
            )
        selected = root_package if lock else section.startswith(b"[project]")
        if selected:
            matches.extend(
                (index, match)
                for match in re.finditer(
                    rb"(?m)^[ \t]*version[ \t]*=[ \t]*[\"'](?P<version>[^\"']+)[\"']", section
                )
            )
        root_package = False
    if len(matches) != 1:
        raise VerificationError("Cannot identify exactly one root package version token")
    index, match = matches[0]
    start, end = match.span("version")
    sections[index] = sections[index][:start] + version.encode() + sections[index][end:]
    return b"".join(sections)


def release_basis(root: Path) -> dict[str, tuple[bytes, bytes]]:  # noqa: PLR0911 - independent ownership proofs fail closed
    """Normalize only a recorded, byte-validated metadata release, never arbitrary versions."""
    record_path = Path(
        os.fsdecode(
            git(
                root,
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "clearml-yolo-release.json",
            )
        ).strip()
    )
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        source, version, changelog = (
            record[key] for key in ("source", "version", "changelog_sha256")
        )
        if not re.fullmatch(r"[0-9a-f]{40,64}", source) or not re.fullmatch(
            r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version
        ):
            return {}
        head = git(root, "rev-parse", "HEAD").decode().strip()
        if head != source:
            if git(root, "rev-list", "--parents", "-n", "1", "HEAD").decode().split()[1:] != [
                source
            ]:
                return {}
            if (
                git(root, "log", "-1", "--format=%s").decode().strip()
                != f"chore(release): {version}"
            ):
                return {}
        changed = set(git(root, "diff", source, "--name-only").decode().splitlines())
        if not git(root, "ls-files", "--", "CHANGELOG.md").strip():
            changed.add("CHANGELOG.md")
        if (
            changed != RELEASE_FILES
            or hashlib.sha256((root / "CHANGELOG.md").read_bytes()).hexdigest() != changelog
        ):
            return {}
        before = {
            path: git(root, "show", f"{source}:{path}") for path in ("pyproject.toml", "uv.lock")
        }
        project = tomllib.loads(before["pyproject.toml"].decode())["project"]
        validated: dict[str, tuple[bytes, bytes]] = {}
        for path, content in before.items():
            expected = version_bytes(content, version, lock=path == "uv.lock", name=project["name"])
            if (root / path).read_bytes() != expected:
                return {}
            validated[path] = (content, expected)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        VerificationError,
        subprocess.CalledProcessError,
    ):
        return {}
    return validated


def require_index_view(root: Path, files: Sequence[str]) -> None:
    index: dict[str, tuple[str, str]] = {}
    for entry in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if entry:
            metadata, encoded_name = entry.split(b"\t", 1)
            mode, digest, stage = metadata.decode().split()
            if stage != "0":
                raise VerificationError("The index contains unresolved merge entries")
            index[os.fsdecode(encoded_name)] = (mode, digest)
    links = {name for name, (mode, _) in index.items() if mode == "120000"}
    untracked = set(os.fsdecode(git(
        root, "ls-files", "-z", "--others", "--exclude-standard"
    )).split("\0"))
    for name in files:
        if not governed(name) or any(str(parent) in links for parent in Path(name).parents):
            continue
        path = root / name
        owned_code = (path.parent == root or Path(name).parts[0] in {"src", "tests", "scripts"})
        if name not in index and name not in untracked and not (
            owned_code and path.suffix in {".py", ".ini", ".toml", ".cfg"}
        ):
            continue  # Ignored fixture data is fingerprinted as an external local input.
        if not os.path.lexists(path) or name not in index:
            raise VerificationError(
                f"Stage the complete governed file view before committing: {name}"
            )
        data = os.fsencode(path.readlink()) if path.is_symlink() else path.read_bytes()
        hashed = (
            subprocess.run(  # noqa: S603 - hash supplied bytes without filters
                ["git", "-C", str(root), "hash-object", "--stdin"],  # noqa: S607
                input=data,
                capture_output=True,
                check=True,
            )
            .stdout.decode()
            .strip()
        )
        mode = (
            "120000"
            if path.is_symlink()
            else "100755"
            if path.stat().st_mode & stat.S_IXUSR
            else "100644"
        )
        if index[name] != (mode, hashed):
            raise VerificationError(f"Index and checked worktree differ: {name}")


def input_paths(root: Path, files: Sequence[str], *, docs: bool) -> set[Path]:
    inputs = (
        {
            root / name
            for name in files
            if (Path(name).suffix == ".md" or name == "scripts/check_docs.py")
        }
        if docs
        else {root / name for name in files if governed(name) and os.path.lexists(root / name)}
    )
    if not docs:
        inputs.update(dependency_files(root))
    inputs.update({Path(sys.executable), Path(__file__).resolve()})
    return inputs


def fingerprint(
    root: Path, commands: Sequence[Sequence[str]], *, hook: bool, docs: bool = False
) -> Fingerprint:
    files = repository_files(root)
    if hook:
        require_index_view(root, files)
    replacements = {} if docs else release_basis(root)
    content = hashlib.sha256(
        json.dumps(
            {
                "environment": environment(root),
                "commands": commands,
                "python": sys.version,
                "executable": sys.executable,
                "prefix": sys.prefix,
                "path": sys.path,
                "targets": files if docs else [],
            },
            sort_keys=True,
        ).encode()
    )
    physical = content.copy()
    stability = hashlib.sha256()
    inputs = input_paths(root, files, docs=docs)
    identities: dict[Path, str] = {}
    for path in sorted(inputs):
        value, identity = file_identity(path)
        identities[path] = identity
        physical.update(json.dumps([str(path), value]).encode())
        if path.parent == root and path.name in replacements:
            mode = stat.S_IMODE(path.stat().st_mode)
            original, expected = replacements[path.name]
            if value != f"{mode}::{hashlib.sha256(expected).hexdigest()}":
                raise VerificationError("Release metadata changed while taking its fingerprint")
            value = f"{mode}::{hashlib.sha256(original).hexdigest()}"
        content.update(json.dumps([str(path), value]).encode())
        stability.update(json.dumps([str(path), identity]).encode())
    if any(repr(file_stamp(path)) != identity for path, identity in identities.items()):
        raise VerificationError("Inputs changed during fingerprinting")
    if input_paths(root, repository_files(root), docs=docs) != inputs:
        raise VerificationError("Input inventory changed during fingerprinting")
    return Fingerprint(content.hexdigest(), stability.hexdigest(), physical.hexdigest())


def check_commands(root: Path, *, docs: bool) -> list[list[str]]:
    if docs:
        new_markdown = [
            name
            for encoded in git(root, "ls-files", "-z", "--others", "--exclude-standard").split(
                b"\0"
            )
            if encoded
            and Path(name := os.fsdecode(encoded)).suffix == ".md"
            and name != "CHANGELOG.md"
            and not (root / name).is_symlink()
        ]
        return [[sys.executable, "scripts/check_docs.py", "--all", *new_markdown]]
    return [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "mypy", "."],
        [sys.executable, "-m", "vulture"],
        [str(Path(sys.executable).parent / "lint-imports")],
        [sys.executable, "-m", "pytest"],
    ]


def reusable(path: Path, digest: str, commands: Sequence[Sequence[str]]) -> bool:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if (
            type(record["schema"]) is not int
            or record["schema"] != 1
            or not isinstance(record["inputs"], list)
            or digest not in record["inputs"]
            or record["commands"] != commands
            or not isinstance(record["results"], list)
            or type(record["completed"]) not in {int, float}
        ):
            return False
        results = record["results"]
        return len(results) == len(commands) and all(
            isinstance(result, dict)
            and type(result["returncode"]) is int
            and result["returncode"] == 0
            and isinstance(result["log"], str)
            and Path(result["log"]).name == result["log"]
            and type(result["seconds"]) in {int, float}
            and result["seconds"] >= 0
            and hashlib.sha256((path.parent / result["log"]).read_bytes()).hexdigest()
            == result["sha256"]
            for result in results
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def save_receipt(path: Path, record: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(record, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def announce(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def require_unchanged(before: Fingerprint, after: Fingerprint) -> None:
    if before != after:
        raise VerificationError("Inputs changed during verification; no success was recorded")


def execute(root: Path, command: Sequence[str], log: Path) -> dict[str, Any]:
    announce(f"Checking: {' '.join(command)}")
    start = time.monotonic()
    with log.open("wb") as stream:
        process = subprocess.Popen(  # noqa: S603 - fixed checking commands, no shell
            command,
            cwd=root,
            env=environment(root),
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = process.wait()
        except KeyboardInterrupt:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
    announce(f"Exit {code}; {time.monotonic() - start:.2f}s; log: {log}")
    if code:
        sys.stderr.write(log.read_text(encoding="utf-8", errors="replace")[-8000:])
        raise VerificationError(f"Check failed: {' '.join(command)}")
    return {
        "returncode": code,
        "seconds": time.monotonic() - start,
        "log": log.name,
        "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
    }


def verify(root: Path, *, docs: bool = False, force: bool = False, hook: bool = False) -> None:
    if not docs and os.environ.get("PYTEST_ADDOPTS"):
        raise VerificationError(
            "Unset PYTEST_ADDOPTS: acceptance must execute the complete ordinary suite"
        )
    directory = private_directory(root)
    directory.mkdir(parents=True, exist_ok=True)
    kind = "docs" if docs else "application"
    receipt = directory / f"{kind}.json"
    commands = check_commands(root, docs=docs)
    with (directory / f"{kind}.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            before = fingerprint(root, commands, hook=hook, docs=docs)
            if not docs and not force and reusable(receipt, before.content, commands):
                record = json.loads(receipt.read_text(encoding="utf-8"))
                if before.physical not in record["inputs"]:
                    record["inputs"].append(before.physical)
                    save_receipt(receipt, record)
                announce(f"Reused successful application checks: {receipt}")
                return
            receipt.unlink(missing_ok=True)
            run_id = uuid.uuid4().hex
            results = [
                execute(root, command, directory / f"{kind}-{run_id}-{index}.log")
                for index, command in enumerate(commands)
            ]
            require_unchanged(before, fingerprint(root, commands, hook=hook, docs=docs))
            record = {
                "schema": 1,
                "inputs": sorted({before.content, before.physical}),
                "commands": commands,
                "results": results,
                "completed": time.time(),
            }
            save_receipt(receipt, record)
            announce(f"Successful {kind} checks: {receipt}")
        except BaseException:
            receipt.unlink(missing_ok=True)
            raise


def interrupted(_signum: int, _frame: FrameType | None) -> NoReturn:
    raise KeyboardInterrupt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", action="store_true", help="fresh Markdown/link validation")
    parser.add_argument("--force", action="store_true", help="ignore a previous successful receipt")
    parser.add_argument(
        "--hook", action="store_true", help="require the exact effective Git index view"
    )
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        root = Path(os.fsdecode(git(Path.cwd(), "rev-parse", "--show-toplevel")).strip())
        verify(root, docs=args.docs, force=args.force, hook=args.hook)
    except (
        OSError,
        ValueError,
        VerificationError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as exc:
        sys.stderr.write(f"Verification failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
