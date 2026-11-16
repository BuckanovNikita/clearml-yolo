# Ticket 03 verification handoff — 2026-11-15

Worktree `/mnt/wsl/data/nkt/clearml-yolo`, branch `master`, base `31e2733`;
local base only, remote references not fetched. No commits, releases, dependency
changes, GPU launches or shared-service teardown by this bounded implementer.
The coordinator owns subsequent full-gate/live execution and independent review.

## Executed checks

- **Passed**: focused product suite, 325 tests in 19.03 s. Actual CPU augmentation
  and numeric/optimizer seams execute; worker/telemetry assertions use mocks.
- **Passed**: final profile/trainer slice, 42 tests in 2.24 s, after including
  augmentation implementation and dependency identity.
- **Passed**: `uv run --locked task --exit-code check`, including 21 import contracts,
  453 typed files, Ruff, lock/hygiene and dependency checks. Subsequent evidence-hash
  harness edits passed affected Ruff/format/mypy; strengthened DEIM test passed
  affected Ruff/format/mypy and 11 CPU tests with testmon refreshed.
- **Passed with advisory limitations**: initial native mutation report against base,
  isolated temporary index, 8 of 32 changed functions, one child, 300-second budget.
  Clean baseline and forced-failure validation passed. Counts: 659 mutants, 74 killed,
  45 survived, 18 timed out (tool groups these with escaped), 153 unreached, 369 unrun.
  Twenty-four changed functions were excluded by the function budget. The full
  selection and excluded names are in the captured report.
- **Passed**: native Spec Kit prerequisite discovery/consistency review; see the
  dated analysis. No installed Spec Kit files were edited.
- **Deferred to coordinator**: final comprehensive automatic gate, representative
  native GPU training through remote readback, and fresh integrated independent review.
  These are acceptance gaps; the ticket is not accepted by these CPU results.

## Mutation dispositions

Initial survivors in DEIM custom samples exposed insufficient numeric assertions:
wrong pixel scale, box conversion/area and target metadata could survive a grayscale
and shape-only test. Added a product `synthetic_batch` test with explicit non-square
image/box coordinates, source preservation, normalization, target fields and rank IDs.
The initial 45 surviving variants were inspected from captured generated source;
full diffs are retained. A targeted native mutation rerun follows this stronger test.

Device-transfer survivors require CUDA to distinguish CPU `.to(None)` from a real
transfer. A leading singleton dimension removed from channel normalization is
broadcast-equivalent. Native GPU `probe` and its configuration-normalization helper
were not reached in the initial CPU selection. Augmentation methods and remaining
synthetic/training-step mutants were unrun at the budget boundary. Timed-out
training-step mutants are inconclusive, not proofs of equivalence or successful kills.
No source was changed merely to satisfy a mutant and no survivor allowlist was added.

## Scope and evidence limitations

The estimator remains conservative synthetic capacity; actual JSON/Mosaic executes
with the GPU model resident, while target padding preserves the target envelope.
Shape-changing custom pipelines fail explicitly. Optional allocator reserve is only
a mitigation; whole-device telemetry owns breach detection and cancellation.
Native CLI defaults remain unchanged. Strict fixed batch/epoch behavior is opt-in.
The existing ordinary YOLO OOM retry discrepancy is coordinator ticket 94.

Immutable fixture v1 configurations are untouched. Per-case request, resolved input,
estimate, augmentation and corpus digests plus downloaded canonical configuration
identity establish supersession after measurement. Raw and selected batches remain
separate. No hypothetical capacity value or native outcome is recorded here.

## Commands for coordinator admission

Use the existing service lifecycle exports and the asset consumer-bindings native
environment, keeping credentials out of logs. The representative pytest selection is:

```bash
uv run --locked pytest \
  'tests/integration/test_severstal_gpu.py::test_native_severstal_smoke[default-ultralytics]' \
  -q -n 0 --run-severstal-gpu \
  --severstal-dataset runs/verification-gap-closure/fixtures-v1/prepared \
  --severstal-home runs/verification-gap-closure/assets-v1 \
  --severstal-artifacts runs/verification-gap-closure/assets-v1/estimated-acceptance-v2 \
  --severstal-clearml-project ticket03 \
  --severstal-tags verification-gap-closure,ticket03 \
  --severstal-device 0 --severstal-timeout 1800 --severstal-free-vram-mib 8192
```

