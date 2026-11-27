# ADR-0221 · Store human-editable per-GPU training batches in YAML

Operators need to override a measured value or supply a value for a known GPU. The batch table groups positive per-GPU batch sizes by GPU name and memory, square image size, and canonical model identifier. CY preserves ordinary comments and stores measurement identity, precise capacity, forced status and confirmed failures in one reserved metadata comment.

A user's changed value is treated as manual. An exact manual entry can supply a usable value after a previous no-capacity measurement. A malformed metadata comment makes the file invalid. This YAML table is the runtime input for training lookup.

[Batch table contract](../docs/formats/batch-table.md) · [Table storage](../src/clearml_yolo/adapters/storage/batch_sizes.py) · [Entry and selection contracts](../src/clearml_yolo/core/batch_sizes.py) · [Batch table editing and metadata cases](../tests/test_batch_sizes.py) · [Editable table decision](https://github.com/BuckanovNikita/clearml-yolo/commit/0d1889dd1c9198a8827b90754c7eae0b2b9925fe)
