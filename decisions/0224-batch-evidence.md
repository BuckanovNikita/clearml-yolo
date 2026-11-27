# ADR-0224 · Keep measurement evidence separate from training inputs

Reusing a synthetic trial requires its hardware and model profile, workload, search limits and outcome. CY validates and saves these case records in `batch-estimates.json` using locked read-modify-write and atomic replacement. A failed or stale case can be remeasured, while an interrupted run retains completed cases.

The estimator can reuse compatible evidence when filling the editable table and reports failed attempts separately. Training reads the YAML table. A corrupt evidence catalogue raises an error with its path and is preserved for inspection.

[Batch table contract](../docs/formats/batch-table.md) · [Evidence store](../src/clearml_yolo/adapters/storage/batch_estimates.py) · [Catalogue schema and compatibility](../src/clearml_yolo/core/batch_estimation.py) · [Legacy and corrupt store cases](../tests/test_batch_estimate_store.py) · [Reuse and interruption cases](../tests/test_batch_estimate_workflow.py)

See [editable batch table](0221-batch-size-table.md).
