# Research: Verification and Release Workflow

Source of truth for adapted files: `/mnt/wsl/data/nkt/cveta2` at `0fa3310`.

## R1. Command owner
- **Decision**: `Taskfile.yml` copied from cveta2 with no `sources`/`status`; `RUN` prefix pins
  `UV_PROJECT_ENVIRONMENT`, `TESTMON_DATAFILE`, `COVERAGE_FILE`, `RUFF_CACHE_DIR`,
  `MYPY_CACHE_DIR` to the worktree; workers from `CY_TEST_WORKERS` (default 2). Invocation:
  `uv run --locked task --exit-code <stage>`. `check` = `uv lock --check`, ruff check + format
  check, `lint-imports`, `mypy .`, `vulture`, `deptry .`. No `build` task.
- **Rationale**: Spec FR-001–FR-003; CY forbids routine distribution builds.
- **Alternatives**: keep per-tool prek hooks (rejected by user); Make (no parity with cveta2).

## R2. Ruff format
- **Decision**: `fix` runs `ruff check --fix --no-unsafe-fixes .` and `ruff format .`; `check`
  includes `ruff format --check .`. If the tree is not yet formatted, a separate mechanical
  `style:` commit formats it first.
- **Rationale**: cveta2 parity; global rule to commit formatting separately.

## R3. Affected-test namespace
- **Decision**: Port cveta2's `_unit` `TESTMON_ENV` hash; package dir `src/clearml_yolo/`
  replaces `cveta2/`; config set adds `ruff.toml`, `.importlinter`. Unit runs use
  `--ignore=tests/integration`.

## R4. Parallel and random order
- **Decision**: add `pytest-xdist`, `pytest-randomly`; addopts gain `-p tests.env_isolation`;
  Task passes `-n W --dist loadgroup`. `tests/conftest.py` assigns `xdist_group("serial")` to
  `ddp_cpu`, `process_capabilities` and Linux process/supervision modules (identified by
  running the suite under xdist and fixing failures), `xdist_group("live")` to
  `tests/integration`. Fallback: one serial group if DDP flakes. Remove the "no xdist" note.

## R5. Live tests and lifecycle
- **Decision**: move `test_native_ddp_gpu.py`, `test_severstal_gpu.py`, the FiftyOne native
  database tests (env-gated portions; split `test_fiftyone_evaluation_results.py`) to
  `tests/integration/`; helpers they import stay in `tests/`. `tests/integration/lifecycle.py`
  ports cveta2's `check|up|env|stop` (exit 0/3/1/130) with `PROJECT="clearml-yolo"`,
  `.run-tag`, and stand access by invoking the k8s-infra scripts the same way
  `.agents/skills/clearml-yolo-environment/scripts/agent_env.sh` does (`infra.py room`,
  `clearml.py --project clearml-yolo env`, `infra.py newtag`), cleanup via `clearml.py cleanup
  --prefix <tag>` then `ls --prefix <tag>`. The environment skill scripts remain for manual runs.
- **GPU/FiftyOne gating**: GPU-marked tests stay deselected unless their `--run-*` flags are
  given (by `release-acceptance`); `release-acceptance` checks GPU idleness via pcboard status
  where available and reports deferral rather than starting.

## R6. CPU stand smoke test (user decision 2026-11-09)
- **Decision**: `tests/integration/test_cpu_stand_smoke.py`: synthesize a tiny YOLO dataset in
  `tmp_path` (few images, disjoint val/test, one empty image per split), write ground truth,
  run the top-level `ultralytics` application on CPU (1 epoch, small `imgsz`, local
  `yolo11n.pt` or downloaded weight per weights manifest) with
  `clearml.project_name="<tag> clearml-yolo"`, `clearml.tags=[<tag>]`, isolated `CY_HOME`; then
  assert via the ClearML SDK that the tagged task completed and published its output model
  and evaluation artifacts. Cleanup by exact tag in the session fixture.
- **Alternatives**: FiftyOne only; no live part (both rejected by user).

## R7. Release mechanism
- **Decision**: `[tool.semantic_release]` keeps current settings (`master`, `v{version}`,
  `major_on_zero=false`, changelog exclusions) and adds `build_command_env=["CY_RELEASE_CHECK"]`
  and `build_command`: `uv lock --upgrade-package clearml-yolo`, `git add uv.lock`, and when
  `CY_RELEASE_CHECK=1`, `git add pyproject.toml CHANGELOG.md` then
  `uv run --locked task --exit-code release-commit-check`. Commit with `SKIP=verify`.
- **Lock entry guard**: `release-commit-check` compares `git show HEAD:uv.lock` with the index
  via a small inline Python step: parse both TOML documents and require that all `package`
  entries other than `clearml-yolo` are identical and only its `version` differs.
- **Release lock**: `flock -n "$(git rev-parse --git-common-dir)/clearml-yolo-release.lock"`
  around fetch, `merge --ff-only`, version, push, as in cveta2's release skill.
- **Remove**: `scripts/local_release.py`, its recovery record and `HEAVY_HOOKS`.
- **Risk**: `uv lock --upgrade-package` requires `external/` trees; the guard catches drift.

## R8. Hooks
- **Decision**: `.pre-commit-config.yaml`: `default_install_hook_types: [pre-commit, commit-msg]`,
  `fail_fast: true`; local `verify` (serial, always_run), manual `integration-tests`,
  `acceptance-tests`, `property-exploration`, `mutmut`; remote `conventional-pre-commit`
  (cveta2's rev and types). Hygiene hooks (large files, merge conflict, toml/yaml, EOF,
  whitespace) and `untracked-sources` are retained before `verify` since they are cheap
  and CY-specific. `scripts/install-hooks.sh` / `scripts/git-hook.sh` ported.

## R9. Coverage and deptry
- **Decision**: measure `pytest --cov` once on the branch; set `fail_under` to the floor
  (rounded down to an integer). Configure deptry with known optional/editable packages; resolve
  real findings by declaring direct dependencies (constitution rule) rather than ignoring.

## R10. Paired release check
- **Decision**: `paired-check` task reads `CY_QUEUE_DIR` (default `../cy-queue`), fails if
  absent, installs both editable into this worktree's venv, runs `uv pip check`, compares
  `pyproject` versions with `importlib.metadata` for both, runs the queue suite and
  `cy-queue --help`, and prints both SHAs and versions.

## R11. Mutation
- **Decision**: port `scripts/mutation.py`; `source_paths=["src/clearml_yolo"]`; drop the static
  `only_mutate` list from `[tool.mutmut]`; ignore `tests/integration` and architecture tests;
  scrub `CLEARML_*`, `INFRA_*`, `CY_RUN_*`, `GIT_*` from the child env.

## R12. Session status
- **Decision**: port `scripts/session_status.sh` (branch vs `master`, release lock
  `clearml-yolo-release.lock`, `.run-tag`); register in `.claude/settings.json` SessionStart.
