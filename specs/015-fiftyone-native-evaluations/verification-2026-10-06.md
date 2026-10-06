# Native FiftyOne evaluation verification — 2026-10-06

## Implemented scope

New publications register one persisted native evaluation per task/split using the
existing digital-metrics matches. Reloadable results expose exact source counts,
confusion associations, class reports, original AP50/AP75/AP50–95 and AP50 PR curves.
Native status, ID and IoU fields support evaluation patches and exact label navigation.
Filtered predictions remain in the audit overlay and are excluded from the active native
prediction field. Receipts and ClearML run links carry evaluation keys.

The opt-in packaged Python plugin provides Imported Model Evaluation and Imported AP / PR
Reports panels. Subset fixed-threshold results remain available; missing/subset AP is
explicitly unavailable. No historical backfill, rematching, dependency revision change,
global plugin installation or deployment is included.

## Verification

Real-database tests cover registration, saved views/results, fresh-process reload,
multiple tasks, retry after interruption, renamed evaluation cleanup, split removal,
filtered-label patches, native rename/delete, exact wrong-class and status selection,
subset restoration, empty evaluations, plugin installation and real operator contexts.
An independent reviewer reproduced an empty-array subset crash inherited from FiftyOne;
the adapter now uses Boolean masks for that case and restores all arrays and sample scope.
The real-database regression verifies the original failure path.

Static checks passed: Ruff, strict mypy and all nine import contracts. The final full
live-enabled suite passed **1188 tests**. After the browser-driven matrix correction,
all **26 backend/panel tests** passed again.

Built wheel and sdist, installed each into a separate environment and verified packaged
plugin resources and all nine command helps. These checks reused the locked development
dependencies; they did not establish a fresh dependency resolution.

## Native execution

Standalone metrics and both CPU and GPU training/prediction/metrics pipelines completed.
Each published three reloadable split evaluations. Fresh readers compared source payloads,
confusion matrices, counts and reports with local outputs, verified ClearML run links,
force-downloaded every task artifact and downloaded both published model checkpoints.

These scoped pipelines explicitly skipped report and comparison stages; this record
makes no new paired-comparison or report-generation claim. Their existing regression
coverage remains part of the full suite.

## Browser acceptance

A real App loaded the packaged plugin from an isolated plugin directory. The summary
showed the fixture's exact 1 TP, 3 FP, 1 FN, precision 0.25 and recall 0.5. The companion
panel displayed original per-class AP values and PR curves. TP/FP/FN Load view actions
changed the view; the companion panel showed subset AP/PR unavailable and restored the
full report after clearing the view.

Browser inspection found that the native frontend's default hide-zero setting tests
only the matrix diagonal, hiding classes with errors but no correct detections. The
project panel explicitly initializes full-matrix display settings for imported runs.
Final browser readback matched the complete source matrix exactly:
`[[0,1,0],[0,1,0],[1,1,0]]` in blue/red/background order. Clicking the blue-to-red
cell selected the corresponding single sample. Zero/unit matrix colorscales contain
only finite values; the previous inherited logarithmic scale produced NaNs.

## Documentation and operational boundaries

Updated the integration specification and publisher contract, current contract index,
Russian README, quickstarts and end-to-end acceptance guidance together. Existing
historical verification records remain unchanged. Machine-specific logs, task IDs and
environment details are archived in the global environment skill, outside this repository.

Live ClearML projects/tasks and the three published datasets were removed after artifact
verification. Shared services and unrelated data were preserved. Browser acceptance used
an isolated MongoDB instance because the shared test role did not permit App index queries;
no shared roles were changed.

## Independent review

Fresh read-only review returned **ship** after the empty-evaluation fix, and again
after the browser-discovered matrix correction. No actionable findings remained.

All 15 changed/new Markdown files parsed and 91 local links/anchors validated.
Documented plugin installation was exercised in the isolated App. Task-owned App,
browser and disposable MongoDB were stopped; the shared test UI dataset was deleted.

## Release

Feature commit `60ab70b` passed ordinary hooks with real FiftyOne persistence enabled.
The changelog hook first regenerated committed history; its reviewed output was staged
and the commit retried with all hooks passing. Release commit `d33dcaf` created annotated
tag `v0.16.0` after ordinary checks and the recovery workflow's full final validation.
Both commits and the tag were pushed to origin.

Automatic preparation encountered the previously observed offline dependency-resolution
limitation with local source overrides absent. Recovery changed only the root version in
`uv.lock`, retained the generated release metadata and verified that every dependency
record and external revision was unchanged. Exact local source overrides were restored
unstaged after every attempt. No hooks were bypassed.

Final 0.16.0 wheel and sdist installations passed all nine command helps, plugin resource
checks, configuration generation and overwrite protection. All 70 installed Python and
plugin resource files matched the accepted checkout byte-for-byte. Distributions were
built only for verification; no package, release asset or deployment was published.
