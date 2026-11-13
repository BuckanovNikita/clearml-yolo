---
name: clearml-yolo-environment
description: Prepare and clean a task-owned live CY environment, or diagnose ClearML authentication/endpoints on this machine. Excludes generic development and cluster administration.
---

# Operate the owned environment

Before a live run or authentication diagnosis, read
[machine workflow](references/machine-workflow.md). The
[test-environment contract](../../../specs/012-own-test-infra/contracts/test-environment.md)
and [lifecycle](../../../tests/integration/lifecycle.py) own creation, adoption and
safe deletion. An invocation of this skill does not authorize live work during a
planning-only task.

1. Work from the intended checkout; its record owns the environment. Inspect an
   existing live record before setup and preserve another session's resources.
2. Source `scripts/agent_env.sh` beside this skill. It creates a fresh environment and
   exports its endpoints, `CY_RUN_TAG` and `CY_RUN_DIR`. A live recorded environment is
   refused; do not replace it without ownership. Exit 3 defers setup, exit 1 needs
   diagnosis/recovery. Never fall back to host credentials.
3. Use task-owned data/output locations and pass
   `clearml.project_name="$CY_RUN_TAG clearml-yolo"` and
   `clearml.tags=[$CY_RUN_TAG]` explicitly. Select CPU or an available GPU according to
   the requested claim and current host capacity. Use current generated YAML and the
   [configuration contract](../../../docs/experiment-records.md#configuration-resolution-and-replay).
4. Inspect outcomes and preserve evidence before running `scripts/agent_cleanup.sh`.
   It removes published data with the environment and deletes the identified run
   directory only after environment deletion succeeds. `--dry-run` previews cleanup;
   `--tag` and `--run-dir` support recovery after losing the original shell. Confirm
   idle owned descendants before deleting local output.
5. Report environment identity, native/publication outcomes and deletion proof.
   Keep failed cleanup records for retry; never describe setup availability as a test
   pass. Forgotten environments have the lifetime defined by the environment contract.

For a 401, missing tasks or a suspected endpoint mix-up, run `scripts/check_env.sh`
from the checkout and follow [diagnosis](references/machine-workflow.md#diagnose-clearml-401-and-missing-tasks).
The helper reports without printing credentials and always exits zero; its FAIL/WARN
lines need interpretation. It is an on-demand diagnostic, not an acceptance gate.

[Historical evidence](references/evidence-archive.md) is consulted only for an audit;
it does not supply current commands or current verification.
