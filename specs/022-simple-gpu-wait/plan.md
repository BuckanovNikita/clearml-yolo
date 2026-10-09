# Implementation Plan: Simple GPU waiting

**Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

## Summary

Replace queued execution with direct invocation after a stateless GPU availability
poll. Reuse demand normalization and NVML/isolated visibility discovery. Select CUDA
logical indices in inherited visibility order without changing CUDA_VISIBLE_DEVICES.
Remove queue storage, liveness locks, worker supervision and the custom Hydra launcher.

## Technical Context

Python 3.12; existing Hydra, Ultralytics, pynvml and uv tooling. No dependency changes.
The poll returns logical indices, never a reservation. Ignore only the invoking PID
in NVML compute users so sequential jobs do not wait on their own CUDA context.
Use existing native memory cleanup between training/prediction and after GPU invocations.
Preserve explicit CPU/MPS values and requested YAML; record selected/effective devices
without claiming reserved UUIDs or scheduler phases.

## Constitution Check

The user's explicit queue-removal instruction supersedes the FIFO/reservation/child
requirements recorded in constitution amendment 7.0.0 and feature 013. Preserve that
dated history and installed `.specify/` files; this feature and the current contract
index record the new authority. Single-task ownership, architecture, dependency pins,
publication verification, privacy and interruption requirements remain applicable.

## Project Structure

- Add `adapters/runtime/gpu_wait.py`; retain `gpu_resources.py` and `gpu_probe.py`.
- Simplify `entrypoints/hydra/common.py`, `execution.py` and `configs.py`.
- Remove `gpu_queue.py`, `gpu_runtime.py`, queued `worker.py` and `hydra_plugins/cy_queue`.
- Bind the resource cleanup port directly to native training-memory cleanup.
- Replace queue tests with wait/direct-execution and standard multirun tests.
- Update distribution/import contracts and architecture target checks.

## Research and Decisions

The installed Ultralytics runtime accepts logical device indices relative to inherited
CUDA visibility. Passing selected logical indices avoids changing CUDA visibility after
CUDA initialization in sequential multiruns. Keep the isolated metadata probe to avoid
initializing the invoking process before the wait. Availability polling cannot atomically
exclude concurrent starts; no replacement lock or hidden reservation will be introduced.

## Documentation Update

Update README.md (Russian), docs/current-contracts.md, project-contracts.md,
filesystem-policy.md, development.md, import-boundaries.md, python-import-migration.md,
the end-to-end skill/prerequisites and the feature 013 maintained contracts with a
superseding link. Preserve completed task history and dated evidence. Validate Markdown,
local links and generated configuration examples. Record native verification separately
from mocked tests, and retain the already-observed full-pipeline model-readback failure
as a pre-existing verification limitation unless independently resolved.

## Verification

Use failing regression tests first, then affected/full pytest, Ruff, mypy, import-linter,
generated YAML and all command helps. Exercise direct real CPU/GPU command completion
and sequential sweep behavior. Inspect distributions for absence of queue plugin/worker.
Parent verifies the combined diff before a fresh independent read-only review.
