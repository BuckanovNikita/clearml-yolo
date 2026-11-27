# ADR-0323 · Bound ClearML finalization and quarantine uncertain owners

Closing a task can block inside the SDK. Starting a new experiment in a process that still has an active owner could attach work to the wrong task.

**Decision.** The owner runs finalizers, checks required uploads and model verifiers, flushes telemetry, closes the task and sets its terminal status. A Unix main-thread alarm bounds finalization. If closure remains uncertain, a new invocation in that process is refused. For eligible trained pipelines, the local outcome records incomplete publication and the owner attempts a warning completion.

**Consequences.** The reference describes a separate 600-second allowance for each SDK step. In the successful path the implementation wraps the entire `_finalize` call in one alarm, so successive operations share the budget. Recovery and other cleanup blocks can have fresh alarms. [SIP-349](https://linear.app/sip-ds-team/issue/SIP-349)

[Owner and alarm scope](../src/clearml_yolo/adapters/clearml/session.py) · [Deadline mechanism](../src/clearml_yolo/adapters/clearml/deadline.py) · [Owner lifecycle tests](../tests/test_clearml_session.py) · [Trained pipeline failure cases](../tests/test_training_success_finalization.py) · [Technical contract](../DOCS.md#clearml-publication) · [User contract](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/d247a2e6f6d179a255ea6caaa5017ac477be8f4c)
