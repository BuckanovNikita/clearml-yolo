# Bug Assessment: Queue view refresh isolation

- **Slug**: queue-view-refresh-isolation (explicit user plan)
- **Created**: 2026-10-19
- **Source**: supplied implementation plan
- **Verdict**: valid
- **Severity**: medium

## Report and symptom

The supplied plan reports that one missing private snapshot prevents both list and TUI
from showing all readable public job summaries. Old package identities and legacy settings
alone did not reproduce the reported ValueError; its exact origin remains unverified.

## Reproduction and inspected cause

Submit a broken and a healthy job into isolated filesystem storage, remove the first
private snapshot, and call QueueService.list(). Its current strict refresh invokes
_refresh_status for every owned job; load_snapshot raises before any QueueView is returned.
Add this automated reproduction before implementation and record its executed result in test.md.
Confidence is high from the service/runtime/storage call chain; no live queue mutation is needed.

## Proposed remediation

Core owns QueueRefreshIssue(job_id, message) and default-empty QueueView.refresh_issues.
Application QueueProcessPort gains refresh_monitoring() returning a tuple of issues;
list uses it, retains affected public summaries without recomputing their wait/allocation
fields, and filters issues with archive visibility. Tick retains strict refresh.
The runtime monitoring path reads status only, without recovery transitions, heartbeat,
process cleanup or reservation release. Storage marks only private snapshot read/validation
failures with a typed exception; manifest/transaction/owner authorization errors propagate.
Runtime catches these and bounded private status read errors per owned job; publication
and coordination failures remain queue-wide. Fixed safe messages contain no exception data.
Entrypoints render row diagnostics, visible warning counts and equivalent JSON fields.
TUI retains rows and selection on later queue-wide failure. No migrations or old-task execution.

## Architecture and task contract

See [architecture.json](architecture.json). Existing inward layers, SDK isolation and
negative architecture tests cover all affected modules; no dependency changes are planned.
Python >=3.12.13,<3.14; uv build backend, prepared environment with frozen/no-sync checks.
Keep approved digital-metrics revision, local source overrides and unrelated ClearML/cache
changes intact. Existing hooks run all checks and generate changelog/version commits;
release must isolate unrelated changes if required.

## Ordered work

1. Reproduce failure; establish typed core/application interfaces and validate architecture plan.
2. Parent owns storage/runtime/service and their tests; bounded parallel agent owns presentation,
   CLI/TUI and rendering tests after the interface contract is established. No further delegation.
3. Integrate and run queue regressions, import contracts, architecture negatives, Ruff, mypy,
   Vulture and documentation checks; run full suite for commit acceptance.
4. Update docs/queue.md and queue contract, and portable corp-skills usage/evaluation guidance.
   Preserve unrelated edits in both repositories. README/index need no change unless inspection
   shows stale claims; they already route to queue.md.
5. Obtain fresh independent review after parent verification; reconcile diff and validate acceptance.
6. Complete authorized Conventional Commit and native Git-tag-only release, without deployment,
   GitHub Releases, package publication or skill installation.

## Risks and acceptance

Mixed missing/malformed/hash-invalid snapshots must retain pending, terminal and archived rows;
healthy progress updates and repaired diagnostics clear. Strict admission/execution/recovery,
ownership, task outcomes and reservations remain protected. Legacy config is opaque JSON and
must not cause Hydra import/evaluation. Public manifest/config/coordination failures remain fatal.
All verification is isolated filesystem/process/UI evidence, not GPU or ClearML acceptance.
