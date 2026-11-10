# Feature Specification: Own Kubernetes Test Infrastructure

**Feature Branch**: `feat/own-test-infra` (feature directory `012-own-test-infra`). The feature
number 012 is shared with `specs/012-editable-batch-sizes` on branch `012-editable-batch-sizes`;
the two are separate features, told apart by their directory names.

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "One-time migration of clearml-yolo to its own Kubernetes test
infrastructure, governed by the owner-approved k8s-infra plan
`docs/plans/2026-11-09-managed-infrastructure-reset.md` (rules for every project, all nine,
and the clearml-yolo block), with the interim rules: host access by `kubectl port-forward`
only; no `storageClassName`, prefer `emptyDir`, and where a claim is unavoidable name
`hostpath` explicitly. Its own ClearML and its own FiftyOne database for tests; remove the
`docker compose version` prerequisite in the environment skill's `check_env.sh`; rewrite
`tests/integration/lifecycle.py` and the environment skill scripts off `infra.py` and
`clearml.py`. Real GPU work execution and cy-queue scheduling are out of scope and do not
change; cy-queue gets no change, only its paired check against the migrated tip. The
project's own ClearML requests no GPU."

Since that input the k8s-infra plan settled host access by `kubectl port-forward` as the
permanent rule (plan decision 10 and rule 9: no wildcard name lookup on this machine); it is no
longer interim. The storage wording stays interim only in naming `hostpath` while two default
storage classes exist (plan phase P5).

Terms follow the "Verification and release" section of [GLOSSARY.md](../../GLOSSARY.md); this
feature adds **test environment** (below). It changes contributor, agent and verification
infrastructure only; product behavior in the [baseline specification](../000-baseline/spec.md)
and every `src/` contract are unchanged.

## Context

The machine's shared stands (ClearML, MongoDB and the run-tag, capacity and credential helpers
`infra.py`, `clearml.py` and `mongodb.py` of the k8s-infra skill) are being wiped without
backup. After the wipe the platform gives only: a Kubernetes cluster (context
`docker-desktop`), the default `hostpath` storage class, ingress with a wildcard certificate,
one exclusive GPU slot, and a sweeper that deletes every unprotected namespace 48 hours after
its creation or when it was created before the last Docker Desktop or PC restart. Each project
deploys and removes its own test infrastructure. Until this feature lands, every clearml-yolo
live check (change acceptance, the CPU stand smoke run, release acceptance, agent live runs)
depends on helpers that will disappear.

The governing rules (numbered as in the k8s-infra plan, "Rules for every project"):

| Rule | Requirement on this project |
| --- | --- |
| R1 | Test infrastructure is deployed into the project's own namespaces with its own manifests and its own teardown. |
| R2 | Namespace names never reuse a protected name (`clearml`, `mongodb`, `ingress-nginx`, `infra-janitor`, `default`, `kube-*`); they use a distinct prefix such as `<project>-it-<id>`. |
| R3 | Every namespace the project creates carries a `ResourceQuota` chosen by the project, and a `LimitRange`. |
| R4 | No `storageClassName` (interim: prefer `emptyDir`; an unavoidable claim names `hostpath`); no `local-path`, no `/mnt/wsl/data/k8s-volumes`. |
| R5 | A namespace can vanish at 48 hours or after a restart; runs finish inside that window and tooling recreates a missing namespace. |
| R6 | No use of the dedicated platform ClearML or FiftyOne MongoDB; the project deploys its own ClearML and its own FiftyOne database. |
| R7 | `nvidia.com/gpu: 1` is requested only where a test needs it; the project's ClearML requests none. |
| R8 | No `INFRA_RUN_TAG`, `INFRA_PROJECT`, `K8S_INFRA_SKILL_DIR`, `INFRA_REGISTRY`, and no calls to `infra.py`, `clearml.py`, `mongodb.py`, `cvat.py`, `lakefs.py`, `postgres.py` in code, skills or shell profiles. |
| R9 | Host access by `kubectl port-forward` only (permanent: plan decision 10); names the project invents do not resolve on the host. |

## Clarifications

### Session 2026-11-10

Answered by the implementing agent from the approved k8s-infra plan, as instructed; no user
question was asked. Each answer is the smallest decision consistent with the plan.

- Q: One namespace per test session, per component, or a long-lived per-worktree namespace? →
  A: One namespace per **test environment**: created by the first live test of a session (or
  by `up`), removed after the session (or by `stop`). A long-lived namespace would only die
  to the sweeper (R5) and would carry data across runs.
- Q: Does the read-only preflight start the environment? → A: No. The preflight stays bounded
  and creates nothing; environment start-up belongs to session setup with its own bounded
  start-up budget. Cold start was measured at about 24 s with cached images (see
  [research.md](research.md)).
