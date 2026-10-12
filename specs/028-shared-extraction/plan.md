# Implementation plan

The approved user plan is the source of intent; [spec.md](spec.md) records its acceptance
requirements. Python, uv, existing numerical libraries and workbook libraries remain.
No new framework, detector, deployment or deduplication change is included.

## Baselines and work ownership

The inspected application baseline is 4aef37f. Dependency baselines are digital-metrics
7c6dfa98cc052ce0202f11655839078534182d77 and report-generator
8ddd0f7f11d25367f4e71ace77524ebb72257699. Both ignored source copies matched those Git
trees byte for byte before independent Git metadata was established.

Unrelated static-analysis edits to configuration, runtime/gpu_queue.py, existing tests,
docs/development.md, pyproject.toml and uv.lock are preserved. Task-owned dependency
documentation hunks must be reviewed separately from those edits.

Parallel streams: metrics_extraction owns external/digital-metrics; reporting_extraction
owns external/report-generator; compatibility_evidence owns the new compatibility test
and baseline evidence. Each delegate has bounded ownership and may not delegate. The
parent owns application integration, workflow records, final checks and delivery.
Delegates were requested as gpt-6.1-sol/high for numerical and artifact compatibility;
runtime settings are not independently observable. Integration follows corresponding
upstream interfaces; parent verification and fresh independent review are sequential.

## Architecture

The executable decision/evidence index is [architecture.json](architecture.json).
Evaluation and reporting adapters own dependency APIs and effects; core retains neutral
models and local policy. Fixed results are converted into existing core records, and
PR reconstruction becomes a wrapper around authoritative observations. Reporting v2
receives exact labels, explicit layout and application-owned identity metadata policy.

Comparison core gains an additive statistics interface/entrypoint sharing existing
assembly. Its original entrypoint and statistical functions stay compatible. The
evaluation adapter implements the statistics interface using digital-metrics. An
additive optional protocol on the existing evaluation dependency enables production
composition to use the extracted path while existing injected implementations keep
working. WorkflowDependencies fields and constructor remain unchanged.

Existing import-linter and architecture tests cover SDK ownership, inward dependencies,
effects, cycles and negative injected violations; no new blanket exception is allowed.
Each dependency records its own module contracts and negative-case check.

## Verification and documentation

Capture legacy science, public contracts and semantic workbooks before replacing
implementations. Run both library suites, new API checks, application pytest, Ruff,
mypy, Vulture and architecture checks. Tests with mocked publication do not establish
GPU execution or remote upload; this change targets offline numerical/report parity.
Document extraction boundaries and deliberate dependency revisions in development and
current-contract guidance; validate Markdown/local links and changed examples. Retain
dated test evidence separately from evergreen instructions. Review the final integrated
diff before release/commit procedures; required failed checks block acceptance.
