# Research: Own Kubernetes Test Infrastructure

Dated measurements: [evidence/2026-11-10-measurements.md](evidence/2026-11-10-measurements.md).
Governing plan: k8s-infra `docs/plans/2026-11-09-managed-infrastructure-reset.md` (settled
decisions, "Rules for every project", "clearml-yolo — first").

## R-1 Deployment mechanism

- **Decision**: Plain YAML manifests under `tests/integration/environment/`, applied with
  `kubectl apply`, credentials Secret created from stdin.
- **Rationale**: Five small Deployments; no templating beyond namespace and component
  selection; no Helm dependency or release state that `kubectl delete namespace` would orphan;
  server-side dry-run can validate them.
- **Alternatives**: The upstream `clearml` Helm chart (renders web UI, async-delete, agent
  services and 50 Gi claims by default; needs many overrides and a Helm binary); Docker Compose
  (forbidden by the platform plan).

## R-2 Minimal ClearML component set

- **Decision**: MongoDB, Redis, Elasticsearch, API server, file server.
- **Rationale**: Measured sufficient for task creation, artifact upload and download, output
  model upload, and the real CPU stand smoke test (1 passed). The web UI serves people, not the
  SDK; async-delete cleans deleted objects, which namespace deletion makes moot; the agent runs
  queued tasks, which this project's tests never do.
- **Alternatives**: The full chart set (more pods, more memory, slower start).

## R-3 Start ordering

- **Decision**: Init containers using the ClearML image's `curl` with `-m 2`: the API server
  waits for Elasticsearch health yellow, the file server waits for `debug.ping`.
- **Rationale**: Without ordering the API server's fixed 30 s Elasticsearch retry and the file
  server's crash loop make cold start ~47 s; with ordering ~24 s (m4, m6, m7). Without `-m`, a
  probe against a Service with no endpoints hung 30 s (m5).
- **Alternatives**: Readiness gates in the lifecycle (more code, same effect); accepting
  restarts (slower, noisy).

## R-4 Credentials

- **Decision**: Generate the API server system pair, token secret and the built-in `tests`
  user pair per environment; the file server uses the system pair; the SDK uses the `tests` pair.
- **Rationale**: Measured: a separate file-server pair is refused by the API server (m1); the
  `tests` pair authenticates `auth.login` and SDK writes (m2-m7). No fixed-user configuration
  file is needed.
- **Alternatives**: Fixed users with passwords plus `auth.create_credentials` (extra calls, a
  configuration Secret).

## R-5 FiftyOne database

- **Decision**: FiftyOne's own database on the environment's MongoDB; a FiftyOne-only session
  starts only MongoDB. Keep a temporary `FIFTYONE_DATABASE_DIR` for the publisher's locks.
- **Rationale**: The suite passed unchanged with `FIFTYONE_DATABASE_URI` pointed at it, both
  sharing ClearML's server (m2) and alone (m8, ready in ~3 s). The locked FiftyOne 1.22.0
  requires MongoDB ≥ 6.0 (`fiftyone.constants.MONGODB_MIN_VERSION`); 7.0.22 satisfies it. The
  product's publisher keeps its lock directory under `fo.config.database_dir`.
- **Alternatives**: Today's host-local `mongod` spawned by FiftyOne (not in a namespace, no
  quota, violates R1/R3); a second MongoDB server (more memory, no isolation benefit inside a
  disposable namespace).

## R-6 Host access

- **Decision**: `kubectl port-forward svc/<component> :<port>` to loopback, kubectl-chosen
  ports, plain HTTP inside the tunnel.
- **Rationale**: Rule R9, permanent since the k8s-infra plan settled decision 10 (the
  wildcard name-lookup probe of 2026-11-10 failed on this machine); no host names, certificate
  or hosts entries. Random ports never collide with the user's host ClearML on 8008 or between
  worktrees.
- **Alternatives**: Ingress host names (names a project invents do not resolve on the host;
  only the platform's dedicated services get host names); NodePorts (fixed ports,
  collisions).

## R-7 Quota and limit range

- **Decision**: Quota pods 8, requests 1 CPU / 2 GiB, limits 8 CPU / 6 GiB, PVC 0, GPU 0;
  limit range defaults 50m/64Mi request, 500m/256Mi limit.
