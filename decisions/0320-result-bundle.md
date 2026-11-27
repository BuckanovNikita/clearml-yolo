# ADR-0320 · Publish one set of result rows per invocation

A single pipeline can first produce raw predictions and later add evaluation and comparison evidence. Publishing an early partial table as the final result would lose those contributions.

**Decision.** Register effective ground truth once and upload its `gt_csv`. Declare the prediction-producing stages up front. Maintain rows and identities per result context and split, persist their index, and assemble `predicts_csv` once the last declared producer has completed.

**Consequences.** The [prediction CSV](0112-prediction-csv.md) is the inference interchange format. An invocation with only ground truth produces no prediction artifact. Rows outside selected splits can remain in the bundle with their status. Conflicting ground truth and late contributions are rejected. A consumer can inspect individual context identities and the combined artifact.

[Result assembly](../src/clearml_yolo/adapters/clearml/results.py) · [Multi-producer and identity cases](../tests/test_clearml_results.py) · [Artifact and row formats](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/fd395d34bff7f3128047e5d0c302f2c3f0720b78)
