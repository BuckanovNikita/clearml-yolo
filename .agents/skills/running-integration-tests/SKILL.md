---
name: running-integration-tests
description: Run clearml-yolo live tests (tests/integration) through Task with bounded preflight, explicit deferral and the project's own Kubernetes test environment (a cy-it-<id> namespace with its own ClearML and FiftyOne database, created and deleted by the run). Use for integration or acceptance runs, the CPU stand smoke test, GPU or FiftyOne live suites, blocked setup, assertion failures, credential errors, an active .run-tag, or leftover cy-it- namespaces.
---

# Run clearml-yolo live tests

Live tests use the project's own **test environment**: one namespace `cy-it-<6 hex>` on
the `docker-desktop` cluster, created by `tests/integration/lifecycle.py` with a
`ResourceQuota` and a `LimitRange` first, holding MongoDB (also the FiftyOne database)
and, when ClearML is needed, Redis, Elasticsearch and the ClearML API and file servers,
every volume `emptyDir`. Host access is by `kubectl port-forward` to loopback ports
kubectl chooses (plain HTTP in the tunnel). Credentials are generated per environment,
kept in its Secret and the process environment, and never printed. No shared stand,
k8s-infra helper or shared credential is used. The contract is
[test-environment.md](../../../specs/012-own-test-infra/contracts/test-environment.md);
`clearml-yolo-environment` covers agent runs and 401 diagnosis.

Live tests are ordinary pytest tests under `tests/integration`. They run only when the
pytest invocation names `tests/integration` or files in it (or selects the `integration`
marker); a plain `pytest`, development verification and affected-test runs never
contact the cluster. `tests/conftest.py` marks them `integration` and puts them in the
`live` xdist group, so one worker runs them serially while unit tests stay parallel;
keep `--dist loadgroup`. ClearML tests request the session fixture `live_run`, the
FiftyOne suites `fiftyone_database` (database component only), and the GPU suites join
through `stand_project` after validating their options. The first of them selects the
session's environment; at the end of the session an environment the session created is
deleted and proven absent, and the session fails when that is not proven.

The `integration` Task creates the environment before pytest, exports it for adoption,
and tears it down on exit. `infra-up`, `infra-env` and `infra-down` expose the same
lifecycle for manual use. Direct pytest invocations retain lazy fixture ownership.

Tests run under an isolated HOME that hides `~/clearml.conf`. Every live suite takes its
ClearML endpoint and credentials from the session's environment, never from the user's
SDK configuration. HOME-dependent locations (the kubeconfig kubectl reads, weights
cache, fonts) come from the real environment saved in `CY_REAL_ENV`.

```bash
uv run --locked task --exit-code infra-check         # read-only preflight
uv run --locked task --exit-code integration         # Task-owned setup, non-GPU tests, teardown
uv run --locked task --exit-code acceptance          # change acceptance
uv run --locked task --exit-code release-acceptance  # + GPU, FiftyOne, paired check
```

`L` abbreviates `uv run --locked python -m tests.integration.lifecycle` for
manual operations:

```bash
L check                                    # bounded preflight; creates nothing
L up [--components all|clearml|fiftyone]   # create an environment with detached port-forwards
eval "$(L env)"                            # export its endpoints, credentials and INTEGRATION_RUN_TAG
L stop [--env <id>] [--dry-run]            # delete it and prove it absent (also crash recovery)
kubectl --context docker-desktop get ns -l app.kubernetes.io/part-of=clearml-yolo-tests
```

After `eval "$(L env)"`, a pytest session in that shell adopts the environment and
leaves it for `L stop`.

## Preflight and deferral

