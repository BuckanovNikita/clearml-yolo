# Implementation Plan: Own Kubernetes Test Infrastructure

**Branch**: `feat/own-test-infra` (feature `012-own-test-infra`) | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-own-test-infra/spec.md`

## Summary

Replace the shared-stand run-tag lifecycle with a project-owned **test environment**: one
`cy-it-<id>` namespace per session, created with a quota and limit range first,
holding MongoDB, Redis, Elasticsearch and the ClearML API and file servers on `emptyDir`,
reached through loopback `kubectl port-forward`, and deleted after the session. The manifests
are project files applied with `kubectl`; no Helm, no ingress, no certificate, no k8s-infra
helper. `tests/integration/lifecycle.py` keeps its commands and exit contract and is
rewritten around the environment; the environment skill's scripts delegate to it;
`check_env.sh` loses its Docker Compose check. The design and its numbers come from throwaway
measurements in `cy-it-*` namespaces ([research.md](research.md)).

## Technical Context

**Language/Version**: Python `>=3.12.13,<3.14` (standard library only in `lifecycle.py`, as
today); Bash for the environment skill scripts

**Primary Dependencies**: `kubectl` against context `docker-desktop`; container images
`allegroai/clearml:2.0.0-613`, `docker.elastic.co/elasticsearch/elasticsearch:7.17.28`,
`mongo:7.0.22`, `redis:7.2.11-alpine` (all cached on this node when measured); ClearML SDK and
FiftyOne as already locked. No new Python dependency.

**Storage**: `emptyDir` only; no PersistentVolumeClaim (quota `persistentvolumeclaims: "0"`).
Per-worktree record `tests/integration/.run-tag` (gitignored, as today).

**Testing**: The product's existing live suites (`tests/integration`) are the evidence for the
environment. No new tooling tests (owner rule); the tooling unit tests of the retired lifecycle
are removed.

**Target Platform**: Linux/WSL2 workstation with Docker Desktop Kubernetes, one GPU used only by
host processes.

**Project Type**: Python library and CLI; this feature touches test infrastructure, skills and
documentation only.

**Performance Goals**: Cold start (namespace creation to first authenticated ClearML call) about
24 s with cached images, measured; default start-up budget 300 s to allow image pulls.
Teardown about 11 s with a 2 s termination grace period (43 s with the default 30 s),
measured.

**Constraints**: R1-R9 of the k8s-infra plan; interim rules (port-forward only; `emptyDir`);
`check` stays read-only and bounded; credentials never printed or written to repository files;
`src/` unchanged; cy-queue unchanged.

**Scale/Scope**: One environment per session per worktree; five pods; quota requests 1 CPU and
2 GiB, limits 8 CPU and 6 GiB (measured use: requests 550m and 1184 MiB, limits 6.5 CPU and
3840 MiB).

## Constitution Check

| Principle | Status |
| --- | --- |
| I. Typed, explicit Python | `lifecycle.py` stays strict-mypy and Ruff clean; standard library only; specific exception types; no secrets in messages. |
| II. Module boundaries | `src/` untouched; `tests/integration` is not imported by product code (existing architecture test). |
| III. Configuration and run ownership | Live suites keep explicit tagged project names and tags; credentials never uploaded or printed; run directories stay isolated. |
| IV. Proportional, evidence-based verification | Live evidence is the product's own live suites run against the new environment, plus dated measurements; mocked tests claim nothing about uploads. Tooling unit tests are removed rather than rewritten (owner rule: tests exercise product code). Deferred/waived semantics are unchanged. |
| V. Collaboration | Russian `README.md` unaffected unless it mentions the stand (it does not); evidence dated in this feature directory. |

Gate result: PASS. Re-checked after design: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/012-own-test-infra/
├── spec.md  plan.md  research.md  data-model.md  quickstart.md  tasks.md
├── contracts/test-environment.md     # lifecycle commands, variables, exits, record
├── checklists/requirements.md
└── evidence/
    ├── 2026-11-10-measurements.md    # dated measurement results
    └── measure/                      # throwaway measurement manifest and driver (not the implementation)
```

### Source Code (repository root)

