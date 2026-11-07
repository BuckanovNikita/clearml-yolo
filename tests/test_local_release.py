"""Local release acceptance tests use real Git, PSR and installed hooks."""

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/local_release.py"
PREK = str(Path(sys.executable).parent / "prek")


def outer_hook_variable(key: str) -> bool:
    """The suite itself runs inside prek hooks; their state must not reach fixtures."""
    return key.startswith(("GIT_", "PREK_", "PRE_COMMIT")) or key in {"CLEARML_YOLO_RELEASE_ACTIVE", "SKIP"}


def command(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # Fixture commits must not inherit the enclosing real pre-commit invocation's index.
    for key in tuple(env):
        if outer_hook_variable(key):
            env.pop(key)
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        UV_PROJECT_ENVIRONMENT=str(Path(sys.executable).parent.parent),
        UV_OFFLINE="1",
    )
    return subprocess.run(  # noqa: S603 - fixed tool arguments in task-owned repositories
        args, cwd=repo, env=env, capture_output=True, text=True, check=check
    )


def git(repo: Path, *args: str) -> str:
    return command(repo, "git", *args).stdout.strip()


def retry(repo: Path) -> subprocess.CompletedProcess[str]:
    return command(repo, sys.executable, str(HELPER), check=False)


def commit(repo: Path, message: str) -> None:
    (repo / "change.txt").write_text(message + "\n")
    git(repo, "add", "change.txt")
    git(repo, "commit", "-m", message)


def semantic_release_policy(project: str) -> str:
    """Copy the project's canonical tool tables without unrelated local settings."""
    selected: list[str] = []
    include = False
    for line in project.splitlines(keepends=True):
        if header := re.fullmatch(r"\s*\[\[?([\w.-]+)\]\]?\s*(?:#.*)?", line):
            name = header[1]
            include = name == "tool.semantic_release" or name.startswith("tool.semantic_release.")
        if include:
            selected.append(line)
    policy = "".join(selected)
    assert tomllib.loads(policy) == {"tool": {"semantic_release": tomllib.loads(project)["tool"]["semantic_release"]}}
    return policy


@pytest.mark.parametrize(
    "following",
    [
        '[tool.uv.sources]\nprivate = { path = "external/private" }\n',
        '[tool.semantic_release_extra]\nkeep = "outside"\n',
        '[project.optional-dependencies]\nextra = ["example"]\n',
    ],
)
def test_release_fixture_copies_only_semantic_release_tables(following: str) -> None:
    policy = (
        '[tool.semantic_release]\ncommit_parser = "conventional"\n'
        '[tool.semantic_release.branches.master]\nmatch = "^master$"\n'
    )
    project = '[project]\nname = "original"\n' + policy + following
    assert tomllib.loads(semantic_release_policy(project)) == tomllib.loads(policy)


def create_release_repository(repo: Path) -> Path:
    repo.mkdir()
    git(repo, "init", "-b", "master")
    git(repo, "config", "user.name", "Release Test")
    git(repo, "config", "user.email", "release@example.invalid")
    git(repo, "remote", "add", "origin", "https://github.com/example/release-fixture.git")
    policy = semantic_release_policy((ROOT / "pyproject.toml").read_text())
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "release-fixture"\nversion = "0.3.0"\nrequires-python = ">=3.12"\n' + policy
    )
    (repo / "uv.lock").write_text(
        'version = 1\nrevision = 3\nrequires-python = ">=3.12"\n\n'
        '[[package]]\nname = "release-fixture"\nversion = "0.3.0"\n'
        'source = { virtual = "." }\n'
    )
    # Use the real post-commit hook definition, substituting only the already-installed
    # interpreter so fixture projects need no environment installation or network.
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    release_hook = next(hook for item in config["repos"] for hook in item["hooks"] if hook["id"] == "local-release")
    release_hook["entry"] = f'{sys.executable} "{HELPER}"'
    config["repos"] = [
        {
            "repo": "local",
            "hooks": [
                {
                    "id": "fixture-check",
                    "name": "Fixture quality check",
                    "entry": f"{sys.executable} check.py",
                    "language": "system",
                    "always_run": True,
                    "pass_filenames": False,
                },
                release_hook,
            ],
        }
    ]
    (repo / ".pre-commit-config.yaml").write_text(yaml.safe_dump(config))
    (repo / "check.py").write_text(
        "from pathlib import Path\nimport sys\nimport tomllib\n"
        "version = tomllib.loads(Path('pyproject.toml').read_text())['project']['version']\n"
        "with Path('.git/checks').open('a') as stream: stream.write(version + '\\n')\n"
        "sys.exit(int(Path('.git/reject-release').exists() and version != '0.3.0'))\n"
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "chore: initial fixture")
    git(repo, "tag", "-a", "v0.3.0", "-m", "v0.3.0")
    command(repo, sys.executable, str(HELPER), "--install-hooks")
    assert git(repo, "tag", "--list") == "v0.3.0"
    return repo


