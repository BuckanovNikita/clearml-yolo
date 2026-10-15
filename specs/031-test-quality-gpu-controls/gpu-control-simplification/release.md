# GPU control release evidence — 2026-10-15

## Source and required hooks

Source commit `dcbbc4903cec07c67ce50cd9b116ea3f6dab8216` implements the reviewed
GC-01–05 amendment. The first commit attempt passed all code checks but stopped
because the generated changelog needed staging. After review, the normal retry
passed all hooks, including full pytest, and retained the source commit.

The automatic `0.31.0` version commit then failed one existing direct-descendant
cleanup case: `test_fork_without_exec_is_owned_and_reaped[True-True]`. Its full run
reported 2576 passed, 1 failed, 30 skipped and 7 deselected in 685.96 seconds. The
failure reported denied `/proc` access during the existing global ownership scan.
The reported process had disappeared by inspection. Another test run in a separate
worktree overlapped; this is context, not proof of the denial's cause. Neither
process_tree.py nor its direct-descendant tests changed in this task.

The complete unchanged direct-descendant suite subsequently passed all 13 tests
in 24.23 seconds. The original permission failure could not be reproduced or tied
to a particular live process from retained evidence. The documented recovery path
retains the prepared metadata and commits only pyproject.toml, uv.lock and the
prepared changelog with the exact recorded release subject. No hook or check is
bypassed, no process was killed to make verification pass, and no unrelated source
change was introduced. The manual recovery version commit `bb07786` passed its full commit hooks. Final
tag revalidation then reported 2575 passed and two test harness failures: a global
process-table churn assertion and reading an empty, newly created child PID file.
The candidate remains unpublished and untagged. T028 records the required harness
corrections and superseding native release attempt; no passing tag check is claimed.

## Abandoned candidate package checks

Built wheel and source distribution from candidate tree `7a79e54240221281347188f4e66599f975bb22d9`.
All six newly relevant queue/identity modules, declared queue console entrypoint,
version `0.31.0`, runtime dependency separation and absence of local source overrides
passed package inspection. An isolated wheel installation outside the checkout
passed imported-module provenance, version, four minimal control parser forms and
three actual CLI help commands. No GPU control mutation was performed.

The candidate lockfile changes only the root package version: all dependency sources,
versions and metadata match the source baseline. The real index remained owned by
the release commit; packaging used a task-owned copy of the already staged index.
This package check belongs to the abandoned candidate; a fresh package build and
tag-tree comparison are required for the superseding candidate.

## Checked restart

The untagged version commit `bb077865307260325e75c8fce8d4cb766118b032`
remains in history. Its pending attempt record was archived unchanged in a
task-owned local evidence file; the record, commit, tree and retained log hashes
are indexed in [abandoned-release.json](abandoned-release.json). Both local and
remote `v0.31.0` were absent before restart. No published tag is replaced.

The replacement-PID test now enumerates its actual child while retaining real
process birth reads and pidfd signalling checks; unrelated global `/proc` churn
cannot invalidate that focused assertion. The subreaper fixture publishes a
newline-terminated PID and waits for complete numeric content under its original
deadline. Deterministic vanished-process and first-empty-read injections reproduced
both failures before the fixes and passed afterward. No production process code,
assertion of ownership, deadline, skip rule or workflow tooling changed.

The parent reran both complete focused suites: 28 tests passed in 18.10 seconds.
Scoped Ruff, mypy and `git diff --check` passed. Fresh independent review accepted
the corrections and restart without blockers; full native source/version hooks
and fresh package/tag checks remain required before delivery.

Only the project and root lock-package version tokens were restored to `0.30.2`
for the new source commit; parsed metadata comparisons confirmed no dependency or
other configuration drift. The normal semantic version calculation reports
`0.31.0`. The native changelog generator owns the corresponding history refresh.
The superseding attempt will name the new checked source commit and create a new
metadata-only direct-child version commit through unmodified hooks.

## Delivery status

Application tag/remote validation and companion `0.2.5` delivery are pending.
The final evidence commit will reconcile T027 and the exact delivered references.
Historical physical multi-GPU/NCCL, real multi-user/NFS and ClearML acceptance remain
open as recorded in [verification](verification.md). No installed portable skill
copies are changed by source delivery.
