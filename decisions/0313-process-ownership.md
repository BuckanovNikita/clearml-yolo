# ADR-0313 · Supervise native descendants using Linux process identity

Training or a batch trial can spawn grandchildren, create another session or outlive its direct parent. A numeric PID can be reused by an unrelated process.

**Decision.** Linux supervision records process birth identity and uses subreaper discovery, scoped ownership evidence and pidfds. The supervisor verifies identity before signalling or reaping, terminates owned descendants and checks for quiescence across successive scans. Ambiguous ownership is an error.

**Consequences.** Cancellation triggers bounded cleanup and can escalate from SIGTERM to SIGKILL. Unknown processes are left alone. A simultaneous workflow and cleanup failure retains evidence of both. The process capability suite exercises host facilities; CPU process tests do not establish native GPU cleanup.

[Ownership and signal rules](../src/clearml_yolo/adapters/runtime/process_tree.py) · [Execution boundary](../src/clearml_yolo/adapters/runtime/execution_lifecycle.py) · [Orphan and replacement scenarios](../tests/test_subreaper_process_tree.py) · [Host capabilities](../tests/test_process_capabilities.py) · [Technical reference](../DOCS.md#process-ownership) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/e1fe64ea7a053bb39daf4d8f477f63e4a6a8a236)
