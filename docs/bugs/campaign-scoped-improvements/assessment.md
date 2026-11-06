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
- [ ] Parent verifies retained 50,000-row exact parity and scoped profiling.
- [ ] Parent runs final integrated canonical, docs and prospective CY/queue pair.
- [ ] Parent reconciles portable usage, fresh integrated review and architecture acceptance.
- [ ] Parent completes authorized Git-only delivery after all integrated gates.

The final integrated source includes subsequent force work. No intermediate release
is claimed. DINOv3 native evidence and the force catalogue gate remain owned by
their respective records. Changes here do not establish recovery of the original
native campaign failures or physical multi-GPU execution.

## Documentation

Update the nonfinite-native-value troubleshooting in `docs/multi-model-backends.md`.
The parent owns companion portable usage inspection/update and validation for
contextual failures; no installed skill or private automation source is changed.
Mutation-selected sources, tests and dependency revisions are unchanged.
