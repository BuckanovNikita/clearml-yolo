# Remaining work after CY 0.46.0: completion plan, 2026-11-06

> **Note 2026-11-07:** WP1 (native forced-estimator acceptance), WP2b (architecture
> acceptance for force, DINOv3 and OOM) and WP4 (original campaign recovery) are
> superseded by the [verification-from-zero plan](../verification-from-zero-20261107.md).
> Their partial verification evidence artifacts were dropped; do not cite them as
> acceptance. The ticked WP0, WP2a, WP3 and WP6 boxes below are history, re-verified
> by that plan.

## Purpose and baseline

This plan lists every unfinished item across CY and cy-queue, so that existing work
can be completed and closed. It is the native ledger for the closure tasks below.
Each work package still updates the record that owns its gate.

- **CY:** `master` at `55bd2b0`, version `0.46.0` (tag `v0.46.0` on `60edd4b`).
- **cy-queue:** `main` at `e944a9b`, version `0.1.9`.
- **Branches and worktrees:** both repositories have one branch and no extra worktrees.
- **Pairing:** the paired check passed for CY 0.46.0 with queue 0.1.9.
- **Portable-guide work outside these repositories:** these corp-skills checkouts
  are kept on purpose:
  - `../corp-skills-dinov3-20261105` (branch `docs/dinov3-usage-20261105`, uncommitted);
  - `../cy-force-20261103/portable` (branch `docs/force-batch-20261103`, uncommitted
    `CHANGELOG.md`/`VERSION`).

  Update 2026-11-07: both checkouts, and `../cy-closure-20261104/portable`, are retired;
  the owner removed them after their content was released as corp-skills v0.7.5
  (`11b6866`). See T3.4.

