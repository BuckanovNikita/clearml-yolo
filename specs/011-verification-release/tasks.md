# Tasks: Verification and Release Workflow

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)
**Reference sources**: `/mnt/wsl/data/nkt/cveta2` (copy and adapt; never edit it).
**Tests**: Product-behavior tests for new Python tooling (`lifecycle.py`, `mutation.py`
helpers, lock-entry guard) and the CPU stand smoke test; no tests of third-party tool behavior.

## Stream ownership (write ownership is exclusive)

| Stream | Owns |
|---|---|
| F Foundation | `pyproject.toml`, `uv.lock`, `Taskfile.yml`, `tests/env_isolation.py`, `.gitignore` |
| A Tests | `tests/conftest.py`, `tests/integration/**`, moved live test modules, xdist-related edits in `tests/*.py` |
| B Hooks + release | `.pre-commit-config.yaml`, `scripts/install-hooks.sh`, `scripts/git-hook.sh`, `scripts/local_release.py` (delete), `scripts/release_lock_guard.py`, `[tool.semantic_release]` and `release-commit-check`/`paired-check` task bodies (handed to F as patch text) |
| C Mutation + status | `scripts/mutation.py`, `scripts/session_status.sh`, `.claude/settings.json`, `[tool.mutmut]` (patch text to F) |
| D Docs | `docs/**`, `AGENTS.md`, `README.md`, `.agents/skills/**` (new skills only + edits to `running-end-to-end-tests`), `.specify/memory/constitution.md`, `.gitignore` re-includes for new skills (patch text to F) |

Streams A–D send `pyproject.toml`/`Taskfile.yml`/`.gitignore` changes to the integrator as patch
text; only the integrator writes those files after Phase 2.

## Phase 1: Setup

- [ ] T001 Add dev dependencies `go-task-bin`, `pytest-xdist`, `pytest-randomly`, `deptry` to `[dependency-groups].dev` in pyproject.toml and refresh uv.lock with `uv lock` (verify only these packages were added; `digital-metrics` entry unchanged)
- [ ] T002 Add `.testmondata*`, `.hypothesis/`, `.coverage`, `tests/integration/.run-tag` to .gitignore (keep existing entries)
- [x] T003 `ruff format --check .` reported all 558 files formatted (2026-11-09); no style commit needed

## Phase 2: Foundational (blocks all stories)

- [ ] T004 Create Taskfile.yml from cveta2's with `RUN` prefix, `TEST_WORKERS` from `CY_TEST_WORKERS` (default 2), tasks `fix`, `_ruff`, `check` (uv lock --check, _ruff, lint-imports, mypy ., vulture, deptry .), `_unit` with TESTMON_ENV hash over `src/clearml_yolo/`, `tests/`, `scripts/` and config files incl. ruff.toml and .importlinter, `test`, `test-full`, `verify` (check → test, no build), `properties`, `infra-check`, `integration`, `_clean-tip`, `acceptance`, `release-acceptance`, `mutation`, placeholders for `paired-check` and `release-commit-check` (bodies from stream B) in Taskfile.yml
- [ ] T005 Create tests/env_isolation.py from cveta2's (fake HOME/XDG, save real env as `CY_REAL_ENV`, delete `GIT_*`, per-PID basetemp under `MUTANT_UNDER_TEST`) keeping `CY_HOME` handling compatible with the existing autouse fixture in tests/conftest.py
- [ ] T006 Update `[tool.pytest.ini_options]` addopts (`-p tests.env_isolation`, `--dist loadgroup`), add `integration` marker, add `[tool.deptry]` config, in pyproject.toml; run `deptry .` and resolve findings by declaring direct dependencies or justified ignores
- [ ] T007 Run `uv run --locked task --exit-code check` and fix failures caused by the new checks only

**Checkpoint**: `task check` passes; streams A–D may start.

## Phase 3: User Story 1 – Development verification at commit time (P1) — Stream B (hooks)

**Independent test**: quickstart steps 1–3.

