# Bug Verification: Default queue worker diagnostics

- **Slug**: queue-default-logs (from assessment/fix context)
- **Tested**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Fix**: [fix.md](fix.md)
- **Result**: verified — original failure path and required behavior/architecture checks pass; delivery pending.

## Original failure path

A real empty-queue worker registered and exited on SIGTERM with no stderr before
implementation; the new default-output regression failed on that empty string.
After implementation the same subprocess path emits startup/root, immediate idle
heartbeat and orderly shutdown, exits zero, clears its registration and leaves
stdout empty. DEBUG exposes polling; WARNING suppresses routine output.

## Executed checks

Commands used the existing prepared Python 3.12.13 environment with uv no-sync and
this checkout's source import path. No dependency resolution or upstream changes.

| Check | Result |
| --- | --- |
| Initial focused queue commands/service/logging | 48 passed; four existing Hydra/Pydantic deprecation warnings. |
| Final `pytest tests/test_queue_logging.py -q` | 7 passed; real CLI, waiting through storage, deduplication/heartbeat, redaction, historical completion and failed-worker cleanup. |
| `uv run --frozen --no-sync lint-imports` | 43 contracts kept, zero broken. |
| `uv run --frozen --no-sync pytest tests/test_architecture.py` | 104 passed; includes injected forbidden logging/adapter edges and dynamic/initializer checks. |
| Ruff / Vulture | Passed. |
| Mypy | Passed, 318 checked files; first test-only re-export error corrected and rerun. |
| `uv build --no-sources` | Source distribution and wheel built successfully with uv_build; unpublished. |
| Actual `cy-queue worker --help` | Correct INFO default and DEBUG/INFO/WARNING/ERROR choices. |
| Markdownlint 0.41.1 | Five changed/new Markdown documents passed with MD013 disabled for existing prose/table style. |
| Local Markdown links/anchors | Five files: 33 valid local targets/anchors. |
| `git diff --check` | Passed. |
| `uv run pre-commit run --all-files` | Full pytest hook passed, along with Ruff, imports, Vulture and file hygiene. The wrapper initially exited 1 for expected generated changelog changes and the test typing issue; the latter passed on rerun, and changelog output was reviewed for staging. |

## Documentation and review

Companion corp-skills source started at `e5c6512`, version 0.2.2; the planned patch
is 0.2.3. Its usage/evaluation references document the actual CLI and child log
location. Metadata, discovery, Markdown and packaged links were checked. Fresh
baseline evaluation exposed the previous gaps. Fresh independent reviewer `/root/final_review` returned **ship** after inspecting
the complete application and companion diffs, module contracts, source behavior
and recorded passing checks. The updated explanation-only usage prompt passed:
INFO/idle/waiting/DEBUG and the exact child log path were retrieved without
starting workloads. The reviewer identified one record reconciliation detail:
`core.redaction` is now included in the CLI allowed dependencies. The parent subsequently observed the full pytest hook pass; native commit and
release gates remain parent-owned. Requested reviewer settings were GPT-6.1 Sol,
high effort; actual runtime model settings are not exposed.

The queue application remains free of Loguru and concrete infrastructure. Its
optional callback receives public QueueView values; the CLI owns rendering and
log policy. Storage/process effects, GPU policy, persisted records, TUI and stdout
formats remain unchanged. Final reconciliation covers the two production modules, new logging tests, README,
queue guide, bug artifacts and native generated changelog. No dependency or
composition-target changes were introduced. The record explicitly includes the
redaction dependency identified during review. All planned implementation, check
and documentation tasks are complete; Git delivery remains separate.

## Scope and limitations

This is logging acceptance, not GPU training or remote ClearML acceptance. The
real idle worker and local queue/process tests do not establish new GPU or upload
outcomes. Existing upstream deprecation warnings are retained. No services or
pre-existing jobs were stopped. Only task-owned subprocesses were terminated.

## Delivery

Pending verified contributor commit, isolated master integration and native Git-tag
release. The original main checkout's unrelated staged compatibility work and local
dependency configuration are excluded and preserved. No registry publishing,
GitHub Release, assets or skill installation is requested.
