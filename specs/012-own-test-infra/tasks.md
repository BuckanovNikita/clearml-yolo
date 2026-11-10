# Tasks: Own Kubernetes Test Infrastructure

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/test-environment.md](contracts/test-environment.md),
[quickstart.md](quickstart.md), [evidence/](evidence/)

**Tests**: No new tests of project tooling (owner rule: tests exercise product code). The
lifecycle is evidenced by running the product's existing live suites through it (Phase 7).
Product tests that guard against retired variables stay unchanged.

**Cluster rule for implementers**: create and delete only namespaces you record; never touch
namespaces, Secrets or workloads you did not create.

## Stream ownership (write ownership is exclusive)

| Stream | Owns | Depends on |
| --- | --- | --- |
| A Environment | `tests/integration/environment/**`, `tests/integration/lifecycle.py`, `tests/integration/conftest.py`, `tests/test_integration_lifecycle.py` (delete) | Phase 2 |
| B Live suites | `tests/integration/fiftyone/*.py`, `tests/integration/test_cpu_stand_smoke.py`, `tests/integration/test_native_ddp_gpu.py`, `tests/integration/test_severstal_gpu.py`, `tests/env_isolation.py` (docstring), `tests/conftest.py` (docstrings) | A's fixture names (contract) |
| C Environment skill | `.agents/skills/clearml-yolo-environment/{SKILL.md,scripts/*.sh,references/machine-workflow.md}` | A's CLI (contract) |
| D Docs and wiring | `Taskfile.yml`, `scripts/session_status.sh`, `.agents/skills/{running-integration-tests,running-end-to-end-tests,verification-workflow,mutation-testing}/SKILL.md`, `docs/development.md`, `docs/ddp-testing.md`, `GLOSSARY.md`, `AGENTS.md`, `README.md` | contract |

B, C and D work from [contracts/test-environment.md](contracts/test-environment.md) and may run
in parallel with A once Phase 2 is done; their live checks wait for A.

## Phase 1: Setup

- [ ] T001 Prepare the worktree environment (`external/`, `uv.toml`, `uv sync --locked --dev`, hooks) per docs/development.md#external-dependencies; confirm `uv run --locked cy --help`
- [ ] T002 Record the starting inventory: `git grep -nE "infra\.py|clearml\.py|mongodb\.py|INFRA_RUN_TAG|INFRA_PROJECT|K8S_INFRA_SKILL_DIR|INFRA_REGISTRY|INFRA_HARNESS|INFRA_SCRATCH_DIR|CY_INFRA_SKILL_DIR|docker compose|k8s\.docker\.internal"` outside `CHANGELOG.md`, `bugs/`, `specs/0*`, dated evidence

## Phase 2: Foundational (blocks all stories)

- [ ] T003 [A] Create `tests/integration/environment/` manifests from evidence/measure/stack.yaml: quota and limit range (data-model.md values), `mongo`, `redis`, `elastic`, `apiserver`, `fileserver` with labels `app.kubernetes.io/part-of=clearml-yolo-tests` and `clearml-yolo/environment=<id>`, init-container ordering with `curl -m 2`, 2 s termination grace, `emptyDir` only, `imagePullPolicy: IfNotPresent`, no `storageClassName`, Ingress, claim or GPU request; one YAML document per file (the `check-yaml` hook rejects multi-document files; use `kind: List` or one object per file); split into a database file and a ClearML file so components can be selected
- [ ] T004 [A] Validate the manifests with `kubectl --context docker-desktop apply --dry-run=server` inside a namespace you create with the `clearml-yolo-it-` prefix, then delete it

**Checkpoint**: manifests validated; streams B, C, D may start.

## Phase 3: User Story 1 – Change acceptance on an own environment (P1) — Stream A

**Independent test**: spec US1.

