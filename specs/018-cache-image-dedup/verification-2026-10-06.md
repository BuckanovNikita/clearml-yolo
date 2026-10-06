# Verification: 2026-10-06

## Scope and workflow

Implemented the approved filename-based cache deduplication command. Spec Kit artifacts
capture the specification, resolved design, contract, task ledger and quality checklist.
Consistency analysis: all six functional requirements map to implementation tasks;
no material ambiguity, unmapped requirement or constitution conflict remains. The
extension registry contained no hooks. Installed workflow tooling was not changed.

## Checks performed

- Initial CLI tests failed because the command/module did not exist; after implementation,
  the focused suite passed: `uv run --no-sync pytest -q tests/test_dedup.py tests/test_dedup_cli.py`
  reported 28 passed and one native reflink skip.
- `uv run --no-sync pytest -q`: 1,189 passed, 30 skipped, 12 dependency deprecation warnings.
  Skips are not passing tests; the deduplication native test is one of those skips.
- `uv run --no-sync ruff check .`: passed.
- `uv run --no-sync mypy .`: passed for 137 source files.
- `uv run --no-sync lint-imports`: all nine contracts kept.
- Installed `cy-dedup --help` and default `cy-dedup --dry-run`: passed; the available cache
  contained zero image files. CLI subprocess tests additionally exercised temporary fixtures,
  explicit/default roots and absence of tracking/model/application initialization.
- Markdown parsing, balanced code fences, whitespace and local link target checks passed
  for all changed documentation and feature artifacts. `git diff --check` passed.
- A fresh read-only native subagent reviewed the integrated change and returned `ship`,
  with no actionable findings. It independently reran the focused suite with the same result.

## Native evidence and limits

Native FICLONE tests were attempted with task-owned fixtures on both the temporary and
workspace filesystems. Both reported unsupported operations and skipped; originals were
preserved. Successful native block sharing is therefore unverified on this machine.
Mocked clone operations establish replacement, metadata, content verification, failure,
interruption cleanup and independent-write behavior, not physical sharing or space savings.
The native integration test remains available for a filesystem that supports reflinks.

The command requires an idle cache. Stat checks detect observed source/destination changes;
they do not synchronize arbitrary external writers. Replacing an inode changes identity
and ctime/birth time; reading can update access times. No native model, GPU or ClearML run
was required or claimed for this filesystem-only command.

## Documentation outcome

Updated Russian README usage, filesystem policy, command summary, current contract index
and maintained CLI contract together. The new feature contract owns the extension allowlist,
exit behavior and metadata limitations. Local dependency source overrides are unrelated
and must remain unstaged after the release workflow.

## Release preparation

The first commit attempt regenerated CHANGELOG.md, then hooks encountered the documented
registry-resolution failure when local source overrides were absent. All hooks are rerun
with UV_NO_SYNC=1 against the verified environment; no validation hooks are bypassed.
As in the previous release, a disposable offline lock refresh with the saved source
configuration supplies the unchanged release helper's root-only version update. Its
parsed dependency records must exactly match the existing lockfile before use.
SSH and HTTPS GitHub connections timed out during preparation; remote publication is
not established by these local checks.

## Local release result

- Feature commit: `d9d6fcd`; release commit: `699dfbc`.
- Ordinary feature and release hooks passed, including full pytest runs.
- Annotated `v0.18.0` resolves to the release commit. The release diff contains only
  project/root-lock version metadata and generated changelog; dependency records are unchanged.
- Frozen dev sync installed version 0.18.0; installed command help passed afterward.
- Exact local source overrides were restored unstaged. No release lock/recovery record
  remains; the temporary offline-lock project, process adapter and message files were removed.
- The first atomic HTTPS push timed out. Subsequent readback showed the remote master
  unchanged and no v0.18.0 tag. A bounded retry is recorded separately below.

## Publication result

The bounded HTTPS retry also timed out. The subsequent atomic SSH push succeeded:
Git acknowledged master advancing from `ff5af62` to `699dfbc` and creation of `v0.18.0`.
A separate SSH readback timed out afterward; publication is established by the successful
push acknowledgement, not by an independent remote readback. Only Git commits and the
version tag were published; no package assets or deployments were created.
Final Markdown parsing, whitespace, local link targets and heading anchors passed for
all 14 affected documents. The task ledger records implementation and release completion.
