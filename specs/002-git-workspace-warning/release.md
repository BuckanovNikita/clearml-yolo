# Git workspace warning delivery — 2026-10-20

## Application

The change was implemented against `3b3bd8fa5b727e7387a0604b94b1f755e18ae5b8`,
independently reviewed with a **ship** verdict, and committed as
[`a609fd7e8ac5d781b8f418e7dad2986dc80dc225`](https://github.com/BuckanovNikita/clearml-yolo/commit/a609fd7e8ac5d781b8f418e7dad2986dc80dc225).
All configured feature commit hooks passed, including Ruff, mypy, import-linter,
Vulture and the full pytest hook. See [verification](verification.md) and
[review](review.md) for parent checks and review scope.

Master was fast-forwarded to that commit. The native release helper completed
its checked release commit and annotated tag:

| Ref | Verified identity |
| --- | --- |
| Release commit | `018450a24c6043bba174ceeddc01c81113b3b70f` |
| Annotated tag | `v0.37.0` |
| Tag object | `20d2c516e97b620acc9497685df8ce53b0ff2455` |
| Tag peeled commit | `018450a24c6043bba174ceeddc01c81113b3b70f` |

The release commit is the direct child of the feature commit and changes only
`pyproject.toml`, `uv.lock` and generated `CHANGELOG.md`. Independent structured
lock comparison confirmed that only the root clearml-yolo version changed from
0.36.0 to 0.37.0; dependency sources, versions and metadata are identical.
Neither commit contains a local uv source section. Both checkouts' exact local
overrides were preserved and restored unstaged.

`git push --atomic origin master refs/tags/v0.37.0` succeeded. A subsequent
`git ls-remote` confirmed remote master at the release commit and both annotated
tag identities above. The release is available through the
[Git tag](https://github.com/BuckanovNikita/clearml-yolo/tree/v0.37.0).
No distributions, GitHub Release objects, release assets or registry packages
were built or published. A later documentation-only delivery commit may advance
master while the published tag remains immutable.

The feature and release hooks used the prepared environment with `UV_NO_SYNC=true`
and private process/queue isolation described in verification. Every configured
hook remained enabled. All task-owned test namespaces exited; shared services
and queue metadata were preserved.

## Companion usage guidance

The reviewed clearml-yolo skill update was committed as
`f652e7ae7010d121d08192e19424f4d0a55dd77e`; the application-delivery evidence
commit is `545d4001d44365540a3c9c6621d66deb9359be76`. The delegate validated
the final metadata, Markdown, local links, no-impact architecture and whitespace,
then published the collection only after application v0.37.0 was remotely verified.

| Ref | Verified identity |
| --- | --- |
| Collection main/release commit | `545d4001d44365540a3c9c6621d66deb9359be76` |
| Annotated tag | `v0.4.1` |
| Tag object | `75930fbda69779d0ca146242fd88f9c6d390ed8c` |
| Tag peeled commit | `545d4001d44365540a3c9c6621d66deb9359be76` |

The atomic main/tag push succeeded. The parent inspected the final delivery
commit and independently confirmed all three remote refs with `git ls-remote`.
Git reported that the corp-skills remote redirects to custom-opencode-skills;
the [published collection tag](https://github.com/BuckanovNikita/custom-opencode-skills/tree/v0.4.1)
contains the update. Remote configuration, installed skills and pre-existing
shared-checkout edits were preserved. Only task-owned clean temporary resources
were eligible for cleanup; the original uncommitted draft was retained.

## Final acceptance

All feature ledger items are complete. Documentation validation covers 60 Markdown
files with zero issues; final architecture acceptance and whitespace validation
passed. This final delivery record changes no runtime behavior or dependency
contract. Required full-suite and commit/release checks passed before publication;
the documented opt-in/environment verification limits remain.
