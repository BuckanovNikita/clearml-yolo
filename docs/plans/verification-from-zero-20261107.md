# Verification from zero, 2026-11-07

## Why

On 2026-11-07 the user merged all started, unfinished and non-cancelled work into
each repository's default branch without verification. Earlier partial verification
evidence (the open WP1, WP2b and WP4 packages of the
[remaining-work plan](remaining-work-20261106/plan.md) and their in-progress
artifacts) is dropped. Nothing merged on or before that date counts as accepted
until this checklist passes from a clean checkout.

For CY nothing was pending on 2026-11-07: no local branches, stashes or extra
worktrees held unmerged work, so the merge step added only this plan and the
supersession note.

## Range

- **Root:** `e4ec105` (first commit).
- **Head under verification:** `1abc844` (`master` tip at the 2026-11-07 merge),
  plus the docs-only commit that adds this plan.
- Verify the whole range `e4ec105..<head>`, not only the latest diff.

## Supersedes

- [Remaining work, 2026-11-06](remaining-work-20261106/plan.md): WP1, WP2b and WP4
  (and the residual gates of WP0, WP2a, WP3 and WP6, which are re-verified here).
- [Unfinished work consolidation, 2026-11-06](unfinished-work-cleanup-20261106/plan.md)
  and its [verification](unfinished-work-cleanup-20261106/verification.md): its
  "Open gates" list.
- [Agent-instructions refactor, 2026-11-04](agent-instructions-refactor-20261104/plan.md)
  verification and review records (`verification-2026-11-05.md`, `review-2026-11-07.md`).
- [Claude/Codex organization, 2026-11-02](claude-codex-organization-20261102/plan.md)
  verification (`verification-2026-11-02.md`).
- Open native and acceptance gates in `specs/006-batch-training/` (tasks T024, T031,
  T064, T065; `force/verification.md`, `speedup/verification.md`) and in
  `docs/bugs/{dinov3-hf-native,accelerator-oom-receipts,campaign-20261102,selected-l-telemetry-loss}/`.

Dated history in those files stays; this plan only replaces their open checklists.

## Checklist

Run every step in order from a fresh clone at the head above. Record dated results
(commands, exit codes, SHAs, versions) in a new `verification-from-zero-20261107/`
evidence directory next to this file. A failure becomes a `speckit-bug-*` record
with a failing regression first; do not relax thresholds or shrink workloads.

### 1. Setup

- [ ] 1.1 Fresh `git clone` of `origin/master`; confirm `git status` is clean and the
  head SHA matches.
- [ ] 1.2 Provision the approved external sources (`external/digital-metrics`,
  `external/report-generator`) at their recorded revisions.
- [ ] 1.3 `uv sync --frozen`, then `uv pip check`; record Python, uv and lock hash.
- [ ] 1.4 Install the hooks with `scripts/local_release.py --install-hooks`.

### 2. Lint, types and import contracts

- [ ] 2.1 `uv run --frozen --no-sync ruff check .`
- [ ] 2.2 `uv run --frozen --no-sync mypy .` (strict)
- [ ] 2.3 `uv run --frozen --no-sync vulture`
- [ ] 2.4 `uv run --frozen --no-sync lint-imports`, including a negative case that a
  prohibited edge fails.

### 3. Full suite

- [ ] 3.1 `env -u PYTEST_ADDOPTS uv run --frozen --no-sync pytest --testmon-noselect`
  (complete suite, including architecture negative cases and native CPU-DDP `ddp_cpu`).
- [ ] 3.2 Record pass, skip and deselect counts; justify every skip.

### 4. Documented gates

- [ ] 4.1 `uv run --frozen --no-sync python scripts/check_docs.py --all`.
- [ ] 4.2 `uv run --frozen --no-sync prek run --all-files`.
- [ ] 4.3 Scoped mutation acceptance: `mutmut run 'clearml_yolo.core.*'` and
  `mutmut results` for the `[tool.mutmut]` targets; triage every survivor.

### 5. Native and GPU acceptance (single RTX 5090, follow pcboard)

Prerequisites: Hugging Face token with the gated `facebook/dinov3-*` license, the
ClearML stand per the `clearml-yolo-environment` skill (tagged project and run
identity), a cy-queue GPU reservation (`queue.max_used_memory_gib = 12.0`).

- [ ] 5.1 **WSL2 sysmem-fallback hazard.** Before any large trial, confirm whether
  WSL2 CUDA honours the "prefer no sysmem fallback" driver setting in the current VM
  and driver session (it did not on 2026-11-07,
  [selected-l-telemetry-loss](../bugs/selected-l-telemetry-loss/assessment.md)).
  Run every GPU step under a memory watchdog that aborts the trial and records the
  receipt when device memory spills into Windows shared memory, so the WSL GPU path
  does not drop out. Resolve the open choice (allocator budget cap as a contract
  change, or an accepted gap) before 5.3.
- [ ] 5.2 **DINOv3 HF.** Fresh weight preparation and conversion
  (`adapters/deim/hf_weights.py`) from an empty cache, including the cache-reload
  error paths fixed in CY 0.46.1; record the DINOv3 `estimator` check.
- [ ] 5.3 **Forced estimator, selected models.** `cy-batch-estimate --force` on the
  selected DEIMv2 L/X models with raw optimizer receipts; each ends in a freshly
  confirmed winner or a raw-proven minimum-eight `no_capacity`.
- [ ] 5.4 **Accelerator OOM.** Replay the X `AcceleratorError` (code 2) case; verify
  the OOM receipt, owned-process cleanup and reservation release.
- [ ] 5.5 **Forced-estimator catalogue.** Run the full 64-model forced catalogue on
  the head source; record every failed or interrupted case as a gap.
- [ ] 5.6 **Original campaign recovery from scratch.** Re-audit the 20-case
  [campaign](../bugs/campaign-20261102/assessment.md) matrix with fresh identities
  and the original AMP settings; rerun every case (no earlier case counts as
  accepted); diagnose numerical failures against their pinned native paths; repeat
  the SIGILL (exit 132) sequence three times with full collection; check the 15
  blocked arms.
- [ ] 5.7 Remove ClearML objects by run tag and verify GPU and reservation cleanup.

### 6. Architecture and record acceptance

- [ ] 6.1 Reconcile the full diff with every `architecture.json` under `specs/`,
  `docs/bugs/` and `docs/plans/`; validate each with the shared
  `validate_architecture.py --phase acceptance`. No record may stay `pending`.
- [ ] 6.2 Close or explicitly limit the open boxes in 006 `tasks.md`, the DINOv3,
  accelerator-oom, campaign and telemetry-loss records. Multi-GPU DDP (T022, T026,
  `ddp-native`) stays waived by the 2026-11-06 user decision, not passed.
- [ ] 6.3 A fresh independent review of the integrated range after these steps.

### 7. Release and pairing

- [ ] 7.1 Any code fix: full suite, patch release through `scripts/local_release.py`
  on `master` (Git tag only, no GitHub Release objects or registry uploads).
- [ ] 7.2 Paired CY/cy-queue check per
  [development](../development.md#paired-cy-and-queue-release-check) against the
  latest fetched cy-queue `main`; record both SHAs and versions.
- [ ] 7.3 Portable guide: confirm corp-skills `skills/clearml-yolo` matches the
  released CY version.
- [ ] 7.4 Repository clean, one branch, pushed.
