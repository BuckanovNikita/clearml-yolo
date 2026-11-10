# Interface contract

The authoritative behavior is [batch estimation](../../../docs/batch-estimation.md), updated with this feature. The public YAML shape is GPU label -> integer square size -> canonical model -> positive integer per-GPU batch. GPU labels use `Name [N GiB]`.

`--classes` is removed. Explicit `--models` or `--refresh` requests fresh measurement. Offline `--list` reports table entries and known failures. Training `batch=null` consults only the table and records its digest and selections.