The inventory comes from a read-only audit of every unchecked box, every pending
architecture review and the dated sections of each record (2026-11-06). Items whose
work is already done or superseded are handled by [WP0](#wp0-ledger-reconciliation-offline).
CY 0.46.0 published the force, DINOv3 HF, scoped-campaign and accelerator-OOM runtime
changes before their review and native gates finished; see the 006
[delivery note](../../../specs/006-batch-training/tasks.md#delivery-note-2026-11-06).
These packages are post-release acceptance. If one finds a defect, fix it through a
new bug workflow (`speckit-bug-*`), with its own regression, release and paired check.

## Execution order

| Order | Package | Kind | Depends on |
| --- | --- | --- | --- |
| 1 | WP0 Ledger reconciliation | offline docs | none |
| 2 | WP2a Integrated source review | offline | none |
| 2 | WP3 Portable usage guide for 0.46.0 | offline, plus corp-skills release | none; feeds WP2b |
| 2 | WP6 Instruction-refactor review | offline | none |
| 3 | WP1 Native forced-estimator acceptance | single GPU | WP2a findings resolved |
| 4 | WP2b Architecture acceptance for force, DINOv3 and OOM | offline | WP1, WP2a, WP3 |
| 5 | WP4 Original campaign recovery | single GPU, long | WP1 telemetry blocker decision (T1.1) |

The WP0, WP2a, WP3 and WP6 tasks touch disjoint files and can run in parallel with
exclusive write ownership. The GPU packages run one at a time: there is one GPU
(an RTX 5090), and WP1 and WP4 both need it for long periods.

## WP0: Ledger reconciliation (offline)

Tick or annotate boxes whose work is already done or superseded, citing their
evidence. Do not rewrite dated history; add a short dated note next to the box or
group instead.

- [x] T0.1 CY [006 tasks](../../../specs/006-batch-training/tasks.md):
  - T024: review and ledger parts done, but the box stays open until WP1 closes T031
    and the record's failed `native` check. Residual T022 is waived (T0.8), not passed.
    Evidence: tasks.md "Fresh review" section, the 006 `architecture.json` accepted
    review and `evidence/release.md`.
  - T025: delivered as v0.41.0 through T033–T035.
  - T031: superseded by T064. Record the forced yolo11n confirmation in
    `speedup/verification.md` (2026-11-05). **Decision needed:** does forced
    confirmation satisfy the original strict-idle intent? If not, keep T031 open
    for WP1.
  - T058 and T060: superseded by T064 and T065. T060's release part is done (v0.46.0).
  - T059: pair and README parts done in `c16dbb1` and the 0.46.0 pair. Its
    portable-guide part moves to WP3/T065.
- [x] T0.2 CY [DINOv3 HF fix](../../bugs/dinov3-hf-native/fix.md):
  - `:74` superseded by T064 (fix.md:89-104);
  - `:78` delivered in v0.46.0 (`60edd4b`).
- [x] T0.3 CY [scoped improvements assessment](../../bugs/campaign-scoped-improvements/assessment.md):
  - `:57` closed by test.md:78-111. Confirm this against the conflicting note in
    [cleanup verification](../unfinished-work-cleanup-20261106/verification.md)
    that says 50,000-row parity is still open.
  - `:58` done (test.md:113-120, and the queue `cy-046-compatibility/verification.md`
    committed pair).
  - `:60` delivered in v0.46.0.
- [x] T0.4 CY [campaign assessment](../../bugs/campaign-20261102/assessment.md):
  - `:37`, `:38`, `:39`, `:43` and `:140`–`:153` are superseded by the 2026-11-03
    checkpoint `:166`–`:180`. `:150` and `:153` map to the still-open `:176` and `:180`.
  - `:93`, `:98`, `:100` are done (assessment.md:112-127; test.md:244-276).
  - [fix](../../bugs/campaign-20261102/fix.md) `:137` is done (test.md:433-447,
    plus the 0.46.0 hooks and pair).
- [x] T0.5 CY [agent-instructions plan](../agent-instructions-refactor-20261104/plan.md)
  `:32`: committed as `43de5af` and released in v0.46.0. `:31` stays open (WP6).
- [x] T0.6 In the scoped and force `architecture.json`, the `docs` checks are
  `not-run` but have passing evidence (scoped test.md:71 and :113-120; force
  verification.md:228-235). Re-run `scripts/check_docs.py --all` and record those
  checks as passed with a dated evidence reference. *(2026-11-07: done for the scoped
  record. The force record's `docs` check stays `not-run` with a partial result,
  because the command covers CY Markdown only; WP2b revisits it.)*
- [x] T0.8 CY [006 tasks](../../../specs/006-batch-training/tasks.md) T022, and the
  `ddp-native` check in the 006 architecture record: annotate them as **waived by
  user decision (2026-11-06)**. Record that physical multi-GPU DDP verification will
  not be done here. Do not mark them passed. cy-queue's seven `ddp_gpu` opt-ins stay
  deselected and are recorded the same way in the queue's dated evidence.
- [x] T0.7 cy-queue:
  - `docs/plans/2026-10-30-gpu-memory-threshold/plan.md:46`: done. Evidence: CY T046
    and CY `specs/006-batch-training/speedup/verification.md:157-166` (v0.44.4,
    queue `2fbaed2`).
  - Add a one-line "superseded by plan.md" note to
    `docs/plans/cy-046-compatibility/preparation-plan.md`. Leave the file otherwise
    unchanged.

**Acceptance:** `scripts/check_docs.py --all` passes in both repositories. Validate
the touched `architecture.json` files with `--phase plan`. Make one docs-only commit
per repository (no release) through the hooks, then push.

## WP2a: Fresh integrated source review (offline)

- [x] T2a.1 Run a fresh independent review of the runtime diff `v0.45.1..v0.46.0`
  (`git diff v0.45.1 v0.46.0 -- src tests`). It covers:
  - forced admission and the persisted `settings.force` policy, including the
    post-review omission fix and its regression;
  - DINOv3 HF weight preparation and conversion (`adapters/deim/hf_weights.py`);
  - accelerator-OOM receipts;
  - the scoped campaign export changes.

  Give the reviewer the code, the four bug/feature records, and the project rules
  (constitution, `docs/project-contracts.md`).
- [x] T2a.2 Resolve the findings. A runtime defect becomes a `speckit-bug-*` record
  with a failing regression first, then a fix, the full suite, a patch release and
  the paired check.
- [x] T2a.3 Record the verdict in `docs/bugs/dinov3-hf-native/review.md`, in a
  `review.md` for accelerator-oom-receipts and campaign-scoped-improvements, and in
  the force record (`specs/006-batch-training/force/verification.md`).
- [x] T2a.4 Accept the scoped campaign architecture record. It has no native gate.
  After T0.6, validate it with `--phase acceptance` and tick
  [scoped assessment](../../bugs/campaign-scoped-improvements/assessment.md) `:59`
  once WP3 lands.

## WP3: Portable usage guide for CY 0.46.0 (offline)

The corp-skills `skills/clearml-yolo` main branch (`0a3ed5e`, collection v0.7.4) still
describes `--force` as unreleased and says "CY 0.45.0 has no --force"
(`references/usage.md:477-494, :540`).

- [x] T3.1 Inventory both corp-skills checkouts named in the
  [baseline](#purpose-and-baseline). Snapshot their diffs and untracked files outside
  the repository before any change.
- [x] T3.2 On a fresh branch from corp-skills `main`:
  - fold in the DINOv3 HF guidance (`usage.md`, `evaluation.md` and the
    `verification/dinov3-selected-20261105/` evidence);
  - fold in the force guidance;
  - state CY 0.46.0 as the version that ships `--force`, its
    `forced/background-sensitive` labelling and the reader-upgrade requirement;
  - follow [batch estimation](../../batch-estimation.md) as the authoritative source.
- [x] T3.3 Validate with the corp-skills MAINTENANCE checks, then release corp-skills
  through its own workflow (Git-only, authorized push).
- [x] T3.4 Remove the two superseded corp-skills checkouts only after their content
  is confirmed on corp-skills `main`. Done 2026-11-07: the owner removed
  `../corp-skills-dinov3-20261105`, `../cy-force-20261103/portable` and
  `../cy-closure-20261104/portable` after their content was released as corp-skills
  v0.7.5 (`11b6866`). The T3.1 snapshots are kept in the owner's cleanup archive.
- [x] T3.5 Record the corp-skills commit and version in a dated section of
  `specs/006-batch-training/force/verification.md`. Mark the portable part of T065
  done.

## WP6: Instruction-refactor review (offline, small)

- [x] T6.1 Run a fresh read-only review of `43de5af` (AGENTS.md, skills and
  references) against the rule-preservation acceptance in its
  [plan](../agent-instructions-refactor-20261104/plan.md).
- [x] T6.2 Check skill discovery in a fresh Claude session and a fresh Codex session.
  Done 2026-11-07: both hosts listed the 19 project skills; see the
  [verification update](../agent-instructions-refactor-20261104/verification-2026-11-05.md#update-2026-11-07-fresh-session-skill-discovery).
- [x] T6.3 Tick plan `:31` and update the "Pending" list in its
  `verification-2026-11-05.md`.

## WP1: Native forced-estimator acceptance (single GPU)

This covers 006 T064, the DINOv3 `estimator` check, the accelerator-OOM `native`
check, the force `native` check and assessment `:49`.

**Prerequisites:**

- frozen CY `v0.46.0` source, plus any WP2a patch release, with the queue pair
  verified;
- a Hugging Face token with the gated `facebook/dinov3-*` license accepted;
- the ClearML stand per the `clearml-yolo-environment` skill (tagged project and
  run identity, and cleanup);
- a cy-queue GPU reservation or an agreed GPU window. Follow pcboard;
  `queue.max_used_memory_gib = 12.0` is the admission threshold.

Tasks:

- [x] T1.1 **Blocker.** Diagnose the selected-L telemetry failure: the helper hits
  ENOMEM, exits 255, and the 15 s `nvidia-smi` query times out (accelerator-oom
  test.md:41-51, :70-77; DINOv3 test.md:307-325). Do not relax deadlines or shrink
  the workload. A code defect follows the bug workflow with a regression.
  *(2026-11-07: diagnosed as environmental and reproduced 3 of 3 in
  [selected-l-telemetry-loss](../../bugs/selected-l-telemetry-loss/assessment.md).
  The batch-8 L trial oversubscribes device memory into Windows shared memory
  (about 92 GB). The WSL GPU driver path then becomes unavailable for about 12 s.
  This is not a CY defect, and no fix or release was made. **WP1 (T1.2–T1.4) and
  WP4 stay blocked** until the user chooses one of the record's three options:
  a sysmem-fallback driver setting, an allocator budget cap as a contract change,
  or an accepted gap. 2026-11-07: the user applied the driver setting (option 1).
  A guarded probe showed that WSL2 CUDA does not honour it in the current VM and
  driver session, so WP1 and WP4 stay blocked.
  The remaining choice is option 2 or option 3.)*
- [ ] T1.2 Run a fresh forced estimate of the selected DEIMv2 L/X models
  (`cy-batch-estimate --force`) with raw optimizer receipts. Each model must end in
  either a freshly confirmed winner or a raw-proven minimum-eight `no_capacity`
  (DINOv3 test.md:276-296).
- [ ] T1.3 Replay the X `AcceleratorError` (code 2) case and verify the corrected
  OOM receipt, owned-process cleanup and reservation release.
- [ ] T1.4 Run the full 64-model forced catalogue on the final source. Record every
  failed or interrupted case as a gap. Do not invent capacity.
- [ ] T1.5 Record dated evidence:
  - `specs/006-batch-training/force/verification.md`;
  - `docs/bugs/dinov3-hf-native/test.md`;
  - `docs/bugs/accelerator-oom-receipts/test.md`.

  Then tick 006 T064 (and T031 if T0.1 keeps it open), and accelerator-oom
  assessment `:49`.

**Acceptance:**

- native exit codes and raw receipts for every selected model;
- a catalogue report covering all 64 models;
- cleanup verified;
- ClearML objects removed by run tag.

Mocked tests do not count as evidence here
([end-to-end skill](../../../.agents/skills/running-end-to-end-tests/SKILL.md)).

## WP2b: Architecture acceptance for force, DINOv3 and OOM (offline, after WP1)

- [ ] T2b.1 Reconcile the final diff and the WP1 evidence with
  `specs/006-batch-training/force/architecture.json` and with
  `docs/bugs/{dinov3-hf-native,accelerator-oom-receipts}/architecture.json`. Set
  check results and an accepted review, then validate with `--phase acceptance`.
- [ ] T2b.2 Tick:
  - 006 T065 (all parts);
  - the DINOv3 fix `:77`;
  - accelerator-oom assessment `:50`.

  Update the "Open gates" section of the
  [cleanup plan](../unfinished-work-cleanup-20261106/plan.md).

## WP4: Original campaign recovery (single GPU, long)

Bug [campaign-20261102](../../bugs/campaign-20261102/assessment.md) covers
assessment `:176`, `:178`, `:180` and fix `:138`, `:139`, plus the architecture
checks `native-matrix` (no result) and `sigill-sequence` (failed).

Current state: on current source, 7 of 20 cases are accepted. Four original-AMP
numerical failures are preserved. The Faster R-CNN R50-FPN case was interrupted by
a host reboot. SIGILL (exit 132) is unresolved (test.md:488-541). The number of
cases never attempted on current source is about 8; it is inferred, so confirm it
first.

**Prerequisites:** a user decision resolving the WP1 telemetry blocker diagnosed in T1.1, the ClearML stand, the private
campaign tooling and the `resume-20261105-postboot` evidence (personal-automations
"CY campaign" profile and the manual CY repair), and GPU windows. The SIGILL
repetitions need CPU time; follow pcboard throttling.

- [ ] T4.1 Re-audit the 20-case matrix on the current source. List accepted cases,
  failed cases, interrupted cases and cases never attempted, with identities.
- [ ] T4.2 Rerun Faster R-CNN R50-FPN and every case not yet attempted with fresh
  identities and the original AMP settings.
- [ ] T4.3 Diagnose each numerical failure against its own pinned native path. Fix
  demonstrated defects through regressions. A passing diagnostic is not a repair;
  scientific settings stay unchanged.
- [ ] T4.4 Repeat the retained SIGILL sequence three times with full collection.
  Either resolve it with a regression, or record a bounded and explicit open
  limitation.
- [ ] T4.5 Check eligibility of the 15 blocked arms, re-audit, and re-validate
  architecture acceptance. If code changed: full suite, patch release, paired check.
- [ ] T4.6 Close the campaign record (`test.md`, `assessment.md`, `fix.md`,
  `architecture.json`) and the cleanup plan's open gates.

## Dropped: physical multi-GPU acceptance

On 2026-11-06 the user decided that physical multi-GPU (DDP) verification is not to
be attempted. This covers CY 006 T022, the 16 T026 DDP scenarios, the `ddp-native`
check and the queue's seven `ddp_gpu` opt-ins. They are waived, not passed:
T0.8 records the decision, and no package plans them.

## Completion definition

All existing work is finished when:

- every box in this plan is ticked, or recorded as an explicit and accepted limitation;
- no `architecture.json` in either repository is left with a `pending` review;
- the cleanup plan's "Open gates" list is empty, apart from the waived multi-GPU gates;
- both repositories are clean, have one branch each and are pushed;
- the last release (if any) passed the paired CY/queue check.

## Architecture

This plan is planning documentation only. See [architecture.json](architecture.json)
(impact `none`). Runtime work that comes out of a package uses its owning record.
New defects get new bug records with module-impact architecture.

## Progress — 2026-11-07

Phase 1 landed on `master` (WP0, WP6 and WP2a branches) and cy-queue `main` (WP0).

- **T0.1:** reconciled in 006 [tasks.md](../../../specs/006-batch-training/tasks.md#ledger-reconciliation-2026-11-07).
  T024 stays open until WP1 closes T031 and the native check; T022 is waived.
- **T2a.1:** the per-topic lenses and an independent rules lens approved the
  `v0.45.1..v0.46.0` runtime diff; see the
  [DINOv3 review record](../../bugs/dinov3-hf-native/review.md#independent-rules-lens--2026-11-07).
  The one defect found is
  [dinov3-cache-reload-errors](../../bugs/dinov3-cache-reload-errors/review.md).
- **T2a.4:** the scoped campaign
  [architecture record](../../bugs/campaign-scoped-improvements/architecture.json)
  passes `--phase acceptance`; its review cites the WP2a review and the rules lens.
- **T3.1–T3.3:** corp-skills `main` `11b6866`, collection v0.7.5 (annotated tag
  pushed; Git only). T3.5 is recorded in the
  [force verification](../../../specs/006-batch-training/force/verification.md#portable-usage-guide-release--2026-11-07).
- **Open for the owner:** T3.4 (remove the superseded corp-skills checkouts) and T6.2
  (fresh-session skill discovery); both closed later on 2026-11-07, see the task notes.
  T2a.2 is closed: CY 0.46.1 (`v0.46.1`) passed the paired
  check with cy-queue 0.1.9 `0c486b5`; see the
  [bug verification](../../bugs/dinov3-cache-reload-errors/test.md#release-and-paired-check--2026-11-07).
