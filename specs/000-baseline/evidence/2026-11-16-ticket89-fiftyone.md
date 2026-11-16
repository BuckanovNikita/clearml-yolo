# Ticket 89: native FiftyOne publication and App views

Date: 2026-11-16. Selected native checks **passed**; integrated documentation gate
and final acceptance review remain coordinator-owned. No product source, dependency,
test, shared environment configuration, commit or release was changed by this task.

## Scope and identities

This closes the native publication/view evidence gap against the current
[product specification](../spec.md#publication-and-process-ownership),
[scientific-result requirements](../spec.md#data-and-scientific-results) and
[publication contract mapping](../../../docs/current-contracts.md).
The existing integration suite supplies its own small fixtures; the separate publisher
and readback below consume the accepted ticket 05 YOLO handoff. These are distinct checks.

- Worktree: `/mnt/wsl/data/nkt/clearml-yolo`, local `master` at
  `60b5c63aebd70fbe6329f6e0534bd1cccfc6832b`, equal to local master at start/end.
  Remote references were not fetched. Unrelated working files were preserved.
- Environment: adopted `cy-it-adb183`; lifecycle exports stayed in process memory.
  FiftyOne 1.22.0, pymongo 4.9.2, numpy 2.5.1, pandas 3.0.5.
- Accepted case: `runs/verification-gap-closure/assets-v1/estimated-acceptance-v2/ultralytics-default-2e66fec4f0`.
  Handoff SHA-256: `283cc515f9d9cab7d5fbfff0b39a2e84d0e3b463c1f0172aaa54809bd54e232b`.
  ClearML task: `d6158c43c4fa4b88b9cca75a7d6fd55b`.
- Effective GT SHA-256: `a840cea5395dda1807b40e566309c342a615249b35d191a9fc2667fb5fd424d3`.
  Raw prediction SHA-256: `bcd2343cd022da95fffbd78fff6bfb437e4768bce3757bdd4feab0c363f4e857`.
  Both evaluation payload hashes are retained in `before.json`.
- Owned dataset: `cy-it-adb183-ticket89-20261116-v1-a840cea5395dda1807b40e566309c342a615249b35d191a9fc2667fb5fd424d3`.

The durable raw bundle is
`runs/verification-gap-closure/ticket89-20261116/`. Its `manifest.json` hashes 73
scripts, logs, receipts, readbacks, browser captures and cleanup records; manifest
SHA-256 is `8567eb5b48ca22bee10665117251fdb8a68f6bd906c842a5d76078ebe630a324`.
`source.json` retains exact relevant adapter/core/test/lifecycle/lockfile hashes and
confirms they equal the recorded source tip. Inputs remained byte-identical.
The raw bundle is local retained evidence, not committed screenshot assets.

## Executed checks

All Python execution was CPU-only with CUDA hidden, native numerical thread limits
of two, and nice 19. The exact pcboard session
`codex:01a1e0ab-e153-7ff1-8329-85585fccf79f` reported normal mode before execution.
No training, GPU job, container lifecycle or shared environment deletion was run.

1. **Passed — existing native product checks.**
   `nice -n 19 .venv/bin/python -B runs/verification-gap-closure/ticket89-20261116/run_checks.py`
   ran the publisher, native-evaluation and panel-view integration modules with
   `-n 0 -ra -q`, lifecycle-provided database settings, an owned pytest basetemp and
   a 1,200-second subprocess timeout. Result: **29 passed, zero skips**, exit 0,
   36.29 seconds, 1,826 warnings. Tests cover native persistence, identity/reuse,
   empty images/evaluations, unknown memberships/counts, exact label navigation,
   subset report unavailability, comparison/status callbacks and plugin registration.
   Some tests inject faults or substitute boundary context; their assertions are
   product checks against a real database, not proof of browser rendering.
2. **Passed — accepted native handoff publication.**
   `nice -n 19 .venv/bin/python -B runs/verification-gap-closure/ticket89-20261116/native.py publish`
   explicitly installed the packaged evaluation plugin into the owned temporary
   plugin directory, then called the real `BoundedFiftyOnePublisher.preflight()` and
   `publish()` with the case GT, raw predictions, val/test evaluation payloads and
   task identity. Receipt reports complete dataset/run, **240 samples** and both
   evaluation keys. Plugin file hashes are in `plugin.json`.
3. **Passed — separate-process readback.** The same command with `readback` loaded
   the published dataset anew: media paths exist, per-image GT counts match CSV,
   **106 empty-GT images** persist, and raw detection count is **23,551**.
   Evaluated source index, label, status and normalized box coordinates match the
   authoritative payloads; confusion matrices match exactly. Native results and
   patch views load. AP/PR projections are available for full results and unavailable
   for subsets. Patch counts are observations, not an asserted one-to-one match count.

   | Split | Images | TP | FP | FN | Native mAP |
   | --- | ---: | ---: | ---: | ---: | ---: |
   | val | 40 | 3 | 1231 | 61 | 0.00004834167953231372 |
   | test | 40 | 0 | 1028 | 56 | 0.000014641172310803087 |

4. **Passed — identity and unavailable-count readback.** The `identity` phase checked
   stored GT identity/completion. All 160 train images have `predicted=false` and
   `evaluated=false` because the explicit selected splits are val/test; their TP/FP/FN
   are null. An initial inspection assertion incorrectly expected unknown prediction
   membership despite explicit splits; it failed, was corrected against the public
   request semantics and passed. The original failure log is retained as
   `identity-readback-initial-assumption.log`; no product code changed. Unknown
   membership with omitted split provenance is covered by the native fixture tests.

## Actual App inspection

**Passed.** `native.py app` started only the owned loopback App on port 5189 with a
30-minute deadline. An isolated cached headless Chromium, GPU disabled, used owned
profile/port 9289 and a 30-minute outer timeout. `browser.cjs` drives bounded CDP
calls and retains screenshot, DOM and selected browser-event files. No user browser
profile or shared plugin installation was modified.

The following screenshots were actually opened and visually inspected, separately
from database assertions:

- `app-initial.png`: real media grid and imported labels, 240 samples.
- `imported-evaluation-list.png`: the installed Imported Model Evaluation panel
  lists the two native evaluations.
- `val-detail.png`: native val summary displays TP 3, FP 1231, FN 61, support 64.
- `reports-menu.png`: Imported AP / PR Reports renders original-precision AP values
  and PR curves for the accepted evaluation. Poor model scores are preserved.
- `matrix-visible.png`: actual native matrix includes all four classes and background.
- `matrix-selection-settled.png`: selecting a populated matrix cell creates a label
  subset and displays “AP and PR are unavailable for subsets; fixed-threshold results
  remain available.”
- `empty-samples.png`: selecting a zero-count matrix cell produces an actual
  zero-sample App view.

The App logged deprecated upstream label-display options; no observed rendering
failure prevented these checks. Browser captures establish these views only, not
every possible panel interaction, browser platform, or a new GPU outcome. Native
test-split results were independently read from the database; the detailed visual
walkthrough used val. No claim of UI correctness is inferred solely from payloads.

## Ownership, cleanup and acceptance boundary

**Passed — cleanup.** `close-browser.cjs` closed only the owned browser endpoint;
the App PID was checked against its exact command before SIGTERM. Both processes
exited and ports 5189/9289 no longer accepted connections. `native.py cleanup`
deleted only the receipt dataset after validating the ticket prefix. `finalize.py`
verified the original dataset set was restored, removed only
`.tmp/ticket89-20261116` (pytest, plugin, browser profile), and retained durable evidence.
No task-owned process remains.

`cy-it-adb183-verification-gap-closure-renewal-durable` remains present with one
sample. The shared `/mnt/wsl/data/nkt/.cache/clearml-yolo/fiftyone` lock-directory
setting was preserved and the directory remains present. Cleanup receipts distinguish
owned data deletion from shared environment ownership; the shared database was not stopped.

All selected ticket 89 native checks passed. No new global coverage, full-suite,
mutation, paired-repository, GPU or release claim follows from this evidence.
The coordinator owns the integrated native documentation gate and final review;
this record does not mark those pending steps passed.

## Coordinator review

On 2026-11-16 the coordinator independently rehashed all 73 manifest entries and
opened the seven listed screenshots. The displayed native counts, full-result AP/PR,
subset-unavailability message and zero-sample view support the recorded claims.
Cleanup receipts confirm the owned dataset/processes were removed and original
shared state preserved. Native specification consistency review found no behavior
change or missing acceptance assertion within ticket 89 scope. The evidence is
accepted subject to the final automatic pass on the documentation commit.