@pytest.fixture(scope="module")
def release_seed(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return create_release_repository(tmp_path_factory.mktemp("release-seed") / "repository")


@pytest.fixture
def release_repo(release_seed: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # In-process failure probes also need isolation when pytest itself runs inside
    # a real release commit's hooks, which export Git's temporary index and guard.
    for key in tuple(os.environ):
        if outer_hook_variable(key):
            monkeypatch.delenv(key)
    # Copy writable Git state and installed hooks; no test mutates the shared seed.
    return Path(shutil.copytree(release_seed, tmp_path / "repository with spaces — репозиторий"))


@pytest.fixture
def protected_release_repo(release_repo: Path) -> Path:
    repo = release_repo
    git(repo, "switch", "-c", "feature/protected-lock")
    project = repo / "pyproject.toml"
    project.write_text(
        project.read_text().replace(
            'requires-python = ">=3.12"\n',
            'requires-python = ">=3.12"\ndependencies = ["digital-metrics>=0.6.1", "report-generator>=0.1.2"]\n',
        )
    )
    (repo / "uv.lock").write_bytes(
        b'version = 1\r\nrevision = 3\r\nrequires-python = ">=3.12"\r\n\r\n'
        b"# Preserve dependency versions, source paths and metadata verbatim.\r\n"
        b'[[package]]\r\nname = "digital-metrics"\r\nversion = "0.6.1"\r\n'
        b'source = { editable = "external/digital-metrics" }\r\n\r\n'
        b'[[package]]\r\nname = "release-fixture"\r\n'
        b"version = '0.3.0' # Only this version changes.\r\n"
        b'source = { editable = "." }\r\n'
        b'dependencies = [{ name = "digital-metrics" }, { name = "report-generator" }]\r\n'
        b"[package.metadata]\r\nrequires-dist = [\r\n"
        b'    { name = "digital-metrics", editable = "external/digital-metrics" },\r\n'
        b'    { name = "report-generator", editable = "external/report-generator" },\r\n'
        b']\r\n\r\n[[package]]\r\nname = "report-generator"\r\nversion = "0.1.2"\r\n'
        b'source = { editable = "external/report-generator" }\r\n'
    )
    git(repo, "add", "pyproject.toml", "uv.lock")
    git(repo, "commit", "-m", "fix: retain approved editable dependencies")
    git(repo, "switch", "master")
    git(repo, "merge", "--ff-only", "feature/protected-lock")
    return repo


def test_release_preserves_protected_lock_without_resolving(
    protected_release_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from scripts import local_release

    repo = protected_release_repo
    before = (repo / "uv.lock").read_bytes()
    original = local_release.run

    def without_resolution(root: Path, *args: str, skip_heavy: bool = False) -> str:
        if args[:2] == ("uv", "lock"):
            pytest.fail("Release must not resolve protected dependencies")
        return original(root, *args, skip_heavy=skip_heavy)

    monkeypatch.setattr(local_release, "run", without_resolution)
    local_release.release(repo)
    assert (repo / "uv.lock").read_bytes() == before.replace(
        b"version = '0.3.0' # Only this version changes.",
        b"version = '0.3.1' # Only this version changes.",
    )
    assert "sources" not in tomllib.loads((repo / "pyproject.toml").read_text())["tool"].get("uv", {})
    assert git(repo, "cat-file", "-t", "v0.3.1") == "tag"
    assert git(repo, "rev-parse", "v0.3.1^{commit}") == git(repo, "rev-parse", "HEAD")
    assert (repo / ".git/checks").read_text().splitlines() == ["0.3.0", "0.3.1"]


@pytest.mark.parametrize(
    "invalid",
    ["missing", "duplicate", "old-version", "source", "dependency-drift", "comment-drift"],
)
def test_lock_refresh_rejects_invalid_source_without_writing(
    protected_release_repo: Path, monkeypatch: pytest.MonkeyPatch, invalid: str
) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from scripts import local_release

    repo = protected_release_repo
    path = repo / "uv.lock"
    content = path.read_bytes()
    replacements = {
        "missing": (b'name = "release-fixture"', b'name = "another-project"'),
        "duplicate": (b'name = "report-generator"\r\n', b'name = "release-fixture"\r\n'),
        "old-version": (b"version = '0.3.0'", b"version = '0.2.0'"),
        "source": (b'editable = "."', b'editable = "../another-project"'),
        "dependency-drift": (b'version = "0.6.1"', b'version = "0.6.2"'),
        "comment-drift": (b"# Preserve dependency", b"# Unreviewed dependency"),
    }
    path.write_bytes(content.replace(*replacements[invalid]))
    # Malformed committed roots must also fail, not merely dirty worktrees.
    if invalid in {"missing", "duplicate", "old-version", "source"}:
        git(repo, "switch", "-c", "feature/invalid-lock")
        git(repo, "add", "uv.lock")
        git(repo, "commit", "-m", "chore: invalid lock fixture")
    before = path.read_bytes()
    attempt = local_release.Attempt(source=git(repo, "rev-parse", "HEAD"), version="0.3.1")
    with pytest.raises(local_release.ReleaseError, match="Lockfile"):
        local_release.refresh_lock_version(repo, attempt)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("message", "version"),
    [
        ("fix: repair something", "0.3.1"),
        ("perf: reduce work", "0.3.1"),
        ("feat: add something", "0.4.0"),
        ("feat(config)!: replace interface", "0.4.0"),
        ("fix: replace interface\n\nBREAKING CHANGE: old interface removed", "0.4.0"),
    ],
)
def test_commit_updates_metadata_and_tags_once(release_repo: Path, message: str, version: str) -> None:
    repo = release_repo
    commit(repo, message)
    assert git(repo, "log", "-1", "--format=%s") == f"chore(release): {version}"
    assert git(repo, "rev-parse", f"v{version}^{{commit}}") == git(repo, "rev-parse", "HEAD")
    assert git(repo, "cat-file", "-t", f"v{version}") == "tag"
    assert tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"] == version
    assert tomllib.loads((repo / "uv.lock").read_text())["package"][0]["version"] == version
    assert (repo / ".git/checks").read_text().splitlines() == ["0.3.0", version]
    assert git(repo, "status", "--porcelain", "--untracked-files=no") == ""
    assert not (repo / "dist").exists()
    changelog = (repo / "CHANGELOG.md").read_text()
    assert f"## v{version} (" in changelog
    assert message.splitlines()[0].split(": ", 1)[1] in changelog.casefold()
    assert "chore(release)" not in changelog
    assert set(git(repo, "diff", "--name-only", "HEAD~1", "HEAD").splitlines()) == {
        "pyproject.toml",
        "uv.lock",
        "CHANGELOG.md",
    }
    before = git(repo, "rev-parse", "HEAD")
    result = retry(repo)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "HEAD") == before
    assert git(repo, "rev-list", "--count", "HEAD") == "3"


def test_docs_only_commit_does_not_release(release_repo: Path) -> None:
    commit(release_repo, "docs: explain usage")
    result = retry(release_repo)
    assert result.returncode == 0, result.stderr
    assert git(release_repo, "rev-list", "--count", "HEAD") == "2"
    assert git(release_repo, "tag", "--list") == "v0.3.0"


@pytest.mark.parametrize("state", ["feature", "detached", "rebase", "cherry-pick"])
def test_unsupported_history_is_untouched(release_repo: Path, state: str) -> None:
    repo = release_repo
    if state == "feature":
        git(repo, "switch", "-c", "feature/example")
    elif state == "detached":
        git(repo, "checkout", "--detach")
    elif state == "rebase":
        (repo / ".git/rebase-merge").mkdir()
    else:
        (repo / ".git/CHERRY_PICK_HEAD").write_text(git(repo, "rev-parse", "HEAD"))
    result = retry(repo)
    assert result.returncode == 0, result.stderr
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert git(repo, "status", "--porcelain", "--untracked-files=no") == ""


@pytest.mark.parametrize("staged", [False, True])
def test_dirty_metadata_is_preserved(release_repo: Path, staged: bool) -> None:
    repo = release_repo
    path = repo / "pyproject.toml"
    path.write_text(path.read_text() + "\n# contributor work\n")
    if staged:
        git(repo, "add", "pyproject.toml")
    before = git(repo, "diff", "HEAD")
    index = git(repo, "diff", "--cached")
    result = retry(repo)
    assert result.returncode == 1
    assert "dirty" in result.stderr.lower()
    assert git(repo, "diff", "HEAD") == before
    assert git(repo, "diff", "--cached") == index


def test_failed_quality_check_leaves_original_commit_and_no_tag(release_repo: Path) -> None:
    repo = release_repo
    (repo / ".git/reject-release").touch()
    commit(repo, "fix: rejected version update")
    assert git(repo, "log", "-1", "--format=%s") == "fix: rejected version update"
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"] == "0.3.1"
    result = retry(repo)
    assert result.returncode == 1
    (repo / ".git/reject-release").unlink()
    # Contributor inspects retained edits and completes the exact metadata commit.
    git(repo, "add", "pyproject.toml", "uv.lock", "CHANGELOG.md")
    git(repo, "commit", "-m", "chore(release): 0.3.1")
    assert git(repo, "rev-parse", "v0.3.1^{commit}") == git(repo, "rev-parse", "HEAD")
    assert git(repo, "rev-list", "--count", "HEAD") == "3"


def test_shallow_history_never_invokes_fetch(release_repo: Path) -> None:
    repo = release_repo
    (repo / ".git/shallow").write_text(git(repo, "rev-parse", "HEAD") + "\n")
    result = retry(repo)
    assert result.returncode == 1
    assert "shallow" in result.stderr.lower()
    assert git(repo, "tag", "--list") == "v0.3.0"


def test_existing_lock_is_not_stolen(release_repo: Path) -> None:
    repo = release_repo
    lock = repo / ".git/clearml-yolo-release.lock"
    lock.mkdir()
    owner = lock / "owner.json"
    owner.write_text(json.dumps({"pid": os.getpid(), "worktree": str(repo)}))
    result = retry(repo)
    assert result.returncode == 1
    assert "lock" in result.stderr.lower()
    assert owner.exists()
    assert git(repo, "rev-list", "--count", "HEAD") == "1"


def test_missing_baseline_is_reported(release_repo: Path) -> None:
    git(release_repo, "tag", "-d", "v0.3.0")
    result = retry(release_repo)
    assert result.returncode == 1
    assert "baseline" in result.stderr.lower()


def refuse_tag(repo: Path) -> Path:
    hook = repo / ".git/hooks/reference-transaction"
    hook.write_text(
        '#!/bin/sh\nif [ "$1" = prepared ]; then\n'
        "  while read -r old new ref; do\n"
        '    if [ "$ref" = refs/tags/v0.3.1 ]; then exit 1; fi\n'
        "  done\nfi\n"
    )
    hook.chmod(0o755)
    return hook


def test_tag_failure_retries_without_another_commit(release_repo: Path) -> None:
    repo = release_repo
    hook = refuse_tag(repo)
    commit(repo, "fix: tag temporarily unavailable")
    head = git(repo, "rev-parse", "HEAD")
    assert git(repo, "log", "-1", "--format=%s") == "chore(release): 0.3.1"
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert (repo / ".git/clearml-yolo-release.json").exists()
    assert not (repo / ".git/clearml-yolo-release.lock").exists()
    hook.unlink()
    result = retry(repo)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "v0.3.1^{commit}") == head
    assert git(repo, "rev-list", "--count", "HEAD") == "3"
    assert (repo / ".git/checks").read_text().splitlines() == ["0.3.0", "0.3.1", "0.3.1"]
    assert not (repo / ".git/clearml-yolo-release.json").exists()


