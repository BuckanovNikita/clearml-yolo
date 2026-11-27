# ADR-0220 · Measure GPU capacity and select a training batch

Batch discovery and training have separate lifetimes. `cy-batch-estimate` measures a model and workload on an admitted GPU and records what the measurement established. A later training invocation can opt into an editable table with `batch=null`. Training lookup neither launches a probe nor retries a failed run at a smaller batch.

## Admission and measurement

The estimator groups selected devices by hardware profile, checks whole-GPU memory, utilization and competing compute processes, then runs bounded training trials for the selected model, square image size and synthetic object population. A busy device can be replaced by another selected device with the same profile. CY checks for contamination during the trial and separately confirms a usable batch against the memory budget.

`--force` permits background activity when no competing compute process is attributable. A known foreign compute PID or missing whole-GPU telemetry still prevents measurement, including unsupported MIG layouts. Forced results retain a background-sensitive marker. A validated capacity, search ceiling, numerical limit, confirmed lack of capacity and failed case have different consequences for reuse. [Estimator command](../docs/commands/cy-batch-estimate.md)

<details>
<summary>Sources and verification</summary>

- Measure training batch capacity on one GPU per probe — [Command and scheduling](../src/clearml_yolo/entrypoints/batch_estimate.py) · [Measurement workflow](../src/clearml_yolo/application/use_cases/batch_estimate.py) · [Trial search](../src/clearml_yolo/core/batch_estimation.py) · [Search bounds](../tests/test_batch_search_strategy.py) · [Workflow and failure cases](../tests/test_batch_estimate_workflow.py) · [Small-batch search and table history](https://github.com/BuckanovNikita/clearml-yolo/commit/0d1889dd1c9198a8827b90754c7eae0b2b9925fe)
- Admit batch probes only on observable CUDA devices — [GPU telemetry and admission](../src/clearml_yolo/adapters/runtime/gpu_inventory.py) · [Telemetry and process cases](../tests/test_gpu_inventory.py) · [Admission and forced reporting](../tests/test_batch_estimate_cli.py) · [Forced-measurement decision](https://github.com/BuckanovNikita/clearml-yolo/commit/c16dbb19d0b59df30c173696406a5f76ec1ac768)

</details>

## Saving evidence and inspecting coverage

CY saves completed cases to `batch-estimates.json` with their hardware and model profiles, workload, search bounds and outcomes. Locked read-modify-write and atomic replacement preserve completed cases across concurrent updates and interruption. Compatible evidence can populate the batch table. Stale or failed cases can be measured again. A corrupt evidence file is preserved and the error names its path.

`cy-batch-estimate --list` reads both files without initializing CUDA. It reports saved entries, known failures and catalogue models with no attempts. It accepts a model filter and rejects measurement-only options. Missing files yield an empty inventory. Invalid input yields an error.

<details>
<summary>Sources and verification</summary>

- Keep measurement evidence separate from training inputs — [Batch table contract](../docs/formats/batch-table.md) · [Evidence store](../src/clearml_yolo/adapters/storage/batch_estimates.py) · [Catalogue schema and compatibility](../src/clearml_yolo/core/batch_estimation.py) · [Legacy and corrupt store cases](../tests/test_batch_estimate_store.py) · [Reuse and interruption cases](../tests/test_batch_estimate_workflow.py)
- Inspect saved batch coverage without a GPU — [Batch estimator guide](../docs/commands/cy-batch-estimate.md) · [Listing entry point](../src/clearml_yolo/entrypoints/batch_estimate.py) · [GPU-free listing cases](../tests/test_batch_estimate_list.py) · [Missing-model listing history](https://github.com/BuckanovNikita/clearml-yolo/commit/a89e4869b0ee801c28ac31f9d99573d9485ac4e3)

</details>

## Editing the table and resolving a global batch

The YAML table stores positive per-GPU batch sizes keyed by GPU name and memory, square input size and canonical model. CY preserves ordinary comments. A reserved metadata comment stores measurement identity, precise capacity, forced status and confirmed failures. Invalid metadata makes the table unusable. A user's changed value is treated as manual, and an exact manual entry can supply a value after a no-capacity measurement. [Editable batch table](../docs/formats/batch-table.md)

Training first looks for an exact GPU name and capacity. Without an exact batch, confirmed no capacity blocks fallback. Otherwise it selects the largest eligible memory capacity no greater than the target and takes the smaller batch in a tie. The global batch equals the number of selected GPUs times the smallest resolved per-device batch. Effective settings identify the source entries. Fallback hardware and forced values generate warnings. CPU/MPS targets, custom YOLO architectures, non-square inputs and missing entries require an explicit batch. A per-GPU estimate alone cannot establish multi-GPU execution.

<details>
<summary>Sources and verification</summary>

- Store human-editable per-GPU training batches in YAML — [Table storage](../src/clearml_yolo/adapters/storage/batch_sizes.py) · [Entry and selection contracts](../src/clearml_yolo/core/batch_sizes.py) · [Batch table editing and metadata cases](../tests/test_batch_sizes.py) · [Editable table decision](https://github.com/BuckanovNikita/clearml-yolo/commit/0d1889dd1c9198a8827b90754c7eae0b2b9925fe)
- Resolve an unspecified training batch from the local table — [Opt-in lookup and provenance](../src/clearml_yolo/adapters/integrations/batch_resolution.py) · [Lookup cases](../tests/test_batch_lookup.py) · [Training integration cases](../tests/test_batch_resolution.py)

</details>
