# Ticket98: Preliminary independent review and reserve-guard mutation evidence

## Review scope and verdict

Independent review compared the initial ticket98 change with `fbcfa25`: only
`reserve_cuda_memory` and its product tests. The reviewed product source is
`abb71bc16eb552c2176c73a9a592d6c7091f9839abb8c166da426b33ab3b0502`, committed by
the coordinator as `5f6746b`; the initial test hash was
`626465526166761f8ff4950482cff9cc6a3245a42ef0741e7108412eace5ff14`.

**Verdict on that implementation: approved; no blocking source findings.**

- Device properties resolve the explicit visible CUDA ordinal to UUID. The
  `GPU-<uuid>` convention matches existing `discover_gpus`; lookup does not assume
  that physical `nvidia-smi` order matches `CUDA_VISIBLE_DEVICES`. The worker passes
  its local ordinal after `native_rank` sets the current device.
- The lower of CUDA free bytes and device-total minus telemetry-used bytes limits
  the budget. Adding existing process reservations preserves the distinction between
  an absolute allocator ceiling and additional allocatable memory. The 256 MiB
  margin and positive reserve remain subtracted before division by CUDA total.
- Missing selected telemetry raises before the fraction setter. Telemetry-query
  errors also propagate without changing the allocator limit. Zero and negative
  reserves leave hardware untouched through their existing early paths.
- Tests cover both free-reading orderings, a competing physical UUID, visible
  ordinal 1, existing reservations, missing/insufficient memory, and disabled/invalid
  inputs. The reviewer independently ran the file: 9 passed in 1.16 seconds.

This verdict is **preliminary for the expanded ticket98 scope**. A subsequent live
retry exposed a separate `gpu_inventory` accounting issue: total minus `memory.used`
omitted reserved/unavailable memory visible in explicit `memory.free`. The
coordinator owns that extension and its tests. Its final integrated review and live
reserve evidence are not supplied by this guard-only report.

## Native mutation selection

The unmodified native mutation API exported an isolated `GIT_INDEX_FILE` containing
the current `src/` and `tests/` snapshot. Explicit module selection was narrowed to
`reserve_cuda_memory`, the complete changed function. The run retained normal native
test selection, exclusions, and process cleanup. Commands used the locked environment,
CPU affinity 0,1, nice19, two numerical threads, one mutmut child, and a 300-second
maximum budget. Both runs finished within that budget without timeouts or unrun
mutants.

Preflight found stale local testmon history selecting only the two old memory-sampler
tests from `test_gpu_memory.py`, suppressing the import fallback for the new guard
tests. A native `pytest --testmon-noselect tests/test_gpu_memory.py` refresh passed
9 tests in 1.87 seconds and made all new guard regressions eligible. No selector or
tooling policy was changed.

Invocation shape:

```python
# Private GIT_INDEX_FILE: git read-tree HEAD; git add -- src tests
mutation.export_staged_tree(export)
targets = [
    target for target in mutation.collect_targets(export, "fbcfa25", (source,))
    if target.qualname == "reserve_cuda_memory"
]
mutation.mutate(export, targets, mutation.Options(
    files=(source,), base="fbcfa25", keep=False, strict=False,
    max_children=1, max_functions=0, budget_seconds=300,
))
```

Native selection retained 10 selectors across five files: the selected memory-guard/
sampler tests and whole batch-probe, DEIM-probe, RF-DETR-probe and torchvision-
distributed modules. Native marker exclusions removed host-wide process/DDP/GPU
checks. Exact selectors and all mutant outcomes are retained in the JSON inventories.

## Test strengthening and rerun

The [initial inventory](2026-11-16-gpu-reserve-mutation-initial.json) contains 53
mutants: 40 killed and 13 survived. Four survivors exposed useful assertion gaps,
not incorrect product code. With coordinator authorization, only
`tests/test_gpu_memory.py` changed:

- Exercise the omitted device argument and observe default ordinal zero.
- Check that CUDA free-memory and current-reservation queries receive the selected
  nondefault ordinal, in addition to the existing properties/UUID and setter checks.
- Exercise exact equality: free memory equals requested reserve plus 256 MiB,
  leaving no additional allocator budget; the guard must reject before setting it.

The strengthened file hash is
`672f365722f645e2513dcb25dfabb46bbd90c3c1f11de4823ce0122199845f04`.
Focused tests and refreshed native history passed **10 tests in 1.76 seconds**;
strict mypy, Ruff check and format check passed. Product source remained unchanged.

The [rerun inventory](2026-11-16-gpu-reserve-mutation.json) contains:

| Outcome | Initial | Strengthened |
| --- | ---: | ---: |
| Killed | 40 | 44 |
| Survived | 13 | 9 |
| Timeout | 0 | 0 |
| Unreached | 0 | 0 |
| Unrun | 0 | 0 |

The four strengthened observations kill suffixes 1, 11, 13, and 38. Both native runs
completed their stats, clean-test, and forced-failure checks and returned advisory
exit 0. Surviving suffixes share prefix
`clearml_yolo.adapters.runtime.gpu_memory.x_reserve_cuda_memory__mutmut_`:

| Suffixes | Disposition |
| --- | --- |
| 7, 8, 20, 21, 40, 41 | Error-message case/prefix/suffix changes only. Exception type and meaningful error category remain; no exact-wording assertion added. |
| 4 | `< 0` to `<= 0` after zero has already returned: equivalent on integer inputs. |
| 5 | `< 0` to `< 1` after zero has already returned: equivalent on the declared integer-byte domain. |
| 49 | Upper fraction clamp 1.0 to 2.0: inactive under coherent CUDA readings, where free plus this allocator's reservations cannot exceed total, and positive reserve/headroom are subtracted. Inconsistent or racy snapshots are outside this equivalence; no claim is made for them, and external monitoring remains required. |

No survivor allowlist, product edit, dependency change, or test weakening was made.
These checks substitute external CUDA/telemetry boundaries and establish CPU-visible
guard behavior. They do not establish a live reserve guarantee, physical GPU capacity,
multi-GPU behavior, or completed training/publication acceptance.

## Ownership and cleanup

The reviewer authored the four test observations after independently reviewing the
unchanged guard implementation; the coordinator owns their integration and final
gate. The expanded `gpu_inventory` product change still requires integrated review.
All owned mutation/test processes exited; private indexes/exports were removed in
`finally`, and temporary logs/test roots were removed after extracting the inventories.
No GPU workload, shared staging, commit, upstream edit, or unrelated cleanup occurred.