def test_retry_still_requires_passing_checks(release_repo: Path) -> None:
    repo = release_repo
    hook = refuse_tag(repo)
    commit(repo, "fix: retry requires validation")
    hook.unlink()
    (repo / ".git/reject-release").touch()
    result = retry(repo)
    assert result.returncode == 1
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert git(repo, "rev-list", "--count", "HEAD") == "3"


def test_retry_does_not_overwrite_conflicting_tag(release_repo: Path) -> None:
    repo = release_repo
    hook = refuse_tag(repo)
    commit(repo, "fix: colliding version tag")
    hook.unlink()
    git(repo, "tag", "-a", "v0.3.1", "HEAD~1", "-m", "conflicting")
    previous = git(repo, "rev-parse", "v0.3.1")
    result = retry(repo)
    assert result.returncode == 1
    assert "conflict" in result.stderr.lower()
    assert git(repo, "rev-parse", "v0.3.1") == previous


def test_stale_attempt_does_not_tag_unrelated_commit(release_repo: Path) -> None:
    repo = release_repo
    hook = refuse_tag(repo)
    commit(repo, "fix: record a release attempt")
    hook.unlink()
    commit(repo, "docs: unrelated follow-up")
    result = retry(repo)
    assert result.returncode == 1
    assert "recorded source" in result.stderr.lower()
    assert git(repo, "tag", "--list") == "v0.3.0"


