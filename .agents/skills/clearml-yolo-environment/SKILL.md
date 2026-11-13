---
name: clearml-yolo-environment
description: Use when preparing or cleaning a live CY environment, or diagnosing this machine's ClearML authentication or endpoints.
---

# Operate the owned environment

Paths start at the repository root. Before live work or authentication diagnosis,
read `.agents/skills/clearml-yolo-environment/references/machine-workflow.md`.
`specs/012-own-test-infra/contracts/test-environment.md` owns lifecycle rules;
`tests/integration/lifecycle.py` implements them. Planning-only tasks remain read-only.

1. Work from the intended checkout; its record owns the environment. Inspect an
   existing live record before setup and preserve another session's resources.
2. Run `source .agents/skills/clearml-yolo-environment/scripts/agent_env.sh`.
   It creates a fresh environment and
   exports its endpoints, `CY_RUN_TAG` and `CY_RUN_DIR`. A live recorded environment is
   refused; do not replace it without ownership. Exit 3 defers setup, exit 1 needs
   diagnosis/recovery. Never fall back to host credentials.
3. Use task-owned data/output locations and pass
   `clearml.project_name="$CY_RUN_TAG clearml-yolo"` and
   `clearml.tags=[$CY_RUN_TAG]` explicitly. Select CPU or an available GPU according to
   the requested claim and current host capacity. Use current generated YAML and the
   `docs/experiment-records.md` (Configuration resolution and replay).
4. Preserve evidence, then run
   `bash .agents/skills/clearml-yolo-environment/scripts/agent_cleanup.sh`.
   It removes published data with the environment and deletes the identified run
   directory only after environment deletion succeeds. `--dry-run` previews cleanup;
   `--tag` and `--run-dir` support recovery after losing the original shell. Confirm
   idle owned descendants before deleting local output.
5. Report environment identity, native/publication outcomes and deletion proof.
   Keep failed cleanup records for retry; never describe setup availability as a test
   pass. Forgotten environments have the lifetime defined by the environment contract.

For a 401, missing tasks or an endpoint mix-up, follow Machine workflow's diagnosis
and run `bash .agents/skills/clearml-yolo-environment/scripts/check_env.sh`.
The helper reports without printing credentials and always exits zero; its FAIL/WARN
lines need interpretation. It is an on-demand diagnostic, not an acceptance gate.

For historical audits only, read
`.agents/skills/clearml-yolo-environment/references/evidence-archive.md`.
