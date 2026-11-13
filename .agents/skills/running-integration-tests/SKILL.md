---
name: running-integration-tests
description: Run live integration or acceptance, select GPU/FiftyOne checks, diagnose blocked setup, or recover a recorded test environment and its owned resources.
---

# Run live verification

[Taskfile.ops.yml](../../../Taskfile.ops.yml) owns invocation and lifecycle ordering;
[acceptance tiers](../../../docs/development.md#acceptance-tiers) select scope.
The [test-environment contract](../../../specs/012-own-test-infra/contracts/test-environment.md)
is authoritative for creation, adoption, deadlines and deletion;
[tests/integration/lifecycle.py](../../../tests/integration/lifecycle.py) implements it.
Use [clearml-yolo-environment](../clearml-yolo-environment/SKILL.md) for manual
application runs and authentication diagnosis.

1. Inspect the recorded environment and ownership before any live action. Run bounded
   `infra-check` before expensive checks. For GPU checks, inspect current host capacity
   through pcboard where available; preserve unrelated workloads.
2. Select `integration`, `acceptance` or `release-acceptance` through Task. Explicit
   commands retain their full scope. For focused diagnosis, preflight first and select
   concrete `tests/integration` files with the configured loadgroup distribution.
   A focused run is evidence only for those checks.
3. Supply required single-GPU Severstal options from pytest help and the
   [augmentation contract](../../../docs/augmentation.md#severstal-execution-checks).
   The Task owns FiftyOne database selection and temporary lock-directory cleanup.
4. Record the environment identifier, selector, result and proof of deletion. Preserve
   useful logs before deleting the environment, which removes published data.

## Ownership and recovery

- A run creates its own environment or explicitly adopts the environment exported by
  its owner. A live record without matching adoption is a refusal, not permission to
  replace another run. Inspect the lifecycle's recovery command; never delete by a
  broad namespace selector.
- Whoever creates the environment deletes it. Adopted environments remain the owner's
  responsibility. `INTEGRATION_KEEP_DATA=1` is a deliberate retention decision subject
  to the contract's lifetime; record the cleanup command and deadline.
- Use Task `infra-up`, `infra-env` and `infra-down` for manual lifecycle operations.
  Exported credentials stay in the process environment and must not be printed/logged.
  Deletion must prove absence; a failed guard or incomplete deletion keeps the record
  for recovery. Preserve unrelated services, namespaces and host credentials.
- Use a fresh environment for each CPU smoke result: repeated adopted runs can leave
  an earlier task with the same base name, making a name-based readback stale.
- Test sessions hide user SDK configuration; live credentials come from the owned
  environment. Never fall back to a shared ClearML service after setup failure.

## Interpret outcomes

`infra-check` reports AVAILABLE/0, UNAVAILABLE/3 or ERROR/1. Availability is not a test
result. Unavailability during preflight/setup and a busy GPU defer supported checks;
assertions after setup remain failures. Errors need diagnosis rather than weakened
permissions or guards. An interruption is not success.

Deferred checks block acceptance, integration and release. Continue independent work
and retry after availability changes, without polling. If only blocked checks remain,
report the unresolved decision. Report cleanup failures with the precise owned
identifier and recovery command. Native CPU/single-GPU direct and queued execution,
publication/readback and standalone charts additionally follow
[running-end-to-end-tests](../running-end-to-end-tests/SKILL.md).