def test_untracked_files_are_not_committed(release_repo: Path) -> None:
    repo = release_repo
    (repo / "private.txt").write_text("unrelated work\n")
    commit(repo, "fix: preserve private files")
    assert git(repo, "ls-files", "private.txt") == ""
    assert (repo / "private.txt").read_text() == "unrelated work\n"
    assert git(repo, "tag", "--list", "v0.3.1") == "v0.3.1"


def test_existing_unreleased_history_is_included(release_repo: Path) -> None:
    repo = release_repo
    git(repo, "switch", "-c", "feature/new-api")
    commit(repo, "feat!: new interface")
    assert git(repo, "tag", "--list") == "v0.3.0"
    git(repo, "switch", "master")
    git(repo, "merge", "--ff-only", "feature/new-api")
    commit(repo, "docs: describe interface")
    assert git(repo, "log", "-1", "--format=%s") == "chore(release): 0.4.0"


def test_lock_is_shared_across_worktrees(release_repo: Path, tmp_path: Path) -> None:
    repo = release_repo
    worktree = tmp_path / "second worktree"
    git(repo, "worktree", "add", "--force", str(worktree), "master")
    lock = repo / ".git/clearml-yolo-release.lock"
    lock.mkdir()
    result = retry(worktree)
    assert result.returncode == 1
    assert str(lock) in result.stderr
    assert lock.exists()


