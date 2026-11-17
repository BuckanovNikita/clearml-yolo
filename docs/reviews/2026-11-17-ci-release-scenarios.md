# CI release scenarios — 2026-11-17

Source: task branch `feat/ci-semantic-release`, based on merged PR #10 at
`d5381ddb701af3509c64c94bc4e22e807d61ba00`. The implementation snapshot used
`scripts.release`, `scripts.release_metadata`, the existing release lock guard,
and the task's semantic-release configuration. Executed with Python 3.12.13 and
Python Semantic Release 10.7.0 from the worktree's isolated environment.

Each scenario copied the actual release scripts, `pyproject.toml`, `uv.lock`,
`CHANGELOG.md` and `.gitignore` to a disposable repository on `master`. A new
annotated `v0.49.0` baseline and a subsequent Conventional Commit established
controlled history. Git's `insteadOf` rewrote a fixture GitHub-shaped origin URL
to a local bare repository. No GitHub requests, publication or production refs
were involved. Git, semantic-release, metadata synchronization, validation and
pushes executed without mocks.

| Scenario | Result | Established observation |
| --- | --- | --- |
| Feature commit | Passed | Version advanced to 0.50.0; project/root lock versions matched, changelog included the version, annotated tag targeted the release commit, remote commit and tag published. |
| Fix commit | Passed | Equivalent publication and metadata checks for 0.49.1. |
| Documentation commit | Passed | Successful no-version result at 0.49.0; all remote refs unchanged. |
| Rerun after each result | Passed | Successful rerun with identical remote refs and no duplicate release. |
| Server rejects tag | Passed | A real bare-repository update hook rejected tags; atomic push failed and neither master nor tags changed. |
| Remote master races with push | Passed | A real pre-push hook advanced remote master to a competing commit after preparation; atomic push failed, retained that competing commit and created no release tag. |
| Conflicting tag identities | Passed | Different local/remote annotated v0.50.0 identities caused fetch to fail; remote refs remained unchanged. |

The first race-fixture attempt failed before exercising the race because its
competing commit was not present in the bare repository. The corrected fixture
first transferred that object under a separate branch, then reran successfully.
This was a fixture correction, not a product failure or counted passing run.

These scenarios establish local Git/semantic-release execution and controlled
failure behavior. They do not establish GitHub event delivery, token permissions,
branch-rule enforcement, hosted-runner execution or native/GPU/application results.
The live workflow outcome remains a post-merge confirmation. Product tests were
not added for release-tooling behavior. All disposable repositories and their
hooks were removed after verification; no background processes remain.

Verified implementation identities (SHA-256):

```text
29d601c7d4ad17b000e6df87d40b6a93916b0e545bb86aac8a625085013ce92d  scripts/release.py
59696faa3e930d9c4c4037214c97c8426364dd69edf2e945fcb0b5ab8c36afd0  scripts/release_metadata.py
eb8e70dce9ab7b464d8cbe40d43fffc8006aa1882ab4a0c11d5d78029c2cbbbc  scripts/release_lock_guard.py
919d80b7d9e773359a689cd31ad5e863a2618706948b05504619c1a907bb0f7c  pyproject.toml
```
