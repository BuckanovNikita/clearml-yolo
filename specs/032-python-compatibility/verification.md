# Python compatibility verification

Date: 2026-10-15. Source baseline: `634f3e2` (v0.29.0).
Task: `032-python-compatibility`.

## Scope and dependency review

Package and lock metadata now declare `>=3.12.13,<3.14`. The development pin,
Ruff target and mypy target remain Python 3.12. Lock regeneration resolved 282
packages without adding or removing any package-name/version pair. Additional
Python 3.13 wheel assets account for most lock changes. Approved editable
`digital-metrics` and `report-generator` sources remain unchanged. Runtime source,
algorithms, process supervision checks and installed workflow tooling are unchanged.

The task owns the manifest/lock, maintained prerequisite prose and this feature's
artifacts. The pre-existing local `[tool.uv.sources]` section and untracked grid
search document are excluded from delivery and preserved. The canonical checkout
uses the existing `master` branch.

## Executed matrix checks

Prepared frozen environments use CPython 3.12.13 and 3.13.14. The local standalone
builds expose pidfd APIs and pass the real `require_process_supervision()` probe;
version metadata alone does not establish that capability on another build/host.

| Check | Python 3.12.13 | Python 3.13.14 |
| --- | --- | --- |
| Ruff, mypy, Vulture | Passed; mypy checked 317 files | Passed; mypy checked 317 files |
| Import-linter | 43 contracts kept | 43 contracts kept |
| Routine pytest | 2,504 passed, 30 skipped, 7 physical-GPU cases deselected | Fresh full repeat: 2,504 passed, 30 skipped, 7 physical-GPU cases deselected |
| Native CPU/Gloo DDP | Included above | 5 passed; 2,536 deselected |
| Installed wheel metadata, import origin, pidfd probe | Passed | Passed |
| Installed wheel `cy`, queue and config helps; default config export | Passed | Passed |

Routine command: `uv run --frozen --no-sync pytest`. Python 3.13 uses an isolated
`UV_PROJECT_ENVIRONMENT` and explicit `--python 3.13`. It initially ran separate
`pytest -m 'not ddp_cpu'` and `pytest -m ddp_cpu` selections to avoid overlapping
CPU distributed runs; the final repeat ran the complete routine suite. Existing architecture
and tooling-boundary tests include prohibited-import/dependency negative cases.
The Python 3.12 routine run completed in 675.16 seconds; Python 3.13 DDP in 61.10
seconds; the complete fresh Python 3.13 repeat passed in 673.06 seconds.
Skips and physical-GPU deselections are not passing native GPU evidence.

### Initial Python 3.13 failure

The first non-DDP run failed one model-replay case at native cleanup because
`/proc` access was denied for PID 111428. The production process-tree code and
replay tests are unchanged from the baseline. That PID was gone on inspection;
its identity and the denial cause were not captured. A focused repeat of
`tests/test_model_replay.py` passed all eleven cases in 1.98 seconds without edits.
This makes the observation non-reproducing in that repeat, not a proven interpreter
bug or a proven root cause. A fresh complete Python 3.13 suite passed all 2,504 cases in 673.06 seconds.

## Packaging and documentation

- `uv lock --check` passed.
- `uv build` produced both wheel and source archive without changing dependency
  revisions. Isolated wheel installs resolve imports from site-packages, outside
  package source, on both supported minors.
- Built `Requires-Python` semantically equals `>=3.12.13,<3.14`; metadata accepts
  3.12.13, 3.12.99, 3.13.0 and 3.13.14 and excludes 3.11.99, 3.12.12 and 3.14.0.
- Fresh wheel and source-distribution environments on both minors passed all
  twelve installed command helps and all nine `cy-init-config --command`
  selections. Package import origin and metadata were verified for each.
- Markdown lint of fifteen task-owned documents passed with the existing
  long-line policy disabled; 206 local links/anchors passed. The final evidence is
  checked again before acceptance. `git diff --check` passed.
- The portable clearml-yolo skill has no conflicting version prerequisite.
  cveta2's separate companion prerequisite correction is owned by its workflow.

## Native release verification and limits

Scoped verification under the end-to-end and environment skills used generated
native YAML, explicit ClearML project/task tags, disjoint validation/test images
with empty examples, one-epoch native YOLO training, and downloaded-checkpoint
prediction. AMP, compilation, native plots and optional FiftyOne publication were
disabled. All four successful training tasks had one native best Output Model,
native scalars, General/run configuration and canonical ground truth. Each best
model was force-downloaded, hash-matched and reloaded with exact class vocabulary.

| Interpreter | Device | Training and downloaded model | Standalone prediction |
| --- | --- | --- | --- |
| 3.12.13 | CPU | Passed | Passed |
| 3.12.13 | Single GPU | Passed | Failed twice before inference in SDK lookup |
| 3.13.14 | CPU | Passed | Passed |
| 3.13.14 | Single GPU | Passed on a fresh invocation | Passed |

The three successful predictions each produced twenty predictions over four
validation/test ground-truth rows, including negative images. Downloaded canonical
CSVs retained exact source/checkpoint bindings and `not_evaluated` semantics.
No prediction task created an Output Model. Source fixture hashes were unchanged.

An initial 3.13 GPU training invocation and both 3.12 GPU prediction attempts
failed before model work in ClearML SDK `Task._query_tasks`, which attempted to
extend a list with `None` after a project-lookup warning. A fresh 3.13 training
invocation completed. Exact SDK query and raw HTTP readbacks subsequently returned
valid existing and empty result lists on both minors, with HTTP/result code 200.
Original failing response bodies were not captured; the root cause remains
unconfirmed. The 3.12 standalone GPU prediction check remains a limitation and
is not counted as passed. No application or dependency patch was made for it.

The machine-environment evidence archive `python-compatibility-20261015-live`
retains exact commands, logs, task/model IDs, checkpoints, downloaded CSVs,
publication audit, response probes and cleanup receipts. The documented helper
removed the owned project and all ten tasks/models/artifacts, then confirmed zero
matching projects/tasks. Owned processes and tagged workspace were removed;
pre-existing services and caches were preserved.

These checks establish native CPU/single-GPU execution and the stated publication
outcomes, not model quality, physical multi-GPU/NCCL, compiled execution, every
optional backend or TensorRT binding availability. No detector/export contract
changes. Independent review evaluates the remaining standalone-prediction limit
against the scoped compatibility acceptance and native release gates.

## Review and delivery

The completed task-owned diff contains compatibility metadata/lock assets,
maintained prerequisite prose and this feature record. No runtime source, tests,
workflow tooling, import contracts or approved dependency revisions changed.
The generated release changelog/version metadata are included in the acceptance
scope. Local source overrides and the unrelated untracked grid-search document
remain excluded. Fresh independent reviewer `/root/clearml_python_review` returned **ship**,
accepting Python compatibility and module architecture with no blocking findings.
The reviewer independently inspected metadata, lock assets, all distribution
checks, regression summaries, native evidence and the preserved failures. The
remaining 3.12 standalone GPU prediction failure is an explicit limitation, not a
failed mandatory per-interpreter prediction matrix: no such matrix is required by
the release contract, and native CPU/single-GPU training passes on both minors
with full standalone prediction on newly admitted 3.13. Evidence wording was
corrected to distinguish the initial split suite from the final full repeat.
Normal commit/release hooks, exact local-source restoration and remote ref
verification follow.
