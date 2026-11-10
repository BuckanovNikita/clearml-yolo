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
| `L stop` | Stops recorded port-forwards (PID and start time must match), deletes the namespace (pods carry a 2 s termination grace period), waits for its absence within `CY_TEST_ENV_STOP_TIMEOUT` (default 180 s), then clears the record. A namespace that is already gone counts as stopped. | 0 stopped, 1 not proven gone (record kept), 130 |

The pytest session fixtures perform `up` (lazily, by the first test that needs a component) and
`stop` (after the last test) in-process; their port-forwards are child processes of the pytest
process. `INTEGRATION_KEEP_DATA=1` skips `stop` and prints the `stop` command and the 48-hour
limit.

## Identity and record

- Environment identifier = namespace name `clearml-yolo-it-<6 lowercase hex>`; also the run tag
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
| ResourceQuota | `clearml-yolo-it` | applied before any workload; values in data-model.md |
| LimitRange | `clearml-yolo-it` | container defaults for init containers and debug pods |
| Secret | `clearml-yolo-it-credentials` | apiserver pair, token secret, test-user pair; created from stdin |
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
- `agent_cleanup.sh [--tag <id>] [--run-dir <dir>] [--dry-run]`: `L stop` for that identifier
  (dry run: report what would be stopped), then the run-directory rule unchanged.
- `check_env.sh [--json]`: uv, kubectl and context reachability, ClearML `debug.ping` and
  authenticated `auth.login`, the host-ClearML (localhost:8008) warning, GPU. No Docker, no
  TLS hints. Always exit 0.
