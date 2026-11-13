---
name: verification-workflow
description: Use when selecting verification, committing, reporting completion or evaluating reusable evidence.
---

# Select verification

Read `docs/development.md` (Verification and Commit procedure). Paths start at the
repository root. Task owns execution; the native evidence record owns selection.

1. Inspect changes and record the comparison base/tip: the whole development branch,
   or changes since the previous release. Select comprehensive verification when no
   reliable release baseline exists.
2. Map affected contracts to checks. Use focused product tests for local changes;
   full coverage for shared runtime/configuration, broad refactors or uncertain impact.
   Select live/manual checks for affected claims automation cannot establish. Use
   `mutation-testing` for product changes and `running-integration-tests` for live work.
3. Record exclusions and reuse reasons alongside source/environment identities.
   Reuse successful evidence only while relevant inputs remain applicable; rerun
   invalidated checks. A focused run cannot establish the global coverage floor.
4. Complete native consistency review, follow the commit procedure, then run the final
   `prek run --all-files` with overrides cleared. Obtain independent review for behavior
   or policy changes after integrated verification.
5. Report selected checks as passed, failed, deferred, waived or error. Unavailable
   required checks block completion until executed or explicitly waived by the user.
   Use `release` only within release authorization.
