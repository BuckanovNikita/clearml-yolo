# Cleanup decisions

- **Decision**: Require CSV ground truth for training. **Reason**: The user selected removal
  of every legacy path. Retaining native-only training under a renamed label was rejected.
- **Decision**: Recover only current best Output Models and validation threshold CSV.
  **Reason**: Publication and recovery should have one contract. Historical payload readers
  and checkpoint artifacts were rejected as obsolete support.
- **Decision**: Use the shared evaluation model without comparison overlays. **Reason**:
  Current pipeline and metrics already consume that model.
- **Decision**: Retain runtime interoperability, explicit destinations, metric plots and
  artifact deduplication. **Reason**: These serve current runs, despite compatibility-like names.
- **Decision**: Preserve completed historical records and dependency revisions. **Reason**:
  Cleanup changes current behavior, not prior observations or upstream ownership.
- **Decision**: Amend only the authorized constitution under `.specify/`. **Reason**:
  Installed workflow tooling and feature state are protected by repository instructions.

## Approved recovery amendment decisions (2026-10-05)

- **Decision**: Restore only task-backed checkpoint/threshold recovery per the
  [recovery contract](contracts/task-recovery.md). **Rationale**: Existing published tasks need
  fresh current-image comparison; restoring native-only training/config aliases is unnecessary.
  **Alternative rejected**: Requiring republishing every source task or recalibrating thresholds.
- **Decision**: Prefer explicit maps, then named threshold artifacts, then historical dashboards.
  **Rationale**: Preserve the best available precision; dashboard rounding/provenance limits
  must be visible. **Alternative rejected**: Swallowing malformed preferred sources and falling
  back, or selecting thresholds according to the current comparison split.
- **Decision**: Select a source once and use it for weights and provenance. **Rationale**:
  Independent selection can mislabel the checkpoint actually compared. **Alternative rejected**:
  Fabricated model links for artifacts or bulk downloads to guess a usable source.
- **Decision**: Preserve the constitution/history without modifying `.specify/` under the
  approved plan. **Rationale**: User approval narrowly supersedes the recorded recovery ban;
  remaining governance and installed workflow files retain their existing scope.