`infra-check` (`L check`) checks that kubectl and the `docker-desktop` context exist,
that the API server answers `/readyz` and that this kubeconfig may create namespaces,
bounded by `CY_INFRA_CHECK_TIMEOUT` (60 seconds by default). It also names pinned images
the node does not list (informational: the node's list is capped). Start-up is bounded by
`CY_TEST_ENV_START_TIMEOUT` (300 s by default, room for pulling images), teardown by
`CY_TEST_ENV_STOP_TIMEOUT` (180 s).

| Result | Exit | Action |
| --- | --- | --- |
| AVAILABLE | 0 | Live verification may start. |
| UNAVAILABLE | 3 | Cluster not answering, timeout, or components not ready within the start-up budget (listed with their reasons): defer live verification. |
| ERROR | 1 | kubectl, context or permission missing, a quota or limit-range rejection, an invalid manifest, or a refusal: diagnose. |
| interrupted | 130 | Not a result; rerun. |

An availability result is not a test result. Losing availability during setup is blocked
setup; assertion failures after setup are test failures. A setup failure after the
session created its namespace deletes that namespace before the failure is reported.

When unavailable, report the reason and the deferred checks, continue independent work
and retry at a meaningful milestone or after restored availability, without polling.
Before GPU work, check pcboard `pc_status` where available; a GPU busy with the user's
workload defers the GPU suites the same way. Multi-GPU DDP is waived unless
`CY_DDP_ARGS` is set and never blocks.
Deferred verification blocks acceptance, integration and release; when only blocked
checks remain, stop and ask for the user's decision.

For a focused selector, run `infra-check` first, then pytest on the selected
`tests/integration` path with `--dist loadgroup`; an ad hoc run is not acceptance.

## Rules

- **One environment per worktree.** `tests/integration/.run-tag` records it: the
  identifier, then `forward` lines for the port-forwards of a manual `L up`. Selection
  (spec FR-014): with no live recorded environment, a stale record (namespace gone) or a
  retired-format record (any first line that is not `cy-it-<6 hex>`) is cleared without
  a delete call and a new environment is created; with a live one, only a pytest session
  whose shell exports `INTEGRATION_RUN_TAG` equal to it adopts it, and `L up`, the
  environment skill and every other session refuse with exit 1 naming `L stop`.
- **Whoever creates an environment deletes it.** A session deletes the one it created
  (`INTEGRATION_KEEP_DATA=1` keeps it and prints `L stop` and the 48-hour limit); an
  adopted environment is never deleted by the session.
- **Deletion guard.** `L stop`, the session fixtures and setup-failure cleanup delete a
  namespace only when its name matches `^cy-it-[0-9a-f]{6}$` and the live namespace
  carries `app.kubernetes.io/part-of=clearml-yolo-tests`. A recorded namespace without
  that label is refused and the record kept; inspect it by hand. Never delete namespaces
  by selector or by any other name.
- **Lifetime.** The platform sweeper deletes every unprotected namespace 48 hours after
  its creation or after a Docker Desktop or PC restart; runs must finish inside that
  window. A vanished namespace only makes the record stale; `L stop` then succeeds.
- **Explicit names.** Every created ClearML project and task carries the environment
  identifier in its name (`"<id> clearml-yolo"`) and tags; deleting the namespace
  removes them all.
- **One CPU smoke run per adopted environment.** The smoke test reads the task named
  `cpu-smoke-pipeline` in the environment's project; an adopted environment keeps earlier
  runs' tasks, a later run's task gets a suffixed name, and the assertion then reads the
  earlier task. Start a new environment for each smoke run whose result counts.
- **Concurrency.** Each worktree creates its own namespace; nothing is shared. Node
  pressure shows as components not ready within the budget (exit 3).
- GPU suites take their `--run-*` options from the environment: the Severstal
  single-GPU suite is required and reads `CY_SEVERSTAL_ARGS`; multi-GPU DDP runs only
  when `CY_DDP_ARGS` is set and is otherwise reported as waived. The options are split
  on spaces, so use space-free project names (for example
  `--ddp-clearml-project=clearml-yolo-ddp`); the published name gets the identifier
  prefix. The GPU is used by the host processes; the environment's pods request none.
  `release-acceptance` runs them with `CY_TASK_VERIFICATION=1`, so an unavailable
  cluster ends the suite with exit 3, deferred. It runs the FiftyOne tests with
  `CY_TEST_FIFTYONE=1` against the environment's database, with a temporary
  `FIFTYONE_DATABASE_DIR` for the publisher's locks that it removes afterwards. Supply
  the GPU options from [the DDP procedure](../../../docs/ddp-testing.md) and
  `pytest --help` ("native Severstal acceptance").
- The real-run gate (CPU and a single GPU) belongs to `running-end-to-end-tests`; these
  tests do not replace it.

## Completion evidence

Report the environment identifier, the selector, the pytest result and the deletion
proof (`namespace <id> deleted and proven absent`, and no `cy-it-` namespace of the run
in the listing above). The lifecycle's `==>` lines show only with `pytest -s`; under the
default capture of the Task stages, take the identifier and the absence from `kubectl`
listings before and after. Distinguish passed tests, failures, deferred, waived and error
outcomes and incomplete deletion. When deletion is not proven, the record stays: report
it with the `L stop --env <id>` retry. A successful preflight without executed live
tests is not acceptance.