- [ ] T008 [P] [US1] Port scripts/install-hooks.sh (backup existing hooks, dispatcher for pre-commit and commit-msg, `UV_PROJECT_ENVIRONMENT=$root/.venv`, fallback to `prek hook-impl` for worktrees without Taskfile.yml) in scripts/install-hooks.sh
- [ ] T009 [P] [US1] Port scripts/git-hook.sh staging guard (refuse unstaged tracked changes and nonignored untracked files before prek; never stage, stash or delete) with the research R13 source-override exemption implemented in scripts/source_override.py (+ tests in tests/test_source_override.py) in scripts/git-hook.sh
- [ ] T010 [US1] Rewrite .pre-commit-config.yaml: install types `[pre-commit, commit-msg]`, `fail_fast: true`, keep hygiene hooks and `untracked-sources`, single local serial always-run `verify` hook (`uv run --locked task --exit-code verify`), manual hooks `integration-tests`, `acceptance-tests`, `property-exploration`, `mutmut`, remote `conventional-pre-commit` v4.5.0 commit-msg with types build, chore, ci, docs, feat, fix, perf, refactor, style, test
- [ ] T011 [US1] Install hooks in this worktree with `bash scripts/install-hooks.sh` and run quickstart steps 1–3; record outcomes in the evidence section of this file

## Phase 4: User Story 2 – Change acceptance on a clean tip (P1) — Stream A

**Independent test**: quickstart steps 4–5.

- [ ] T012 [P] [US2] Port tests/integration/lifecycle.py (`check|up|env|stop`, exits 0/3/1/130, `CY_INFRA_CHECK_TIMEOUT` default 60, tag order `INFRA_RUN_TAG` → `.run-tag` → mint via `infra.py newtag --project clearml-yolo --slug integration`, stand env via `clearml.py --project clearml-yolo env`, cleanup via `clearml.py cleanup --prefix <tag>` + `ls --prefix <tag>`, k8s-infra dir from `K8S_INFRA_SKILL_DIR` or `~/.agents/skills/k8s-infra` or `~/.claude/skills/k8s-infra`) in tests/integration/lifecycle.py
- [ ] T013 [P] [US2] Unit tests for lifecycle tag selection, exit-code mapping and refusal on an active foreign tag with the infra scripts substituted, in tests/test_integration_lifecycle.py
- [ ] T014 [US2] Create tests/integration/conftest.py with session `live_run` fixture (prepare, export, finish, fail on incomplete cleanup) and helpers for tagged ClearML project names
- [ ] T015 [US2] In tests/conftest.py: auto-mark items under tests/integration with `integration` and `xdist_group("live")`; assign `xdist_group("serial")` to `ddp_cpu`, `process_capabilities` and supervision tests that fail under xdist; add Hypothesis profiles `clearml-yolo` (deadline None, derandomize, 50 examples) and `explore` (1000) selected by `HYPOTHESIS_PROFILE`
- [ ] T016 [US2] Move tests/test_native_ddp_gpu.py, tests/test_severstal_gpu.py, tests/test_fiftyone_publisher.py, tests/test_fiftyone_panel.py and the env-gated part of tests/test_fiftyone_evaluation_results.py into tests/integration/ (helpers stay in tests/), keeping existing `--run-*` deselection logic working
- [ ] T017 [US2] Write tests/integration/test_cpu_stand_smoke.py per research R6 (synthetic tiny dataset in tmp_path, CPU train 1 epoch small imgsz, tagged project and tags, isolated CY_HOME, assert completed task, output model and evaluation artifacts via ClearML SDK)
- [ ] T018 [US2] Run `task test-full` under xdist with random order several times; fix or serialize order/parallel failures; then measure coverage and set `[tool.coverage.report] fail_under` (patch text to integrator)

## Phase 5: User Story 3 – Release under an exclusive lock (P1) — Stream B (release)

**Independent test**: quickstart step 7.

- [ ] T019 [P] [US3] Create scripts/release_lock_guard.py: compare `uv.lock` at HEAD with the index, require identical `package` entries except `clearml-yolo` whose only difference is `version`; exit 0/1 with a precise message
- [ ] T020 [P] [US3] Unit tests for the guard (root-only version change passes; digital-metrics revision change, added package, removed package fail) in tests/test_release_lock_guard.py
- [ ] T021 [US3] Define `release-commit-check` task body (no unstaged changes, no untracked files, staged paths ⊆ pyproject.toml/uv.lock/CHANGELOG.md, `python scripts/release_lock_guard.py`, `uv lock --check`, `_ruff`, `deptry .`) and `[tool.semantic_release]` `build_command_env=["CY_RELEASE_CHECK"]` + `build_command` (patch text to integrator)
- [ ] T022 [US3] Delete scripts/local_release.py and remove references from pyproject.toml/vulture config

