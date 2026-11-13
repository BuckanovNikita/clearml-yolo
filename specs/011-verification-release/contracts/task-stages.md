# Contract: Task stages

Invocation: `uv run --locked task --exit-code <stage>`. All stages use this worktree's tool state. Development commands live in the root
Taskfile; `Taskfile.ops.yml` supplies the operational stages through a flattened include.

| Stage | Runs | Live | Notes |
|---|---|---|---|
| `local-deps` | sdists of `external/digital-metrics` and `external/report-generator` into `external/wheelhouse`; creates `uv.toml` find-links when absent | no | development-only archives; bootstrap with `uvx --from go-task-bin task local-deps` |
| `fix` | safe Ruff fixes, `ruff format` | no | never stages |
| `check` | `uv lock --check`, Ruff check+format check, import-linter, mypy, vulture, deptry | no | |
| `test` / `test-full` | unit suite (testmon affected / all), `--ignore=tests/integration`, xdist | no | |
| `coverage` | complete unit suite with branch coverage and configured floor | no | |
| `verify` | `check` → `test` | no | pre-commit hook; development verification |
| `properties` | unit suite, Hypothesis `explore` profile, `-p no:randomly` | no | |
| `mutation` | `scripts/mutation.py {{.CLI_ARGS}}` | no | exit 0 ok / 1 strict survivors / 2 tool error |
| `infra-check` | `python -m tests.integration.lifecycle check` | read-only | 0 / 3 / 1 |
| `integration` | `infra-check`, `pytest tests/integration` (non-GPU) | yes | serial `live` group |
| `acceptance` | clean tip (record HEAD) → `check` → `properties` → `infra-check` (exit 3 = deferred) → unit suite with coverage floor → `integration` → clean tip and unchanged HEAD | yes | change acceptance; preflight and live part skipped for documentation-only changes |
| `release-acceptance` | `acceptance` + Severstal single-GPU suite (`CY_SEVERSTAL_ARGS`, required) + multi-GPU DDP (`CY_DDP_ARGS`; waived when unset) with `CY_TASK_VERIFICATION=1` + FiftyOne in a temporary database + `paired-check` | yes | real-run gate per `running-end-to-end-tests` is a skill step; busy GPU (pcboard) = deferred |
| `paired-check` | cy-queue at `CY_QUEUE_DIR` (default `../cy-queue`) in a temporary venv | no | records SHAs and versions; never modifies `.venv` |
| `release-commit-check` | staged-path allowlist, root-only lock diff, lock check, Ruff read-only, deptry | no | only inside semantic-release `build_command` |
