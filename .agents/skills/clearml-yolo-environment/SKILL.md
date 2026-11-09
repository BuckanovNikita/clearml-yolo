---
name: clearml-yolo-environment
description: Runs, diagnoses, and cleans up real clearml-yolo pipeline runs on this machine's shared Kubernetes ClearML stand. Sources the project identity and run tag (agent_env.sh), requires explicit tagged project overrides, explains ClearML LoginError 401, TLS trust, and host-versus-stand endpoint mistakes, and removes tagged run objects (agent_cleanup.sh). Use for a live clearml-yolo run, its credentials or endpoint failure, its tagged cleanup, or an explicit environment diagnosis; not for generic library development or Kubernetes stand administration (k8s-infra).
---

# ClearML YOLO environment

Use this skill only for a real `clearml-yolo` run, its ClearML credentials or
endpoint failure, its tagged cleanup, or an explicit environment diagnosis. The
`k8s-infra` skill owns the shared stand lifecycle and contract; never modify the
stand through this skill. It does not authorize a live run during planning-only
or documentation-only work.

## Live run checklist

1. Before the first live run or a 401, read
   [the machine workflow](references/machine-workflow.md) and the installed
   k8s-infra `references/run-contract.md` and `references/clearml-stand.md`.
2. Run the application from its checkout root (including a Git worktree) and keep
   the run output outside it. This project owns the skill in `.agents/skills/`;
   `.claude/skills` exposes the same source to Claude.
3. Use this block. The helpers live beside this file. The k8s-infra tag helper
   defaults the harness to `claude`; Codex, CI and humans export
   `INFRA_HARNESS=codex|ci|human` first.

   ```bash
   project_root="$(git rev-parse --show-toplevel)"
   skill_dir="$project_root/.agents/skills/clearml-yolo-environment"
   export CY_PROJECT_ROOT="$project_root"
   source "$skill_dir/scripts/agent_env.sh" smoke
   uv run cy run_dir=$CY_RUN_DIR/smoke \
     clearml.project_name="$CY_RUN_TAG clearml-yolo" \
     clearml.tags=[$CY_RUN_TAG] \
     ground_truth=ground_truth.csv \
     ultralytics.device=0 \
     ultralytics_predict.device=0
   # Read the outcome and copy anything to keep out of $CY_RUN_DIR first.
   "$skill_dir/scripts/agent_cleanup.sh"
   ```

4. If `source agent_env.sh` returns 3 (WAIT), nothing was minted: retry later.
   If it returns 1, read its message and stop. It refuses rather than falling
   back to host credentials.
5. Every new ClearML command passes
   `clearml.project_name="$CY_RUN_TAG clearml-yolo"` and
   `clearml.tags=[$CY_RUN_TAG]` explicitly, even after `agent_env.sh` has set
   the tag. The application no longer rewrites tags from the environment.
6. Keep `ultralytics.device=0` and `ultralytics_predict.device=0` only when the
   run needs the host GPU (see Run shape and GPU in the machine workflow).
7. Run `agent_cleanup.sh` after successful and failed live runs, once you have
   read the outcome, diagnosed any failure and copied the logs or results you need:
   it deletes the tagged ClearML tasks and the run directory. The helper prints the
   remaining tag-scoped listing before it removes a directory named for that tag;
   confirm that listing is empty before reporting the stand clean.

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
run-tag status, never the ClearML environment. For a 401, follow
[Diagnose ClearML 401](references/machine-workflow.md#diagnose-clearml-401-and-missing-tasks)
and stop if the k8s-infra helper reports an unavailable stand or Secret.

## Scripts

| Script | How to use | Side effects | Exit status |
| --- | --- | --- | --- |
| `scripts/agent_env.sh [<slug>]` (slug default `run`) | `source` it; running it directly is refused with exit 1 | runs `infra.py room`; evals `clearml.py --project clearml-yolo env`; unsets `FIFTYONE_DATABASE_URI`/`FIFTYONE_DATABASE_NAME`, then, when available, evals `mongodb.py --project clearml-yolo env` and on success defaults `FIFTYONE_DATABASE_DIR=$HOME/.cache/clearml-yolo/fiftyone` (a MongoDB failure only warns); mints `INFRA_RUN_TAG` unless already exported; exports `CY_RUN_TAG`, `CY_INFRA_SKILL_DIR`, `CY_RUN_DIR=${INFRA_SCRATCH_DIR:-/tmp/clearml-yolo-runs}/<tag>` (created); then runs `check_env.sh` | returns 0; 3 = WAIT, nothing minted; 1 = refusal |
| `scripts/agent_cleanup.sh [--tag <tag>] [--run-dir <dir>] [--dry-run]` | run in the shell that sourced `agent_env.sh`, or pass the tag explicitly | `clearml.py --project clearml-yolo cleanup --prefix <tag>` then `ls --prefix <tag>`; removes the run directory only when its basename equals the tag; `--dry-run` deletes nothing | 0 = success, including stand-only cleanup when `CY_RUN_DIR` is unset; 2 = no tag or unknown argument (before any stand call); 1 = run directory not named after the tag, or k8s-infra skill not found; any other nonzero = a k8s-infra helper failure passed through (`set -euo pipefail`; it can also be 1 or 2, and `--tag`/`--run-dir` without a value fails on an unbound `$2`), so treat stand cleanup as unproven and read the output |
| `scripts/check_env.sh [--json]` | run from the application checkout | read-only: checks uv, an authenticated ClearML `auth.login`, the host-stand warning, GPU and docker compose; never prints credential values; missing `uv` and ClearML configuration, reachability and credential problems are `FAIL` lines; GPU and docker problems and the ClearML host-stand endpoint are `WARN` lines; `--json` emits a single `{"report": "<text>"}` object wrapping the same text, with no structured fields to parse | always 0 (reports, never blocks) |

## References

- [references/machine-workflow.md](references/machine-workflow.md): before any live run, host-GPU use, or ClearML auth or TLS failure.
- [references/evidence-archive.md](references/evidence-archive.md): only when auditing past acceptance. Everything it indexes is dated history, never current instructions.
