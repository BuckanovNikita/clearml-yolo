# Delivery — 2026-10-16

## Published revisions

| Repository / change | Identity |
| --- | --- |
| Application source | `bdf21a63be95151759c58d2d701735b548c4baaa` |
| Application version commit / annotated tag | `3e79bf00a6b1915a6ff7ad7f5361df33881be91d` / [v0.32.0](https://github.com/BuckanovNikita/clearml-yolo/tree/v0.32.0) |
| Application tag object | `4bd11af35e8e9c53010511d103a7d253c598df25` |
| Test-only fixture follow-up on master | `0c2e720c0f04860dd5d9582c7893279a58945b21` |
| Portable usage collection commit / annotated tag | `46b9aec0ddb92d1ef9d443abcf86f9e9bdcf5ee6` / [v0.2.6](https://github.com/BuckanovNikita/corp-skills/tree/v0.2.6) |
| Portable usage tag object | `3e018771c3fd2bebac838d1927c56ab9dbb088b7` |

Both releases used atomic branch/tag pushes. Subsequent remote queries matched the
branch commits, annotated tag objects and peeled commit targets. The application
was published before its companion guidance. The fixture follow-up and this closing
evidence extend master; neither changes the 0.32.0 runtime artifacts.

## Release checks and recovery

The source commit passed all applicable hooks. The first automatic version-commit attempt
failed one new checker fixture: inherited `GIT_INDEX_FILE` redirected its temporary
repository's index. That run reported 2812 passed, one failed, 30 skipped and seven
deselected; it did not produce a version commit or tag. The native documented
recovery retained the prepared version files, committed them through all applicable hooks,
and repeated all pre-commit checks before creating the tag. Both recovery gates
passed. The initial changelog-generation retry and failed hook output remain in
the ignored task archive; no hook was bypassed and no history was rewritten.

The fixture correction was prepared separately while recovery ran. It follows the
existing release-test environment-isolation pattern, preserves the inherited
external index byte-for-byte, and passed scoped reproduction, all 48 checker tests,
Ruff, mypy and independent read-only review. Its own commit passed all applicable hooks and
was integrated by fast-forward; the parent reran all 48 checker tests successfully.
See the [feature follow-up](../../../specs/033-documentation-checks/verification.md#release-hook-fixture-follow-up--2026-10-16)
and [review record](review.md). The checker implementation and all runtime files
are unchanged by this follow-up.

## Final distribution reconciliation

Wheel and source archive were rebuilt from version commit `3e79bf0`, tree
`285a4c301360b32d464b37164f4973ea81962fe0`. Both match all 180 runtime files from
[accepted installed distributions](packaging-verification.md). Runtime requirements
and the Python constraint are unchanged; local source overrides are absent.

| Local verification artifact | SHA-256 |
| --- | --- |
| `clearml_yolo-0.32.0-py3-none-any.whl` | `048b78397636ed6d79f5fef3f34b74dee6386ef00eba86b88f70e435b9e8af8b` |
| `clearml_yolo-0.32.0.tar.gz` | `3311ec8e80351323ba0d1f5ec5ded5fefcf7c3e5eb89371c3879d0609f480914` |

The ignored `correctness-docs-20261015` archive retains release logs, final build
verification, remote-ref records and the fixture reproduction/patch. An earlier
source-commit build still bore 0.31.1 and is stored separately; it is not the final
release-artifact check. No artifacts were uploaded or packages published.

## Acceptance and preserved limits

[Integrated verification](verification.md), [native CPU/single-GPU and downloaded
ClearML evidence](native-verification.md), [documentation](documentation.md), and
[fresh reviews](review.md) establish the task's accepted scope. The companion
[source evidence](https://github.com/BuckanovNikita/corp-skills/blob/v0.2.6/verification/2026-10-15-clearml-yolo-input-correctness.md)
records package checks and fresh explicit Codex scenarios without claiming live
OpenCode/DeepSeek behavior. Skills were not reinstalled.

Five-physical-GPU, multi-user/multi-host NFS and CUDA 11.8 acceptance remain open.
Interrupted compiled warmup is not accepted. Historical compression used a
conservative 448-document screening pass; uncertain wording and original evidence
remain, as recorded in the documentation ledger.

The exact original local uv source section was restored unstaged after commits and
hooks. The untracked grid-search draft and shared services remain intact. Task-owned
native processes and disposable environments were cleaned; reproduction evidence
is retained. Delivery uses Git commits/tags only, with no deployment or GitHub Release.

Closing documentation validation passed all 474 project Markdown files and all four
architecture acceptance records. The closing diff contains only generated changelog,
delivery/status evidence and the reconciled prose architecture record.