- Q: Is the FiftyOne database a separate server or a separate database? → A: A separate
  database (FiftyOne's own database name) on the environment's MongoDB server, which also
  holds ClearML's databases. A FiftyOne-only session starts only that server. The FiftyOne
  suite was measured passing unchanged against it.
- Q: How is host access provided? → A: `kubectl port-forward` to loopback on ports chosen by
  kubectl, never fixed host ports and never the user's host ClearML port 8008, over plain
  HTTP inside the tunnel. No ingress, certificate or hosts entry is used (R9).
- Q: Is the ClearML web UI part of the test environment? → A: No. The measured minimal set
  for SDK publication is MongoDB, Redis, Elasticsearch, the API server and the file server.
  The web UI, async-delete service and agent are excluded; a person who wants to look at a
  kept environment uses the API or a later, separate feature.
- Q: What replaces exact-tag cleanup? → A: Deleting the environment's namespace removes every
  object it held; cleanup is proven by the namespace no longer existing. ClearML project
  names and tags still carry the run identifier, because explicit names and tags are an
  application contract and the GPU suites rely on the prefix; it no longer drives cleanup.
- Q: What happens to the unit tests of `lifecycle.py`? → A: They test project tooling, not
  product code, so they are removed with the behaviour they covered and not replaced by new
  tooling tests. The lifecycle is evidenced by live runs of the product's live suites
  against environments it created (owner rule: tests exercise product code only).
- Q: Does the environment need a GPU, an Ingress or persistent storage? → A: No to all three:
  the GPU is used by host processes of the GPU suites, never by the environment's pods; data
  lives in `emptyDir` and dies with the namespace.
- Q: Which namespace prefix? → A: `cy-it-` (the project's short name CY), the prefix the
  implementing session is authorised to create and delete on the shared cluster; it is
  distinct from every protected name (R2). Earlier drafts named `clearml-yolo-it-`.
- Q: May a pytest session use an environment that a manual `up` created? → A: Only when the
  shell exports `INTEGRATION_RUN_TAG` equal to the identifier of the live recorded environment,
  mirroring the retired rule that only an exported tag equal to the record adopted a run
  (FR-014).
- Q: (revised 2026-11-10 after verification found the adoption, reuse and recovery rules in
  conflict) What happens when the exported identifier names no live recorded environment, does
  `agent_env.sh` reuse an environment, and who removes an adopted one? → A: One selection rule
  (FR-014): with no live recorded environment, `up`, `agent_env.sh` and session setup clear any
  stale or retired record and create a new environment, ignoring an exported identifier (R5:
  tooling recreates a missing namespace); with a live recorded environment, only a pytest
  session whose exported identifier equals it adopts it, and everything else is refused.
  `agent_env.sh` never reuses: it always performs `up`. Whoever creates an environment removes
  it: a session removes only the environment it created; an adopted environment is removed
  only by `stop` or `agent_cleanup.sh`, so automatic teardown never deletes a namespace its
  process did not create.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Change acceptance against an environment the run deploys itself (Priority: P1)

A contributor runs change acceptance (or the `integration` stage) on a clean tip. The live
part creates a namespace of its own with a quota, starts a ClearML server inside it, runs the
CPU stand smoke test and the other non-GPU live tests against it through a port-forward, and
deletes the namespace afterwards. Nothing of the shared stands is contacted or needed.

**Why this priority**: Change acceptance is the integration gate into `master`; without it no
change can be accepted after the wipe.

**Independent Test**: With the shared ClearML stand absent or unreachable, run the
`integration` stage on a clean tip; the CPU smoke test passes and no namespace of the run
remains afterwards.

**Acceptance Scenarios**:

1. **Given** a reachable cluster and no shared stand, **When** the live part runs, **Then** a
   new namespace with the project prefix, a `ResourceQuota` and a `LimitRange` is created
   before any workload, the CPU stand smoke test passes against the ClearML inside it, and the
   namespace no longer exists when the stage ends.
2. **Given** the cluster does not answer, **When** the preflight runs, **Then** it reports
   unavailable with exit status 3 within its bound, creates nothing, and the live checks are
   reported as deferred.
3. **Given** the environment does not become ready within its start-up budget, **When**
   session setup gives up, **Then** the partially created namespace is deleted, the reason
   (the components not ready and their state) is reported, and the session ends as deferred
   (exit 3) under Task verification or skips interactively.
4. **Given** a test fails after setup, **When** the session ends, **Then** the namespace is
   still deleted and the failure is reported as a test failure, not as an infrastructure
   outcome.

---

### User Story 2 - FiftyOne suites against the run's own FiftyOne database (Priority: P1)

Release acceptance runs the FiftyOne native-database tests. The database they write to is a
FiftyOne database inside the run's own environment, reached through a port-forward, and it is
destroyed with the environment. A FiftyOne-only session starts only the database server.

**Why this priority**: Release acceptance requires these tests; the plan requires the project's
own FiftyOne database with a quota.

**Independent Test**: Run the FiftyOne suite through its stage; it passes, the database it used
was inside a namespace of the run, and that namespace is gone afterwards.

**Acceptance Scenarios**:

1. **Given** `CY_TEST_FIFTYONE=1` under the release-acceptance FiftyOne step, **When** the suite
   runs, **Then** FiftyOne connects to the environment's database (not to a host database
   process and not to the platform MongoDB), every test passes, and the namespace is deleted
   at the end.
2. **Given** the FiftyOne step, **When** the environment starts, **Then** no ClearML component
   is started for it.
3. **Given** the publisher lock location `FIFTYONE_DATABASE_DIR`, **When** the suite runs,
   **Then** it is still an isolated temporary directory removed afterwards, as today.

---

### User Story 3 - Agent live runs use the project's own environment (Priority: P2)

An agent sources the environment skill's `agent_env.sh` before a real `cy` run. It gets a run
identifier, a run directory and ClearML (and FiftyOne database) endpoints of an environment
the project deployed, with credentials in the environment and nothing printed.
`agent_cleanup.sh` deletes that environment and the run directory. `check_env.sh` reports
the tools and endpoints the run needs and no longer reports or requires Docker Compose.

**Why this priority**: Agent live runs and the real-run gate depend on the environment skill;
they break at the wipe like the tests do, but acceptance stages come first.

**Independent Test**: Source `agent_env.sh` in a clean shell, run `check_env.sh`, run a tiny
CPU `cy` command against the exported endpoint, then run `agent_cleanup.sh`; the run's
namespace and directory are gone and no k8s-infra helper was invoked.

**Acceptance Scenarios**:

1. **Given** a shell without any k8s-infra skill installed, **When** `agent_env.sh` is sourced,
   **Then** it succeeds, exports the run identifier, run directory and ClearML variables, and
   prints no credential value.
2. **Given** the cluster does not answer, **When** `agent_env.sh` is sourced, **Then** it
   returns 3 and creates nothing.
3. **Given** `check_env.sh` on a machine without Docker, **When** it runs, **Then** no line
   mentions Docker or Compose and the report has no Docker-related warning.
4. **Given** an environment from `agent_env.sh`, **When** `agent_cleanup.sh` runs, **Then** the
   namespace is deleted and proven absent, and the run directory is removed only when it is
   named after the run identifier.
5. **Given** a live recorded environment in the checkout (for example from an earlier
   `agent_env.sh` in the same shell, which exports its identifier), **When** `agent_env.sh` is
   sourced again, **Then** it returns 1 naming the recorded environment and
   `agent_cleanup.sh`, and creates, deletes and exports nothing (FR-020).
6. **Given** a recorded environment whose namespace no longer exists, **When** `agent_env.sh`
   is sourced, **Then** the stale record is cleared without any delete call and a new
   environment is created and exported under a new identifier (FR-014, R5).
7. **Given** a shell that exports `FIFTYONE_DATABASE_URI` and `FIFTYONE_DATABASE_NAME` from an
   earlier session and no `FIFTYONE_DATABASE_DIR`, **When** `agent_env.sh` is sourced, **Then**
   on success `FIFTYONE_DATABASE_URI` names the new environment's database,
   `FIFTYONE_DATABASE_NAME` is unset and `FIFTYONE_DATABASE_DIR` is
   `$HOME/.cache/clearml-yolo/fiftyone`; on failure neither database variable is set.
8. **Given** `source agent_env.sh <slug>`, **When** it runs, **Then** one line says the slug is
   ignored and the run proceeds as without it.
9. **Given** an environment from `agent_env.sh` and a live pytest session started in the same
   shell, **When** the session ends, **Then** the session adopted that environment, made no
   create or delete call, and the namespace and record remain until `agent_cleanup.sh` runs
   (FR-014).

---

### User Story 4 - Recovery from crashes, sweeps and restarts (Priority: P2)

A session crashes, the sweeper deletes an environment after 48 hours, or Docker Desktop
restarts and the sweeper deletes everything created before it. The worktree's record of the
active environment then points at a namespace that may or may not exist. Stopping always
converges; starting again recreates what is missing.

**Why this priority**: R5 makes vanishing namespaces normal, not exceptional.

**Independent Test**: Start an environment with `up`, delete its namespace out of band, run
`stop` (succeeds, record cleared), run `up` again (creates a fresh namespace).

**Acceptance Scenarios**:

1. **Given** a recorded environment whose namespace no longer exists, **When** `stop` runs,
   **Then** it succeeds, reports that the namespace was already gone, and clears the record.
2. **Given** a recorded environment whose namespace no longer exists, with or without
   `INTEGRATION_RUN_TAG` exported equal to it, **When** `up` or a live session starts, **Then**
   it clears the stale record without any delete call and creates a new environment instead of
   refusing; a session that created it deletes it at the end.
3. **Given** a live recorded environment, **When** `up` runs (whatever `INTEGRATION_RUN_TAG`
   holds), **Then** it refuses with exit 1, naming the environment and the `stop` command, as
   today's active-run refusal does.
4. **Given** `INTEGRATION_KEEP_DATA=1`, **When** the session ends, **Then** the environment is
   kept, the record stays, and the output names the `stop` command and the 48-hour limit.
5. **Given** a crash while the port-forward children run, **When** `stop` runs later,
   **Then** no port-forward of that environment remains.
6. **Given** a name that is not this project's environment identifier (for example
   `agent_cleanup.sh --tag clearml`, with or without `--dry-run`, or `stop --env default`),
   **When** teardown runs, **Then** it refuses with exit 1 and makes no delete call (FR-018).