def test_lock_refresh_cannot_upgrade_dependencies(release_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from scripts import local_release

    repo = release_repo
    git(repo, "switch", "-c", "feature/fix")
    commit(repo, "fix: test dependency drift")
    git(repo, "switch", "master")
    git(repo, "merge", "--ff-only", "feature/fix")
    original = local_release.refresh_lock_version

    def drifting_lock(root: Path, attempt: local_release.Attempt) -> None:
        original(root, attempt)
        with (root / "uv.lock").open("a") as stream:
            stream.write('\n[[package]]\nname = "unexpected"\nversion = "9.9.9"\n')

    monkeypatch.setattr(local_release, "refresh_lock_version", drifting_lock)
    with pytest.raises(local_release.ReleaseError, match="changed dependencies"):
        local_release.release(repo)
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert git(repo, "rev-list", "--count", "HEAD") == "2"


@pytest.mark.parametrize("mode", ["all", "only"])
def test_commit_index_modes_leave_a_clean_release(release_repo: Path, mode: str) -> None:
    repo = release_repo
    with (repo / "check.py").open("a") as stream:
        stream.write("# source change\n")
    if mode == "all":
        git(repo, "commit", "-am", "fix: commit all tracked changes")
    else:
        git(repo, "commit", "--only", "check.py", "-m", "fix: commit selected path")
    assert git(repo, "log", "-1", "--format=%s") == "chore(release): 0.3.1"
    assert git(repo, "status", "--porcelain", "--untracked-files=no") == ""
    assert git(repo, "rev-parse", "v0.3.1^{commit}") == git(repo, "rev-parse", "HEAD")


def test_installed_hook_preserves_unstaged_work(release_repo: Path) -> None:
    repo = release_repo
    path = repo / "pyproject.toml"
    original = path.read_text() + "\n# unfinished contributor edit\n"
    path.write_text(original)
    commit(repo, "fix: partial commit with unrelated work")
    assert git(repo, "log", "-1", "--format=%s") == "fix: partial commit with unrelated work"
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert path.read_text() == original
    assert git(repo, "diff", "--cached") == ""


def test_amend_does_not_automatically_release(release_repo: Path) -> None:
    repo = release_repo
    commit(repo, "docs: original message")
    git(repo, "commit", "--amend", "-m", "fix: amended message")
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert git(repo, "log", "-1", "--format=%s") == "fix: amended message"


def test_single_cherry_pick_does_not_automatically_release(release_repo: Path) -> None:
    repo = release_repo
    git(repo, "switch", "-c", "feature/cherry")
    commit(repo, "fix: cherry-picked change")
    source = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "master")
    git(repo, "cherry-pick", source)
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert git(repo, "log", "-1", "--format=%s") == "fix: cherry-picked change"


