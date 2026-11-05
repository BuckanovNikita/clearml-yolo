# Fix: preserve training outcomes

Date: 2026-11-05. Status: applied and verified.
Assessment: [assessment](assessment.md). Architecture: [record](architecture.json).

## Changes

Core count policy distinguishes exact nonnegative integers from unavailable values. Reporting
adapters preserve unavailable-class metrics separately and exclude those classes from eligibility
aggregates. Diagnostics never introduce synthetic class rows into machine-readable dashboards.
Generated counts come from the exact trained checkpoint, not evaluation data. Counts without
matching provenance remain unavailable; historical model count recovery is not implemented.

Pipeline stage outcomes persist atomically and distinguish failed, skipped, successful and
warning results. A verified trained checkpoint survives downstream failures. Resource-handoff
failure skips downstream work. Interruptions remain fatal and persist an honest failed outcome.
Native completed callbacks and DDP replay/cleanup have explicit publication boundaries; normal
epoch/validation computation errors remain strict. Finalization preserves missing-upload truth
and publishes warning outcomes and supported ClearML completion messages where reachable.

## Review corrections

Independent review identified diagnostic footer rows interpreted as classes, stale interruption
outcomes, native callback/relay gaps and stale worker-normalized arguments. These were corrected
with regressions. Native verification exposed nested finalization deadlines and an unsupported
ClearML completion keyword; deadlines are now sequential and completion uses status_message.

## Scope amendments

Native runtime/trainer callbacks, result contracts, integration adapters and explicit workbook
SDK ownership were added to scope based on traced failure paths. Tests were updated to provide
actual nonempty checkpoints, structured metric tables and the new tracking seam. No dependency
source or approved revision changed.

## Completion reconciliation

The original assessment remains unchanged as planning history. Reporting/count behavior,
pipeline dependency outcomes, storage/tracking integration, native completion boundaries,
regression tests, documentation and independent review are complete. Current/proposed paired
queue checks and source-only portable usage validation passed. The first full suite exposed
four fixture mismatches; focused corrections and the complete canonical rerun passed.
Architecture scope matches the final diff and is independently accepted. Git-only delivery
follows the checked source commit; release evidence preserves this dated verification history.
