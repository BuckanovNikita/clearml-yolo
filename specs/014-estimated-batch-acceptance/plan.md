# Implementation Plan: Estimated-batch native acceptance

**Branch**: `master` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

## Summary

Pass explicit training recipes through native batch-profile/probe boundaries, execute
custom augmentation during bounded synthetic probes, and update the maintained
acceptance harness to estimate before its two-epoch training invocation.

## Technical Context

Python >=3.12.13,<3.14; existing Pydantic, Torch, native backends, Albumentations,
Hydra and ClearML dependencies. JSON evidence and existing catalogue storage. Linux
single-GPU execution; pytest at public product seams. Preserve installed versions,
search strategy, five warmup/ten measured updates and existing 300s trial/1800s
scenario bounds. Scope is 21 selections by three variants; no external topology.

## Constitution Check

Before research and after design: typed boundaries retained; core remains pure;
SDK/telemetry/process effects stay in adapters; orchestration stays in the acceptance
owner. No source dependency changes. Existing CLI defaults and catalogue behavior
remain compatible. Product tests exercise actual behavior, not harness settings.
Independent review follows integration and selected checks. Live evidence is separate
from mocked checks. Spec Kit owns these artifacts; installed tooling is unchanged.

## Project Structure

- `src/clearml_yolo/core/batch_estimation.py`: optional reserve and pure batch selection.
- `src/clearml_yolo/application/training_workers.py`: serialized recipe in probe requests.
- `src/clearml_yolo/adapters/integrations/batch_profiles.py`, `batch_probe.py`: identity and worker ownership.
- `src/clearml_yolo/adapters/augmentation/`: shared synthetic custom-pipeline execution.
- Existing YOLO/DEIM/RF-DETR/Torchvision probe modules: selected recipe and actual augmentation.
- `src/clearml_yolo/adapters/integrations/native_trainer.py`: opt-in fixed batch/epoch execution.
- `src/clearml_yolo/adapters/runtime/gpu_memory.py`: optional allocator cap, with external telemetry authoritative.
- `tests/severstal_harness.py` and `tests/severstal_batch.py`: fresh estimate, admission, two epochs and readback.
- `tests/test_batch_*.py`, `tests/test_*probe.py`: product-boundary regressions.
- `docs/augmentation.md`, `docs/batch-estimation.md`: maintained behavior.

## Verification

Run focused red/green product regressions, strict typing/lint and architecture checks,
changed-function mutation review, then coordinator-owned representative native GPU
execution and independent review. The coordinator runs the full suite once at the end.
No deployment/release and no nested delegation.
