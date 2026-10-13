# Independent review: Ctrl+C GPU orphan cleanup

Date: 2026-10-13. Reviewer: native subagent `/root/review_cancellation`, fresh
context, requested GPT-6.1 Sol/high; realized runtime settings are not independently
observable. Read-only assignment, no further delegation. Final verdict: **ship**.

The reviewer inspected the complete task-owned runtime, supervisor, tests, docs and
architecture record after parent targeted verification. It checked PID/start-time
validation around pidfd signalling, detached/reparented discovery, fresh scans,
nested signal deferral/restoration, unsuccessful cancellation and cleanup before
queue release. No blocking correctness or architecture findings remained.

The reviewer independently reproduced an unrelated newer same-user non-dumpable
process preventing verified cleanup. Documentation was corrected to disclose this
conservative visibility requirement, and a real-process regression confirmed the
unknown process remains alive while the owned worker is stopped. The reviewer then
approved the amended docs/test. Its minor privileged-runner portability suggestion
was applied: skip that regression when the process environment remains readable.
The nonprivileged targeted rerun passed; Ruff passed afterward.

Parent verification: the full suite passed 2269 tests with 30 skips, and the final
expanded cancellation file passed eight checks separately. The last portability
amendment passed its targeted test. Mypy, Ruff, Vulture, import-linter and architecture
checks passed. Full-suite output was reviewed by the parent; the reviewer did not
claim to rerun it. Physical remote GPU behavior remains unverified.

Diff reconciliation: runtime process ownership and Hydra launch/cleanup changes,
the new cancellation test file, one existing test signature adaptation, README,
runtime/GPU contracts and these bug artifacts are task-owned. No dependencies,
registry schema, model SDKs, public configuration or composition targets changed.
Pre-existing edits in static-analysis configuration/docs, pyproject/lock, gpu_queue
and unrelated tests were excluded and preserved. No files were deleted or renamed.

## Corrected release candidate review — 2026-10-13

A fresh read-only reviewer (`/root/review_corrected_release`) initially identified
late-fork discovery gaps after the earlier PID-reuse correction. Following the
three failing regression reproductions and stable-scan correction, the reviewer
returned **SHIP**, subject to remaining release checks, with no blocking findings.
Marker-based ownership, retained PID/start identities, visibility failures and bounded
cleanup remain intact. The reviewer inspected the 185-pass focused log and independently
passed diff whitespace and architecture acceptance validation. This supersedes earlier
code approvals; full release hooks and distribution checks are recorded separately in
[release.md](release.md).

## Release evidence review — 2026-10-13

The same independent reviewer checked the source and version commits after full-suite
verification and fresh package installation. The verdict was **SHIP**, conditional
on the final tag hook and remote ref readback. It independently confirmed owned
source hashes, version-only metadata changes, unchanged dependency references, both
2281-pass/30-skip suite reports and both 790-check distribution reports. All 157
Python files in both distribution archives matched the checkout byte-for-byte.
Native artifact/checkpoint hashes, 6/108 row counts, ticket release and zero tagged
resources matched the retained readbacks. No release-blocking findings remained.
The final tag hook and local acceptance are recorded in [release.md](release.md);
remote publication is checked separately after this record.

## Fresh 0.26.2 integration review — 2026-10-13

`/root/review_v0262_base` returned **SHIP**, conditional on remaining release gates,
with no blocking code, integration, architecture or scope findings. The read-only
review independently confirmed the seven owned paths, six bug records and three
release metadata paths, no upstream overlap, all four source/test hashes, root-only
metadata version changes and clean approved dependency revisions.

It inspected the 2296-pass/30-skip source suite, including 18 cancellation and 94
architecture cases. Both packages passed 790 checks; all 157 Python files in each
archive matched the source. Native artifact/checkpoint bytes matched the readbacks,
the GPU registry was empty, and tagged-resource cleanup was confirmed. Independent
whitespace, architecture and Markdown checks passed, including 44 local links/anchors.
The version hook/tag and final evidence update were still pending at review time;
[release.md](release.md) records their subsequent acceptance. Remote publication and
workspace preservation are checked separately. Physical remote multi-GPU cancellation
and the cause of the historical SIGILL remain unverified. No repository edits or
additional test-suite/native runs were performed by the reviewer.

## Feature 029 integration — 2026-10-13

The records above preserve the preceding cleanup implementation and checks. Feature
[029](../../../specs/029-shared-cy-queue/spec.md) replaces the old Hydra scheduler.
Its generic process-tree ownership and signal protections are retained in runtime
`process_tree.py`/`supervision.py` and extended by queue guardians and direct native
descendant scopes. The new [task ledger](../../../specs/029-shared-cy-queue/tasks.md)
owns integrated verification, physical GPU cancellation, forced worker/guardian death,
reservation recovery and release acceptance. Earlier counts are historical evidence,
not a claim that the refactored execution paths have passed those same checks.
