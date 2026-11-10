# Contract: test environment lifecycle

Owner: `tests/integration/lifecycle.py`, invoked as
`uv run --locked python -m tests.integration.lifecycle <command>` (abbreviated `L`), by the
session fixtures in `tests/integration/conftest.py`, and by the environment skill scripts.

## Commands

| Command | Effect | Exit statuses |
| --- | --- | --- |
| `L check` | Read-only preflight bounded by `CY_INFRA_CHECK_TIMEOUT` (default 60 s): `kubectl` present, context `docker-desktop` present, API server `/readyz`, `kubectl auth can-i create namespaces`. Informational line naming pinned images the node does not list in `status.images`. Creates nothing. | 0 available, 3 unavailable, 1 error, 130 interrupted |
| `L up [--components clearml\|fiftyone\|all]` (default `all`) | Clears a stale record (namespace gone); refuses a live recorded environment; creates the environment; waits for readiness within `CY_TEST_ENV_START_TIMEOUT` (default 300 s); starts detached port-forwards; writes the record. On failure after creation, deletes the namespace before reporting. | 0, 3 (not ready in budget, lost connectivity), 1 (refusal, forbidden, invalid, quota rejection), 130 |
| `eval "$(L env)"` | Prints `export` lines for the recorded environment: `CLEARML_API_HOST`, `CLEARML_FILES_HOST`, `CLEARML_WEB_HOST`, `CLEARML_API_ACCESS_KEY`, `CLEARML_API_SECRET_KEY` (ClearML component), `FIFTYONE_DATABASE_URI` (database component), `INTEGRATION_RUN_TAG`. Credentials are read from the environment's Secret. Refuses a terminal. | 0, 1 |
| `L stop [--env <id>] [--dry-run]` | Target: `--env` when given, else the record's identifier. First applies the deletion guard (below). Then stops recorded port-forwards (PID and start time must match) when the target is the recorded identifier, deletes the namespace (pods carry a 2 s termination grace period), waits for its absence within `CY_TEST_ENV_STOP_TIMEOUT` (default 180 s), then clears the record if it names the target. A namespace that is already gone counts as stopped. `--dry-run` applies the guard and reports what would be stopped; it signals and deletes nothing. No record and no `--env`: refuses as today (exit 1, nothing to stop). | 0 stopped (including a retired-format record cleared), 1 refused by the guard (no delete call), no record and no `--env`, or not proven gone (record kept), 130 |

The pytest session fixtures perform `up` (lazily, by the first test that needs a component) and
`stop` (after the last test) in-process; their port-forwards are child processes of the pytest
process. `INTEGRATION_KEEP_DATA=1` skips `stop` and prints the `stop` command and the 48-hour
limit.

## Deletion guard (spec FR-018)

Applied by `stop` (manual, session fixtures, setup-failure cleanup) and therefore by
`agent_cleanup.sh`, in dry and real form, before any other teardown step:

1. A target from the command line (`--env`) must match `^cy-it-[0-9a-f]{6}$`;
   otherwise exit 1, naming the rejected value, record untouched, with no `kubectl delete` and
   no signal sent. A target from the record that does not match is not an environment: the
   record is cleared with a line saying a retired record was cleared, nothing is signalled or
   deleted, and `stop` exits 0 (`up` and session setup clear it the same way and continue).
   Example of a retired record: `clearml-yolo-claude-20261105-integration-a1b2` (harness word and date; never matches).
2. `kubectl get namespace <target>`: absent → already stopped (exit 0, record cleared if it
   names the target); present without the label `app.kubernetes.io/part-of=clearml-yolo-tests`
   → exit 1, no delete call, record kept; present with it → continue.
3. Only then port-forwards are stopped and `kubectl delete namespace <target>` runs.

## Identity and record

- Environment identifier = namespace name `cy-it-<6 lowercase hex>`; also the run tag
  used in ClearML project names (`"<id> <project>"`) and `clearml.tags`.
- Record `tests/integration/.run-tag` (gitignored): first line the identifier; following lines
  `forward <component> <local-port> <pid> <start-time>` for detached port-forwards. Never a
  credential.
- `INTEGRATION_RUN_TAG` exported by the shell must equal the recorded identifier when both are
  set; otherwise `up`/`env` refuse, as today.

## Kubernetes objects

Labels on the namespace and every object: `app.kubernetes.io/part-of=clearml-yolo-tests`,
`clearml-yolo/environment=<id>`.

| Object | Name | Notes |
| --- | --- | --- |
| ResourceQuota | `cy-it` | applied before any workload; values in data-model.md |
| LimitRange | `cy-it` | container defaults for init containers and debug pods |
| Secret | `cy-it-credentials` | apiserver pair, token secret, test-user pair; created from stdin |
| Deployment + Service | `mongo` | `mongo:7.0.22`, `emptyDir` |
| Deployment + Service | `redis` | ClearML component only |
| Deployment + Service | `elastic` | ClearML component only; single node, 256 MiB heap |
| Deployment + Service | `apiserver` | ClearML component only; init container waits for Elasticsearch |
| Deployment + Service | `fileserver` | ClearML component only; init container waits for the API server; system pair |

No Ingress, PersistentVolumeClaim, `storageClassName`, `hostPath`, NodePort, `nvidia.com/gpu`
request or cluster-scoped object other than the Namespace.

## Classification

| Observation | Outcome |
| --- | --- |
| kubectl missing, context missing, `can-i` denied, Forbidden on create | 1 error |
| API server not answering, timeouts, connection refused/reset | 3 unavailable |
| Component not ready within the start-up budget (Pending, ImagePullBackOff, CrashLoopBackOff) | 3 unavailable, listing each component's reason |
| Object rejected by quota or limit range, invalid manifest | 1 error, quoting the rejection |
| Recorded namespace absent | not an error: stale record cleared |

## Environment skill

- `source agent_env.sh [<slug>]`: `L up --components all`, then `eval "$(L env)"`, exports
  `CY_RUN_TAG=<id>` and `CY_RUN_DIR=${CY_SCRATCH_DIR:-/tmp/clearml-yolo-runs}/<id>`, runs
  `check_env.sh`. Returns 0, 3 (unavailable, nothing left behind), 1.
- `agent_cleanup.sh [--tag <id>] [--run-dir <dir>] [--dry-run]`: `L stop --env <id>
  [--dry-run]` with `<id>` from `--tag`, else `CY_RUN_TAG`; no identifier → exit 1 as today.
  A guard refusal (exit 1) ends the script before the run-directory step, in both forms; then
  the run-directory rule unchanged. Example: `agent_cleanup.sh --tag clearml --dry-run` and
  `agent_cleanup.sh --tag clearml` both exit 1 with no delete call.
- `check_env.sh [--json]`: uv, kubectl and context reachability, ClearML `debug.ping` and
  authenticated `auth.login`, the host-ClearML (localhost:8008) warning, GPU. No Docker, no
  TLS hints. Always exit 0.
