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
At that checkpoint the candidate was unpublished and untagged. T028 recorded the
required harness corrections and superseding native release attempt. The abandoned
version commit remains in the delivered ancestry; it has no version tag.

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
the corrections and restart without blockers. The full native source/version hooks
and fresh package/tag checks subsequently passed as recorded below.

Only the project and root lock-package version tokens were restored to `0.30.2`
for the new source commit; parsed metadata comparisons confirmed no dependency or
other configuration drift. The normal semantic version calculation reports
`0.31.0`. The native changelog generator owns the corresponding history refresh.
The superseding attempt named the new checked source commit and created a new
metadata-only direct-child version commit through unmodified hooks.

## Completed release and package verification

The checked follow-up source commit is
`c5b19fb9f9e2471d77fce91dfd1724dc83935760`. Its normal commit hooks passed Ruff,
strict mypy, all import contracts, Vulture and the full pytest suite. The automatic
release workflow then passed the version commit's required checks and created the
annotated tag `v0.31.0` at `7a4759876b57a511db071287a7eb708a916f35dc`.
That version commit is the direct child of the checked source and changes exactly
pyproject.toml, uv.lock and CHANGELOG.md. No hook or check was bypassed.

The final wheel and source archive were built from immutable candidate tree
`7c5da6a3b572d3a1284c794f9127ab26a0cae4cb`; the annotated tag resolves to that exact
tree. All 29 reviewed source/test fingerprints matched. Package inspection confirmed
the six queue/identity modules, version, queue entrypoint, runtime dependency
separation and absence of local source overrides. Isolated installed-wheel checks
confirmed imported-module provenance, version, four minimal control parser forms
and three actual CLI help commands. No GPU control mutation was performed.
[Package evidence](package.json) records artifact hashes and the checked references.
All dependency sources, versions and metadata match the baseline after excluding
only the root package version. Temporary extracted checkouts, wheel installations,
index copies and archives were removed; evidence logs and built packages remain.

## Delivery status

Application master and annotated `v0.31.0` were pushed atomically. Remote branch,
annotated-tag object and peeled commit matched the local references. Companion
collection `v0.2.5` was committed at
`48675d3473a668650673a8a2808046c217728485`, tagged and pushed atomically with main;
its remote branch/tag/peeled references also matched. The collection's full Markdown,
discovery, skill metadata, local link and architecture checks passed; final release
wording was linted again. This publishes source and Git tags only. No GitHub Release,
assets, registry packages, deployment or installed skill updates were performed.

T027 and T028 are complete. The exact local source overrides and unrelated draft
were preserved, and the index was clean after release. Final documentation evidence
is delivered in a separate task-scoped documentation commit; no new semantic version
is expected from that record. Historical physical multi-GPU/NCCL, real multi-user/NFS
and ClearML acceptance remain open as recorded in [verification](verification.md).

The deterministic test-race injections were executed through stdin and retained in
the agent transcript, not as standalone scripts or log files. They added a vanished
entry to `/proc` enumeration and returned an empty first child-PID read respectively.
The same injections passed after the corrections, including fork/orphan/thread
cleanup modes. The parent focused-suite log and original release failure logs remain
local evidence; their outcomes are recorded above without implying hardware checks.
