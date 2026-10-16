# Verification — 2026-10-16

## Baseline and focused behavior

The added tests reproduced the previous blanket NFS rejection and missing default
config discovery: 29 failed and 25 passed before implementation. After implementation,
the initial settings suite passed 54 cases. The final suite passed 56 cases including
real CLI help/missing-file/default-file subprocesses and absent/empty HOME account
fallback. Invalid effective NFS options, incomplete mount records, nested/escaped
mountpoints, missing fields and required setup with --root are covered.

The selected CLI/process/supervision/generation/handoff regressions passed 140 tests
before the final empty-HOME parameter was added; the final settings rerun covers that
addition. Existing protected bindings, legacy evidence, competing roots, restrictive
umask and frozen guardian settings remain exercised without implementation changes.
The initial regression invocation named a nonexistent supervision test file; it ran
no tests. The corrected command uses tests/test_gpu_supervision.py.

The final full suite passed 2,959 tests, with 30 skipped, seven deselected and
93 warnings, in 846 seconds. No skipped/deselected case is counted as passing.

## Architecture and quality

- All 43 import contracts passed using lint-imports.
- Separate architecture tests passed 227 cases, including injected forbidden edges.
- Ruff passed; strict mypy passed all 343 source files; Vulture exited successfully.
- Initial docs invocation incorrectly supplied a directory, reported one read error,
  and was corrected to explicit new Markdown files. The corrected check passed 503
  maintained Markdown files with no local-link/fence issues.
- Isolated CLI examples passed help, HOME/XDG discovery, explicit override, required
  fields, metadata override and human/JSON inspection without creating queue roots.
  A parent rerun initially omitted the helper's source-path argument; the corrected
  invocation passed. The examples use local files only.

## Scope and preservation

Runtime changes are confined to settings lookup/filesystem validation and CLI help.
No schema, dependency revision, storage protocol, lock/guardian behavior or production
queue state changed. The unrelated local uv sources and user draft remain excluded.
Spec Kit templates were resolved read-only; mutating setup helpers were not used
because they persist protected workflow files. Plan architecture validation passed.

The canonical companion usage package was updated and passed frontmatter/local links,
Markdown, discovery and isolated examples. Its source/evidence is in
[corp-skills](https://github.com/BuckanovNikita/corp-skills/tree/main/skills/clearml-yolo).
The companion reviewer identified the empty-HOME fallback edge; the application now
uses the account database when HOME is absent or empty, with regression coverage.

## Isolated candidate package

Built the source distribution and wheel without local source overrides in build
resolution. Installed the candidate wheel into a separate environment with frozen
approved dependencies, outside the checkout. All 12 command helps, nine configuration
selections, alternate model variants, Hydra composition, overwrite preservation and
read-only required user/shared settings checks passed. This pre-release candidate
still reports the previous package version; final release metadata is verified later.

## Final acceptance

Fresh independent application and companion reviews accepted their scopes; see
[review](review.md). Reconciled architecture acceptance passed. The full suite, native checked release and final installed-package checks passed;
all task ledger items are complete. See [delivery](release.md) for published versions,
remote verification, cleanup and preserved user state.

Actual NFS locking, reconnect, server restart, outage and multi-host behavior are
unverified: no NFS mount exists on this machine and the user explicitly scoped this
task to the library error. Simulated mountinfo establishes validator behavior only.
No mount, service, account, GPU workload or production queue was provisioned or changed.