## Phase 6: User Story 4 – Release acceptance and paired release check (P2) — Streams A/B

**Independent test**: quickstart step 8.

- [ ] T023 [US4] Define `paired-check` task body (`CY_QUEUE_DIR` default `../cy-queue`, fail if absent, editable install of both into this venv, `uv pip check`, metadata/version match for both, queue `pytest -q`, `cy-queue --help`, print both SHAs and versions) (patch text to integrator)
- [ ] T024 [US4] Define `release-acceptance` (acceptance → GPU-marked tests with their `--run-*` options from env → FiftyOne with `CY_TEST_FIFTYONE=1` → paired-check) and document the real-run gate as a skill step in Taskfile.yml via integrator

## Phase 7: User Story 5 – Mutation report and session status (P3) — Stream C

**Independent test**: change one function; `task mutation`; `bash scripts/session_status.sh`.

- [ ] T025 [P] [US5] Port scripts/mutation.py (changed lines vs index or `--base`, AST to top-level functions, `git checkout-index` copy, write `only_mutate`, budget 8 functions/120 s, exits 0/1/2, scrub `CLEARML_*`, `INFRA_*`, `CY_RUN_*`, `GIT_*`) in scripts/mutation.py
- [ ] T026 [P] [US5] Unit tests for changed-function mapping and exit statuses in tests/test_mutation_driver.py
- [ ] T027 [US5] Replace `[tool.mutmut]` static targets with `source_paths=["src/clearml_yolo"]` and cveta2-style `pytest_add_cli_args` ignoring tests/integration and architecture tests (patch text to integrator)
- [ ] T028 [P] [US5] Port scripts/session_status.sh (branch vs master, uncommitted paths, worktrees, `clearml-yolo-release.lock`, `.run-tag`; never fails) and register it as SessionStart in .claude/settings.json (merge with existing content)

## Phase 8: Polish — Stream D (docs)

- [ ] T029 [P] Rewrite docs/development.md Verification, Commit procedure and Local releases (Task stages, hooks, acceptance tiers, deferral/waiver, release under flock, recovery); remove stale post-commit and verifier passages; keep weights and external-dependency sections
- [ ] T030 [P] Remove the "no xdist" statement and describe serial groups in docs/ddp-testing.md
- [ ] T031 [P] Add skills .agents/skills/verification-workflow, release, mutation-testing, running-integration-tests (English; reference clearml-yolo-environment and running-end-to-end-tests; no version pins) with .claude/skills discovery via existing symlink
- [ ] T032 [P] Update AGENTS.md commands and skill list; update Russian README.md developer section
- [ ] T033 [P] Write docs/adr/0001-semantic-release-with-flock.md (context, decision, alternatives, consequences, incl. two acceptance tiers)
- [ ] T034 Amend constitution Principle IV wording (Task stages; `prek run --all-files` runs `verify`) with a PATCH governance note in .specify/memory/constitution.md

## Phase 9: Integration and verification

- [ ] T035 Integrator applies stream patch texts to pyproject.toml, Taskfile.yml, .gitignore; `uv lock --check`
- [ ] T036 `task verify`; then commit per stream with Conventional Commits
- [ ] T037 `task mutation -- --base master`; `task acceptance` on the clean tip (report deferral if infra-check exits 3)
- [ ] T038 Release rehearsal in a scratchpad `git clone --local` on branch `master` with a throwaway `fix:` commit (research R14); inspect commit/tag; delete clone; `task paired-check`
- [ ] T039 Fresh independent review of the integrated diff; fix findings; rerun affected checks; `prek run --all-files` with SKIP cleared
- [ ] T040 Record dated evidence (checks, outcomes, deferrals, waivers) below

Design constraints from research R13–R14 (overrides, worktree isolation, real env, FiftyOne placement, coverage/docs-only) apply to all tasks.

## Dependencies

Phase 1 → Phase 2 → {US1, US2, US3, US5, Docs} in parallel → US4 (needs US2 lifecycle, US3 task bodies) → Phase 9.

## Parallel example

After T007: T008+T009 (B), T012+T013 (A), T019+T020 (B), T025+T026+T028 (C), T029–T033 (D).

## MVP

US1 (Phase 3) on top of Phases 1–2.

## Evidence

_(dated entries added during implementation)_
