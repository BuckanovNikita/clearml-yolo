# ADR-0409 · Exercise the native detector lifecycle on one GPU

The Severstal integration suite needs a prepared corpus, a selected GPU and an explicit ClearML destination. Each scenario exercises short training, checkpoint reload, inference and publication checks. Resource preflight and bounded execution make the operational requirements visible to the operator.

The suite is intended to establish execution for the chosen scenario. It supplies neither an accuracy benchmark nor evidence of multi-GPU training. Permanent evidence for a particular run belongs with its revision and inputs in the issue or PR. [Native suite](../tests/integration/test_severstal_gpu.py) · [Scenario harness](../tests/severstal_harness.py) · [Live procedures](../DOCS.md#live-test-environment)