- **Rationale**: Measured use requests 550m / 1184 MiB, limits 6.5 CPU / 3840 MiB; headroom
  for a debug pod and init containers; PVC 0 and GPU 0 enforce R4 and R7 at admission.
- **Not yet shown**: the measurement runs applied a looser quota (requests 2 CPU / 4Gi, limits
  8 CPU / 8Gi); the designed values were derived from the measured use and were not
  themselves applied. Their first application is the live acceptance run (tasks T027).
- **Alternatives**: No limits quota (an unlimited pod could starve the node); tighter limits
  (Elasticsearch peaked at 634 MiB with a 1 GiB limit).

## R-8 Preflight versus start-up

- **Decision**: `check` stays read-only (cluster, context, permission, informational image
  cache line); start-up is part of session setup with `CY_TEST_ENV_START_TIMEOUT` (300 s).
- **Rationale**: The preflight contract (bounded, creates nothing, 0/3/1/130) is relied on by
  acceptance and the skills; cold start (~24 s cached, minutes with ~3.7 GB of pulls) does not
  fit a 60 s read-only check.

## R-9 Teardown

- **Decision**: 2 s termination grace in pod specs; `kubectl delete namespace` and a bounded
  wait for absence; already-absent counts as stopped.
- **Rationale**: Measured 11 s versus 43 s; nothing in the environment needs a clean shutdown.

## R-10 Tooling tests

- **Decision**: Delete `tests/test_integration_lifecycle.py`; add no unit tests of the new
  lifecycle. Evidence for the lifecycle is the product's live suites run through it.
- **Rationale**: Owner rule: tests exercise product code, never project tooling. The existing
  tests cover helper-call behaviour that is being removed.
- **Consequence**: Lifecycle regressions surface only in live runs; the tasks therefore make
  the live acceptance runs (integration, FiftyOne step, vanished-namespace recovery) explicit
  acceptance items.

## R-11 Paired check

- **Decision**: No cy-queue change. Run the repository's documented stage on the tip:
  `CY_QUEUE_DIR=/mnt/wsl/data/nkt/cy-queue uv run --locked task --exit-code paired-check`
  (a temporary environment with both checkouts installed editable, then cy-queue's suite).
- **Rationale**: Running cy-queue's `pytest` with `--project <worktree>` uses the worktree's
  development environment, which does not have cy-queue installed, and fails at collection by
  construction.
- **Observed 2026-11-10**: the stage fails at collection because cy-queue `d3627a0` imports
  `clearml_yolo.adapters.storage.batch_sizes`, which exists only on the unmerged branch
  `012-editable-batch-sizes`, not on master
  ([evidence/2026-11-10-paired-check.md](evidence/2026-11-10-paired-check.md)). This is
  outside this feature; SC-007 depends on it (spec "Dependencies").
- **Observed later on 2026-11-10**, after `012-editable-batch-sizes` was merged into this
  branch on the owner's direction: the stage passed (cy-queue's suite 527 passed, 7
  deselected; evidence file above).

## R-12 Environment selection and ownership

- **Decision**: One selection rule for `up`, `agent_env.sh` and session setup (spec FR-014,
  contract "Environment selection"): no live recorded environment → clear any stale or
  retired record and create; live recorded environment → a pytest session adopts it only when
  `INTEGRATION_RUN_TAG` equals it, every other caller is refused with exit 1. The creator
  deletes; an adopting session never deletes. `agent_env.sh` never reuses.
- **Rationale**: Rule R5 requires tooling to recreate a missing namespace, so a stale record or
  stale export must lead to creation, not refusal. A single owner per deletion keeps automatic
  teardown from deleting a namespace its process did not create. Dropping reuse from
  `agent_env.sh` removes a second adoption path with its own failure cases; a re-sourced shell
  is refused and names `agent_cleanup.sh`.
- **Alternatives**: Refusing an exported identifier with no live environment (blocks recovery
  after a sweep, contradicting R5); letting `agent_env.sh` reuse the exported environment
  (needs the forward-liveness and component checks of adoption in shell code too); letting an
  adopting session delete at its end (deletes an environment another shell still uses).
