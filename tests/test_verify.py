"""Verification receipts bind successful checks to actual bytes and commit views."""

import importlib.metadata
import json
import os
import sys
from pathlib import Path

import pytest

with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    from scripts import verify


def git(root: Path, *arguments: str) -> str:
    return verify.git(root, *arguments).decode().strip()


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    git(root, "init", "-b", "master")
    git(root, "config", "user.name", "Verifier")
    git(root, "config", "user.email", "verify@example.invalid")
    (root / "src").mkdir()
    (root / "src/input.py").write_text("value = 1\n")
    (root / "check.py").write_text(
        "from pathlib import Path\nimport os\nimport sys\n"
        "with Path('.git/count').open('a') as out: out.write('run\\n')\n"
        "if os.environ.get('VERIFY_TEST_EDIT'):\n"
        "    p = Path('src/input.py'); b = p.read_bytes()\n"
        "    p.write_bytes(b + b'# edit'); p.write_bytes(b)\n"
        "sys.exit(int(os.environ.get('VERIFY_TEST_FAIL', '0')))\n"
    )
    git(root, "add", ".")
    git(root, "commit", "-m", "chore: fixture")
    dependencies = tmp_path / "dependency"
    dependencies.mkdir()
    (dependencies / "__init__.py").write_text("dependency = 1\n")
    metadata = tmp_path / "dependency-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Name: dependency\nVersion: 1.0\n")
    (metadata / "RECORD").write_text(
        "dependency/__init__.py,,\ndependency-1.0.dist-info/METADATA,,\n"
    )
    distribution = importlib.metadata.Distribution.at(metadata)
    monkeypatch.setattr(importlib.metadata, "distributions", lambda: [distribution])
    monkeypatch.setattr(verify, "check_commands", lambda *a, **k: [[sys.executable, "check.py"]])
    return root


def count(root: Path) -> int:
    return len((root / ".git/count").read_text().splitlines())


def test_unchanged_manual_and_staged_views_reuse_success(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    verify.verify(repository)
    verify.verify(repository, hook=True)
    assert count(repository) == 1
    receipt = json.loads((verify.private_directory(repository) / "application.json").read_text())
    assert receipt["commands"] == [[sys.executable, "check.py"]]
    assert receipt["results"][0]["returncode"] == 0
    assert (verify.private_directory(repository) / receipt["results"][0]["log"]).is_file()
    for key in verify.NOISE:
        monkeypatch.setenv(key, "changed bookkeeping")
    monkeypatch.setenv("GIT_INDEX_FILE", str(repository / ".git/index"))
    monkeypatch.setenv("PATH", os.environ["PATH"] + os.pathsep + os.environ["PATH"])
    verify.verify(repository, hook=True)
    assert count(repository) == 1
    assert not any(key.startswith("GIT_") for key in verify.environment(repository))
    assert not verify.NOISE.intersection(verify.environment(repository))


@pytest.mark.parametrize(
    "name", [
        "src/input.py", "tests/test_added.py", "tests/data.csv", ".importlinter", "src/new.py",
        "tests/fixture.pt", "root_fixture.pt", "pytest.ini", "delete", "env",
        "fixtures/tensor.pt", "fixtures/data.md", "root_fixture.md",
        *[f"tests/{d}/data.pt" for d in ("outputs", "runs", "build", "mutants", ".tmp", ".cache")],
    ],
)
def test_changed_inputs_invalidate_success(
    repository: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    (repository / ".git/info/exclude").write_text("*.pt\n*.ini\n*.md\n")
    verify.verify(repository)
    if name == "env":
        monkeypatch.setenv("CY_TEST_AFFECTING", "changed")
    elif name == "delete":
        (repository / "src/input.py").unlink()
    else:
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed input\n")
    verify.verify(repository)
    if name == "delete":
        git(repository, "add", "-u")
        verify.verify(repository, hook=True)
    assert count(repository) == 2
    if name == "root_fixture.pt":
        verify.verify(repository, hook=True)
        assert count(repository) == 2
    elif name == "pytest.ini":
        with pytest.raises(verify.VerificationError, match="Stage the complete"):
            verify.verify(repository, hook=True)


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "json",
        "schema",
        "schema_bool",
        "failed",
        "result_bool",
        "log",
        "commands",
        "results_type",
    ],
)
def test_missing_or_malformed_evidence_runs_fresh(repository: Path, damage: str) -> None:
    verify.verify(repository)
    receipt = verify.private_directory(repository) / "application.json"
    record = json.loads(receipt.read_text())
    if damage == "missing":
        receipt.unlink()
    elif damage == "json":
        receipt.write_text("not JSON")
    else:
        if damage in {"failed", "result_bool"}:
            record["results"][0]["returncode"] = 1 if damage == "failed" else True
        elif damage == "log":
            (receipt.parent / record["results"][0]["log"]).unlink()
        else:
            field, value = {
                "schema": ("schema", 999), "schema_bool": ("schema", True),
                "commands": ("commands", []), "results_type": ("results", {}),
            }[damage]
            record[field] = value
        receipt.write_text(json.dumps(record))
    verify.verify(repository)
    assert count(repository) == 2


