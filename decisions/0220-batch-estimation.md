# ADR-0220 · Measure training batch capacity on one GPU per probe

Training batch capacity depends on the model, square input size, synthetic object population and available device memory. `cy-batch-estimate` launches bounded training trials for each distinct selected hardware profile, searches against the specified memory budget and separately confirms the usable batch. CUDA admission checks device visibility and other compute processes. Forced measurements can allow background utilization and are marked accordingly.

The workflow saves completed case evidence as it goes and updates the batch table with its results. A numerical limit, capacity limit, search ceiling and failed measurement have different meanings. A recommendation for several GPUs derives from the weakest selected per-GPU value. It does not establish that distributed training ran.

[Batch estimator guide](../docs/commands/cy-batch-estimate.md) · [Command and scheduling](../src/clearml_yolo/entrypoints/batch_estimate.py) · [Measurement workflow](../src/clearml_yolo/application/use_cases/batch_estimate.py) · [Trial search](../src/clearml_yolo/core/batch_estimation.py) · [Search bounds](../tests/test_batch_search_strategy.py) · [Workflow and failure cases](../tests/test_batch_estimate_workflow.py) · [Small-batch search and table history](https://github.com/BuckanovNikita/clearml-yolo/commit/0d1889dd1c9198a8827b90754c7eae0b2b9925fe)

See [saved evidence](0224-batch-evidence.md), [editable batch table](0221-batch-size-table.md), [training lookup](0222-batch-lookup.md), [offline coverage listing](0223-batch-coverage.md) and [GPU admission](0225-batch-probe-admission.md).
