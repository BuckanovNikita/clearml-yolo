# ADR-0306 · Browse experiment overlays and their evaluation evidence in FiftyOne

CY publishes predictions from different runs against shared ground truth. FiftyOne provides the browsable dataset and App, while CY supplies run identity, scientific matches and the optional publication policy.

## Dataset and run overlays

`cy`, `cy-predict` and `cy-metrics` can publish to FiftyOne. Preflight and publication use bounded workers with GPU visibility and task ownership removed. The publisher locks a dataset identified by configured prefix, schema version and the ground truth CSV hash. Prediction and evaluation field names derive from the ClearML task ID. Two runs using the same ground truth can contribute distinct overlays.

Successful publication leaves a local `fiftyone_publication.json` receipt containing the dataset and field names. An ordinary connection or publication failure warns and lets the experiment continue. Cancellation propagates. Prediction and metrics can publish independently.

<details>
<summary>Sources and verification</summary>

- Publish run-scoped overlays to a shared FiftyOne dataset — [Workflow policy](../src/clearml_yolo/application/use_cases/publication.py) · [Worker supervision](../src/clearml_yolo/adapters/fiftyone/bounded.py) · [Dataset publication](../src/clearml_yolo/adapters/fiftyone/publisher.py) · [Database integration scenarios](../tests/integration/fiftyone/test_fiftyone_publisher.py) · [Command-specific configuration](../docs/configuration/fiftyone.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/63fd89940303402af3fcd957dcd3cfabb5eea795)

</details>

## Native evaluation from CY matches

For each published split with evaluation data, CY registers a native detection evaluation with method `digital_metrics`. It translates CY match identities and indices into FiftyOne label IDs, using the same claimed ground truth as the source confusion matrix. Persisted labels therefore refer to the pairs CY already scored. The evaluation also carries fixed-threshold observations and the supplied AP and precision–recall report. Prediction-only overlays have no evaluation. Confirming that a particular run persisted its labels requires a live database.

<details>
<summary>Sources and verification</summary>

- Import CY matches as native FiftyOne evaluations — [Native evaluation mapping](../src/clearml_yolo/adapters/fiftyone/evaluation.py) · [Result tests](../tests/test_fiftyone_evaluation_results.py) · [Native database scenarios](../tests/integration/fiftyone/test_fiftyone_native_evaluations.py) · [FiftyOne usage](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/60ab70bf90fffab7747f0f53ab2e0e67ac08b764)

</details>

## App and subset views

The environment serving the App needs access to the published dataset and media. Its operator explicitly calls `install_evaluation_plugin()` to install `@clearml-yolo/evaluation` and restarts a running App. Reinstallation requires explicit overwrite.

The panel uses the stored reports and label IDs to navigate from a result to its samples and matched labels. A filtered view can show fixed-threshold evidence for its subset. AP and precision–recall curves are available for the full split where they were computed and stay unavailable on subsets.

<details>
<summary>Sources and verification</summary>

- Install the FiftyOne evaluation panel explicitly — [Installer and panel](../src/clearml_yolo/adapters/fiftyone/panel.py) · [Extension manifest](../src/clearml_yolo/adapters/fiftyone/plugin/fiftyone.yml) · [Panel behavior](../tests/test_fiftyone_panel.py) · [Live view scenarios](../tests/integration/fiftyone/test_fiftyone_panel_views.py) · [App instructions](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/60ab70bf90fffab7747f0f53ab2e0e67ac08b764)

</details>