@pytest.mark.parametrize("addition", ["same", "new", "outputs/new"])
def test_dependency_content_changes_do_not_trust_record_version_size_or_mtime(
    repository: Path, addition: str,
) -> None:
    dependency = repository.parent / "dependency/__init__.py"
    verify.verify(repository)
    before = dependency.stat()
    if addition != "same":
        dependency = dependency.parent / f"{addition}.py"
        dependency.parent.mkdir(exist_ok=True)
    dependency.write_text("dependency = 2\n")
    os.utime(dependency, ns=(before.st_atime_ns, before.st_mtime_ns))
    verify.verify(repository)
    assert count(repository) == 2


@pytest.mark.parametrize("kind", ["file", "missing", "directory"])
def test_symlink_targets_are_verified_and_can_be_staged(repository: Path, kind: str) -> None:
    if kind != "missing":
        for name in ("first", "second"):
            target = repository / name
            if kind == "directory":
                target.mkdir()
                target = target / "module.py"
            target.write_text("identical target bytes\n")
    link = repository / "src/fixture"
    link.symlink_to("../first")
    git(repository, "add", ".")
    verify.verify(repository)
    link.unlink()
    link.symlink_to("../second")
    verify.verify(repository)
    assert count(repository) == 2
    git(repository, "add", "src/fixture")
    verify.verify(repository, hook=True)
    assert count(repository) == 2


def test_docs_evidence_does_not_invalidate_application_checks(repository: Path) -> None:
    verify.verify(repository)
    evidence = repository / "specs/evidence.md"
    evidence.parent.mkdir()
    evidence.write_text("# Verification\n\nRecorded evidence.\n")
    verify.verify(repository)
    verify.verify(repository, docs=True)
    evidence.write_text("# Verification\n\nUpdated evidence.\n")
    verify.verify(repository)
    assert count(repository) == 2  # One application command and one separate docs command.
    assert (verify.private_directory(repository) / "docs.json").is_file()


@pytest.mark.parametrize("change", ["untracked", "linked_edit", "linked_retarget"])
def test_editable_dependency_includes_untracked_and_linked_source(
    repository: Path, change: str,
) -> None:
    source = repository.parent / "editable"
    source.mkdir()
    target = repository.parent / "linked"
    target.mkdir()
    (target / "module.py").write_text("value = 1\n")
    (source / "package").symlink_to(target, target_is_directory=True)
    (target / "cycle").symlink_to(source, target_is_directory=True)
    metadata = repository.parent / "dependency-1.0.dist-info"
    (metadata / "direct_url.json").write_text(
        json.dumps({"url": source.as_uri(), "dir_info": {"editable": True}})
    )
    verify.verify(repository)
    if change == "untracked":
        (source / "plugin.py").write_text("new_plugin = True\n")
    elif change == "linked_edit":
        (target / "module.py").write_text("value = 2\n")
    else:
        alternative = repository.parent / "alternative"
        alternative.mkdir()
        (alternative / "module.py").write_text("value = 1\n")
        (alternative / "cycle").symlink_to(source, target_is_directory=True)
        (source / "package").unlink()
        (source / "package").symlink_to(alternative, target_is_directory=True)
    verify.verify(repository)
    assert count(repository) == 2


