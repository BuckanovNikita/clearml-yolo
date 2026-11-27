# ADR-0417 · Run live service checks with isolated credentials and tagged resources

The integration task provisions an [owned environment](0407-live-environment.md), runs the non-GPU integration scope and arranges cleanup on exit. The CPU smoke scenario invokes commands with an explicit project and run tags and queries the ClearML result. FiftyOne tests exercise dataset publication, evaluation and panel behavior at their own service boundary.

A recorded passing live scenario establishes only the paths it exercised. Agent replay, browser UI behavior and multi-host operation require their own observations. A release also has a distinct [native GPU validation](0409-native-validation.md). [Integration orchestration](../Taskfile.ops.yml) · [CPU ClearML scenario](../tests/integration/test_cpu_stand_smoke.py) · [FiftyOne service scenarios](../tests/integration/fiftyone) · [Environment contract](../DOCS.md#live-test-environment)
