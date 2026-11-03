# Consistency analysis (2026-11-03)

The amendment reuses feature 006 and its current implementation; no installed
Spec Kit files, historical tasks, catalogue schemas or search/lookup policy change.
Extension hooks are empty. Existing feature checklists remain unchanged.

| Requirement | Design/implementation | Verification |
| --- | --- | --- |
| Offline saved coverage | Pure ModelCoverage/model_coverage, existing store.read, early CLI dispatch | Missing/all-covered/mixed evidence; forbidden runtime/GPU/probe/write calls |
| Honest reasons and context | Existing diagnostic/trial/status fallback, no inferred cause, escaped cells | Failed/incomplete/distinct contexts and control characters |
| Any usable record covers | Reuse EstimateCase.usable, catalogue order | Validated/ceiling/numerical cases and mixed failures |
| Existing selection and measurement | select_models aliases; conditional imgsz; explicit measurement flag rejection | Filter/order/aliases/duplicates/defaults/abbreviations and existing estimation tests |
| Failure and data preservation | Existing read validation; argparse errors; no save or schema migration | Missing/corrupt/unreadable catalogues, unchanged bytes and directory inventory |
| Architecture and documentation | Inward core rules, inert options, adjacent record and documentation tasks | Existing executable import/negative contracts; scoped effects and docs checks |

No unresolved product decisions or conflicting requirements were found. Shared
parser help/default snapshots change only for the intentional list/imgsz interface;
other command/schema baselines remain equivalent. The published baseline is 84166d5;
original checkout changes are excluded. Queue bound compatibility and portable usage
changes are dependent companion workstreams, with final pair/source review required
before release. No mutation selection or selected policy dependency changes, so the
maintained evaluation/export mutation suite is outside the affected contract.
