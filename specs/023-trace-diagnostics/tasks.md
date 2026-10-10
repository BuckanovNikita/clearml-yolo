# Tasks: readable TRACE diagnostics

## Foundation

- [X] T001 Parent: inspect contracts, preserve overrides, update global/project collaboration.
- [X] T002 [P] Read-only A/B/C inventories; establish spec/plan and coverage requirements.
- [X] T003 Parent: helper, monitor, resources port, composition and architecture allowance;
  foundational behavior/redaction/watchdog tests in tests/test_tracing.py.

## Publication and execution (depends on T003)

- [X] T004 [P] A: adapters/clearml and tests/test_trace_clearml.py; full finalization spans.
- [X] T005 [P] B: adapters/fiftyone and tests/test_trace_fiftyone.py; lock/write/evaluation spans.
- [X] T006 [P] C: adapters/runtime + integrations and tests/test_trace_runtime.py; GPU/native/DDP.
- [X] T007 Parent: application workflows/evaluation and entrypoints; command return and port use.

## Remaining coverage (depends on T004-T007)

- [X] T008 [P] A: adapters/storage and tests/test_trace_storage.py; cache/conversion/export.
- [X] T009 [P] B: adapters/evaluation/reporting/yolo and tests/test_trace_compute.py.
- [X] T010 Parent: cross-component/subprocess tests, integrate inventories and fixes.

## Documentation update (depends on implemented interfaces)

- [X] T011 [P] C: README.md, docs/diagnostics.md, docs/current-contracts.md,
  docs/project-contracts.md; Bash capture, examples, architecture and limitations.
- [X] T012 Parent: validate changed Markdown/local links/examples and record dated evidence.

## Acceptance and release

- [X] T013 Parent: required static/full/native checks and combined-diff review.
- [X] T014 Fresh read-only review; resolve findings, verify and re-review material corrections.
- [ ] T015 Parent: authorized checked release commit/tag/push; restore exact local uv sources.
