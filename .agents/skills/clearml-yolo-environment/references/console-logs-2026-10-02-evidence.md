# ClearML console verification: 2026-10-02

Project checkout: /mnt/wsl/data/nkt/clearml-yolo. The approved repair enables
owner stdout/stderr capture without changing lifecycle or framework capture.

## Live verification

The environment helper authenticated the clearml-yolo project identity on the shared
Kubernetes ClearML stand. Capacity preflight returned GO. Fresh tag:
clearml-yolo-codex-20261002-console-logs-4v24.

- Completed task: 9020b3b8f22047218135fd696edf40d3.
- Failed task: ef2d54539d1c452cbce6a8844ef1c3f2.
- Project: 973d74145d0e49c592e790baa38fe84c.

Separate fresh processes used the actual invocation context and explicit tagged project
configuration. Each emitted unique stdout, stderr, default Loguru, installed Ultralytics
LOGGER and nested-stage markers. After flush, events.get_task_log returned every marker
exactly once while the task was active. After owner closure, backend retrieval again
returned each once; task status was completed or failed as expected. The failure was a
controlled RuntimeError. Terminal output contained each marker once as well.

This is console delivery verification, not native training or DDP acceptance. No training,
GPU computation, existing experiment repair or post-closure traceback forwarding was tested.

## Cleanup

agent_cleanup.sh deleted the tagged project and its two tasks. The final prefix listing
reported zero projects and zero tasks. The tagged local workspace was removed. No
pre-existing stand, user experiment, workload or credentials were modified. Temporary
verification scripts were removed after recording acceptance.