Admit only under the active host policy; this command is prepared, not executed.
Whole-device reserve monitoring covers estimation and training. Keep fresh case
evidence and downstream checkpoints before cleaning only task-owned disposable data.

## Follow-up and freeze checkpoint

The targeted native rerun selected four DEIM functions, one child, 180-second budget:
325 mutants, 165 killed, 28 survived, nine timed out, 18 unreached and 105 unrun.
All pixel/box/target-field defects exposed in the initial custom conversion survivors
are now killed. Sixteen custom conversion survivors remain: fourteen GPU-placement
changes need CUDA, and two singleton-channel-view changes are broadcast-equivalent.
The existing unchanged `target_bound` function was included by the explicit-file
selector: eleven survivors expose untested optional-key/default/custom-count branches;
one positive default-probability change (1→2 under a >0 predicate) is equivalent.
These unchanged branches were not rewritten as part of this task. Nine synthetic
wrapper timeouts remain inconclusive. All follow-up survivor diffs were inspected
and retained. This report is bounded coverage, not mutation completeness.

The final existing Severstal CPU/composition slice passed 66 tests in 5.19 s. A
disposable manual check confirmed explicit shared-home containment, case-owned temp
root and clearing inherited runtime-arena state; the fixture was removed. This
addresses redundant per-case downloads while preserving real catalogue preparation.
The shared home and asset caches remain coordinator-owned until downstream consumers
finish; only case outputs/scratch may be cleaned after retaining evidence.

`native_trainer.py` and its augmentation test were released to the ticket-94 owner
after their ticket-03 tests passed. The first input receipt records their pre-94
content; the final-03 receipt excludes these two now-shared paths. The coordinator
will verify and review the integrated final content rather than reuse stale hashes.

Temporary mutation workspaces and temporary indexes were automatically removed.
Captured generated-mutant copies and local check logs were removed after retaining
their evidence. No task-owned process, mount, GPU allocation or service remains.

## Review remediation: nested process cleanup

The reviewer identified a P1 harness gap: signalling only the scenario process group
could orphan estimator children launched in independent sessions. The outer runner
now uses the existing `IndependentWorkerPool` case boundary. It preserves the
prelaunch reserve check, rate-limited 250 ms monitoring, the scenario deadline and
`native.log`. Cancellation/timeout unwinds the pool's owned descendant cleanup;
completion requires confirmed cleanup, not only a successful leader exit.

A bare `run_workers`→`run_workers` replacement was tested first and rejected: nested
worker markers overwrite the outer marker, leaving adopted descendants ambiguous
when an unrelated helper predates the scope. Three real CPU tests failed and safely
cleaned their owned processes. The exact reproducer and failure log are retained;
the coordinator tracks that separate product defect as ticket 95. No product source
was changed in this harness remediation.

The intended `IndependentWorkerPool`→`run_workers` topology passed three real tests
in 8.72 s **before ticket-95 product changes**: reserve-like monitor cancellation,
KeyboardInterrupt and deadline expiry. Each nested worker launches a further
detached session; stubborn children ignore SIGTERM to exercise escalation. All owned
PIDs were gone and reaped while the preexisting unrelated sibling remained alive.
The test finally terminated its own sibling. A follow-up combined slice passed
69 tests in 14.78 s; affected Ruff/format/mypy passed. Product source hashes before
ticket-95 edits are recorded separately. This is real CPU process evidence, not a
claim about GPU execution or actual reserve telemetry.

The new product supervision test is `tests/test_nested_worker_cleanup.py`, marked
`process_capabilities` so the existing serial grouping and mutation exclusion apply.
No tooling-mirroring test was added. Final integrated review and full gate remain
coordinator-owned; this remediation invalidates earlier harness source hashes.
