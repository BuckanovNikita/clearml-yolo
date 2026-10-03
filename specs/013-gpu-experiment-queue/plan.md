# Implementation Plan: GPU experiment queue

**Feature**: `013-gpu-experiment-queue` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

## Summary

Add a user-wide same-OS FIFO scheduler around the five model commands. Derive atomic whole-GPU
demand from native device configuration, exclude externally used devices through NVML telemetry,
isolate inherited-visibility mapping, and launch admitted work in fresh children that own the existing ClearML lifecycle. Add a
BasicSweeper-compatible Hydra launcher and contract multi-GPU pipelines to one retained device only
after verified native/DDP cleanup.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Hydra, hydra-zen, Pydantic, filelock, nvidia-ml-py, Ultralytics, ClearML

**Storage**: Atomic JSON-compatible local registry under the per-user OS state directory; existing
run, dataset, ClearML, and native outputs remain unchanged

**Testing**: pytest with controlled process/clock/probe boundaries; Ruff, strict mypy,
import-linter; native multi-GPU/ClearML acceptance under the repository end-to-end contract

**Target Platform**: Supported Unix-like and Windows local execution with NVIDIA whole GPUs;
same-user coordination within one OS instance

**Project Type**: Python CLI applications and Hydra launcher plugin

**Performance Goals**: Registry locks cover only bounded read-modify-write transactions; waiting
does not serialize admitted jobs; every head request that fits can be admitted in the same pass

**Constraints**: Strict head-of-line FIFO; atomic N-device reservation; fail-closed telemetry;
no daemon, TTL, PID-only reclaim, bypass, priority, MIG, remote host, or new count configuration;
no native GPU context or ClearML task before admission

**Scale/Scope**: Five model commands, BasicSweeper local multiruns, one user-wide queue per OS;
whole NVIDIA GPUs only

## Constitution Check

Constitution 7.0.0 was required because version 6.0.0 prohibited runtime GPU scheduling.
The explicitly authorized amendment permits only this user-wide, local, whole-device scheduler and
keeps native model configuration authoritative. The design preserves strict typing, module/import
boundaries, one ClearML task per admitted execution child, delayed model imports, output ownership,
upstream-native execution, credential protection, direct dependency declaration, proportional
tests, native evidence rules, and safe collaboration.

Pre-design gate: PASS after the narrow 7.0.0 amendment. No other principle exception is required.

Post-design gate: PASS. Queue/probe modules remain independent of Hydra, ClearML, Ultralytics, and
Torch; app execution owns process launch; the Hydra plugin delegates to public execution contracts;
pipeline contraction uses application boundaries without upstream monkeypatching.

## Project Structure

### Documentation (this feature)

```text
specs/013-gpu-experiment-queue/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── execution.md
│   └── queue-state.md
├── checklists/
│   ├── requirements.md
│   └── scheduling.md
├── tasks.md
└── analysis.md
```

### Source and tests

```text
src/
├── clearml_yolo/
│   ├── gpu_resources.py
│   ├── gpu_queue.py
│   ├── gpu_runtime.py
│   ├── apps/
│   │   ├── common.py
│   │   ├── execution.py
│   │   └── job_worker.py
│   ├── configs.py
│   └── tasks/pipeline.py
└── hydra_plugins/cy_queue/
    ├── __init__.py
    └── launcher.py

tests/
├── test_gpu_resources.py
├── test_gpu_queue.py
├── gpu_queue_worker.py
├── test_gpu_execution.py
├── test_hydra_queue_launcher.py
├── test_configs.py
└── test_pipeline.py
```

**Structure Decision**: Keep GPU inventory and durable scheduling as low-level typed modules.
Centralize supervision in `apps/execution.py`, fresh-process execution in `apps/job_worker.py`, and
invocation-scoped reservation transitions in `gpu_runtime.py`; model app entrypoints call that seam.
Register a separately discoverable Hydra plugin in `src/hydra_plugins/cy_queue`. Limit task-layer
change to the verified pipeline reservation contraction boundary.

## Design Phases

### Phase 1: Resource model and queue

Implement native-device demand normalization, direct NVML telemetry, and isolated inherited-
visibility mapping to UUIDs. Implement validated durable registry state,
short lock transactions, ticket allocation, strict-head admission, liveness reconciliation, atomic
reservation/contraction, and terminal release.

### Phase 2: Execution and Hydra integration

Split app preparation from execution so waiting precedes ClearML and native imports. Launch each
admitted job in a fresh child with assigned visibility and concrete effective device settings.
Register the queue-aware local launcher for the five model commands and preserve BasicSweeper job
ordering, callbacks, environment, output directory, chdir, and status behavior.

### Phase 3: Pipeline transition

Derive pipeline demand as the maximum of training and enabled GPU-inference demand. After native
model verification and DDP cleanup, consult telemetry and contract N devices to the first retained
UUID. Route GPU prediction and comparison to local `0`; retain the first UUID through child exit
for CPU-only downstream stages as well.

### Phase 4: Acceptance and documentation

Run focused deterministic tests, full repository gates, artifact build/import checks, and the
quickstart. Record dated native multi-GPU/ClearML evidence before claiming the runtime behavior was
exercised. Update current contracts, README, filesystem policy, and portable end-to-end guidance;
validate Markdown, links, and documented commands.

## Documentation Update

Update `README.md`, `docs/project-contracts.md`, `docs/current-contracts.md`,
`docs/filesystem-policy.md`, and
`.agents/skills/running-end-to-end-tests/references/pipeline-prerequisites.md`. The new feature
contracts become maintained authority for scheduling and queued execution. Amend the constitution
to 7.0.0. Update the active native configuration and configuration/artifact contracts to distinguish
requested device values from child-local effective values. Preserve dated historical evidence and
annotate any older active statement superseded by the queue contract. Machine-specific examples
remain outside this repository scope.

## Verification Strategy

- Unit/contract tests: device normalization, visibility mapping, external-use exclusion, telemetry
  failure, registry validation, oversized-demand rejection, strict FIFO, atomic N allocation,
  native-lock liveness, spawn failure,
  interruption, release, and pipeline contraction.
- Hydra tests: default launcher composition for exactly five commands, BasicSweeper concurrent
  fresh children, callback/environment/directory/chdir preservation, ordered `JobReturn`, nonzero
  failures, and wheel discovery of both modules.
- Integration/static gates: focused pytest, full pytest, Ruff, mypy, import-linter, build and wheel
  contents/imports.
- Native acceptance: same-user contention plus real multi-GPU training, DDP cleanup observation,
  early N-1 release, retained-device inference, ClearML task ownership/publication, and cleanup.
  Store actual counts/times/outcomes only in dated evidence.

## Complexity Tracking

No unapproved constitution violation remains after amendment 7.0.0. The new plugin namespace is
required by Hydra discovery; process isolation is required to keep pre-admission supervisors free
of native GPU context.