7. **Given** a worktree record left by the retired run-tag lifecycle (its first line is not an
   environment identifier, for example `clearml-yolo-claude-20261105-integration-a1b2`), **When** `stop`, `up` or a live
   session runs, **Then** the record is cleared without any delete call; `stop` exits 0 and
   `up` or the session continues (FR-018).
8. **Given** a live recorded environment from `up` and `INTEGRATION_RUN_TAG` exported equal to
   it (`eval "$(L env)"`), **When** a live session runs and ends, including with
   `INTEGRATION_KEEP_DATA=1` or after a test failure, **Then** the session uses that
   environment, makes no create or delete call, and afterwards the namespace and record still
   exist; `stop` then removes them (FR-014).
9. **Given** a live recorded environment and `INTEGRATION_RUN_TAG` unset or different, **When**
   a live session starts, **Then** it refuses with exit 1 naming the environment and `stop`,
   and creates and deletes nothing.
10. **Given** no live recorded environment and `INTEGRATION_RUN_TAG` exported (for example the
    identifier of a swept environment), **When** a live session starts, **Then** one line says
    the exported identifier names no live recorded environment, the session creates its own
    environment under a new identifier, uses that identifier for the tests, and deletes only
    that namespace at the end.
11. **Given** a shell that still exports the identifier of a swept environment, **When** `up`
    and then `eval "$(L env)"` run, **Then** `up` creates a new environment and `env` exports
    the new identifier; the old export blocks neither command.
