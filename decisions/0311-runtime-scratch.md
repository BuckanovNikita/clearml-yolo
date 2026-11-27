# ADR-0311 · Retain invocation scratch after every exit

Captured logs, worker diagnostics and paths inherited by late descendants can still be needed after their initiating scope exits.

**Decision.** An outer runtime scope creates a unique `cy-runtime-*` arena under the workspace scratch root. Nested scopes in the same process reuse it. A spawned process entering a new runtime scope can create its own. `CY_RUNTIME_TEMP_ROOT` can relocate the scratch parent within the workspace.

**Consequences.** Success, error and cancellation all leave the invocation arena available. Starting another run never sweeps old arenas. A helper can separately clean its own operation-specific temporary files. Operators can inspect and remove obsolete run scratch after consumers finish.

[Arena lifetime](../src/clearml_yolo/adapters/runtime/bootstrap.py) · [Retention and subprocess scenarios](../tests/test_runtime_bootstrap.py) · [Workspace cleanup guide](../docs/workspace.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/28b74f72054889c4b0706fecb8983c0ed6196235)
