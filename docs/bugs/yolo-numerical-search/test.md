# Verification: numerical-search recovery

- Slug: `yolo-numerical-search`.
- Date: 2026-10-30.
- Assessment: [assessment.md](assessment.md).
- Implementation: [fix.md](fix.md).
- Status: recovery behavior verified; native numerical cause remains unconfirmed.

## Executed evidence

The new reported-sequence regression failed before the fix: expected pending batch
24 after numerical failure at 28, observed no candidate. After implementation the
focused command passed **218 tests**:

```bash
uv run --frozen --no-sync pytest tests/test_batch_numerical_recovery.py \
  tests/test_batch_estimation.py tests/test_batch_estimate_workflow.py \
  tests/test_batch_estimate_store.py tests/test_batch_estimate_cli.py \
  tests/test_batch_lookup.py tests/test_batch_probe.py -q
```

The exact reported search history/peaks are exercised as deterministic policy evidence,
including B32 over-budget, B24 successful, B28 nonfinite and fresh B24 confirmation.
The synthetic receipts in these tests are not native A40 execution evidence.

Real cached YOLOv3u direct probes passed at 128/batch 1/AdamW and 640/batch 28/MuSGD,
including eager and compiled MuSGD. Every successful run performed five warmup and
ten measured optimizer updates plus native validation. They used a different CUDA
GPU/runtime than the user's A40 environment. The relevant installed Ultralytics
8.4.184 detection code was compared against 8.4.189: no numerical detection-path
change explains the report. No checkpoints, user SDK settings or installed original
environments were modified.

A supervised integration experiment intended to inject a numerical failure between
two real native trials stopped before that injection: existing telemetry protection
reported `active compute has no PID telemetry`. This is an incomplete integration
check, not a passing recovery run. It did not bypass the guard or create a usable
estimate. The exact A40/960/batch-28 numerical failure remains unverified locally.

Full Ruff, strict mypy, Vulture and import-linter steps passed during canonical
verification. Full pytest, documentation reconciliation, paired-release integration,
final independent review and release outcomes are appended below when completed.

## Acceptance limits

Acceptance covers safe search recovery, persistence, presentation and compatibility,
not a correction to the native numerical calculation. A limited recommendation is
never a measured capacity maximum. Failed confirmation remains unusable. Physical
multi-GPU capacity and target A40 behavior are not claimed by these tests.

## Proposed release pairing

An isolated normal resolver installation paired proposed CY **0.44.3** with latest
cy-queue **0.1.5**, source `397753c123f379ade50f06a2babf5e4b1476b9d2`. Source and
installed metadata agreed; `uv pip check`, queue Ruff/formatting, strict mypy,
import-linter and command help passed. The full configured queue suite passed
**518 tests, 7 deselected**, with 19 warnings. Final release-hook metadata must
still be rechecked before push. Approved external dependency revisions and the
original installed environments remain unchanged.

Documentation checks passed for all changed CY guidance and new bug artifacts.
Portable collection **0.6.6** is prepared from **0.6.5**, with metadata, discovery,
Markdown, local-link and architecture checks passing. Its explanation-only
evaluation cases await the fresh independent review.

## Canonical verification

`uv run --frozen --no-sync python scripts/verify.py` completed with exit 0 and
unchanged verification inputs. Ruff, strict mypy, Vulture and import-linter passed.
The complete ordinary suite passed **4508 tests**, with **30 skipped, 81 deselected**
and 182 warnings in 1029.12 seconds. All six native CPU-DDP tests ran successfully.
Skipped/deselected targets are not presented as passing native GPU/publication checks.
The documentation verification command passed after final guidance reconciliation.
The required fresh independent review and release outcome follow below.

## Review and acceptance

[Fresh independent review](review.md) returned **ship**, with no findings. It
independently reran the 26 new recovery tests and passed both portable explanation-only
evaluations. No native target-model benchmark or A40 success is inferred from that
evaluation. The complete owned diff matches the architecture record and remediation.
The final architecture acceptance validator and documentation checks passed before
release. The actual post-hook CY/queue pair is checked again before the authorized
Git commit/tag pushes; no package assets or GitHub Release objects are published.