12. **Given** an adopted environment (as in scenario 8) whose recorded port-forward for a
    component the session needs is missing or no longer running, **When** the session starts,
    **Then** it refuses with exit 1 naming the component and `stop`, and creates and deletes
    nothing.
13. **Given** a record naming an existing namespace that lacks the project label, **When**
    `up`, `agent_env.sh` or a live session starts, **Then** it refuses with exit 1, keeps the
    record, and creates and deletes nothing (FR-018).

---

### User Story 5 - Paired check and GPU suites keep their behaviour (Priority: P3)

The paired CY and cy-queue check, the GPU suites and the real-run gate keep their behaviour.
The GPU suites publish into the session's environment instead of the shared stand; cy-queue
and real GPU execution are untouched.

**Why this priority**: Required for release, but nothing in their own logic changes.

**Independent Test**: Run cy-queue's suite against the migrated tip with cy-queue unchanged;
run the GPU suite's option validation without a GPU and confirm it still rejects an invalid
selection before any environment is created.

**Acceptance Scenarios**:

1. **Given** the migrated tip, **When** cy-queue's suite runs in the paired environment,
   **Then** it passes with no change to cy-queue (subject to the `batch_sizes` dependency in
   "Dependencies").
2. **Given** a GPU suite with invalid options, **When** it runs, **Then** it fails validation
   before creating any environment, as it fails before claiming a run tag today.

### Edge Cases

- **Namespace swept mid-session.** A session that runs longer than the sweeper allows, or
  spans a restart, loses its namespace; the remaining tests fail on lost connectivity and
  teardown still succeeds because the namespace is already gone.
- **Two worktrees at once.** Each creates its own namespace; nothing is shared. Node pressure
  shows up as pods that never become ready and is reported as deferred, not as failure.
- **Uncached images.** The first start on a machine without the pinned images pulls several
  gigabytes; the preflight reports which pinned images the node lacks (informational) and the
  start-up budget is configurable.
- **Quota rejection.** A pod that the quota or limit range rejects is a configuration error
  (exit 1) with the rejection event quoted, not a timeout.
- **Port-forward dies.** A pod restart ends kubectl's port-forward; requests then fail as lost
  connectivity, which the existing classification already reports.
- **Manual commands under pytest isolation.** The test HOME is replaced; kubectl still needs
  the real kubeconfig, which is restored from `CY_REAL_ENV` for children as today.
- **Stale per-worktree namespaces.** Environments of a crashed worktree that nobody stops are
  removed by the sweeper within 48 hours. Teardown deletes only a namespace whose name is an
  environment identifier and whose live labels mark it as this project's (FR-018); no
  other name, from a record or from `--tag`, ever reaches a delete call.
