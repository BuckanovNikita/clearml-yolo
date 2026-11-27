# ADR-0307 · Import CY matches as native FiftyOne evaluations

A second matcher could assign a different detection to the same ground truth. Browsing results should preserve the scientific decisions already made by CY.

**Decision.** Using [CY scoring evidence](0132-fixed-scoring.md), register a native detection evaluation with method `digital_metrics` for each published split that has evaluation data. Carry CY match identities and indices into FiftyOne label IDs, preserving the source confusion matrix's rules for claimed ground truth. The imported evaluation retains fixed-threshold observations and the supplied AP and precision–recall report.

**Consequences.** A prediction-only publication has no native evaluation to browse. Persisted runs expose sample and label relationships to the [App extension](0308-fiftyone-app.md). A live database is needed to establish SDK persistence.

[Native evaluation mapping](../src/clearml_yolo/adapters/fiftyone/evaluation.py) · [Result tests](../tests/test_fiftyone_evaluation_results.py) · [Native database scenarios](../tests/integration/fiftyone/test_fiftyone_native_evaluations.py) · [FiftyOne usage](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/60ab70bf90fffab7747f0f53ab2e0e67ac08b764)
