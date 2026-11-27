# ADR-0223 · Inspect saved batch coverage without a GPU

Operators can inspect preparation on a host without initializing CUDA. `cy-batch-estimate --list` reads the batch table and estimator evidence and reports available entries, known failures and catalogue models with no attempts. It accepts a model filter and rejects measurement-only options.

Missing files describe an empty inventory. Invalid stored input produces an error. Listing neither launches trials nor changes saved measurements.

[Batch estimator guide](../docs/commands/cy-batch-estimate.md) · [Listing entry point](../src/clearml_yolo/entrypoints/batch_estimate.py) · [GPU-free listing cases](../tests/test_batch_estimate_list.py) · [Missing-model listing history](https://github.com/BuckanovNikita/clearml-yolo/commit/a89e4869b0ee801c28ac31f9d99573d9485ac4e3)
