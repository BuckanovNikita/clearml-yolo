# Tickets96/97: Bounded YOLO probe mutation disposition

## Scope and source identity

The product diff against `4b73f62` changes only `batch_probe.probe`: native seed/
determinism initialization and concrete candidate-batch binding. The checked source
SHA-256 is `55fd12ccf58cfc6fe58ea69fb48dfb3485e66fc68cd6eb1d0dd0d20956cfeed3`,
matching the coordinator's reviewed source and canonical gate snapshot
`fbcfa251e4b26ffd786d2e4cb72174fa4fe8606a`.

This implementer ran from `/mnt/wsl/data/nkt/clearml-yolo`, local `master` at
`e1fe64ea7a053bb39daf4d8f477f63e4a6a8a236` with the integrated working changes;
local HEAD equaled local master and remote references were not fetched. The
coordinator's canonical commits are in a separate managed worktree. Exact source
hashes, rather than an unrelated worktree HEAD, identify the tested implementation.
The [machine-readable inventory](2026-11-16-yolo-probe-mutation-96-97.json) records
all source/test hashes, selected tests, 234 native statuses, timeout diffs, and the
fresh-process check commands and outcomes.

## Native bounded run

The prior three-function run included broad configuration dependencies and exhausted
its budget during statistics. This run used the unchanged native mutation API with
an isolated `GIT_INDEX_FILE` and export. It narrowed the explicit module to `probe`,
the whole function changed by these two tickets, while preserving native testmon/
import-based test selection. No source, mutation settings, dependencies or shared
index were modified.

Invocation shape (private paths omitted):

```python
# Run under: nice -n 19 taskset -c 0,1 env OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
#            uv run --locked python ...
# GIT_INDEX_FILE points to a unique temporary index.
# git read-tree HEAD; git add -- src tests
mutation.export_staged_tree(export)
targets = [target for target in mutation.collect_targets(export, "4b73f62", (source,)) if target.qualname == "probe"]
mutation.mutate(
    export,
    targets,
    mutation.Options(
        files=(source,),
        base="4b73f62",
        keep=False,
        strict=False,
        max_children=1,
        max_functions=0,
        budget_seconds=300,
    ),
)
```

Native selection contained **16 selectors across four files**: selected existing
`test_batch_probe.py` nodes and the entire batch-binding, determinism, and precision
modules. Parameterization expands those selectors. The native statistics pass,
clean tests, and forced-failure sanity check all completed before mutation judging.

| Native outcome | Count |
| --- | ---: |
| Killed | 33 |
| Timed out | 10 |
| Actually survived | 0 |
| Unreached by tests | 0 |
| Unrun within budget | 191 |
| Total selected mutants | 234 |

The 300-second bounded run stopped gracefully and returned advisory exit 0. The
native textual summary calls all ten timeout outcomes “survived”; the saved raw
statuses are `timeout`, not `survived`. Its graceful SIGINT return also omitted a
separate budget message. Neither detail turns the timeouts or 191 unrun mutants
into successful verification. This is a completed **advisory report with explicit
limits**, not full mutation coverage.

### Timeout disposition

Every timeout is inconclusive. No production change or equivalent-mutant exemption
is justified by these outcomes. They affect existing setup/telemetry statements:

| Mutant suffix | Mutation | Disposition |
| --- | --- | --- |
| 2 | Pass null catalogue architecture to recipe settings | Timeout; no equivalence or correctness conclusion |
| 6 | Replace local rank with null | Timeout; rank/device semantics remain unjudged |
| 11 | Replace per-rank batch with null | Timeout; downstream failure not observed within native run |
| 12 | Replace integer batch division with floating division | Timeout; downstream type failure not observed |
| 13 | Replace device with null | Timeout; CPU/GPU placement semantics remain unjudged |
| 15 | Use null CUDA ordinal | Timeout; current-device equivalence is not assumed |
| 16 | Construct device from rank alone | Timeout; accelerator/device behavior remains unjudged |
| 17 | Omit CUDA ordinal | Timeout; current-device equivalence is not assumed |
| 42 | Reset peak statistics on implicit device | Timeout; telemetry correctness remains unjudged |
| 43 | Replace memory observer with null | Timeout; downstream failure not observed |

All IDs share prefix `clearml_yolo.adapters.yolo.batch_probe.x_probe__mutmut_`.
The unrun mutants include the candidate-batch overlay. No budget extension or broad
repeat was performed; the coordinator requested the exact focused checks below.

## Fresh exact-current regression reversions

A second private index/export started with the same frozen source. Each check used
a fresh Python process and a 45-second timeout, preserving the installed pytest
test-isolation flags (`-n 0`, no cacheprovider/randomly/coverage). `PYTHONPATH` pointed
to that export's `src`, and only external CUDA/asset boundaries were substituted by
the existing product tests. The tests executed real native CPU behavior.

| Private source variant | Selected module(s) | Result |
| --- | --- | --- |
| Unmodified current source | Batch binding + determinism | 16 passed in 2.95s |
| Remove only `batch=request.global_batch` from execution settings | Batch binding | 8 failed in 2.91s; reversion killed |
| Replace native `init_seeds` call with the prior Torch-only seeding call | Determinism | 8 failed in 2.25s; reversion killed |

These are fresh red/green checks of the two corrected behaviors against exact current
inputs. They are recorded separately and do not inflate the native 33-killed count
or resolve its ten timeout outcomes. No physical GPU capacity, CUDA determinism,
multi-GPU execution, or completed acceptance/publication claim follows from them.

## Cleanup and related acceptance

All owned mutation and pytest processes exited. Both private exports and indexes
were removed in `finally`; their temporary logs/directories were removed after
extracting this evidence. No shared staging, source/test edits, commits, upstream
changes, GPU jobs, or unrelated cleanup were performed.

Ticket97's [implementation evidence](2026-11-16-yolo-probe-batch-binding.md) records
fresh exact-hash independent approval and the passing canonical final gate. The
retained GPU retry cleared the null-batch validator failure at batches 8/16/48 but
later stopped on the separate reserve defect tracked by ticket98. Overall ticket03
acceptance remains incomplete; this report does not override that outcome.
