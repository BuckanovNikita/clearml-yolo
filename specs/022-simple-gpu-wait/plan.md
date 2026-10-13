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

## Amendment plan: configurable memory availability (2026-10-12)

Use an SDK-free Pydantic automatic-GPU control with a finite positive
`max_used_memory_gib` default of 2.0. Query NVML total used bytes in GPUInventory,
compare strictly below the binary GiB cutoff, and remove process-count eligibility.
Keep GPUDevice's busy interface, visibility ordering and fail-closed telemetry.
Wire the setting through Hydra composition/export, wrapper validation, direct waiting,
queued admission, worker contraction and execution-policy provenance. Do not resolve
dependencies or change installed workflow files.

Shared queue policy must belong to the invoking job: preserve registry v1 by having
each supervisor admit only its own FIFO-head ticket with its configured inventory.
Other supervisors poll their own tickets; active reservations always exclude devices.
Worker contraction uses the launch limit after existing native cleanup.
Resolve queued policy with the job's Hydra context and environment, then freeze its
validated values before worker transport; worker startup must not re-evaluate resolvers.

Parent owns implementation, tests and documentation. A bounded read-only investigator
checks independent configuration/queue risks in parallel. Regression tests precede
implementation; integration and parent checks precede a fresh independent review.
No concurrent writers or worktree are needed for this amendment.

Documentation scope: maintained execution and queue-state contracts, project contract
summary, README and GPU quickstart; append this spec/plan/task amendment and dated
verification without rewriting completed history. Validate changed Markdown, local
links, exported YAML and threshold override examples. Relevant tests cover inventory,
direct/queued execution, queue sharing, replay, CPU bypass and configuration export;
run repository lint/type/import and commit gates before the authorized Git-tag release.

## Amendment plan: force and readable admission (2026-10-12)

Implement FR-011–015 in the existing layers, without changing dependencies or registry
v1. See [architecture.json](architecture.json) for module scope and executable gates.
Core owns strict force and concrete-selector validation. Runtime scheduling reads
effective switches; Hydra common owns replay protection and provenance; launcher
routes effective unqueued jobs through BasicLauncher. Inventory records retain UUID
and busy compatibility while adding physical/logical indexes and measured bytes.
Admission diagnostics are immutable snapshots of one telemetry sample and locked
registry view. Ticket acquisition still returns UUID tuples or None. Presentation
uses diagnostics after the lock, tracking categorical reasons for throttled refresh.

Parallel ownership: policy delegate owns core/execution.py, gpu_scheduling.py,
Hydra common.py, launcher.py and dedicated force tests. Inventory delegate owns
gpu_resources.py and its tests. Parent owns gpu_queue.py, gpu_wait.py, Hydra
execution.py, diagnostic tests, artifacts and documentation. Agree data interfaces
before integration. Inventory and policy work are independent after this gate; queue
integration, parent verification, fresh independent review and acceptance are sequential.
Preserve pre-existing static-analysis edits (including gpu_queue.py cleanup comment).

Documentation scope: README, maintained execution/queue contracts, GPU quickstart,
project/current contract summaries and diagnostic guide. Validate Markdown, local
links and generated configuration examples. Record native checks and hardware limits
in dated evidence; do not claim the original waiting cause was established.

Integration reconciliation: direct polling publishes immutable decisions through an
optional callback; formatting/throttling live in the existing Hydra execution
boundary. The launcher implementation already routes effective controls and needs
only regression coverage, not a source edit. The explicit force requirement
supersedes the historical constitution's prohibition on bypass while leaving queued
admission invariants unchanged. No installed workflow/governance files are modified.

## Release verification resume — 2026-10-13

The user requested verification and release after source delivery. Resume T027
and T030 against the committed force implementation; preserve earlier failed and
successful observations. Expected writes are this plan, tasks and dated evidence,
architecture acceptance reconciliation, and generated release metadata/changelog.
Only the root package version may change in `pyproject.toml` and `uv.lock`.
No runtime interfaces, effects, module placement or dependency references change.
The existing module/import contracts remain the executable acceptance boundary.

Parallel work: a bounded native-verification delegate owns tagged CPU/GPU execution,
fresh exact-task status/policy/artifact readback and scoped cleanup; a separate
packaging delegate owns wheel/source installation, command helps and generated
configuration checks in external temporary environments. Parent owns isolation,
quality/architecture checks, documentation, acceptance review and release. Agents
write only their external evidence. Live verification precedes task closure and
release; final integrated evidence receives fresh independent read-only review.

Use the documented shared-stand environment without SDK or application patches.
Synthetic native runs establish execution and publication, not model accuracy.
Keep physical multi-GPU/DDP/MPS limitations explicit. Reuse the already reviewed
force/admission implementation and require ordinary commit/release hooks. Publish
only the checked branch and annotated Git tag after every applicable gate passes.
