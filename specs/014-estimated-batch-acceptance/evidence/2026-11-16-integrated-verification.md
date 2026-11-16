# Integrated verification — 2026-11-16

## Full unit baseline

The resumed native `task coverage` stage passed with **4,766 passed, one skipped**,
400 warnings, in 573.62 seconds. Branch-inclusive coverage was **84.67%**, exceeding
the configured 84.12% floor. The command used the locked environment, two pytest
workers, CPU-only CUDA visibility and two library threads at low scheduling priority.
It included native CPU process/distributed regressions; it establishes no physical
GPU, multi-GPU, service publication or detector-quality outcome.

All 33 captured implementation/document/test inputs match committed content
`4b73f6227e789e17b3431f4de1039c1351890862` in the isolated verification worktree.
The source mapping and local log SHA-256 are in `2026-11-16-coverage-inputs.json`.
The retained local log is `.tmp/verification-gap-closure/coverage-2026-11-16-resumed.log`.
Earlier interrupted runs remain incomplete and are not substituted for this pass.

## Subsequent localized correction

Tickets 96 and 97 correct the YOLO probe's native deterministic initialization and
concrete candidate-batch binding after this baseline. Its focused execution, state-restoration tests and independent review
supplement the baseline for that changed boundary. The full-run coverage percentage
above describes the captured pre-96 content, not an independently measured new
percentage after those corrections. Unchanged shared runtime, other backend and
ownership evidence remains reusable. Final automatic verification and representative
GPU/publication acceptance are still required before integration and completion.

## Resource and commit scope

The coordinator renewed owned services through the native lifecycle after proving
the previous environment absent. Separate renewal evidence records current identities
and independent ClearML/FiftyOne restoration checks. Shared fixtures and model assets
remain retained for downstream consumers. Intermediate local commits preserve
Conventional Commit validation and the staging guard; their `verify` hook is deferred
until the final canonical pass. Captured-log whitespace fixes are a separate commit.
No push, deployment or release is authorized or performed.

## Final automatic gate through ticket97

**Passed**: the canonical automatic command, with `SKIP`, `PREK_SKIP`,
`CY_VERIFY_SCOPE` and `PRE_COMMIT_ALLOW_NO_CONFIG` cleared, exited zero on
`fbcfa251e4b26ffd786d2e4cb72174fa4fe8606a` in the prepared managed worktree.
Its log records `Task change-aware verification ... Passed`; the worktree remained
clean. The root live-attempt receipt independently matched all 459 tracked Python
files and the lockfile to that commit. The failed reserve-limited GPU attempt is
recorded in `2026-11-16-gpu-retry.md`, with ticket98 owning the newly observed
CUDA/whole-device accounting discrepancy. The automatic gate does not convert that
live failure into an accepted outcome; affected checks must follow ticket98.
