# Forced selection and readable admission — 2026-10-12

## Scope and reproduced behavior

FR-011–015 implement strict force policy, protected concrete device choices, sequential
forced sweeps and readable admission decisions. The reported eight-card memory sample
(1215, 3, 409, 3, 3, 3, 3, 3 MiB) admits five through the inventory and empty queue.
Live reservation/FIFO fixtures explain waits and admit after release. The user's
actual waiting run was not inspected, so its cause remains unconfirmed.

Initial force tests failed for the absent policy and selector helpers; initial
admission tests failed for the absent diagnostics/visibility API. Inventory regressions
failed before hidden-card scoping was implemented. Integration caught and fixed an
unconditional force-selector check affecting ordinary automatic mode, and updated
fake inventory interfaces/default-policy expectations.

## Executed checks

Commands use `uv run --frozen --no-sync` to preserve the prepared environment.

- GPU/launcher/controls/force/decision/memory-wiring/direct suite: 283 passed before
  final presentation placement and added blocked-queue regressions.
- Post-integration direct/force/decision/wait/execution/wiring checks: 100 passed.
- Final decision suite, including real inventory on the supplied five-of-eight sample:
  8 passed. Required-device failures, hidden memory/MIG, threshold equality, reordered
  indexes, simultaneous reservation/memory reasons, FIFO, detached sample and refresh
  behavior have deterministic coverage.
- `ruff check .`: passed. `mypy .`: no issues in 283 source files. `vulture`: passed.
- `lint-imports`: 40 kept, zero broken. `pytest tests/test_architecture.py`: 94 passed.
  Negative cases include injected forbidden dependencies, mutated actual import
  graphs, core effects, dynamic targets, helper cycles and unclassified modules.
- `cy-init-config` plus `--cfg job`: all six model/export commands export force=false
  and compose concrete force overrides. The documented five-GPU example composes.
- MarkdownIt parsed 10 changed Markdown files and checked 188 local links/anchors.
  Final evidence/task edits receive a final documentation/whitespace check.

The full suite passed 2255 tests with 30 skips and 56 warnings before the final
selector-normalization correction. After that correction, the complete affected
GPU/launcher/force/decision/wiring/direct/model-scheduling selection passed 345
tests; Ruff, mypy (283 files), Vulture, all 40 import contracts and all 94
architecture tests passed again.

## Architecture and ownership

Core validates strict force and concrete selectors; adapters own NVML, isolated CUDA
metadata, telemetry scoping and locked registry effects. Immutable diagnostics are
created from the admission sample and registry transaction; Hydra formats/logs after
lock release. Direct waiting accepts a callback; it does not import entrypoints.
The existing launcher consumes effective controls and retains its implementation.

Planning record validation passed before implementation. The task-owned diff preserves
pre-existing static-analysis changes in `.pre-commit-config.yaml`, `pyproject.toml`,
`uv.lock`, `docs/development.md`, `docs/static-analysis.md`, feature 026 and existing
test cleanups. Only the new force-default expectations in `test_gpu_memory_wiring.py`
and admission changes in `gpu_queue.py` belong to this task; their initial edits
remain separately owned. No dependency reference or upstream source changed.

## Deferred follow-ups

Forced-kill orphan recovery and permission-denied process inspection require separate
reproduction/lifecycle work. Physical multi-GPU/DDP and MPS execution are not established
by synthetic inventory tests or single-device native execution.

## Native execution and publication limitation

Using the repository end-to-end skill and tag-scoped environment workflow, controlled
random-checkpoint prediction on two small synthetic images completed on CPU and one
CUDA GPU. A two-job forced GPU confidence sweep completed sequentially in one process
with separate invocation-owned tasks. Each successful invocation logged required
`gt_csv` and `predicts_csv` uploads, kept inherited CUDA visibility unchanged, and
left its dedicated queue directory absent. These are execution observations, not
accuracy or physical multi-GPU/DDP evidence.

Fresh server status/configuration/artifact-download readback remains unverified.
The first acceptance reader used an incorrect project lookup; required cleanup
removed the successful test resources. Follow-up attempts, including a bounded
single-GPU retry with direct task-ID readback, failed before inference in the
pre-existing documented ClearML naming query: `Task.query_tasks` attempted to extend
a list with `res.response.tasks=None`. No application or dependency workaround was
applied. Effective policy/replay are covered by deterministic tests, not claimed as
fresh server readback. This is an outstanding publication/release acceptance gap.

Every successful and failed attempt's tag-scoped resources and invocation arenas
were cleaned; the final scoped listings were empty. External test scripts and logs
are retained with the environment evidence, outside the repository.

## Independent review and correction

The first fresh read-only review reproduced a case/whitespace forwarding gap:
force validation accepted padded/uppercase selectors, but native detector device
converters received the raw strings. New owner/provenance regressions failed for
` CUDA: 2 ` and ` MPS:0 ` before the fix. Hydra now normalizes effective string
selectors without changing requested provenance, identity, order or visibility.
Regression cases call the native DEIMv2, RF-DETR and Faster R-CNN device converters
with normalized CPU and CUDA inputs. No backend or external dependency was patched.

A second independent read-only review (`final_review`, fresh context) returned
`ship` for implementation with no blocking correctness or architecture findings.
It reviewed the integrated source/test/documentation diff and the final check logs,
and independently passed planning-record validation and `git diff --check`.
The reviewer accepted validation/effect ownership, immutable admission evidence,
Hydra presentation, selector normalization and reuse of launcher contracts.

Final Markdown validation parsed 11 files and checked 189 local links/anchors;
whitespace checks passed. Architecture acceptance validation passed after evidence
and review reconciliation. This validates the architecture record and its executed
code/documentation checks, not the outstanding live publication/release gate.
T027 and T030 remain open; no commit, release tag or push was attempted while the
required fresh server readback remained unverified.

## Source delivery authorization — 2026-10-13

After the implementation report, the user explicitly requested “commit and push
work”. This authorizes source delivery while the T027 live ClearML readback and
T030 release acceptance remain open. No version tag is included in this delivery.

A fresh read-only scope review (`commit_scope_review`) returned `ship` for the
scoped source commit and push. The source is prepared on an isolated feature
branch using the committed development and hook configuration. Existing
static-analysis edits and fixture/WorkerClaim cleanups are excluded. The isolated
`pyproject.toml` contains no local source overrides; the original workspace keeps
its exact local overrides and unrelated edits. Normal commit hooks are required,
with the prepared environment reused without dependency resolution. The verified
source commit can then fast-forward `master`; this does not close the documented
publication/release acceptance gap.

The first source-commit attempt passed Ruff, mypy and all import contracts, but
its full pytest hook terminated with SIGILL (exit 132) while the existing native
DDP relay tests were running. The trace showed garbage collection in the relay
thread and `fsync` in the main thread; it did not establish a cause. An unchanged
focused rerun of `tests/test_native_ddp.py` passed all 22 tests. The source remains
unchanged; delivery still requires the complete normal commit hooks to pass on
retry, with no skipped tests or disabled hooks.
