# Capability: Maintainable implementation and trustworthy verification

## Problem

Duplicated implementation and redundant verification increase maintenance effort;
weak tests and unsafe reuse can conceal changes to scientific results or ownership.

## Desired behavior

Preserve active process/queue behavior, typed composition and public interfaces while
removing unused internal supervision APIs and redundant parsing. Asset validation must
reject empty/truncated tensors, invalid dtype/shape and overlapping offsets, preserve
error translation/tracing, and check identity after reading. Cancellation must account
for detached descendants while protecting unrelated processes and reused PIDs.

Architecture enforcement covers ordinary, dynamic and type-only edges, cycles and
representative negative cases. Bounded offline mutation assessment covers selected
training-box, evaluation-policy and export-quality logic; rerun affected selections
when logic, tests or dependencies change. Surviving mutants require stronger assertions
or reviewed equivalence; untested, timeout and runner errors remain unresolved gaps.

The [verification interface](../011-simplify-hooks/spec.md) defines direct prek checks
and testmon selection. Generated release reuse requires exact parent, root-version-only
metadata, release paths and changelog validation, with tag ownership/concurrency checks.
Preserve local dependency overrides exactly and retain approved external revisions.

## Acceptance

Exercise valid and malformed assets, repeated cancellation and uncertain ownership,
forbidden imports and lifecycle release conflicts. Every selected mutant is killed or
has a reviewed equivalence explanation. Timing improvements require measured comparable
workloads; no count reduction or cached execution alone proves faster full acceptance.
Git-only code delivery and the explicit model-asset exception follow development policy.
