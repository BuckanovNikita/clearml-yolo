# ADR-0300 · Share one ClearML task across experiment stages

One pipeline may enter training, prediction, evaluation and publication in the same process. Each stage needs the identity and terminal status of the same experiment.

**Decision.** The outer invocation initializes a task with `reuse_last_task_id=False`. Nested stages borrow the active task. Distributed workers bypass task creation and upload. During Agent replay the owner checks that the SDK attached to the task whose configuration it read.

**Consequences.** The [pipeline](0001-pipeline.md) composes multiple stages under this rule. A direct invocation produces one task when initialization succeeds. A sweep starts a separate owner for each job. An unconfirmed close prevents a later owner in the same process. [Task finalization](0323-task-finalization.md) governs terminal status.

[Owner and worker guard](../src/clearml_yolo/adapters/clearml/session.py) · [Ownership and failure cases](../tests/test_clearml_session.py) · [ClearML configuration](../docs/configuration/clearml.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/589dc4a563e8a767a3cf9b675df66820b0a3c83b)
