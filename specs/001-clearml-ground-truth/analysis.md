# Cross-artifact analysis — 2026-10-20

The specification, plan, task ledger, source interfaces and architecture record
were inspected before implementation. All nine functional requirements and four
success criteria have explicit implementation and acceptance tasks. The approved
selector, root CSV, external-image, local-warning and dependency-floor decisions
leave no unresolved implementation ambiguity.

Application policy owns normalization and provenance through injected ports.
The dataset adapter owns SDK lookup, cached CSV materialization and hashing.
Existing exhaustive import/effect contracts need one exact SDK edge and the
new application module classification; negative cases remain mandatory.
Packaging keeps protected external sources, upstream extras and existing pins.
Documentation includes the portable usage skill and preserves completed history.

The integration amendment adds pure export input-presence validation after a
regression exposed effects occurring before missing-input validation. It also
records the newer upstream publication/cache integration. These changes remain
within the approved compatibility scope and require renewed checks and review.
No workflow tooling or upstream dependency source change is required.

## New-epoch integration analysis — 2026-10-20

Upstream `0340e9c` consolidates retired contracts in `specs/000-baseline/spec.md`,
moves Ruff/import rules into dedicated files, and relocates frozen test fixtures.
This feature's nine requirements and four success criteria remain unchanged.
The new `001` feature references the baseline and adds only its source/dependency
contracts to the maintained index; the baseline is not converted into a task ledger.
T019–T024 append integration, documentation, renewed acceptance and delivery work.
Earlier completed checks remain evidence for their original source snapshots;
they do not establish the new merge's acceptance.
