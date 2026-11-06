# Consolidation verification — 2026-11-06

Result: CPU checks and the review pass. The native gates listed in the [plan](plan.md)
remain open. This task makes no version, tag or GPU execution.

## Environment

- Worktree from master `43de5af`, with dependencies installed by
  `uv sync --frozen --dev` and copied files (`UV_LINK_MODE=copy`).
- `external/` holds plain source copies at the approved revisions: `6e801be`
  (digital-metrics) and `d10aa39` (report-generator).
- There is no `[tool.uv.sources]` section and no lockfile change.

## Checks

| Check | Result |
| --- | --- |
| `ruff check .` | Exit 0 |
| `mypy .` (strict) | Exit 0; no issues in 467 source files |
| `vulture` | Exit 0 |
| `lint-imports` | Exit 0; all contracts kept |
| `pytest` (complete ordinary suite, including architecture negatives and CPU-DDP) | Exit 0; **4,857 passed, 30 skipped, 81 deselected** |
| Focused batch suites after the force fix | 201 passed |
| Architecture validator, plan phase, all eight touched records | Exit 0 |
| Architecture validator, acceptance phase | Exit 0 for this record, 004 and speedup. The force, DINOv3, scoped campaign, campaign-20261102 and accelerator-OOM records stay pending on their declared native checks and review |

The full check list passed in several separate runs. The `scripts/verify.py` wrapper
never recorded a success receipt, because its stat-level input fingerprint reported
drift. An instrumented run of the same commands found no change in the environment,
`sys.path`, inventory, or content and stat identity of all 48,110 inputs.

The user accepted the directly executed results. At the user's direction, the
commit skipped only the `verify` pre-commit hook. All other hooks ran.

## Review

A fresh, independent read-only review of the integrated tree found no blocking
issue. It found one issue that should be fixed: every ordinary catalogue write
added `settings.force: false`, which strict CY 0.45 readers reject. The fix and its
regression test are recorded in the
[force verification](../../../specs/006-batch-training/force/verification.md#ordinary-record-compatibility-fix--2026-11-06).

Four minor items are left as they are. Each is either a UX-only concern or already
disclosed in existing records:
- the HF-only failure message;
- historical test counts for other source states;
- a reused reviewer identifier;
- the still-open 50,000-row result-export parity check.
