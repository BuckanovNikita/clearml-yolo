# Ticket97: Materialize the YOLO probe candidate batch

## Retained live finding

The first ticket03 native acceptance case retained failed evidence under
`runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/ultralytics-default-4794e3a821/`.
Its batch-estimate record identifies trial global batch 8 and the error
`TypeError: 'batch=None' is invalid. 'batch' must not be None.` No usable capacity
was recorded and acceptance training did not start. The case summary reports owned
cleanup complete. These failed artifacts were preserved for the coordinator's retry.

The estimator intentionally excludes unresolved batch selectors from profile
identity, but the YOLO probe forwarded the recipe's `batch=None` into its native
components. Installed Ultralytics 8.4.184 `BaseValidator.__init__` calls
`get_cfg(overrides=args)`, whose `check_cfg` rejects a null batch. Existing scaler
boundary tests stopped before that validator path; existing direct validator tests
supplied empty/native-default values, so neither exposed this recipe combination.

## Minimal correction

In `adapters/yolo/batch_probe.py`, the existing execution-settings overlay now binds
`batch=request.global_batch` alongside effective `imgsz`, before assigning model and
trainer arguments. Native validation receives the same concrete global candidate.
The source diff against coordinator snapshot `7c8f694` is exactly this one-line change.
Profile construction, recipe input, candidate selection, failure/no-fallback policy,
timeouts, two-epoch acceptance inputs and the memory reserve remain unchanged.

This is a routine correction of the existing candidate-binding/exact-recipe contract,
also supporting feature014 FR-001/005. No upstream or specification change is needed.

## Red/green verification

The new `tests/test_yolo_probe_batch_binding.py` exercises public `probe()` through
actual native detector construction/loading, optimizer updates, EMA, assignment loss,
and validator metrics. A tiny locally initialized detector substitutes the external
model asset. CUDA device admission is redirected to CPU and CUDA telemetry is stubbed;
native configuration parsing and the native validator remain real. The existing
shared fixture restores process RNG and deterministic policy after each case.

Before the fix, four cases failed: the null selector reproduced the exact retained
TypeError at native `get_cfg`, and fixed batch 16/AutoBatch -1/fraction 0.5 reached
native validation unchanged instead of using candidate 2. After the fix, eight cases
cover candidates 2 and 4 crossed with those four recipe selectors. They confirm the
native validator receives the candidate, the successful receipt reports the same
batch and completed update/validation steps, and the original recipe remains unchanged.

- **Passed**: focused locked pytest across batch binding, determinism, precision,
  batch probes and batch profiles: 164 passed, 19 warnings, 4.69 seconds.
- **Passed**: final new-module rerun after correcting the typed native-config import:
  8 passed in 2.57 seconds.
- **Passed**: strict mypy for the affected product module and new test module.
- **Passed**: Ruff check and format check on both files. Test-only lint/type issues
  were corrected before the final checks.
- **Passed**: fresh independent review by `/root/final_recipe_review` approved the
  exact product `55fd12cc...` and test `ee45d917...` hashes below. Review confirmed
  global candidate binding before native configuration, preserved per-rank sizing
  and validation doubling, and unchanged recipe/profile identity.
- **Passed**: coordinator's canonical final gate on
  `fbcfa251e4b26ffd786d2e4cb72174fa4fe8606a` exited 0; Task change-aware verification
  passed and the managed worktree was clean. Coordinator log: `.tmp/ticket97-final-gate.log`.
- **Completed advisory mutation disposition**: the [combined ticket96/97 report](2026-11-16-yolo-probe-mutation-96-97.md)
  records 33 killed, ten timeouts, and 191 budget-unrun native mutants. Fresh exact-current
  private reversions separately failed all eight batch-binding tests and all eight
  determinism tests. Native timeout/unrun limits remain explicit.
- **Live retry observation**: retained case `ultralytics-default-720bf0a94c` records
  successful native optimizer and validation work at batches 8, 16, and 48, each
  covering AdamW and MuSGD with one validation step. This clears the original
  null-batch validator failure. The later memory-reserve cancellation leaves no
  accepted capacity or completed two-epoch training/publication outcome; ticket98
  tracks that separate defect. See the coordinator's [GPU retry evidence](../../014-estimated-batch-acceptance/evidence/2026-11-16-gpu-retry.md).
- **Not established**: accepted GPU capacity, multi-GPU execution, or the full
  acceptance training/publication outcome.

All execution used the locked environment, CPU affinity 0,1 and nice19. No GPU job or
remote service was launched by this implementer.

## Frozen snapshot and cleanup

| Path | SHA-256 |
| --- | --- |
| `src/clearml_yolo/adapters/yolo/batch_probe.py` | `55fd12ccf58cfc6fe58ea69fb48dfb3485e66fc68cd6eb1d0dd0d20956cfeed3` |
| `tests/test_yolo_probe_batch_binding.py` | `ee45d917292cc9535686c7b851ec5711aa70e205f84d6115fe2ffb30afdf1a39` |

All owned pytest/type-check processes exited. The three owned
`.tmp/yolo-batch-binding-{red,green,final}` directories were removed after recording
results. Retained live failure evidence, model assets, shared caches and other agents'
files were preserved. No commits, shared staging changes or upstream edits were made.