- **Record from the retired lifecycle.** A worktree may still hold a `.run-tag` written by the
  run-tag lifecycle (a shared-stand run tag such as `clearml-yolo-claude-20261105-integration-a1b2`, which can never match
  the identifier pattern because it carries a harness word and a date). It names no namespace
  of this project; it is cleared without a delete call (FR-018).
- **User's host ClearML.** The port-forward never binds local port 8008, so the host-stand
  warning keeps meaning "this is the user's own ClearML".

## Requirements *(mandatory)*

### Functional Requirements

**Environment ownership (R1-R4, R6, R7)**

- **FR-001**: Live tests and agent live runs MUST use a **test environment** that the project
  creates: one Kubernetes namespace on context `docker-desktop`, named
  `cy-it-<id>` with a fresh random `<id>`, never a protected name (R2).
- **FR-002**: Creating an environment MUST apply the namespace's `ResourceQuota` and
  `LimitRange` before any workload object, and the quota MUST cover the measured set with
  headroom while allowing no `PersistentVolumeClaim` and no `nvidia.com/gpu` request (R3, R4,
  R7). Its values live in the project's manifests with the measurement that justifies them.
  The designed values were derived from the use measured on 2026-11-10; the measurement runs
  applied a looser quota, so the designed quota itself is first applied, and its admission of
  every pod first shown, by the live acceptance run (tasks T027).
- **FR-003**: The environment MUST provide its own ClearML server (API and file server with
  their MongoDB, Redis and Elasticsearch) and its own FiftyOne database; it MUST NOT contact
  the platform's dedicated ClearML or MongoDB or any retired shared stand (R6).
- **FR-004**: Every environment volume MUST be `emptyDir`; manifests MUST NOT name a
  `storageClassName`, `local-path` or a host path (R4, interim rule).
- **FR-005**: The environment MUST start only the components its session needs: ClearML
  components when a test or run needs ClearML; only the database server for a FiftyOne-only
  session.
- **FR-006**: Credentials for the environment MUST be generated per environment, held only in
  the environment's own Secret and the consuming process environment, never printed, logged,
  committed or written to a repository file.
- **FR-007**: The environment's namespace and objects MUST carry labels that identify the
  project and the environment identifier, so leftovers are recognisable.

**Lifecycle (replaces the run-tag lifecycle)**

- **FR-010**: A read-only preflight MUST remain, bounded by `CY_INFRA_CHECK_TIMEOUT` (default
  60 s), creating nothing, with exit statuses 0 available, 3 unavailable (cluster not
  answering, timeout), 1 error (kubectl missing, context missing, permission to create
  namespaces denied), 130 interrupted. It MUST NOT call any k8s-infra helper. `up` and
  session setup MUST run the same bounded preflight before they read the record or create
  anything, so an unavailable cluster ends them with exit 3 and nothing changed.
- **FR-011**: Session setup MUST adopt or create the environment by the selection rule
  (FR-014); when it creates one, it MUST wait for readiness within a start-up
  budget configurable through an environment variable (default chosen from the measured cold
  start with room for pulling images), open port-forwards to loopback on kubectl-chosen ports,
  and export the ClearML endpoint, files endpoint and credentials (and the FiftyOne database
  URI) to the tests.
- **FR-012**: A setup failure after the namespace exists MUST delete the namespace before the
  failure is reported. Temporary causes (not ready within the budget, lost connectivity) MUST
  be reported as unavailable (exit 3, deferred); permanent causes (forbidden, invalid
  manifest, quota rejection) as errors (exit 1).
- **FR-013**: Teardown MUST stop the environment's port-forwards, delete the namespace and
  prove its absence within a bounded wait; incomplete teardown MUST fail the session and keep
  the record for a retry, as incomplete exact-tag cleanup does today. Every teardown is
  subject to the deletion guard (FR-018).
- **FR-014**: One worktree MUST have at most one recorded environment. A **live recorded
  environment** is one whose record identifier matches the identifier pattern and whose
  namespace exists with the project label. `up`, `agent_env.sh` and session setup MUST select
  by one rule (contract "Environment selection"):
  - no record, a retired-format record or a stale record (namespace absent): the record is
    cleared without any delete call and a new environment is created (R5); an exported
    `INTEGRATION_RUN_TAG` is ignored, and session setup says so in one line and uses the new
    identifier;
  - a live recorded environment and a pytest session whose shell exports `INTEGRATION_RUN_TAG`
    equal to it (as `eval "$(L env)"` after `up` or `agent_env.sh` does): the session
    **adopts** it, provided each component it needs has a running recorded port-forward
    (otherwise exit 1 naming the component and `stop`);
  - any other live recorded environment, including every case for `up` and `agent_env.sh`:
    refused with exit 1 naming the environment and the `stop` command;
  - a record naming an existing namespace without the project label: refused with exit 1,
    record kept (FR-018).

  Whoever creates an environment removes it: a session deletes only the environment it
  created (unless `INTEGRATION_KEEP_DATA=1`); an environment created by `up` or `agent_env.sh`,
  and therefore every adopted one, is deleted only by `stop` or `agent_cleanup.sh`. An adopting
  session makes no create or delete call, including on setup failure, test failure and under
  `INTEGRATION_KEEP_DATA=1`. `stop` on a stale record succeeds and clears it. Only session
  setup reads an exported `INTEGRATION_RUN_TAG`, and only to decide adoption; `up` and `env`
  ignore it (`env` overwrites it).
