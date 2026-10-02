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
