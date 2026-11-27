# ADR-0306 · Publish run-scoped overlays to a shared FiftyOne dataset

`cy`, `cy-predict` and `cy-metrics` can make the same ground truth browsable alongside results from different runs. The database may be unavailable while the main experiment is healthy.

**Decision.** Preflight and publication run in bounded workers with GPU visibility and invocation ownership removed. The publisher locks the dataset named by prefix, schema version and ground truth CSV hash. Run-specific prediction and evaluation fields derive from the ClearML task ID. CY records a local `fiftyone_publication.json` receipt for successful publication.

**Consequences.** A later run can reuse the dataset and keep a distinct overlay. Ordinary optional publication failures produce warnings and cancellation propagates. Inspect the receipt for dataset and field names. [Prediction](0110-prediction.md) and [metrics](0130-metrics.md) can publish independently. A metrics payload can also produce a [native evaluation](0307-fiftyone-evaluation.md).

[Workflow policy](../src/clearml_yolo/application/use_cases/publication.py) · [Worker supervision](../src/clearml_yolo/adapters/fiftyone/bounded.py) · [Dataset publication](../src/clearml_yolo/adapters/fiftyone/publisher.py) · [Database integration scenarios](../tests/integration/fiftyone/test_fiftyone_publisher.py) · [Command-specific configuration](../docs/configuration/fiftyone.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/63fd89940303402af3fcd957dcd3cfabb5eea795)