- **FR-015**: `INTEGRATION_KEEP_DATA=1` MUST keep an environment the session created, and its
  record, after the session and print the `stop` command and the 48-hour limit. An adopted
  environment is kept in every case (FR-014); the session prints the same lines for it.
- **FR-016**: The manual commands `check`, `up`, `env` and `stop` of
  `python -m tests.integration.lifecycle` MUST keep their names and exit-status contract;
  `env` MUST keep refusing to print to a terminal.
- **FR-017**: The live suites MUST keep passing explicit ClearML project names and tags that
  carry the environment identifier; the GPU suites keep joining the session environment on
  demand after validating their options.
- **FR-018**: Teardown (`stop`, the session fixtures, setup-failure cleanup and
  `agent_cleanup.sh`, including `--dry-run`) MUST make a `kubectl delete` call only for a
  name that matches `^cy-it-[0-9a-f]{6}$` and whose live namespace carries the
  label `app.kubernetes.io/part-of=clearml-yolo-tests`. The name is checked before any other
  teardown step. By source:
  - a name given on the command line (`stop --env <id>`, `agent_cleanup.sh --tag`, or
    `CY_RUN_TAG`) that does not match is refused with exit 1; the record is left untouched;
  - a record whose first line does not match (the retired run-tag format or anything else) is
    not an environment: it is cleared, reported as a retired record, and `stop` exits 0;
  - a matching name whose live namespace lacks the label is refused with exit 1 and the
    record is kept;
  - a matching name whose namespace is absent is already stopped (FR-014).

**Environment skill and repository references (R8, R9)**

- **FR-020**: `agent_env.sh` MUST always create a new environment through the same lifecycle
  (`up --components all`, then `env`), run in the clearml-yolo checkout that contains the
  skill, so the environment is that checkout's recorded environment; it never reuses an
  environment: a live recorded environment is refused with return status 1 naming it and
  `agent_cleanup.sh`, and a stale or retired record is cleared and replaced (FR-014). It MUST
  export the run identifier, run directory and ClearML variables and `FIFTYONE_DATABASE_URI`
  without printing credentials; unset `FIFTYONE_DATABASE_URI` and `FIFTYONE_DATABASE_NAME`
  before `up`, so a failure leaves neither set; default `FIFTYONE_DATABASE_DIR` to
  `$HOME/.cache/clearml-yolo/fiftyone`; ignore a `<slug>` argument with a one-line notice;
  return 3 when unavailable and 1 on refusal or error; and require no k8s-infra skill.
- **FR-021**: `agent_cleanup.sh` MUST tear the environment down through the same lifecycle,
  passing the identifier from `--tag` (else `CY_RUN_TAG`) as `stop --env <id>`, and keep its
  rule that a run directory is removed only when named after the run identifier; `--dry-run`
  MUST delete nothing. A name the deletion guard refuses (FR-018) ends the script with exit 1
  before the run-directory step, in both the dry and the real form.
- **FR-022**: `check_env.sh` MUST NOT run or report `docker compose`; it MUST report the
  tools the live path needs (uv, kubectl with a reachable `docker-desktop` context, the GPU
  as today) and the ClearML endpoint check as today, without TLS trust hints for the retired
  stand. It MUST keep exiting 0.
- **FR-023**: No tracked file outside dated evidence and historical feature records MUST
  reference `INFRA_RUN_TAG`, `INFRA_PROJECT`, `K8S_INFRA_SKILL_DIR`, `INFRA_REGISTRY`,
  `INFRA_HARNESS`, `INFRA_SCRATCH_DIR`, `CY_INFRA_SKILL_DIR`, `infra.py`, `clearml.py`,
  `mongodb.py`, `*.k8s.docker.internal` stand endpoints, the destroyed shared database
  `clearml_yolo_tests`, `FIFTYONE_DATABASE_NAME`, or
  the shared MongoDB host port `27018` as current instructions or code. Product tests that set
  a retired variable to prove the application ignores it, the mutation driver's scrubbing of
  `INFRA_*` variables a shell may still export, and `agent_env.sh` unsetting a
  `FIFTYONE_DATABASE_NAME` a shell may still export (FR-020) are guards, not uses, and stay.
