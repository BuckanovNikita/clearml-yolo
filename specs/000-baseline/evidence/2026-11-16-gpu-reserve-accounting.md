# Ticket98: conservative whole-device allocator admission

## Observed defect and scope

The [representative retry](../../014-estimated-batch-acceptance/evidence/2026-11-16-gpu-retry.md)
failed the 8 GiB free-memory reserve during capacity search. The reserve monitor
stopped owned computation; no acceptance training began. A subsequent metadata-only
process observed CUDA free memory 3,041,132,544 bytes above the contemporaneous
whole-device free reading. The process exited and left no compute PID. This
establishes an accounting discrepancy, not a specific driver-internals explanation.

The old `reserve_cuda_memory` trusted CUDA free bytes when setting PyTorch's
allocator fraction. The correction takes the lower of that reading and selected
CUDA device total bytes minus whole-device used bytes. Device properties resolve
the visible ordinal to UUID before looking up telemetry, preserving remapped device
selection. Missing telemetry fails before setting a fraction. Existing reservations,
256 MiB additional headroom, zero-reserve compatibility, negative validation and
external monitoring remain unchanged. Foreign/native-library allocation can still
change after admission; the monitor remains required.

This is a routine correction within feature014's existing optional reserve contract.
It changes no dependency, default reserve, capacity-search rule, timeout, training
recipe or documented failure/no-fallback behavior.

## Red/green verification

The existing product guard is the regression seam; only external Torch/telemetry
readings and allocator-setting effects are substituted. The first case supplied
24 GiB total, CUDA free 20 GiB, whole-device used 10 GiB, and an 8 GiB reserve.
Before correction it returned allocator fraction 0.48958333 instead of 0.23958333;
the reverse-order free-reading case already passed. These checks executed without
GPU allocation.

- **Passed**: original regression after correction, two cases.
- **Passed**: `pytest tests/test_gpu_memory.py tests/test_batch_probe.py tests/test_batch_estimation.py -q -n 0`, 204 tests in 3.22s, with CUDA hidden and two numerical threads.
- **Passed**: strict mypy on the changed product and test modules.
- **Passed**: Ruff check and format check on both modules after wrapping a new test expression.
- **Error, corrected invocation**: an initial command also named nonexistent `tests/test_probe_worker.py`; it collected no tests and is not counted as a pass. The corrected command above completed.
- **Pending**: fresh independent review, native scoped mutation report, final automatic gate and representative live retry.

Additional regressions cover missing telemetry, insufficient whole-device memory,
a competing physical GPU entry, selected visible ordinal, preservation of existing
allocator reservations, and no hardware query for disabled/invalid reserves.
CPU regressions do not establish preservation of the reserve during live training,
physical capacity, multi-GPU behavior or publication.

## Frozen implementation

- `src/clearml_yolo/adapters/runtime/gpu_memory.py`: `abb71bc16eb552c2176c73a9a592d6c7091f9839abb8c166da426b33ab3b0502`
- `tests/test_gpu_memory.py`: `626465526166761f8ff4950482cff9cc6a3245a42ef0741e7108412eace5ff14`

The source is compared with `fbcfa25` in the managed worktree; root HEAD remains
`e1fe64e` with task-owned integrated working changes and unrelated files preserved.
Remote references were not fetched. The coordinator owns commits and live execution.
No GPU/model/service process was started for these tests; all focused check
processes exited. No user data, upstream source or shared staging was changed.