def test_concurrent_staging_is_not_included_in_release_commit(
    release_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from scripts import local_release

    repo = release_repo
    git(repo, "switch", "-c", "feature/concurrent")
    commit(repo, "fix: concurrent contributor")
    git(repo, "switch", "master")
    git(repo, "merge", "--ff-only", "feature/concurrent")
    original = local_release.run

    def concurrent_staging(root: Path, *args: str, skip_heavy: bool = False) -> str:
        if args[:2] == ("git", "commit"):
            (root / "unrelated.txt").write_text("contributor work\n")
            original(root, "git", "add", "unrelated.txt")
        return original(root, *args, skip_heavy=skip_heavy)

    monkeypatch.setattr(local_release, "run", concurrent_staging)
    with pytest.raises(local_release.ReleaseError):
        local_release.release(repo)
    assert "unrelated.txt" not in git(repo, "ls-tree", "-r", "--name-only", "HEAD")
    assert git(repo, "diff", "--cached", "--name-only") == "unrelated.txt"
    assert git(repo, "tag", "--list") == "v0.3.0"


def test_installer_preserves_existing_custom_hook(release_repo: Path) -> None:
    repo = release_repo
    hook = repo / ".git/hooks/post-commit"
    original = "#!/bin/sh\n# contributor hook\nexit 0\n"
    hook.write_text(original)
    result = command(repo, sys.executable, str(HELPER), "--install-hooks", check=False)
    assert result.returncode == 1
    assert "not owned" in result.stderr
    assert hook.read_text() == original
    assert git(repo, "tag", "--list") == "v0.3.0"


def test_unreachable_tag_conflict_does_not_stamp_metadata(release_repo: Path) -> None:
    repo = release_repo
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    other = git(repo, "commit-tree", tree, "-m", "chore: unrelated history")
    git(repo, "tag", "-a", "v0.3.1", other, "-m", "other branch release")
    commit(repo, "fix: conflicting next version")
    result = retry(repo)
    assert result.returncode == 1
    assert "conflict" in result.stderr.lower()
    assert git(repo, "rev-parse", "v0.3.1^{commit}") == other
    assert tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"] == "0.3.0"
    assert git(repo, "status", "--porcelain", "--untracked-files=no") == ""


def install_changelog_hook(repo: Path) -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    hook = next(hook for item in config["repos"] for hook in item["hooks"] if hook["id"] == "changelog")
    hook["entry"] = f'{sys.executable} "{HELPER}" --changelog'
    path = repo / ".pre-commit-config.yaml"
    fixture_config = yaml.safe_load(path.read_text())
    fixture_config["repos"][0]["hooks"].insert(0, hook)
    path.write_text(yaml.safe_dump(fixture_config))
    git(repo, "add", ".pre-commit-config.yaml")


def test_pre_commit_refreshes_history_without_staging(release_repo: Path) -> None:
    repo = release_repo
    git(repo, "switch", "-c", "feature/changelog")
    commit(repo, "feat: historical change")
    install_changelog_hook(repo)
    result = command(repo, PREK, "run", "--all-files", check=False)
    assert result.returncode == 1
    changelog = (repo / "CHANGELOG.md").read_text()
    assert "historical change" in changelog.casefold()
    assert "Unreleased" in changelog
    assert "v0.3.0" in changelog
    assert git(repo, "ls-files", "CHANGELOG.md") == ""
    git(repo, "add", "CHANGELOG.md")
    result = command(repo, PREK, "run", "--all-files", check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / "CHANGELOG.md").read_text() == changelog
    assert git(repo, "rev-list", "--count", "HEAD") == "2"


def test_changelog_hook_preserves_release_and_tag_retry(release_repo: Path) -> None:
    repo = release_repo
    install_changelog_hook(repo)
    result = command(repo, sys.executable, str(HELPER), "--changelog", check=False)
    assert result.returncode == 1
    git(repo, "add", "CHANGELOG.md")
    hook = refuse_tag(repo)
    commit(repo, "fix: finalized release entry")
    head = git(repo, "rev-parse", "HEAD")
    assert git(repo, "log", "-1", "--format=%s") == "chore(release): 0.3.1"
    changelog = (repo / "CHANGELOG.md").read_text()
    assert "## v0.3.1 (" in changelog
    assert "finalized release entry" in changelog.casefold()
    assert "Unreleased" not in changelog
    # A manual hook run during recovery must preserve the untagged release section.
    command(repo, PREK, "run", "--all-files")
    assert (repo / "CHANGELOG.md").read_text() == changelog
    hook.unlink()
    result = retry(repo)
    assert result.returncode == 0, result.stderr
    assert git(repo, "rev-parse", "v0.3.1^{commit}") == head
    result = command(repo, PREK, "run", "--all-files", check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / "CHANGELOG.md").read_text() == changelog


def test_recovery_rejects_changed_changelog(release_repo: Path) -> None:
    repo = release_repo
    (repo / ".git/reject-release").touch()
    commit(repo, "fix: protect release notes")
    path = repo / "CHANGELOG.md"
    path.write_text(path.read_text() + "\nUnreviewed addition\n")
    (repo / ".git/reject-release").unlink()
    git(repo, "add", "pyproject.toml", "uv.lock", "CHANGELOG.md")
    git(repo, "commit", "-m", "chore(release): 0.3.1")
    result = retry(repo)
    assert result.returncode == 1
    assert "changelog" in result.stderr.lower()
    assert git(repo, "tag", "--list") == "v0.3.0"


def test_release_commit_and_tag_recovery_skip_heavy_hooks(release_repo: Path) -> None:
    """Heavy checks run once on the contributor commit; generated commits skip them."""
    repo = release_repo
    config_path = repo / ".pre-commit-config.yaml"
    config = yaml.safe_load(config_path.read_text())
    hooks = config["repos"][0]["hooks"]
    # The id is what the helper skips by name; the entry only counts invocations.
    hooks.insert(
        1,
        {
            "id": "pytest",
            "name": "Counting heavy check",
            "entry": f"{sys.executable} -c \"import pathlib; pathlib.Path('.git/heavy').open('a').write('run\\n')\"",
            "language": "system",
            "always_run": True,
            "pass_filenames": False,
        },
    )
    config_path.write_text(yaml.safe_dump(config))
    git(repo, "add", ".pre-commit-config.yaml")
    tag_hook = refuse_tag(repo)
    commit(repo, "fix: count heavy checks")
    assert git(repo, "log", "-1", "--format=%s") == "chore(release): 0.3.1"
    assert git(repo, "tag", "--list") == "v0.3.0"
    assert (repo / ".git/heavy").read_text().splitlines() == ["run"]
    # The light quality hook still checks the generated release commit.
    assert (repo / ".git/checks").read_text().splitlines() == ["0.3.0", "0.3.1"]
    tag_hook.unlink()
    result = retry(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert git(repo, "rev-parse", "v0.3.1^{commit}") == git(repo, "rev-parse", "HEAD")
    assert (repo / ".git/heavy").read_text().splitlines() == ["run"]
    assert (repo / ".git/checks").read_text().splitlines() == ["0.3.0", "0.3.1", "0.3.1"]


def test_version_bytes_replaces_exactly_one_root_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from scripts.local_release import ReleaseError, version_bytes

    project = b'[project]\r\nname = "fixture"\r\nversion = \'0.3.0\' # kept\r\n[tool.x]\r\nversion = "9"\r\n'
    assert version_bytes(project, "0.3.1", lock=False, name="fixture") == project.replace(b"0.3.0", b"0.3.1")
    lock = b'[[package]]\nname = "dep"\nversion = "1.0.0"\n\n[[package]]\nname = "fixture"\nversion = "0.3.0"\n'
    assert version_bytes(lock, "0.3.1", lock=True, name="fixture") == lock.replace(b'"0.3.0"', b'"0.3.1"')
    missing = b'[project]\nname = "fixture"\n'
    duplicate = b'[project]\nversion = "1"\nversion = "2"\n'
    for ambiguous in (missing, duplicate):
        with pytest.raises(ReleaseError, match="exactly one root package version token"):
            version_bytes(ambiguous, "0.3.1", lock=False, name="fixture")


def test_skipped_heavy_hooks_name_configured_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from scripts.local_release import HEAVY_HOOKS

    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    configured = {hook["id"] for repo in config["repos"] for hook in repo["hooks"]}
    assert set(HEAVY_HOOKS) <= configured
    # Light checks keep validating generated release commits.
    assert {"changelog", "check-toml"} <= configured - set(HEAVY_HOOKS)


def test_changelog_rewrite_stops_before_heavy_hooks() -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    order = [hook["id"] for repo in config["repos"] for hook in repo["hooks"]]
    changelog = next(hook for repo in config["repos"] for hook in repo["hooks"] if hook["id"] == "changelog")
    assert changelog.get("fail_fast") is True
    heavy = ("mypy", "pytest-full", "pytest")
    assert order.index("changelog") < min(order.index(name) for name in heavy)
