# Bug Assessment: Current dependency minimums

- **Slug**: current-dependency-minimums (generated)
- **Created**: 2026-10-05
- **Source**: user request
- **Verdict**: valid
- **Severity**: low

## Report and reproduction

Raise digital-metrics and report-generator minimums to their current versions,
run regression checks, then create a release.
The project declares digital-metrics >=0.5.3, while the pinned submodule,
lockfile and installed metadata all report 0.6.0. report-generator already
matches its current version, >=0.1.0. This is a metadata mismatch;
no runtime failure was reported.

## Remediation

Raise only the digital-metrics minimum to >=0.6.0. Preserve both pinned revisions
and all other dependency metadata. Validate constraints, run the complete pytest
suite and code checks, then follow the existing local release procedure.

## Documentation scope and risks

Review README.md, docs/development.md and docs/current-contracts.md. Package
metadata is authoritative for versions; runtime and installation syntax do not
change. Tests cover the pinned dependencies, not live GPU/ClearML execution.
Keep workflow artifacts in bugs/ to preserve installed .specify/ files.

## Corrected release baseline

The user clarified that current upstream releases are digital-metrics 0.6.1 and
report-generator 0.1.1, and clearml-yolo 0.14.0 was already published.
The initial observations above described stale local checkouts. Fetching origin
confirmed all three tags. The authorized remediation is now to fast-forward master,
raise both minimums to the specified releases, advance their gitlinks to those tags,
and refresh the lockfile. Run the suite again on this corrected baseline before
creating clearml-yolo 0.14.1. The earlier test run is historical evidence only.