```text
tests/integration/environment/          # new: project manifests (namespace guard, quota, limit range,
                                        # mongo, redis, elastic, apiserver, fileserver) as YAML
tests/integration/lifecycle.py          # rewritten: environment create/wait/forward/teardown
tests/integration/conftest.py           # live_run → environment session fixture; new fiftyone_database fixture
tests/integration/fiftyone/*.py         # take the database URI from the fixture; keep FIFTYONE_DATABASE_DIR locks
tests/integration/test_*_gpu.py         # docstrings only ("shared stand" wording)
tests/test_integration_lifecycle.py     # deleted (tooling tests of retired behaviour)
tests/test_clearml_session.py           # untouched (asserts application ignores INFRA_RUN_TAG; product behaviour)
Taskfile.yml                            # infra-check/integration descriptions; FiftyOne step uses the fixture
scripts/session_status.sh               # reports the recorded environment instead of a run tag
.agents/skills/clearml-yolo-environment/{SKILL.md,scripts/*.sh,references/machine-workflow.md}
.agents/skills/running-integration-tests/SKILL.md
.agents/skills/running-end-to-end-tests/SKILL.md
docs/development.md  docs/ddp-testing.md  GLOSSARY.md  TECH_DETAILS.md
```

**Structure Decision**: Test infrastructure stays under `tests/integration` beside the lifecycle
that applies it; manifests are plain YAML so `kubectl apply --dry-run=server` can validate them;
no `src/` change.

## Design decisions

1. **Namespace per session, not per worktree.** R5 makes long-lived namespaces fragile, and a
   fresh ClearML per session replaces exact-tag cleanup with namespace deletion.
2. **Preflight stays read-only.** Start-up (≈24 s cached) moves into session setup with its own
   budget variable (`CY_TEST_ENV_START_TIMEOUT`, default 300 s). Exit 3 on budget expiry with
   the not-ready components listed; exit 1 on forbidden, invalid or quota-rejected objects.
3. **Minimal component set.** MongoDB, Redis, Elasticsearch, API server, file server. No web
   UI, async-delete or agent. Measured sufficient for task creation, artifact upload and
   download, and output-model upload, and for the real CPU stand smoke test.
4. **Start ordering by init containers.** The API server waits for Elasticsearch, the file
   server for the API server; each wait probe carries its own short timeout (`curl -m 2`),
   because a probe against a Service without endpoints otherwise hangs for 30 s. Measured:
   cold start 47 s → 24 s and no file-server restarts.
5. **Credentials.** The ClearML server's built-in `tests` user (role user) gets a generated key
   pair; the API server's system pair and token secret are generated too, and the file server
   authenticates with the system pair (a separate file-server pair was refused, measured). The lifecycle keeps
   them in memory, writes them into the namespace Secret through stdin, and reads them back
   from that Secret for `env` in a later process. Nothing is written to the record.
6. **FiftyOne database on the environment's MongoDB.** FiftyOne uses its own database name on
   the same server. A FiftyOne-only session applies only the MongoDB component. The suite
   passed unchanged against it (29 tests); `FIFTYONE_DATABASE_DIR` stays a temporary lock
   directory, as the publisher uses it for locks.
7. **Port-forward ownership.** Session fixtures own the port-forward children and stop them at
   teardown. Manual `up` starts detached port-forwards and records their process IDs with
   their start times; `stop` signals only processes whose recorded start time matches, so a
   reused PID is never signalled.
8. **Quota.** `pods 8`, `requests.cpu 1`, `requests.memory 2Gi`, `limits.cpu 8`,
   `limits.memory 6Gi`, `persistentvolumeclaims 0`, `requests.nvidia.com/gpu 0`. Limit range
   defaults (50m/64Mi request, 500m/256Mi limit) cover the init containers. Elasticsearch runs
   with a 256 MiB heap, request 512 MiB, limit 1 GiB (measured sufficient for the smoke test).
9. **Fast teardown.** Pods declare a 2 s termination grace period (no data to preserve);
   teardown waits for the namespace to disappear, bounded (`CY_TEST_ENV_STOP_TIMEOUT`,
   default 180 s). Measured 11 s. Every delete passes the deletion guard first (spec FR-018,
   contract "Deletion guard"): the name must be an environment identifier and the live
   namespace must carry the project label; `agent_cleanup.sh` passes its identifier as
   `stop --env <id>` and has no delete path of its own.
10. **Tooling tests.** `tests/test_integration_lifecycle.py` is deleted; the lifecycle is
    evidenced by live runs. Product tests that mention retired names (for example
    `tests/test_clearml_session.py` proving the application ignores `INFRA_RUN_TAG`) stay: they
    test product behaviour, not the retired tooling.

## Complexity Tracking

No violations.
