# Campaign repair assessment

- Slug: campaign-20261102 (from approved plan).
- Date: 2026-11-02.
- Source: retained private FAILURES.md, failures.json and original runner logs.
- Verdict: valid publication/runtime defects; native numerical causes need reproduction.
- Severity: high, incomplete screening coverage.

## Contract and evidence

20 technical failures: 2 ClearML requests above the 15 MiB client limit; 4 YOLO
runs with NaN native validation losses; 1 FCOS nonfinite training loss; 13 native
510-second timeouts. One operator stop is excluded. The 15 dependent blocked jobs
need eligibility checks only; eight pending jobs are excluded. Original campaign,
schedules and all prior outputs remain untouched. Fresh recovery identities only.
The inspected failure-path sources match the original frozen campaign byte-for-byte.
Existing unrelated dirty work is preserved in a separate starting-state manifest.

## Remediation

Retain original AMP, native optimizer, weights, seeds, datasets, image sizes, batch,
thresholds and splits. Reproduce numerical causes before computation changes; preserve
finite guards and add precise context. A numerical failure unresolved under original
AMP remains a blocker, not successful recovery. Profile source-row enrichment and
CSV assembly from retained populations; optimize only demonstrated overhead without
changing output semantics. Use measured finite per-job native/readback budgets and
verify effective launcher PATH and the existing 64 MiB client overlay.

## Architecture and tasks

See [architecture.json](architecture.json). SDK, GPU and IO effects remain in adapters;
core evaluation remains pure. No new public CLI/configuration or dependency change.
The private automation source owns preflight, scheduling, provenance and budgets.
Python >=3.12.13,<3.14 and approved digital-metrics revision remain unchanged.

- [x] Capture immutable starting state and isolate the current working tree.
- [ ] Reproduce numerical failures and profile timeout paths.
- [ ] Add regressions before implementation; apply demonstrated fixes.
- [ ] Verify original 20 commands with fresh identities and original AMP.
- [x] Validate blocked dependencies without running their experiments.
- [x] Update docs/portable usage/private restoration guidance as applicable.
- [x] Current-source canonical code/docs checks, paired CY/queue checks, independent review.
- [ ] Reconcile diff, architecture acceptance and authorized Git-only delivery.

Useful independent workstreams: numerical investigation (read-only initially), private
campaign tooling (exclusive source files), and parent-owned performance investigation.
GPU reproductions are serialized by the parent under the existing reservation contract.
Independent review follows integrated verification. No success claim from mock checks.

## Verification

Run `uv run --frozen --no-sync python scripts/verify.py` and its separate `--docs`
mode; applicable mutation selection if covered inputs change. Validate architecture
plan before source changes and acceptance after evidence and independent review.
For every recovery require exit zero, forced artifact/model readback, reloadable
weights, complete population/provenance and verified owned process exit. Keep detailed
machine evidence external; portable dated findings belong beside this assessment.

## Integration checkpoint, 2026-11-02

The initial isolated copy preserved the user's dirty working tree. After its broad
verification exposed the effect-checker's generic rename ban and an untouched
process-cleanup failure, the task-only patch was applied to clean latest CY
`73bb044` (0.44.7), paired with queue `32bea01` (0.1.7). No unrelated source changes
were copied or rewritten. Source overrides in the initial copy were preserved and
restored byte-exactly; no dependency revision changed. Bulk column projection now
uses the pure DataFrame set_axis API rather than weakening the effect contract.
Existing architecture and behavior regressions pass this correction.

The original-AMP numerical reproductions and native recovery observations are
retained separately with frozen source manifests. They are not evidence that the
complete latest-source 20-case native matrix passes. Remaining native, release and
host-export gates stay explicit in the verification report.

## Task reconciliation

The numerical/profile and regression tasks remain partial: all five numerical
failures reproduce, one timeout pilot remains censored, and eleven originals have
not been replayed. Diagnostics and row conversion have regression coverage, but
there is no accepted correction for the original numerical computation. Eligibility
coverage for all fifteen blocked arms is complete without executing their trials.
Documentation source updates are complete; installed skill exports remain blocked
by preserved drift and pending source delivery. Paired development checks and fresh
source review passed, while canonical and full native acceptance remain open.
The original stopped campaign and unrelated source changes remain preserved.

## CPU-only continuation and load restriction

User authorized continued non-GPU work, then prohibited heavy load until
2026-11-03 01:00 Europe/Moscow. Until that time use static inspection, small
metadata/document checks and preparation only; no suites or Torch/model diagnostics.

- [ ] Correct the CPU observer test fixture so accelerator discovery cannot
  initialize CUDA while readiness properties are deliberately stubbed. Existing
  retained failure traces reach AdamW accelerator health probing at optimizer.step.
  Keep real CPU optimizer, EMA, serialization and digest checks. This affects only
  tests/test_native_backend_ddp_harness.py; runtime interfaces/effects stay unchanged.
- [ ] After the restriction, verify that fixture and preserve full test collection
  when selecting the minimal numerical/asset pair for the SIGILL investigation.
- [ ] Complete remaining canonical CPU, source-release and new-snapshot export
  checks; keep native twenty-case acceptance separate and pending.

