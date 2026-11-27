# ADR-0407 · Give each integration run an owned test environment

ClearML and FiftyOne integration tests create state in external services. The lifecycle manager allocates a namespaced test environment, records its ownership and supplies session credentials and port forwards to the tests. The run tag identifies its resources. Teardown checks that the worktree owns the environment being removed.

The preflight distinguishes an unavailable cluster from invalid configuration. Operators can retain an environment for inspection and use its identifier for cleanup. The lifecycle below describes test infrastructure. Production deployments have their own hosts, credentials and data. [Lifecycle and operating guide](../tests/integration/lifecycle.py) · [Task entry points](../Taskfile.ops.yml) · [Live fixtures](../tests/integration/conftest.py)
