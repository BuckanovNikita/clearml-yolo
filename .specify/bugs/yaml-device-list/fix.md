# Bug Fix: Hydra device list serialization

- **Slug**: yaml-device-list (from assessment context)
- **Fixed**: 2026-10-12
- **Assessment**: [assessment](assessment.md)
- **Status**: applied

## Summary and changes

`_device_values` now applies `OmegaConf.to_container(resolve=True, throw_on_missing=True)`
to configuration-valued devices at the Hydra boundary. YAML snapshots and ClearML
provenance receive independent plain lists; scalar values retain their shape. Requested
device intent remains separate from selected execution ordinals. SDK code, YAML global
representers, dependencies and scheduling policy are unchanged.

| File | Change |
| --- | --- |
| `src/clearml_yolo/entrypoints/hydra/common.py` | Convert device snapshots before passing them to application adapters |
| `tests/test_gpu_execution.py` | Real YAML/JSON round trips through assigned execution, scalar forms and detached interpolated detector values |

## Verification

Before implementation, the new tests produced three failures with the reported
`RepresenterError`; six scalar checks already passed. After implementation, all 197
focused GPU-execution/configuration/replay/pipeline/training/detector tests passed.
Ruff and import-linter passed. Full results are maintained in [verification](test.md).

## Documentation update

Reviewed README device/DDP instructions, `docs/project-contracts.md`,
`docs/current-contracts.md`, `docs/runtime-isolation.md` and the feature 022 GPU execution
contract. They already require list device support and separate requested/effective
snapshots. The fix restores those contracts without changing commands, configuration,
outputs or scheduling semantics; no normative documentation change is needed.
The bug records document reproduction, remediation, checks and limits.

## Deviations and follow-ups

None. The user's original full launch cannot be replayed because its command/configuration
and complete traceback are unavailable. Verification covers the exact locally reproduced
serialization path, not physical five-GPU training.
