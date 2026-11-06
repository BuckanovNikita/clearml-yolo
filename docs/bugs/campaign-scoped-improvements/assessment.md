# Scoped campaign improvements assessment

- Slug: `campaign-scoped-improvements` (explicit bounded parent task).
- Created: 2026-11-05.
- Source: user-selected scoped campaign integration and preserved campaign remediation.
- Verdict: valid diagnostic/export overhead defects; numerical recovery remains separate.
- Severity: low for diagnostics, medium for large-population export overhead.

## Scope and original observations

The current scalar guard rejects nonfinite values without identifying the title,
series, iteration or value. Shared Torchvision training rejects a nonfinite loss
without its batch, input image identities or component losses. Current result-row
enrichment constructs a pandas Series per source row, retaining demonstrated
overhead from the earlier campaign. The CPU observer fixture supplies incomplete
accelerator properties while AdamW can probe the default accelerator at step time.

This selected scope ports the existing contextual errors, bulk record conversion
with exact output semantics, and CPU-only observer fixture correction. It does not
change AMP, optimizers, weights, seeds, datasets, thresholds, batch, model choice
or public configuration. The original campaign's numerical failures, SIGILL
investigation and full 20-case recovery remain unresolved separate work. Their
preserved assessment, evidence and pending gates are neither copied as accepted
work nor weakened by this bounded integration. Historical timings are not fresh
performance measurements.

## Reproduction and remediation

Run the four preserved campaign diagnostic regressions before runtime edits. They
exercise NaN/positive infinity/negative infinity journaling and a real Torch CPU
forward path with a nonfinite component; all must fail on missing context. Port
the diagnostics without changing exception types or finite guards, then require
the same tests to pass before any backward/update on invalid loss.

Use the preserved column-wise record conversion in `_enrich_rows`, retaining
source-row occurrence, extension metadata, null boxing, threshold flags, geometry
exclusion reasons and match lineage. Retain the sparse all-text-row inference
needed for exact CSV parity. Add the preserved export edge regressions and run
parent-owned 50,000-row exact parity/profile checks on retained inputs. Stub only
accelerator discovery in the CPU observer fixture; real optimizer, EMA, hashes
and serialization remain exercised.

## Architecture and acceptance

[Architecture record](architecture.json) records the three affected modules and
existing executable inward/effect contracts. Core row conversion remains pure;
the capture adapter owns its journal effects and the Torchvision adapter owns
training/checkpoint effects. No new module, SDK dependency, import exception or
composition target is introduced. Python compatibility and approved dependencies
remain unchanged. The port starts at current master `66279a6` plus the parent's
reviewed isolated DINOv3 changes, which are excluded from this write ownership.

- [x] Validate the architecture plan before runtime edits.
- [x] Capture the four diagnostic baseline failures.
- [x] Port the exact scoped runtime, tests and backend guidance.
- [x] Pass focused diagnostics/export/CPU observer and architecture checks.
- [x] Parent verifies retained 50,000-row exact parity and scoped profiling.
- [x] Parent runs final integrated canonical, docs and prospective CY/queue pair.
- [x] Parent reconciles portable usage, fresh integrated review and architecture acceptance.
- [x] Parent completes authorized Git-only delivery after all integrated gates.

The final integrated source includes subsequent force work. No intermediate release
is claimed. DINOv3 native evidence and the force catalogue gate remain owned by
their respective records. Changes here do not establish recovery of the original
native campaign failures or physical multi-GPU execution.

## Documentation

Update the nonfinite-native-value troubleshooting in `docs/multi-model-backends.md`.
The parent owns companion portable usage inspection/update and validation for
contextual failures; no installed skill or private automation source is changed.
Mutation-selected sources, tests and dependency revisions are unchanged.

## Ledger reconciliation — 2026-11-07

- Line 57 is ticked: [test.md](test.md#parent-relationship-edge-confirmation)
  records the 50,000-row exact frame/CSV comparison and the relationship-edge
  confirmation that together close scoped export parity, and the architecture
  `parity` check is passed. The "still-open" parity item in the
  [cleanup verification](../../plans/unfinished-work-cleanup-20261106/verification.md)
  most likely reflects this then-unticked box (an inference: no record states why
  that review called parity open). Parity is closed per test.md and the passed
  architecture `parity` check. That dated record is left unchanged.
- Line 58 is ticked: [test.md](test.md#final-integrated-verification-checkpoint)
  records the final canonical run (4,844 passed) and the proposed CY 0.46.0 /
  queue 0.1.9 pair (583 queue tests). The committed-version pair (584 queue tests,
  7 physical opt-ins deselected) is in cy-queue
  `docs/plans/cy-046-compatibility/verification.md`. The two counts come from
  separate runs.
- Line 59 stays open for WP2a/WP3 (portable usage, fresh integrated review and
  architecture acceptance).
- Line 60 is ticked with an exception: this source was delivered in CY 0.46.0
  (`60edd4b`, tag `v0.46.0`) before the line 59 gates finished, as the 006
  [delivery note](../../../specs/006-batch-training/tasks.md#delivery-note-2026-11-06)
  records. The release does not claim those gates.
- Documentation check: on 2026-11-07,
  `uv run --frozen --no-sync python scripts/check_docs.py --all` exited 0 with
  "Checked 268 Markdown files; 0 issue(s)." The architecture `docs` check now
  records this command, because `scripts/verify.py --docs` no longer exists.

## Acceptance — 2026-11-07

Line 59 is ticked. Portable usage: corp-skills v0.7.5 (`11b6866`) states CY 0.46.0
guidance. Fresh integrated review: [review.md](review.md), no finding, including the
independent rules lens. Architecture: [architecture.json](architecture.json) review is
`accepted` and the record passes `validate_architecture.py --phase acceptance`.
