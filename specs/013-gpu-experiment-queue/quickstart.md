# Quickstart: validate the GPU experiment queue

This guide defines acceptance scenarios. Do not describe native GPU, DDP, ClearML, or upload
behavior as verified until the commands have run and their outcomes are recorded in dated evidence.

## Prerequisites

- Install the locked development environment with the repository's documented `uv` workflow.
- For deterministic tests, no NVIDIA hardware or ClearML connection is required.
- For native acceptance, use a host with at least two supported whole NVIDIA GPUs, valid NVML
  telemetry, ClearML access, an isolated project and tags, and task-owned input/output resources.
- Follow the repository `running-end-to-end-tests` skill and the applicable machine environment
  guidance before native execution.

## Deterministic acceptance

```bash
uv run pytest tests/test_gpu_resources.py tests/test_gpu_queue.py tests/test_gpu_execution.py tests/test_hydra_queue_launcher.py tests/test_pipeline.py
uv run ruff check .
uv run mypy .
uv run lint-imports
```

Expected outcomes:

- Native device forms produce the counts in [the execution contract](contracts/execution.md).
- Later small requests never bypass a blocked head request.
- Several head requests run concurrently when complete, non-overlapping allocations fit.
- External compute users and unknown telemetry prevent admission.
- Dead ownership is reclaimed only when both supervisor and child native liveness locks are
  acquirable; a held lock preserves ownership regardless of PID observations.
- Child failure/interruption releases reservations and reports nonzero.
- Hydra returns results in submission order while preserving callbacks and per-job context.

Build and inspect the wheel so both import roots are shipped:

```bash
uv build
python -m zipfile -l dist/*.whl
```

The wheel must contain `clearml_yolo` and `hydra_plugins/cy_queue`.

## Isolated queue-state scenario

Use the queue's internal constructor root in an isolated test. Submit a two-GPU job followed by a
one-GPU job on a simulated host with two supported GPUs while only one is currently free. Inspect
through the supported diagnostics/test boundary rather than editing registry state manually.

Expected: the valid two-GPU head remains pending and the later request does not start. When both GPUs
become available, the head receives both atomically. The later request starts after it becomes head
and one GPU is free.

A three-GPU request against that two-GPU visible set must fail before enqueue.

## Native pipeline acceptance

Run a minimal pipeline with explicit project name and tags, at least two training GPUs, and enabled
GPU prediction/comparison. Observe and record:

1. No ClearML task and no native GPU context exists while the request waits.
2. The admitted fresh child owns one ClearML task and receives concrete local training devices.
3. The requested native selector and effective concrete selector are recorded separately.
4. No reservation contracts before best-model verification and DDP worker cleanup.
5. Telemetry confirms N-1 released UUIDs are unused before they return to the queue.
6. Prediction and comparison both use retained child-local device `0`.
7. The first UUID remains reserved until the child exits; all state is then released.
8. Required artifacts/model uploads and task completion retain their current verification rules.

Also run CPU training with GPU inference enabled. Expected: one GPU is reserved before child start,
training remains CPU-backed, and downstream inference uses local `0` without reacquisition.

For GPU training with CPU-only downstream stages, the first assignment remains through child exit.

## Documentation validation

Run the repository Markdown/link checker when available and verify every changed relative link.
Review examples against current command composition. Record the exact command and result in dated
evidence; do not convert a planned scenario into a verification claim.