Current export correction: the independently released 390c91a snapshot was
reconciled and installed by maintenance work recorded in private source v0.12.1.
The outstanding gate is publishing this task's new source and synchronizing its
exact released snapshot, rather than unresolved old-copy drift. Preserve the
earlier observations as history and do not equate old-pin health with new rollout.

## Heavy CPU work resumed by explicit user instruction

On 2026-11-02 at 23:21 Europe/Moscow the user lifted the load restriction early.
GPU work remains excluded. The prepared CPU observer regression passed (one
test). The full-collection minimal numerical/asset probe passed two selected
tests with 4,816 deselected; this is diagnostic evidence rather than canonical
acceptance. The time guard remains default-on; explicit authorized-now invocation
records the superseding user instruction. A canonical CPU run is in progress,
and current upstream CY 0.44.8 plus current queue source are prepared separately
because the earlier 0.44.7 source is no longer the latest release.

## Final CPU-stage reconciliation

Current-source canonical, documentation, development-pair and fresh source-review
gates passed. Helper source and exact-snapshot cross-host rollout are delivered
and privately accepted. The application diff remains isolated and uncommitted;
aggregate architecture acceptance and application release remain blocked by the
original native matrix. Eventual release also requires proposed-version paired
checks. Original stopped runtime/evidence and unrelated work remain preserved.

## Service-resilient continuation, 2026-11-03

The approved continuation preserves all original scientific settings and requires
all twenty original cases on one final revision before release. Historical campaign
rows, schedules and logs remain immutable. Private tooling owns endpoint and
credential discovery, finite readiness retries, durable deferral, fresh launch
identities and readback-only continuation; application publication semantics remain
unchanged. GPU ownership ends only after verified descendant exit and is not held
for remote readback. The existing architecture record still describes the application
diff: no new core effects, SDK ownership or public configuration is introduced.

- [ ] Implement and independently verify resilient private recovery tooling and
  current-source/interpreter bindings; release and synchronize its exact snapshot.
- [ ] Diagnose each numerical case against its own pinned native path, preserving
  AMP and every original training/evaluation setting. Retain FCOS preceding updates.
- [ ] Measure progressing timeout pilots at 1,800/3,600/7,200 seconds and resolve
  stalled stage boundaries. Derive budgets from complete successful samples only.
- [ ] Repeat the retained SIGILL sequence three times with full collection and
  guardian-death cleanup five sequential plus five under bounded owned CPU load.
- [ ] Re-run canonical code/docs, applicable mutation and complete current paired
  queue checks after the final application changes; preserve exact parity controls.
- [ ] Verify all twenty native exits, required forced downloads, checkpoint reloads,
  complete populations and identities on the final source; eligibility-check the
  fifteen blocked arms without running their experiments.
- [ ] Reconcile architecture, fresh review and prospective release-version paired
  evidence before the authorized application commit/tag/push.

Passing source tests or a temporary service outage cannot waive native acceptance.
Native numerical failures and infrastructure failures remain separate outcomes.

## Reconciled continuation after host interruption, 2026-11-03

The following checkpoint supersedes earlier pending/count statements while retaining
their history. Private recovery tooling is implemented and independently tested:
source v0.14.2 and rollout metadata v0.14.3 are released, with exact registered
exports. Original AMP, initialization and scientific settings remain unchanged.

- [x] Implement resilient discovery/readiness/retries, uncertain-write reconciliation,
  readback-only resumption, durable process ownership and current-source bindings.
- [x] Investigate all five numerical paths independently, including FCOS preceding
  updates; retain original failures and corrected bare-native YOLO control evidence.
- [x] Complete progressing timeout pilots, separate traced stage envelopes and derive
  recovery budgets only from successful measurements; retain censored samples.
- [x] Execute three full-collection SIGILL prefixes and ten requested guardian
  repetitions. SIGILL recurred; executing the investigation does not close its gate.
- [x] Verify unchanged application code, separate docs and current development pair;
  inspect mutation applicability and portable guidance. Final dated checks are in test.md.
- [ ] Complete strict final-source native acceptance: 14/20 accepted, six native
  steps remain (Faster50 replacement and five ordinary numerical replays).
- [ ] Resolve the five original-AMP numerical failures and recurrent SIGILL without
  changing scientific settings or claiming passing diagnostics as repairs.
- [ ] Pass aggregate architecture and proposed-release pair checks, then release CY.

Fifteen distinct cases have successful historical/current recovery evidence. The
Faster50 earlier successful pilot lacks complete final environment proof; its final
replacement run was interrupted by host reboot. Old descendant exit is positively
reconciled through the boot transition, but native zero exit is unknown. A fresh
linked attempt is prepared; no incomplete run counts as acceptance. Five numerical
ordinary attempts are also prepared, unlaunched. GPU work resumes only in an allowed
window with fresh ownership, readiness, hashes and budget admission.

All fifteen blocked arms received eligibility checks only. Twelve have strict
final-source accepted baseline evidence; three Faster50 dependencies retain the
legacy proof gap. No blocked experiment, interrupted original or pending original
was executed. The original campaign ledger and logs remain protected.
