# Bug Assessment: Informative error diagnostics

- Slug: informative-error-diagnostics
- Created: 2026-10-06
- Source: user report and approved implementation/release plan
- Verdict: valid
- Severity: medium

## Report

“Make error messages at whole lib more informative. FiftyOne visualization publication failed; continuing task: OSError gives no information about what actually happens.”

## Symptom and reproduction

Publication handlers currently log only the exception class. Inject an OSError with a useful message into a publisher and call publish_results; the warning loses the message. Existing tests assert only the class. The original live backend failure is unknown; this fix addresses lost diagnostics, not an inferred backend fault.

## Root cause

Publication and ClearML secondary-failure boundaries discard exception text intentionally to avoid credentials. Other configuration boundaries suppress sensitive payloads; several recoverable failures omit operation/resource context. Loguru currently defaults to DEBUG, which the user explicitly chose to retain.

## Proposed remediation

Add a shared low-level diagnostics module that redacts messages/context, summarizes cause chains and formats DEBUG traceback locations without source excerpts or locals. INFO-level sinks show concise summaries. Preserve raw-payload suppression for opaque configuration resolution errors. Distinguish all publication operations, improve affected handlers across project-owned library and CLI modules, and preserve failure semantics, exception types, status privacy and dependencies. No external dependency edits.

Files: new diagnostics module/tests; publication and tests; affected caught-error boundaries in configuration, session, dataset/cache, model recovery, filesystem, GPU/CLI modules and their regression tests. Audit adequate handlers without unnecessary rewrites. Update publication/logging contracts and Russian README troubleshooting.

## Acceptance

Reproduce the reported missing-message path with injected failures; verify messages, contexts, causes, DEBUG frames, credentials absent, empty exceptions/cycles and secondary errors preserving primary failures. Run full pytest, Ruff, mypy, import checks and documentation validation. Obtain independent review. For release follow repository end-to-end CPU/GPU/live publication and fresh wheel/source install gates, then checked semantic release and explicit branch/tag push verification. Block publication if mandatory gates fail.

## Risks and boundaries

Arbitrary error text cannot be exhaustively sanitized: retain conservative opaque-config suppression and never expose locals/source excerpts. Preserve current raw stdout/stderr forwarding and credential-safe task status contract. Existing local dependency source overrides must be restored exactly after commit hooks. Do not change approved dependency copies. No claim to resolve the originally unknown backend failure.