- [ ] T005 [US1] Rewrite `check` in tests/integration/lifecycle.py: kubectl present, context `docker-desktop`, `get --raw=/readyz`, `auth can-i create namespaces`, informational missing-image line from node `status.images`; keep `CY_INFRA_CHECK_TIMEOUT`, process-group kill on timeout, `is_temporary` classification and exits 0/3/1/130; remove skill lookup, `room`, Secret, TLS and `whoami` probes
- [ ] T006 [US1] Implement environment creation in tests/integration/lifecycle.py: identifier `clearml-yolo-it-<6 hex>`, namespace with labels, quota and limit range first, credentials Secret from stdin (`secrets` module; never echoed), component manifests, readiness wait bounded by `CY_TEST_ENV_START_TIMEOUT` (default 300) listing not-ready components and reasons; quota/limit-range rejection and Forbidden → `LifecycleError`; budget expiry and lost connectivity → `StandUnavailableError`
- [ ] T007 [US1] Implement port-forwarding in tests/integration/lifecycle.py: `kubectl port-forward svc/<c> :<port>` children, parse the kubectl-chosen local port, export `CLEARML_API_HOST`, `CLEARML_FILES_HOST`, `CLEARML_WEB_HOST`, `CLEARML_API_ACCESS_KEY`, `CLEARML_API_SECRET_KEY`, `FIFTYONE_DATABASE_URI`, `INTEGRATION_RUN_TAG`; restore the real HOME/kubeconfig for children from `CY_REAL_ENV` as today
- [ ] T008 [US1] Implement teardown in tests/integration/lifecycle.py: `stop [--env <id>] [--dry-run]`; the deletion guard first (contract "Deletion guard", spec FR-018: name must match `^clearml-yolo-it-[0-9a-f]{6}$`, live namespace must carry `app.kubernetes.io/part-of=clearml-yolo-tests`, else exit 1 with no delete call and no signal); then stop owned port-forwards, `kubectl delete namespace`, bounded wait for absence (`CY_TEST_ENV_STOP_TIMEOUT`, default 180), already-absent is success, keep the record when absence is not proven; session fixtures and setup-failure cleanup use the same guarded path
- [ ] T009 [US1] Rework `prepare`/`finish` and the record in tests/integration/lifecycle.py: setup failure after creation deletes the namespace; `INTEGRATION_KEEP_DATA=1` keeps it and prints `stop` plus the 48-hour limit; keep `env` refusing a terminal and the `INTEGRATION_RUN_TAG` conflict check (FR-016); remove `find_skill_dir`, `clearml()`, `remove_tagged_objects`, `INFRA_RUN_TAG` adoption, TLS constants and the module docstring's shared-stand text
- [ ] T010 [US1] Update tests/integration/conftest.py: `live_run` creates the ClearML-capable environment lazily and exports its variables; `stand_project` unchanged in behaviour (tagged name with the environment identifier); deferral and failure handling unchanged; live tests stay opt-in through tests/conftest.py marking (FR-031)
- [ ] T011 [US1] Delete tests/test_integration_lifecycle.py (tooling tests of removed behaviour; research R-10)

## Phase 4: User Story 2 – FiftyOne suites on the own database (P1) — Streams A, B, D

- [ ] T012 [A] [US2] Add a session fixture `fiftyone_database` in tests/integration/conftest.py that ensures the session environment with the database component only (or reuses a ClearML-capable one) and sets `FIFTYONE_DATABASE_URI`; it never starts ClearML components
- [ ] T013 [P] [B] [US2] Make tests/integration/fiftyone/test_fiftyone_publisher.py, test_fiftyone_native_evaluations.py and test_fiftyone_panel_views.py request `fiftyone_database`; keep the `CY_TEST_FIFTYONE=1` opt-in and the isolated `FIFTYONE_DATABASE_DIR` requirement for the publisher's locks; update docstrings and skip reasons
- [ ] T014 [D] [US2] Keep the release-acceptance FiftyOne step in Taskfile.yml creating and removing a temporary `FIFTYONE_DATABASE_DIR`; the database now comes from the fixture (no host `mongod`)

## Phase 5: User Story 3 – Agent live runs (P2) — Stream C

- [ ] T015 [C] [US3] Rewrite .agents/skills/clearml-yolo-environment/scripts/agent_env.sh: sourced-only guard kept; `lifecycle up --components all` then `eval "$(lifecycle env)"`; export `CY_RUN_TAG`, `CY_RUN_DIR=${CY_SCRATCH_DIR:-/tmp/clearml-yolo-runs}/<id>`; return 3/1 as the lifecycle does; run check_env.sh; no k8s-infra skill, `INFRA_*` or `CY_INFRA_SKILL_DIR`
- [ ] T016 [C] [US3] Rewrite .agents/skills/clearml-yolo-environment/scripts/agent_cleanup.sh: `lifecycle stop --env <id> [--dry-run]` with the identifier from `--tag`, else `CY_RUN_TAG` (no `INFRA_RUN_TAG` fallback); no own kubectl call, so the lifecycle's deletion guard (FR-018) is the only path to a delete; a guard refusal exits 1 before the run-directory step in both forms; `--dry-run` reports only; run-directory rule unchanged; exit statuses documented in SKILL.md
- [ ] T017 [C] [US3] Rewrite .agents/skills/clearml-yolo-environment/scripts/check_env.sh: remove `check_docker` and every Docker/Compose line; add a kubectl/context reachability line; drop the TLS hint and k8s-infra CA text; keep the `auth.login` check, the localhost:8008 host-ClearML warning (reworded: "not this run's own test ClearML"), GPU line, `--json` and exit 0
- [ ] T018 [C] [US3] Rewrite .agents/skills/clearml-yolo-environment/SKILL.md and references/machine-workflow.md for the own environment (port-forward endpoints, no TLS, no k8s-infra skill); leave dated evidence files under references/ unchanged

