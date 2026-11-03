# Saved coverage listing verification

Date: 2026-11-03. Isolated CY worktree based on origin/master `84166d5` (0.44.8).
The original dirty checkout and its installed environment were preserved.
Python 3.12.13; locked dependencies prepared in a new worktree-local environment.
Approved external source copies were reused unchanged, without dependency updates.

## Observed regression and focused checks

Before implementation, 137 existing batch policy/CLI/store tests passed. The new
coverage tests then failed as expected: `--list` was unrecognized/`--imgsz` required,
and pure coverage functions were absent (20 failures, four existing assertions
passed, 96 deselected). After implementation and extended coverage, the focused
policy/CLI/store/compatibility selection initially passed 357 tests with 19 upstream warnings:

```bash
CUDA_VISIBLE_DEVICES= uv run --frozen --no-sync pytest -q \
  tests/test_batch_estimation.py tests/test_batch_estimate_cli.py \
  tests/test_batch_estimate_list.py tests/test_batch_estimate_store.py \
  tests/test_docs_compatibility.py
```

Coverage includes missing/empty catalogues, full default model inventory,
aliases/filtering/catalogue order, explicit default-valued measurement flags and
abbreviations, corrupt/unreadable files, saved failures and distinct contexts,
all-covered output and limited usable statuses, diagnostic fallback, control
escaping, unchanged catalogue bytes and directory inventory, and forbidden runtime,
GPU/probe/pool/save calls. Existing measurement and historical replay remain tested.
Focused Ruff and strict mypy passed; the full canonical check is recorded below
when finished. Mutation selection and its dependencies are unchanged.

## Documentation

Generated tutorial HTML was rebuilt from its Russian source. `cy-docs --check`
passed (469 fields, 156 configurations and eight tutorials). Canonical documentation
verification passed; Markdown/local links include task-owned untracked artifacts.
Portable usage changes are in an isolated companion worktree, with package,
metadata, Markdown, local links, discovery and architecture checks reported; final
source/example reconciliation and independent review remain pending here until
recorded below. No installed skill copies were changed.

## Acceptance boundary

This feature only reads stored evidence. No native capacity search, CUDA training,
ClearML task or publication is required or claimed. Existing feature timing and
physical-DDP limitations remain unchanged. Current/proposed queue pairing, final
canonical results, independent review, architecture acceptance and Git-only release
are recorded below after execution, without converting pending checks to passes.


## Proposed-version pairing and final focused checks

The new terminal-failure regression first failed because an earlier OOM diagnostic
masked a later crash with no diagnostic. Fallback now uses the latest unsuccessful
trial diagnostic or status; final focused checks passed **358 tests**, 19 upstream
warnings, exit 0. No cause is inferred from an older capacity boundary.

Latest queue source is `0139152c999a97dde816a72d5524d10a2ba8ad7f` plus the
minimal 0.1.8 compatibility companion; its full suite passed 583 cases with seven
physical opt-ins deselected against CY0.44.8. Normal resolution and pip check passed.
For the proposed CY0.45.0/queue0.1.8 pair, the root project version was temporarily
set to 0.45.0 and normally reinstalled, with no dependency/lockfile updates. The
complete queue suite again passed **583 tests, 7 deselected**, 19 warnings, exit 0.
Source and installed versions matched, and every installed queue Python module
matched latest source bytes. Queue source-installed mode was made noneditable to
freeze installed inputs while allowing independent documentation/review evidence.
The final committed pair will be reinstalled and checked after hooks.

The earlier CY canonical run was intentionally interrupted after companion editable
documentation changed its fingerprint; it has no passing acceptance receipt. The
original 0.44.8 root version was restored exactly and normally reinstalled before
the final canonical run. The worktree has no local uv.sources section; the original
checkout's local overrides remain untouched. No source revision of approved external
dependencies changed.


## Full ordinary suite and input-stability investigation

The full ordinary suite passed **4,731 tests, 30 skipped, 81 deselected**, with
178 warnings; Ruff, strict mypy, Vulture and import-linter also passed. The
canonical wrapper nevertheless exited 1 with Inputs changed during verification,
so no successful application receipt was recorded. This is not full acceptance.

Investigation found that preparing the second isolated environment with uv's
default hardlinks changed ctimes in the first environment while tests ran. Its
ruff binary shared device/inode with the second environment; the changed ctime
matched the provisioning log timestamp. The verifier correctly detected those
metadata changes even though the test checks themselves passed. The parent caused
this interference by provisioning during verification.