- **FR-024**: The skills, development procedures, ddp-testing procedure, Taskfile stage
  descriptions, session-start status report, glossary, `TECH_DETAILS.md` and the Russian
  `README.md` command comment MUST describe the project-owned environment instead of the
  shared stand.

**Unchanged behaviour**

- **FR-030**: `src/`, the GPU suites' execution logic, the real-run gate, cy-queue and the
  paired check's procedure MUST NOT change; the paired check MUST pass against the migrated
  tip with cy-queue unchanged, once its dependency in "Dependencies" is met.
- **FR-031**: Development verification MUST still never contact the cluster; live tests MUST
  still run only when `tests/integration` is named or the `integration` marker is selected.

### Behaviour map (specification rewrite)

Each current behaviour of the run-tag lifecycle and the environment skill, with its new home.

| Current behaviour | Disposition | New home |
| --- | --- | --- |
| `check` bounded read-only preflight, exits 0/3/1/130 | Kept; probes change (cluster, context, permission instead of `room`, Secret, TLS, `whoami`) | FR-010 |
| `up` (and session setup) run the same bounded check before claiming a tag | Kept: they run `check` within its bound before reading the record or creating anything | FR-010 |
| `infra.py room` capacity WAIT → exit 3 | Removed (no capacity logic on the platform); node pressure surfaces as start-up timeout → exit 3 | FR-012 |
| `clearml.py env` credentials + CA trust exports | Changed: generated per environment; no CA exports (plain HTTP over port-forward) | FR-006, FR-011 |
| TLS failure classified as permanent error with CA remedy | Removed with TLS | FR-022 |
| `infra.py newtag` run tag minted, `.run-tag` record | Changed: environment identifier is the namespace name; the per-worktree record remains | FR-001, FR-014 |
| `INFRA_RUN_TAG` adopts a run started elsewhere | Changed: a pytest session adopts the worktree's live recorded environment only when `INTEGRATION_RUN_TAG` is exported equal to it; `up` and `agent_env.sh` never adopt; `INFRA_RUN_TAG` is retired (R8) | FR-014, FR-023 |
| A session with an adopted tag removed that tag's leftovers at start and its objects at the end (unless `INTEGRATION_KEEP_DATA=1`) | Changed: an adopting session makes no create or delete call; the environment is removed by `stop` or `agent_cleanup.sh`, so automatic teardown never deletes a namespace its process did not create | FR-014, FR-015 |
| Refuse `up` while another run is recorded | Kept, for a live recorded environment whatever is exported; plus vanished-namespace convergence; a recorded namespace without the project label is refused too | FR-014, FR-018 |
| Tagged project names and `clearml.tags` | Kept; no longer the cleanup selector | FR-017 |
| Exact-tag cleanup proven by empty `ls --prefix` | Changed: namespace deletion proven by absence | FR-013 |
| Keep tag file until cleanup is proven | Kept for the environment record | FR-013 |
| Setup failure stops the run | Kept: namespace deleted before reporting | FR-012 |
| `INTEGRATION_KEEP_DATA=1` | Kept; adds the 48-hour note | FR-015 |
| `env` refuses a terminal | Kept | FR-016 |
| Children get the real HOME from `CY_REAL_ENV` | Kept (kubectl needs the real kubeconfig) | Edge cases |
| `INTEGRATION_RUN_TAG` conflict check (`up` and `env` refused when it differed from the resolved tag) | Changed: only session setup reads it, to decide adoption; when it names no live recorded environment the session says so and creates its own; `up` and `env` ignore it (`env` overwrites it), so a stale export never blocks recovery | FR-014 |
| Interactive skip vs Task exit 3 on unavailability | Kept | FR-012 |
| FiftyOne suites on a host-local database in `FIFTYONE_DATABASE_DIR` | Changed: database in the environment; the directory stays as the lock location | FR-003, US2 |
| `agent_env.sh` room/env/mongodb/newtag steps | Changed to the lifecycle (`up --components all`, then `env`) | FR-020 |
| `agent_env.sh` keeps an already exported `INFRA_RUN_TAG` instead of minting | Removed: it always performs `up`; a live recorded environment is refused with 1 naming `agent_cleanup.sh` | FR-014, FR-020 |
| `agent_env.sh` acts on the shared stand with no worktree record | Changed: it uses the record of the checkout that contains the skill, so agent runs, manual `up` and pytest sessions share the one-environment-per-worktree rule | FR-014, FR-020 |
| `agent_env.sh [<slug>]` passes the slug to `infra.py newtag` | Removed: the identifier carries no slug; a given argument is ignored with a one-line notice | FR-020 |
| `agent_env.sh` treats MongoDB as optional (warning, run continues without `FIFTYONE_DATABASE_URI`) | Changed: the database is a component of the environment that `up --components all` starts; its failure fails `up` (3 or 1) like any component | FR-005, FR-020 |
| `agent_env.sh` unsets `FIFTYONE_DATABASE_URI` and `FIFTYONE_DATABASE_NAME` before refreshing | Kept, before `up`; `env` sets only `FIFTYONE_DATABASE_URI`, so `FIFTYONE_DATABASE_NAME` stays unset | FR-020, FR-023 |
| `agent_env.sh` defaults `FIFTYONE_DATABASE_DIR` to `$HOME/.cache/clearml-yolo/fiftyone` | Kept (the publisher's lock location) | FR-020 |
| `agent_cleanup.sh` exact-tag cleanup + directory rule | Changed to teardown; directory rule kept | FR-021 |
| `--tag` / `.run-tag` accepted any lowercase `[a-z0-9-]` tag as the cleanup selector | Changed: teardown accepts only an environment identifier whose live namespace carries the project label; a retired-format record is cleared without a delete | FR-018 |
| `check_env.sh` `docker compose` check | Removed | FR-022 |
| `check_env.sh` host-stand (localhost:8008) warning | Kept, reworded for the run's own ClearML | FR-022 |
| `check_env.sh` authenticated `auth.login` check, exit 0 | Kept | FR-022 |
| `INFRA_HARNESS` for tag minting | Removed | FR-023 |
| `INFRA_SCRATCH_DIR` run-directory root | Changed: project-named variable with the same default | FR-020 |
| Unit tests of `lifecycle.py` (`tests/test_integration_lifecycle.py`) | Removed: tooling tests; lifecycle evidenced by live runs | Clarifications |

### Key Entities

- **Test environment**: one namespace of this project with its identifier, quota, limit range,
  credentials Secret, components and port-forwards; lives at most until teardown or the
  sweeper.
- **Environment record**: the worktree's note of its active environment (identifier and
  port-forward processes); never holds a credential. It is live, stale, retired-format or
  foreign (unlabelled namespace), and that state alone with the exported identifier decides
  adoption, creation or refusal (FR-014).
