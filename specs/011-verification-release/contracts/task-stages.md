# Contract: Task stages

Invocation: `uv run --locked task --exit-code <stage>`. All stages use this worktree's tool state.

| Stage | Runs | Live | Notes |
|---|---|---|---|
| `fix` | safe Ruff fixes, `ruff format` | no | never stages |
| `check` | lock check, Ruff check+format check, import-linter, mypy, vulture, deptry | no | |
| `test` / `test-full` | unit suite (testmon affected / all), `--ignore=tests/integration`, xdist | no | |
| `verify` | `check` → `test` | no | pre-commit hook; development verification |
| `properties` | unit suite, Hypothesis `explore` profile, `-p no:randomly` | no | |
| `mutation` | `scripts/mutation.py {{.CLI_ARGS}}` | no | exit 0 ok / 1 strict survivors / 2 tool error |
| `infra-check` | `python -m tests.integration.lifecycle check` | read-only | 0 / 3 / 1 |
| `integration` | `infra-check`, `pytest tests/integration` (non-GPU) | yes | serial `live` group |
| `acceptance` | clean tip → `check` → `properties` → `infra-check` → full suite with coverage → clean tip | yes | change acceptance |
| `release-acceptance` | `acceptance` + GPU-marked tests + FiftyOne + `paired-check` | yes | real-run gate per `running-end-to-end-tests` is a skill step |
| `paired-check` | cy-queue at `CY_QUEUE_DIR` (default `../cy-queue`) | no | records SHAs and versions |
| `release-commit-check` | staged-path allowlist, root-only lock diff, lock check, Ruff read-only, deptry | no | only inside semantic-release `build_command` |
