# Forced admission current-source reconciliation — 2026-11-04

## Scope and preservation

The preserved force implementation was based on CY `84166d5` (0.44.8). This
integration uses `8be76e4` (0.45.0), retaining the delivered saved-coverage listing.
Only the force implementation, regressions, declarations/help fixture, documentation
and native-ledger amendments were imported. Original worktrees, environments,
native outputs, version metadata and dependency revisions were not changed.

Five production modules retain their existing import/effect boundaries: immutable
core settings carry `force`, telemetry adapters enforce its narrow admission policy,
the probe forwards it to every boundary, and CLI composition renders the provenance.
Existing `.importlinter` and negative architecture tests remain authoritative;
[the architecture record](architecture.json) passed planning validation before
runtime integration and again after reconciliation. Final review remains pending.

The delivered list ledger already uses T051–T055, so the unpublished force tasks
map to T056–T060 without modifying completed list history. Combined documentation
and help preserve `--list`, optional `--imgsz` for listing, and the new `--force`.
The explicit measurement-only rejection test now covers `--list --force` while
forbidding runtime initialization, discovery, probes and store writes.

## Focused verification

Checks use the prepared interpreter with this checkout's `src` selected explicitly;
no packages were installed and no shared environment metadata was changed. These
checks establish the source behavior only, not a normally installed final pair.

- Five initial focused modules (`test_batch_estimation`, `test_batch_estimate_cli`,
  `test_batch_probe`, `test_gpu_inventory`, `test_docs_compatibility`): **397 passed**,
  19 upstream deprecation warnings, 20.10 seconds.
- Current listing, catalogue store and estimator workflow: **45 passed**, 1.30 seconds.
- Search-strategy/frozen historical keys and aligned-search regressions: **188
  passed**, 0.96 seconds.
- Ruff on all changed Python modules/tests: passed.
- Strict mypy: no issues in 11 changed source/test files.
- Changed README, maintained batch guide, plan/spec/tasks and historical force
  verification: six Markdown documents passed, zero issues.
- The final task amendment and this reconciliation report: two Markdown documents
  passed, zero issues.
- Task-owned diff whitespace check: passed.

An initial additional test invocation named nonexistent `test_batch_legacy_reuse.py`
and exited 4 before execution. The corrected invocation above passed; the invalid
command is not counted as verification.

The configured mutation targets and their selected tests/dependencies are unchanged
by this port. Full canonical verification, architecture negative checks, final
documentation verification, normal current/proposed-version pairing and fresh
independent integrated review remain parent-owned acceptance gates.

## Native evidence remains incomplete

The required catalogue contains 64 models: 44 YOLO, four DEIMv2, four RF-DETR,
six Faster R-CNN and six FCOS. The retained proposed-0.44.9 catalogue contains nine
validated models and one interrupted/unconfirmed model. A separate final-attempt
catalogue contains only one interrupted case. No complete native audit receipt was
found; those historical partial results cannot establish final-source acceptance.

Native acceptance retains the specified 960-pixel workload, 150 classes, 300 objects
per image, five warmup and ten measured steps, all optimizer paths, 300-second
trial deadline, 1,024 per-GPU ceiling, 90% memory budget and fresh confirmation.
Genuine measured no-capacity outcomes are allowed; failures, missing assets and
interrupted or unconfirmed searches are not accepted recommendations. No GPU work,
new native measurement, commit, version change or push was performed in this port.

## Sequential integration checkpoint — 2026-11-05

This port starts at master `66279a6` (CY 0.45.1), after the isolated DINOv3
fix and scoped campaign improvements. It imports only the twenty force-owned
paths, preserving the other integrated changes, source worktrees, version metadata
and approved dependency pins. The existing follow-up ledger and historical
verification remain intact. The architecture record was reconciled before runtime
edits; existing import and negative contracts need no new exception.

The user declared the low-utilization background idle and asked it to be ignored.
The explicit `--force` mechanism honors that request while retaining strict
default behavior, numeric telemetry, known foreign-PID rejection, baseline memory
accounting and supervised native receipts. It does not establish graphics-only
activity or uncontended capacity. No ordinary-estimator success is inferred.

All current architecture checks and review start pending. The parent owns final
canonical/docs verification, final proposed CY 0.46.0 / compatible queue pairing,
the complete frozen-source 64-model native catalogue, selected DINOv3 L/X fresh
optimizer/winner confirmation, final independent review and architecture acceptance.
The latest retained partial catalogue has only nineteen cases, thirteen validated
and six failed. It does not establish this integration's coverage or acceptance.
No intermediate code release is authorized by this port's bounded implementation
task; delivery remains held until the parent's final integrated gates pass.

### Current port outcome

The force settings baseline failed before runtime integration. After the exact
scoped port, 424 focused cases and 38 legacy-key/resolution cases passed, as did
scoped Ruff, strict mypy, seven-document validation and whitespace checks.
See [current verification](verification.md#sequential-current-master-force-port--2026-11-05).
All final integrated/native/prospective-version/review gates remain pending.
