---
name: clearml-yolo-environment
description: Runs, diagnoses, and cleans up real clearml-yolo pipeline runs on this machine against the project's own test environment (a cy-it-<id> Kubernetes namespace with its own ClearML server and FiftyOne database, reached through kubectl port-forward). Creates the environment and exports its endpoints (agent_env.sh), requires explicit tagged project overrides, explains ClearML LoginError 401 and host-versus-environment endpoint mistakes, and deletes the environment (agent_cleanup.sh). Use for a live clearml-yolo run, its credentials or endpoint failure, its cleanup, or an explicit environment diagnosis; not for generic library development or platform administration of the cluster.
---

# ClearML YOLO environment

Use this skill only for a real `clearml-yolo` run, its ClearML credentials or
endpoint failure, its cleanup, or an explicit environment diagnosis. A run uses the
project's own **test environment**: one `cy-it-<6 hex>` namespace on the
`docker-desktop` cluster with a quota, holding its own ClearML server (API and file
server with MongoDB, Redis and Elasticsearch) and its own FiftyOne database, every
volume `emptyDir`, reached through loopback `kubectl port-forward`. The environment is
created and deleted by `tests/integration/lifecycle.py` of the checkout that contains
this skill; no shared stand, k8s-infra helper or shared credential is involved. It
does not authorize a live run during planning-only or documentation-only work.

## Live run checklist

1. Before the first live run or a 401, read
   [the machine workflow](references/machine-workflow.md).
2. Run the application from its checkout root (including a Git worktree) and keep
   the run output outside it. This project owns the skill in `.agents/skills/`;
   `.claude/skills` exposes the same source to Claude. The environment belongs to the
   checkout that contains the skill (its `tests/integration/.run-tag` records it).
3. Use this block. The helpers live beside this file.

   ```bash
   project_root="$(git rev-parse --show-toplevel)"
   skill_dir="$project_root/.agents/skills/clearml-yolo-environment"
   export CY_PROJECT_ROOT="$project_root"
   source "$skill_dir/scripts/agent_env.sh"
   uv run cy run_dir=$CY_RUN_DIR/smoke \
     clearml.project_name="$CY_RUN_TAG clearml-yolo" \
     clearml.tags=[$CY_RUN_TAG] \
     ground_truth=ground_truth.csv \
     ultralytics.device=0 \
     ultralytics_predict.device=0
   # Read the outcome and copy anything to keep out of $CY_RUN_DIR first.
   "$skill_dir/scripts/agent_cleanup.sh"
   ```

4. If `source agent_env.sh` returns 3, the cluster is unavailable or the environment
   was not ready in time; nothing was left behind: retry later. If it returns 1, read
   its message and stop: it refuses rather than falling back to host credentials, and
   it refuses while this checkout already records a live environment (remove that one
   with `agent_cleanup.sh` first; `agent_env.sh` never reuses an environment).
5. Every new ClearML command passes
   `clearml.project_name="$CY_RUN_TAG clearml-yolo"` and
   `clearml.tags=[$CY_RUN_TAG]` explicitly. The application does not derive tags from
   the environment.
6. Keep `ultralytics.device=0` and `ultralytics_predict.device=0` only when the
   run needs the host GPU (see Run shape and GPU in the machine workflow). The
   environment's pods request no GPU.
7. Run `agent_cleanup.sh` after successful and failed live runs, once you have
   read the outcome, diagnosed any failure and copied the logs or results you need:
   it deletes the environment's namespace, with everything published into it, proves
   the namespace absent, and removes the run directory. Everything in the environment
   is lost; the platform sweeper deletes a forgotten environment 48 hours after its
   creation or after a restart.

## Configuration contract

The pipeline and standalone training derive their data from `ground_truth`;
`cy-train` requires that CSV and preparation owns `ultralytics.data`. Use the
current top-level groups and ordinary known-key overrides. Raw `cfg`, nested
`train.ultralytics` / `predict.ultralytics` and their `+` overrides are removed.
Consult the checkout's `docs/current-contracts.md` before adapting archived
examples.

## Diagnose

For an explicit diagnosis, run `"$skill_dir/scripts/check_env.sh"` from the
application checkout. It reports the endpoint and credential source without
printing credential values. Environment diagnostics are on demand: the repository's
session-start hook (`scripts/session_status.sh`) reports only Git, release-lock and
recorded-environment status, never the ClearML endpoint. For a 401, follow
[Diagnose ClearML 401](references/machine-workflow.md#diagnose-clearml-401-and-missing-tasks).

## Scripts

| Script | How to use | Side effects | Exit status |
| --- | --- | --- | --- |
| `scripts/agent_env.sh` | `source` it; running it directly is refused with exit 1; an argument is ignored with a one-line notice | unsets `FIFTYONE_DATABASE_URI`/`FIFTYONE_DATABASE_NAME`; runs `lifecycle up --components all` in the checkout containing the skill (creates `cy-it-<id>` with quota, limit range, ClearML and the FiftyOne database, starts detached port-forwards, writes `tests/integration/.run-tag`); evals `lifecycle env` (`CLEARML_*`, `FIFTYONE_DATABASE_URI`, `INTEGRATION_RUN_TAG`); exports `CY_RUN_TAG`, `CY_RUN_DIR=${CY_SCRATCH_DIR:-/tmp/clearml-yolo-runs}/<id>` (created) and `FIFTYONE_DATABASE_DIR=${FIFTYONE_DATABASE_DIR:-$HOME/.cache/clearml-yolo/fiftyone}`; then runs `check_env.sh` | returns 0; 3 = cluster unavailable or not ready in time, nothing left behind; 1 = refusal (a live recorded environment, a foreign namespace) or error |
| `scripts/agent_cleanup.sh [--tag <cy-it-id>] [--run-dir <dir>] [--dry-run]` | run in the shell that sourced `agent_env.sh`, or pass the identifier explicitly | `lifecycle stop --env <id>` (stops the recorded port-forwards, deletes the namespace, proves it absent); then removes the run directory only when its basename equals the identifier; `--dry-run` reports and deletes nothing | 0 = success, including environment-only cleanup when `CY_RUN_DIR` is unset and an environment that was already gone; 2 = no identifier or unknown argument (before any cluster call); 1 = the deletion guard refused (a name that is not `cy-it-<6 hex>`, or a namespace without the project label: nothing deleted, the run directory left alone), the namespace was not proven absent (the record stays for a retry), or the run directory is not named after the identifier |
| `scripts/check_env.sh [--json]` | run from the application checkout | read-only: checks uv, an authenticated ClearML `auth.login`, the host-ClearML warning, kubectl reaching the `docker-desktop` cluster, and the GPU; never prints credential values; missing `uv`, kubectl and ClearML configuration, reachability and credential problems are `FAIL` lines; GPU problems and the host ClearML endpoint are `WARN` lines; `--json` emits a single `{"report": "<text>"}` object wrapping the same text, with no structured fields to parse | always 0 (reports, never blocks) |

## References

- [references/machine-workflow.md](references/machine-workflow.md): before any live run, host-GPU use, or a ClearML authentication failure.
- [references/evidence-archive.md](references/evidence-archive.md): only when auditing past acceptance. Everything it indexes is dated history, never current instructions.
