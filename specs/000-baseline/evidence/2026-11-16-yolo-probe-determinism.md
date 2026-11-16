# Ticket96: Match native YOLO probe determinism

## Finding and correction

Fresh independent review of ticket03 found that YOLO profiles recorded `seed` and
`deterministic`, while the probe initialized only the Torch seed. The installed
Ultralytics 8.4.184 trainer instead calls
`init_seeds(args.seed + 1 + RANK, deterministic=args.deterministic)` before model
allocation. That helper seeds Python, NumPy and Torch; it enables or clears native
deterministic algorithms, warn-only behavior, cuDNN determinism, uninitialized-memory
fill policy, `CUBLAS_WORKSPACE_CONFIG`, and `PYTHONHASHSEED`.

The product probe now delegates to this installed helper before model construction.
Its private worker protocol sets `RANK=0` even with one worker, so one-rank probes
use native rank -1 to match ordinary single-device training. Distributed probes use
global `RANK`, not device-local `LOCAL_RANK`, for the native `seed + 1 + rank` offset.
The change preserves the BF16/scaler fix, explicit-recipe rejection, model loading,
optimizer selection and other backends. No upstream source or dependency changed.

This is a routine correction of the exact-recipe contract, also covered by feature014
FR-001/005. Ticket03 live capacity acceptance depends on its acceptance. No separate
capability or competing specification was introduced.

## Red/green verification

Eight CPU regressions exercise public `batch_probe.probe()` up to the external YOLO
asset-construction boundary. Only CUDA peak-stat reset and model asset construction
are replaced; native initialization and actual Python/NumPy/Torch random streams
execute. Each test starts with the opposite native deterministic policy, then checks
both enabling and clearing it. Cases cover one-rank execution, distributed global
ranks 0/1, and global rank 1 with local rank 0 to distinguish the two rank concepts.
All eight failed before the product edit with unchanged algorithm flags and Python/
NumPy seeds, plus missing distributed Torch seed offsets.

The shared autouse fixture in `test_yolo_probe_precision.py` restores process RNG
state, deterministic/warn-only/cuDNN/fill flags and both affected environment values.
The new determinism module imports that fixture, so prior precision-boundary tests
remain isolated after native initialization starts changing global state.

After the coordinator's pre-fix full coverage completed, the product edit was applied.
The prior precision file was restored to its exact frozen hash while that full run
was in progress; the red regression was kept in a new file until the green edit.

- **Passed**: focused locked pytest on `test_yolo_probe_determinism.py`,
  `test_yolo_probe_precision.py`, `test_batch_profiles.py`, `test_batch_probe.py`:
  156 passed, 19 warnings in 4.28 seconds.
- **Passed**: strict mypy for the changed probe and both test modules.
- **Passed**: Ruff check and format check for those three files.
- **Budget-limited mutation evidence**: the preceding three-function native run
  selected `probe`, `_optimize`, and `batch_probe_settings`, with one child and a
  180-second limit. Its stats pass consumed the budget: all 349 mutants were unrun,
  with none judged killed or surviving. That snapshot preceded the deterministic
  correction and makes no claim for the new call. The coordinator explicitly declined
  a budget extension; details are in the [recipe evidence](../../014-estimated-batch-acceptance/evidence/2026-11-16-yolo-probe-recipe.md).
- **Pending coordinator**: fresh independent review, final automatic checks on the
  integrated snapshot, and commit/integration evidence. The coordinator's completed
  full-suite baseline precedes this focused correction and is not represented here
  as a run against the corrected source.

All checks used CPU affinity 0,1 and nice19. These tests establish actual CPU native
initialization and policy at the model boundary. They do not establish CUDA kernel
selection, CUDA numerical determinism, physical DDP, BF16 GPU execution, GPU capacity,
or live publication; those remain separate campaign acceptance evidence.

## Frozen corrected snapshot

| Path | SHA-256 |
| --- | --- |
| `src/clearml_yolo/adapters/yolo/batch_probe.py` | `868baec5b65b40695e39bde00dc1eb3d25340bd1069e84dde0b93dfae463dc3b` |
| `tests/test_yolo_probe_precision.py` | `d62fbf4835498e1293b853f67c7f5936b39b2887e71f193c9c7e158b3a93353f` |
| `tests/test_yolo_probe_determinism.py` | `5063a555ba43a8ec67d606f64f463f23987f157efc59d84c973b0f1de2154906` |
| Installed `ultralytics/utils/torch_utils.py` | `274357cc6841205d1eb5a6016ff81bfd2ec961c53d1f689380bd0222ec3b1c33` |

All owned test/type-check processes exited. `.tmp/yolo-deterministic-red` and
`.tmp/yolo-deterministic-green` were removed after recording outcomes. The preceding
mutation export, private index and temporary report were also removed. No GPU job,
remote service, shared index modification, commit, or unrelated cleanup was performed.

## Combined mutation follow-up

The later [ticket96/97 mutation report](2026-11-16-yolo-probe-mutation-96-97.md)
checks the combined current source: 33 native mutants killed, ten timed out and
191 unrun within budget. A fresh private copy passed the 16 current targeted tests;
restoring Torch-only seeding then failed all eight determinism cases. This new
advisory evidence supplements the earlier stats-only run without claiming full
mutation coverage or resolving the timeout outcomes.