@pytest.mark.parametrize("selection", ["-k example", "--collect-only", "-m 'not ddp_cpu'"])
def test_partial_suite_environment_is_rejected(
    repository: Path, monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", selection)
    with pytest.raises(verify.VerificationError, match="PYTEST_ADDOPTS"):
        verify.verify(repository)


@pytest.mark.parametrize("interruption", [False, True])
def test_failure_removes_success_and_retry_executes(
    repository: Path, monkeypatch: pytest.MonkeyPatch, interruption: bool
) -> None:
    verify.verify(repository)

    def interrupted(*args: object) -> None:
        raise KeyboardInterrupt

    with monkeypatch.context() as failure:
        if interruption:
            failure.setattr(verify, "execute", interrupted)
        else:
            failure.setenv("VERIFY_TEST_FAIL", "1")
        error = KeyboardInterrupt if interruption else verify.VerificationError
        with pytest.raises(error, match=None if interruption else "Check failed"):
            verify.verify(repository, force=True)
    assert not (verify.private_directory(repository) / "application.json").exists()
    verify.verify(repository)
    assert count(repository) == (2 if interruption else 3)


def test_edit_and_restore_during_checks_cannot_publish_success(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VERIFY_TEST_EDIT", "1")
    with pytest.raises(verify.VerificationError, match="Inputs changed"):
        verify.verify(repository)
    assert (repository / "src/input.py").read_text() == "value = 1\n"
    assert not (verify.private_directory(repository) / "application.json").exists()


@pytest.mark.parametrize("limited", [False, True])
def test_index_must_match_verified_worktree(
    repository: Path, monkeypatch: pytest.MonkeyPatch, limited: bool
) -> None:
    (repository / "src/input.py").write_text("value = 2\n")
    if limited:
        git(repository, "add", "src/input.py")
    verify.verify(repository)
    if limited:
        monkeypatch.setenv("GIT_INDEX_FILE", str(repository / ".git/limited-index"))
        git(repository, "read-tree", "HEAD")
    with pytest.raises(verify.VerificationError, match="Index and checked worktree differ"):
        verify.verify(repository, hook=True)
    git(repository, "add", "src/input.py")
    verify.verify(repository, hook=True)
    assert count(repository) == 2  # A rejected hook invalidates its prior evidence.


def test_release_normalization_requires_exact_bytes_paths_and_parent(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repository / "pyproject.toml").write_text('[project]\nname = "fixture"\nversion = "0.1.0"\n')
    (repository / "uv.lock").write_text(
        '[[package]]\nname = "fixture"\nversion = "0.1.0"\nsource = { editable = "." }\n'
    )
    (repository / "CHANGELOG.md").write_text("# Changelog\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "chore: release metadata")
    source = git(repository, "rev-parse", "HEAD")
    verify.verify(repository)
    for name in ("pyproject.toml", "uv.lock"):
        path = repository / name
        path.write_text(path.read_text().replace('"0.1.0"', '"0.1.1"'))
    (repository / "CHANGELOG.md").write_text("# Changelog\n\nPatch.\n")
    import hashlib

    record = {
        "source": source,
        "version": "0.1.1",
        "changelog_sha256": hashlib.sha256((repository / "CHANGELOG.md").read_bytes()).hexdigest(),
    }
    attempt = repository / ".git/clearml-yolo-release.json"
    attempt.write_text(json.dumps(record))
    git(repository, "add", ".")
    verify.verify(repository, hook=True)
    assert count(repository) == 1
    original_basis = verify.release_basis
    metadata_path = repository / "pyproject.toml"
    prepared_bytes = metadata_path.read_bytes()

    def raced_basis(root: Path) -> dict[str, tuple[bytes, bytes]]:
        basis = original_basis(root)
        metadata_path.write_bytes(prepared_bytes + b"# concurrent edit\n")
        return basis

    with monkeypatch.context() as race:
        race.setattr(verify, "release_basis", raced_basis)
        with pytest.raises(verify.VerificationError, match="Release metadata changed"):
            verify.fingerprint(
                repository, verify.check_commands(repository, docs=False), hook=False
            )
    metadata_path.write_bytes(prepared_bytes)
    git(repository, "commit", "-m", "chore(release): 0.1.1")
    verify.verify(repository, hook=True)
    assert count(repository) == 1
    path = repository / "pyproject.toml"
    path.write_text(path.read_text() + "# unexplained metadata edit\n")
    assert not verify.release_basis(repository)
    path.write_text(path.read_text().removesuffix("# unexplained metadata edit\n"))
    record["changelog_sha256"] = "0" * 64
    attempt.write_text(json.dumps(record))
    assert not verify.release_basis(repository)
    git(repository, "commit", "--allow-empty", "-m", "chore: unrelated child")
    assert not verify.release_basis(repository)


def test_application_command_selection_is_one_complete_suite() -> None:
    commands = verify.check_commands(Path.cwd(), docs=False)
    assert commands[-1] == [sys.executable, "-m", "pytest"]
    assert len(commands) == 5
    assert not any(
        "test_architecture.py" in argument for command in commands for argument in command
    )
