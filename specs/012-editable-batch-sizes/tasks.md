# Tasks: Editable batch sizes

## Setup and foundation

- [x] T001 Inspect current contracts, boundaries and native workflow; create design artifacts in specs/012-editable-batch-sizes/.

## US1 - Editable training lookup

- [x] T002 [P] [US1] Implement pure table selection in src/clearml_yolo/core/batch_sizes.py and storage in src/clearml_yolo/adapters/storage/batch_sizes.py; test exact/fallback ties, precision, comments, corruption and concurrent updates in tests/test_batch_sizes.py.
- [x] T003 [US1] Integrate YAML training resolution and provenance in src/clearml_yolo/adapters/integrations/batch_lookup.py and batch_resolution.py; verify mixed GPUs, manual edits and removed workload/recipe gates in tests/test_batch_lookup.py and test_batch_resolution.py.

## US2 - Small-batch search

- [x] T004 [P] [US2] Add versioned search in src/clearml_yolo/core/batch_estimation.py; test capacities zero through eight, ceilings, confirmation, numerical recovery and historical replay in tests/test_batch_search_strategy.py and test_batch_alignment.py.

## US3 - Safe refresh and offline inspection

- [x] T005 [US3] Implement fixed workload, refresh selection, parent publication and offline listing in src/clearml_yolo/entrypoints/batch_estimate.py and options.py; verify receipt rejection and refresh preservation in tests/test_batch_estimate_cli.py and test_batch_estimate_list.py.

## Integration and verification

- [x] T006 Update docs/batch-estimation.md, docs/current-contracts.md and README.md; reconcile specification meaning with final diff.
- [x] T007 Run project verification and mutation; record outcomes in specs/012-editable-batch-sizes/verification.md.
- [x] T008 Commit coherent changes, run clean-tip acceptance, paired source compatibility and final prek pipeline; record evidence and limitations in specs/012-editable-batch-sizes/verification.md.
- [x] T009 Run bounded native estimation and training lookup when hardware permits; record actual outcomes in specs/012-editable-batch-sizes/verification.md.
- [x] T010 Obtain fresh independent review after integration/verification; reconcile findings and evaluate authorized release boundary in specs/012-editable-batch-sizes/verification.md.

## Dependencies and execution

T002 and T004 are parallel; T003 depends on T002 API. T005 depends on T002 and T004. T006 reconciles all integrated work. T007 precedes clean-tip checks and T010. Implementation and verification are incremental; no deployment/push is authorized. Required deferred checks keep acceptance incomplete.