- **Component**: a deployable part of the environment (database server, Redis,
  Elasticsearch, ClearML API server, ClearML file server) with its requests and limits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no shared stand present, the `integration` stage passes on a clean tip and
  leaves no namespace with the project prefix behind.
- **SC-002**: The release-acceptance FiftyOne step passes against the environment's database
  and leaves no namespace behind.
- **SC-003**: `git grep` for the retired names in FR-023 finds nothing outside dated evidence,
  `CHANGELOG.md`, `bugs/` and earlier feature records.
- **SC-004**: Every namespace the project creates appears with a `ResourceQuota` in the
  sweeper's report (or `kubectl get resourcequota -n <ns>` before the sweeper exists).
- **SC-005**: Environment cold start with cached images stays within the default start-up
  budget with margin; the measured value is recorded as dated evidence.
- **SC-006**: `stop` after an out-of-band namespace deletion succeeds; `up` afterwards creates
  a new environment.
- **SC-007**: cy-queue's suite passes against the migrated tip with cy-queue unchanged
  (the `paired-check` stage); see "Dependencies" for its current blocker.
- **SC-008**: A live session in a shell that exports the identifier of the live recorded
  environment leaves that namespace and record in place; a session with no live recorded
  environment, whatever is exported, creates a namespace and deletes exactly that one; a
  second `agent_env.sh` against a live recorded environment creates nothing (US3 scenarios
  5-6, US4 scenarios 8-13).

## Assumptions

- The cluster context `docker-desktop` and `kubectl` are available on the developer machine;
  the user's kubeconfig grants namespace creation.
- The container images pinned by the manifests stay pullable or cached; the measured images
  were already cached on this node.
- Host-side GPU processes of the GPU suites reach the environment through the same loopback
  port-forward as the CPU tests.
- The platform sweeper is not yet armed; when armed it may delete environments as R5 says.

## Dependencies

- **SC-007 and the paired check depend on master gaining
  `clearml_yolo.adapters.storage.batch_sizes`** (branch `012-editable-batch-sizes`) or on the
  owner's decision about that dependency. cy-queue `d3627a0` imports that module; on
  2026-11-10 the `paired-check` stage failed at collection for that reason alone
  ([evidence/2026-11-10-paired-check.md](evidence/2026-11-10-paired-check.md)). Until the
  dependency is met, the paired check is reported as failed for a cause outside this feature,
  never as passed; this feature makes no change to cy-queue or `src/` to work around it.

## Out of Scope

- Real GPU work execution, cy-queue scheduling and any cy-queue change.
- Running ClearML tasks inside the cluster (agents, queues, the k8s glue) and the ClearML web UI.
- Wildcard host names, ingress and the platform certificate (R9: host access is by
  port-forward only).
- The platform's dedicated ClearML and MongoDB and their credential bundles.
- Releasing a version; pushing.