## Phase 6: User Story 4 – Recovery (P2) — Stream A

- [ ] T019 [A] [US4] In tests/integration/lifecycle.py: `up` and session setup clear a record whose namespace is absent and create a new environment; refuse a live recorded one naming `stop`; `stop` on an absent namespace succeeds and clears the record; a record whose first line is not an environment identifier (retired run-tag format) is cleared by `stop`, `up` and session setup without any delete call (FR-018); a live recorded namespace without the project label is refused by `stop` with exit 1 and no delete call; detached port-forwards of manual `up` recorded with PID and start time and signalled only when both match

## Phase 7: Documentation, wiring and acceptance — Stream D, then all

- [ ] T020 [P] [D] Update Taskfile.yml descriptions of `infra-check`, `integration`, `acceptance` (own environment, not the shared stand)
- [ ] T021 [P] [D] Update scripts/session_status.sh to report the recorded environment identifier and the `lifecycle stop` hint
- [ ] T022 [P] [D] Rewrite .agents/skills/running-integration-tests/SKILL.md for the environment lifecycle (commands, variables, exits, record, recovery, no k8s-infra); update running-end-to-end-tests, verification-workflow and mutation-testing wording that names the stand
- [ ] T023 [P] [D] Update docs/development.md (verification table, acceptance tiers, FiftyOne step), docs/ddp-testing.md (project prefix from `.run-tag`, no shared stand), GLOSSARY.md (change acceptance; add **Test environment**), AGENTS.md routing wording, README.md (Russian comment on line with `task --exit-code acceptance`)
- [ ] T024 [P] [B] Update docstrings in tests/integration/test_cpu_stand_smoke.py, test_native_ddp_gpu.py, test_severstal_gpu.py, tests/env_isolation.py and tests/conftest.py that name the shared stand or the k8s-infra skill
- [ ] T025 Re-run the T002 inventory; every remaining hit is dated evidence, a historical feature record, `CHANGELOG.md`, `bugs/`, a product guard test or the mutation driver's scrub (spec FR-023)
- [ ] T026 Run `uv run --locked task --exit-code verify`, then `uv run --locked prek run --all-files` with `SKIP` cleared after the last commit
- [ ] T027 Live: `uv run --locked task --exit-code integration` on a clean tip with no shared stand used; record the environment identifier, pass/fail, cold start, the namespace's `ResourceQuota` while it exists, and that no `clearml-yolo-it-` namespace remains (SC-001, SC-004, SC-005)
- [ ] T028 Live: the release-acceptance FiftyOne step alone; record pass/fail and namespace absence (SC-002)
- [ ] T029 Live: `lifecycle up`, delete its namespace out of band, `lifecycle stop` (success), `lifecycle up` (new identifier), `lifecycle stop` (SC-006)
- [ ] T029a Live, deletion guard (FR-018, US4 scenarios 6-7): with `kubectl --context docker-desktop get ns` captured before and after, run `agent_cleanup.sh --tag clearml --dry-run` and `agent_cleanup.sh --tag clearml`; both exit 1 with no delete call and an unchanged namespace list. Write a retired-format record (`clearml-abc123` on line 1) into `tests/integration/.run-tag` and run `lifecycle stop`: exit 0, record cleared, namespace list unchanged. Create a namespace `clearml-yolo-it-<6 hex>` without the project label, run `lifecycle stop --env <it>`: exit 1 and the namespace still exists; then delete that namespace by hand
- [ ] T030 Live: source agent_env.sh in a clean shell without the k8s-infra skill, run check_env.sh (no Docker lines), run agent_cleanup.sh; record namespace and directory absence (US3)
- [ ] T031 Paired: `cd /mnt/wsl/data/nkt/cy-queue && uv run --frozen --no-sync --project <worktree> pytest -q` with cy-queue unchanged (`git -C cy-queue status --short` before and after) (SC-007)
- [ ] T031a Run a GPU suite with deliberately invalid `--run-*` options and no GPU; it must fail validation before any `clearml-yolo-it-` namespace is created (US5 scenario 2); confirm `git diff master -- src` is empty (FR-030)
- [ ] T032 Fresh independent review of the integrated branch (behaviour, security of credential handling, operational policy), comparing the behaviour map in spec.md against `git show master:tests/integration/lifecycle.py` and the original skill scripts
- [ ] T033 Record dated evidence for T027-T031 (including T029a and T031a) in this feature directory; report deferred checks (GPU suites, release acceptance) as deferred, never as passed

## Dependencies

Phase 1 → Phase 2 → {A: Phases 3, 4 (T012), 6} ∥ {B: T013, T024} ∥ {C: Phase 5} ∥ {D: T014, T020-T023} → T025-T026 → live T027-T031 → T032 → T033.
