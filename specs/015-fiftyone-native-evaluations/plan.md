# Implementation plan

## Summary

Register exact imported evaluation results and extend the native FiftyOne UI without
changing the project's evaluation methodology. See [spec](spec.md).

## Technical context and constitution check

Python 3.12, uv, Pydantic, existing FiftyOne 1.x and pinned digital-metrics. Typed neutral
payloads remain outside the lazily loaded FiftyOne boundary. Expand the import allowlist
only to the new backend/UI adapters. No dependency changes or installed tooling edits.
All constitution principles pass; existing uncommitted local sources are preserved.

## Implementation

1. Add a versioned optional report to EvaluationPayload: class order, exact confusion
   matrix, PRCurve records and typed class AP values, populated after evaluate_split.
2. Add importable DigitalMetricsEvaluationConfig/Evaluation/Results adapters. Register
   deterministic task/split evaluation keys, persist native result arrays and source
   evidence, status/ID/IoU fields, and exact canonical confusion associations.
3. Integrate cleanup-before-write and saved views/results into publisher's lock. Extend
   receipts and run links; preserve existing schema/datasets and raw overlay evidence.
4. Package a Python plugin extending the builtin evaluation panel and an AP/PR panel.
   Correct wrong-class totals and exact ID clicks, bypass stale builtin cached wrappers,
   support native fixed-threshold subset semantics, hide subset AP without evidence.
5. Run isolated persistence, UI, metrics/pipeline acceptance and regression/static gates.

## Ownership

Parent: publisher integration, receipt/link, import contract, integration tests, docs and
final verification. Payload agent: evaluation payload/scoring and dedicated tests.
Backend agent: new backend module and dedicated tests. UI agent: plugin/UI module and
its tests. Each agent has exclusive files and cannot delegate.

## Documentation and validation

Amend specs/006-fiftyone-integration/contracts/publisher.md, docs/current-contracts.md,
README.md, affected integration spec/quickstart, and local acceptance guidance. Validate
Markdown/local links and examples. Keep dated evidence separate. Native UI behavior
requires an actual App check; mocks alone do not establish acceptance.
