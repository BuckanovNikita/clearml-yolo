# Feature Specification: Evaluation publication

**Created**: 2026-10-05
**Status**: Implemented and independently accepted; release pending
**Input**: Parallel implementation: artifacts, confusion matrices and PR curves.

## User scenarios and testing

### US1 — Inspect complete evaluation evidence (P1)

An evaluator downloads one effective `gt_csv` and one combined `predicts_csv`.
Every source object remains distinguishable, including identical boxes, background
records, invalid geometry, suppressed predictions and excluded duplicate GT.
Tests join pre/post-threshold match endpoints through explicit prepared-index mappings.
Standalone prediction remains not evaluated; training and GT commands invent no predictions.

### US2 — Inspect interactive evaluation plots (P1)

For every selected model/split context, inspect the exact post-threshold confusion
counts in raw, row, column and global normalization and per-class PR at IoU 0.50.
Tests cover asymmetric matrices, zero denominators, numeric/Unicode labels, both AP
integration methods, all matching strategies, ties, empty predictions and absent GT.

### US3 — Identify experiments and calibrated models (P1)

Unused names remain unchanged. Exact project-local collisions, including archived
records, receive a shared readable adjective–noun suffix. Names are rechecked for
up to 20 attempts. Paths, checkpoint URLs and model IDs remain stable. Clones resolve
fresh names. Owned best models receive full-precision class thresholds only after
matching calibration checkpoint hashes; writes must pass readback verification.

## Functional requirements

- FR-001: Export effective GT with original fields and stable source/object IDs assigned
  before preprocessing. In the combined CSV, retain context/model/split identity,
  evaluation status and exclusion reasons for both GT and prediction rows.
- FR-002: Combined CSV stores every match relationship as JSON lists with IDs,
  endpoints, labels, IoU, status and pre/post-threshold phase. Threshold comparison is
  strict `<`; GT/unavailable flags are null. Raw, geometry-valid AP and preprocessed
  fixed-matching populations remain separate; existing schema/confidence errors persist.
- FR-003: Enrich existing prediction contexts when evaluated; comparison reinference
  is distinct. Durable shards assemble deterministically and canonical CSVs upload once.
- FR-004: Preserve default train/val/test and explicit validated splits. Calibrate only
  on val; freeze elsewhere. Pipeline comparison stays test. Missing automatic baseline
  publishes candidate dashboards/plots and skip reason without fabricated comparisons.
- FR-005: Publish original full/DTRK workbooks for each context, exact validation
  threshold CSV, three existing test comparison/report workbooks, comparison exclusions,
  native best model and retained telemetry/provenance. Redundant evaluation summaries,
  match/threshold/methodology sidecar artifacts are replaced by canonical outputs;
  necessary local diagnostics and historical outputs remain intact.
- FR-006: Publish four interactive confusion variants preserving class order/background;
  rows true, columns predicted; hover shows counts/denominators and zero observations.
- FR-007: Publish class PR with recall X, precision Y in [0,1], AP50/method/context and
  confidence/cumulative TP/FP hover. Public dependency matching reconstructs authoritative
  compute_map populations/order/precision, verified for AP50 parity without dependency edits.
  Empty predictions with GT mean AP50 zero; no GT means unavailable recall. No mismatched
  operating-point overlay and no PR CSV artifact.
- FR-008: Resolve names and verify model threshold association/readback as US3 describes;
  standalone metrics never creates or changes models. Artifact-first recovery persists.
- FR-009: Workers never publish. Required publication/flush/interruption failures prevent
  completion and retain local diagnostics. FiftyOne stays optional with link/local receipt.

## Key entities

Result context, source row, prepared-index mapping, evaluation relationship, confusion
payload, PR curve, durable context shard, invocation CSV bundle, naming state, owned model.
See [interfaces](contracts/interfaces.md).

## Success criteria

- SC-001: Downloads retain complete row lineage and exact workbook/threshold contents.
- SC-002: Reconstructed AP50 matches authoritative AP50 for the supported test matrix.
- SC-003: Exact command inventories upload once and fail reliably on required errors.
- SC-004: Repository checks, native CPU/GPU/ClearML verification, documentation validation
  and fresh independent review establish acceptance before applicable release gates.

## Assumptions and constraints

The supplied reviewed design is authoritative; no new design approval is needed.
Pinned dependencies, historical records, explicit paths and unrelated local source
overrides are preserved. No deployment or package/asset publication is authorized.
The current recovery amendment and explicit user intent supersede the stale historical
recovery prohibition in the constitution; installed workflow/governance files are unchanged.
