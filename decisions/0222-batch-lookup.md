# ADR-0222 · Resolve an unspecified training batch from the local table

Setting the training batch to `null` opts into a lookup by selected GPU, catalogue model and square image size. An exact GPU name and capacity wins. Without an exact entry, confirmed no capacity blocks fallback. Otherwise CY takes the largest eligible capacity no greater than the target, choosing the smallest batch in a tie. Across GPUs it multiplies the smallest resolved per-device value by the device count.

The effective settings retain which entries supplied the batch. A fallback warns that the source GPU differs, and a forced source warns about background load. Missing entries, custom YOLO architectures, non-square inputs and CPU/MPS targets require an explicit batch. Training does not run a probe or retry at a smaller batch.

[Batch table contract](../docs/formats/batch-table.md) · [Opt-in lookup and provenance](../src/clearml_yolo/adapters/integrations/batch_resolution.py) · [Hardware selection](../src/clearml_yolo/core/batch_sizes.py) · [Lookup cases](../tests/test_batch_lookup.py) · [Training integration cases](../tests/test_batch_resolution.py) · [Lookup design history](https://github.com/BuckanovNikita/clearml-yolo/commit/0d1889dd1c9198a8827b90754c7eae0b2b9925fe)