The second environment was reinstalled using independent copies. A device/inode
comparison confirmed separation. The required retry uses UV_LINK_MODE=copy, with
no concurrent environment installation or modification. Final post-hook pairing
will use that second environment without changing the accepted canonical view.
Source code and existing dependency versions are unchanged; the pending stable
canonical result and final review are recorded only after execution below.


## Unicode row-preservation correction

Initial feature review identified non-ASCII controls/line separators escaping the
ASCII-only JSON control handling. Four new CLI regressions first failed, then
passed after nonprintable Unicode escaping while preserving printable names and
diagnostics. The new integrated focused suite passes 362 cases; final Ruff and
strict mypy pass. The in-progress copy-mode retry was interrupted before changing
source for this correction; the final successful stable receipt remains required.


## Corrected source full suite and copied verifier environment

The corrected source passed **4,735 ordinary tests, 30 skipped, 81 deselected**,
178 warnings, and all static/import checks. Its wrapper still rejected stability
(Inputs changed during fingerprinting). The diagnostic stamp inventory identified
pathspec package files through the original environment's shared cache hardlinks;
package payload bytes matched the independent copies. No task install ran during
that retry, so the shared-cache metadata activity was outside this task's copied
second-environment setup. No unrelated process was stopped or changed.

The final verifier itself now runs in the fully copied environment, selected by
UV_PROJECT_ENVIRONMENT. Its pathspec files have one link and share no inode with
the original environment. Verification tooling and stability requirements remain
unchanged. The ordinary environment is reserved for the final actual-version pair
check, leaving the successful copied verification view intact through release.


## Stable canonical acceptance (2026-11-04, Moscow)

The independently copied environment completed the canonical command with exit 0:
4,735 passed, 30 skipped, 81 deselected, 178 warnings. Ruff, strict mypy, Vulture
and all import contracts passed. The final input fingerprint remained stable and
the canonical verifier wrote its own successful application receipt; no checker
or acceptance safeguard was changed. Raw results are retained in Git-private
verification logs. The earlier metadata-rejected runs remain non-acceptance evidence.

```bash
UV_PROJECT_ENVIRONMENT=../pair-env UV_LINK_MODE=copy CUDA_VISIBLE_DEVICES= \
  uv run --frozen --no-sync python scripts/verify.py
```

Final source is unchanged since the accepted Unicode-corrected code review. Actual
post-hook version pairing and Git delivery are recorded after execution below.


## Final-code proposed pair before tagging

After stable verification, the final corrected source was tested again with
prospective CY0.45.0 and queue0.1.8 through normal resolution and pip check.
The complete queue suite passed 583 tests, seven physical opt-ins deselected,
19 warnings, exit 0. A guarded finally block restored the original project metadata
bytes exactly; no source/lockfile change remained. The copied verification view
was not modified. Architecture acceptance validation and fresh Markdown checks
passed after post-canonical review. Master release and actual committed pair follow.


## Actual release and companion publication (2026-11-04, Moscow)

Normal pre/post-commit hooks passed, creating feature a89e486 and version commit
850557ccba23f5e39a6fbdcca77e64fb1aab6a5b (0.45.0). The annotated tag object is
ad711bf56cb3a8b893ba1315dc24173bf89db1b4. Only the generated changelog and two
root version tokens changed in the version commit; dependency references/revisions
and runtime source remain unchanged. Post-release verification reused the exact
successful copied-environment receipt through the documented metadata guard.

The actual committed CY0.45.0/queue0.1.8 pair resolved normally and passed pip check,
source/installed version checks, released CY import-origin and exact queue Python
module-byte comparisons. All 583 queue tests passed, seven physical opt-ins
deselected, 19 upstream warnings. Queue help and generated documentation validation
passed (469 fields, 156 configurations, eight tutorials).

Verified published identities:

- CY master and peeled v0.45.0 initially matched 850557c; this documentation-only
  closure follows the immutable code tag without changing its runtime contents.
- Queue main: 4cf32f0cd84730aebd3cf930829f80ba47d5af24, package0.1.8; no tag created.
- Portable collection main/peeled v0.7.2: 5e1cb87471e5d56660a6cc7f3139ab3b7cff37da.
  The legacy corp-skills remote redirected to custom-opencode-skills; both exact
  branch/tag identities were verified after the authorized atomic push.

The original checkout remains on preserve/local-work-before-batch-list-20261104
at its original commit. Every one of its 180 snapshotted changed/untracked file
contents remains identical. No reset, stash, unrelated staging, shared-service
intervention, installed-skill update, deployment or registry publication occurred.
Task-owned test processes completed. The auxiliary copied verification environment
is retained through the final hooks and scheduled for cleanup after publication;
the isolated source worktree and its ordinary tested environment are retained.
