# Verification: clean architecture and Pandera

Date: 2026-10-08. Baseline: `72334f4` (`0.19.1`). This records checks of the
feature implementation; it is not an evergreen test-count or deployment promise.

## Implementation and regression evidence

- All runtime modules now belong to core, application, responsibility-specific
  adapters, entrypoints or the shipped Hydra launcher. No legacy module aliases
  remain. The [migration map](migration-map.json) records the cutover.
- Workflow dependencies are explicit, structurally checked ports. The composition
  root binds them per invocation; worker payloads retain importable unbound targets.
- Scientific computation and comparison remain separate from rendering, storage,
  SDKs and logging. Pandera validates stage-specific frames without coercion,
  filtering or changing source-row lineage.
- Baseline pytest: 1,279 passed, 30 skipped. The integrated regression rerun before
  the final observability/cache changes: 1,373 passed, 30 skipped, 52 warnings.
  The later full suite passed 1,387 tests with 30 skips and 52 warnings. After
  the content-hash cache repair, all 59 comparison assembly tests passed; six
  focused cache tests and 164 architecture/injection/comparison tests also passed.
- Parent Ruff and strict mypy passed, and import-linter kept all 27 contracts.
  Architecture tests exercise actual configured contracts, forbidden imports,
  unclassified modules, cycles, effects, initializers and generated runtime targets.
- Only Pandera, typeguard and typing-inspect were added to the lockfile. Existing
  dependency versions and both external dependency entries remain unchanged.

Verification exposed and corrected a Boolean ownership check in standalone calibration
and missing comparison observations after extraction. Tests cover warning/INFO levels,
completion ordering and progress cleanup on calculation failure. Native acceptance also
exposed an existing comparison cache-key bug: toggling `reuse_existing` changed the
cache identity. The fix excludes only that operational flag and retains model identity,
data fingerprints and scientific/native settings. A second reproduced cache miss came
from ClearML touching cached checkpoint modification times. Cache identity now uses
checkpoint content, preserving reuse after a timestamp touch and invalidating changed
bytes even when size/time are retained. Both regression cases failed before the fix
and passed afterward; no SDK code was patched.

The real cache hit then exposed an existing CSV precision issue: default parsing read
confidence `0.006217078305780888` as `0.0062170783057808`, dropping detections exactly at
the frozen threshold. The cache reader now requests pandas round-trip float parsing.
Its public reinference regression reproduced two accepted rows becoming zero before
the fix and exact fresh/cached equality afterward, with inference forbidden on replay.
Parent verification passed 85 affected reinference, provenance, geometry and scoring
tests, plus Ruff, strict mypy and all 27 import contracts.

## Packaging and documentation

Both wheel and sdist were built and installed into separate environments with locked
runtime dependencies. Each installation passed all ten command helps, inert root import,
legacy-module absence, packaged FiftyOne resource and regenerated configuration target
checks. Existing-directory rejection and explicit `cy-init-config --force` also passed.

The maintained contract index, architecture boundaries, migration guide, filesystem
policy, development guidance, README and targeted constitution amendment were reconciled.
The programmatic example passed strict typing; regenerated YAML was exercised in real
commands. Parent validation checked 19 changed Markdown files and 137 local links and
anchors with no errors.

## Native acceptance

The isolated acceptance tag is `clearml-yolo-codex-20261008-clean-architect-pyfj`.
Fresh disjoint train/validation/test image populations include background rows.

| Execution | Task ID | Observed result |
|---|---|---|
| CPU pipeline | `aae519ed0cab4a21874724cec803ab72` | Completed; exact required 11 artifacts downloaded; checkpoint load/hash/identity and validation calibration metadata verified |
| GPU pipeline | `bf602454f711485a9758bdd60608710e` | Completed; exact required 17 artifacts downloaded; paired comparison and checkpoint/metadata verified |
| Standalone validation | `a42cd71125724cdbbbcec3a4b9cac212` | Completed with required uploads |
| Standalone comparison | `b4b81c356af94731a9b57ac7ce257326` | Completed with current-data paired comparison artifacts |
| Standalone report | `d124afa5435f4760b46fbc512ffb1bcc` | Completed with exact required artifact inventory |
| Standalone prediction | `47d73da7c8ac4b0298ad66d5c1e62302` | Completed with exact required artifact inventory |
| Standalone metrics | `dbdb877b07e240b0badead42efb0b0df` | Completed with exact required artifact inventory |

The no-baseline path was verified before promoting the task-owned CPU model for the GPU
comparison. Dataset image/NDJSON cache hashes and modification times remained unchanged
between CPU and GPU runs. Real FiftyOne persistence suites passed 36 tests against the
isolated helper-selected database.

Actual ClearML browser interactions verified PR legend hide/restore, point hover and
confusion-matrix Counts/Row %/Column %/Overall % controls. Published numeric values match
local payloads/workbooks, including PR confidence and cumulative TP/FP arrays. The plot
inventory excludes forbidden legacy tables and native PR duplicates.

Injected required artifact, output-model, callback and flush failures were exercised
against real ClearML tasks: each exited nonzero and ended failed. A real SIGTERM exited
143 and marked its task failed. Local diagnostic files were retained. These injected
failures establish the error boundaries, not a physical hardware-failure experiment.

Optional publisher OSError injection preserved completed computation and downloaded
artifacts, logged sanitized diagnostics and produced no false publication receipt.

One SDK naming query returned an unexpected empty response before comparison scoring.
Raw API checks confirmed the project and prior tasks remained intact; retry succeeded
without changing application or SDK code. The transient query's root cause is unverified.

The original acceptance tag is closed. Cleanup removed its 20 tasks, two models, one
project, workspace and 98 identified SDK cache copies. A counted FiftyOne rerun passed
36 tests and observed 29 dataset deletions. Raw API inventory confirmed zero remaining
owned projects/tasks/models; test datasets, queue requests, owned processes and GPU
compute applications were empty. Downloads and diagnostic evidence were retained
outside the repository. Shared services and unrelated resources were preserved.

The independent full-diff review returned **ship**, with 112 focused tests, six cache
tests and all import contracts passing. A fresh independent review of the subsequent
CSV precision correction also returned **ship**, with 32 reinference/provenance tests
and focused Ruff passing. It independently reproduced the default-parser bit loss and
confirmed that round-trip parsing restores the original value.

The final native precision gate passed under fresh tag
`clearml-yolo-codex-20261008-cache-exact-0w8n`. Fresh comparison task
`c555505c468d4bf4b8455f9ec16f5a13` and cached task
`a48d9e5cce244974b523ec33affa4e3e` used retained real CPU/GPU-trained checkpoints,
current images and exact validation thresholds with CPU inference. All raw confidence
bits matched, including three candidate rows exactly at the frozen threshold. Both
runs published identical scientific/source-reference values, five workbook cell sets,
model identities, exclusions and confusion/PR data. Invocation context IDs and
process-local match ordinals were normalized for comparison; each run's match-ID
relationships independently resolved consistently to its source rows.

Prediction CSVs and inference metadata retained their file set, bytes, hashes and
modification times, with no repeated inference. Provenance sidecars were rewritten
with identical bytes, retaining their existing behavior. Cleanup removed the two new
tasks, one project, workspace and 16 identified SDK cache copies. Raw API inventory
and owned process/queue checks were empty; this follow-up created no models, datasets
or services. It used no GPU queue ticket.

Final stable hooks, convergence and release remain pending at this evidence checkpoint.
Physical multi-GPU execution is not established by the single-GPU run or mocked tests.
