# Verification — 2026-10-19

## Scope and preservation

Implementation uses an isolated snapshot of the existing stable-cache work and
queue-fix changes. Only differences from that snapshot belong to this feature.
The queue fix independently released as 0.34.1. The stable-cache prerequisite
remains uncommitted; this feature's release waits for its owner/delivery.
The initial forecast found no overlapping concurrent changes. A later lint-config
split touched the shared contract index and architecture tests; both three-way merges
were clean. A read-only `git apply --check` of all 60 feature-owned paths against the
current canonical checkout passed. The patch was not applied. Repeat reconciliation
after the other agents finish.

## Reproduced failures and checks

- The baseline focused suite passed 192 tests. New export timing tests failed in
  three expected places against baseline: producers had no artifact-ready callback
  and finalized engine/metadata publication waited for the returned inventory.
- Configuration, replay, YAML/CLI queue snapshots, multirun, startup General,
  session and cache checks passed 453 tests. A final conservative-cache regression
  reproduced two failures: malformed recognized configurations retained the derived
  `run_overrides` object. Removing only that object before conservative fallback
  fixed both; the complete cache suite then passed 236 tests.
- Artifact/workflow checks passed 154 tests; active-invocation publication tests
  passed 21, including all eight combinations of enabled result contributors.
- Parent integration checks passed 104 tests, covering configuration, queue worker
  loading, replay, complete artifact timing, export and detector workflows.
- Ruff passed. Strict mypy passed all 353 source/test/tool files before the final
  cache correction; the corrected source/tests subsequently passed their 350-file
  mypy run. Final parent Ruff and 353-file mypy checks passed after all corrections. Vulture passed.
- Import-linter kept all 43 contracts. Separate architecture tests passed 246,
  including injected SDK imports in export/pipeline workflows and export verification,
  and a reverse import from tracking results to composition.
- Application Markdown/local-link validation passed 516 files including the new
  feature documents; final review/evidence additions are also checked before handoff.

Commands use the prepared environment with `PYTHONPATH=src uv run --frozen --no-sync`.
The final full regression run passed **3321 tests**, with 30 skipped and 7 deselected
in 567.51 seconds. The first integrated run found eleven outdated test fixtures;
those fixtures were corrected, their 49 + 25 affected tests passed, and the full
rerun passed. No production relaxation was used. Local logs are retained outside the repository;
counts here are dated evidence, not permanent requirements.

## Distributions and documentation

Both source archive and wheel built successfully. Each installed without dependency
resolution in a fresh virtual environment reusing the prepared dependency set.
Installed module bytes matched the candidate source and all twelve command help
entrypoints passed outside the checkout. Both distributions were rebuilt after the final cache correction. Each passed all
nine generated command selections, omitted default selection, selected Faster R-CNN
configuration, actual generated-YAML composition, overwrite protection and unrelated-file
preservation outside the checkout. These checks do
not establish a fresh dependency resolution.

The companion portable usage skill explains active configuration, selected-preset
differences, replay, early General and complete-only artifacts. Discovery, package
validation, Markdown lint and local-link checks passed. A fresh native agent read
only the skill/usage reference and correctly answered both queued-detector precedence
and incomplete-aggregate/failure scenarios without expected answers. This is native
agent evaluation, not live OpenCode target-model execution. Companion release waits
until the corresponding application interface is released.

## Live acceptance

A real direct CPU run has passed independent SDK reads while the task was active:
YAML weight decay 0.0123 became CLI-selected 0.0234 in run, run_overrides and General
before dataset preparation, then reached the training arguments unchanged. Effective
GT was downloadable before training; complete validation dashboards were visible
before subsequent evaluation. Prediction completion did not publish the aggregate;
comparison's explicit no-baseline completion did. Every final artifact was forcibly
downloaded, canonical CSV membership/empty images were checked, each canonical CSV
uploaded once, and the single best checkpoint matched its local hash.

Actual queue submission and frozen worker loading passed on CPU with a paired
baseline, active-server reads before statistics, and downloaded final comparison/report
workbooks. This executed the real loader but did not claim scheduler admission.
Faster R-CNN ResNet-50-FPN completed a CPU epoch with early selected-model General,
COCO resolution, no inactive YOLO groups and a downloaded matching best checkpoint.
A real two-rank CPU Gloo run completed two epochs with live owner scalars, no worker
SDK/HTTP effects and a downloaded matching best model. Its harness adapts accelerator
boundaries to CPU; it does not establish physical multi-GPU execution.

A subsequent direct single-GPU pipeline also passed, including paired evaluation,
reports, early configuration/artifacts, all final downloads and best-checkpoint hash.
The native optimizer confirmed weight decay 0.0234. Shared workloads were not changed.

The ordinary scheduler attempt remained pending under its strict memory admission
policy for the bounded observation period, then was cancelled without creating a
task or claiming an allocation. Post-direct production telemetry still reported the
device unavailable. Actual scheduled execution remains an acceptance gap; no bypass
was used. Physical multi-GPU, other detector presets/families and real ONNX/TensorRT
export targets were not exercised in this scoped run. Synthetic fixtures establish
execution/publication behavior, not trained-model accuracy or export numerical parity.

## Remaining gates

Native evidence archival and cleanup finished. The parent verified all 650 archived
file hashes; zero tagged remote tasks/projects or owned processes remained, and shared
coordination was preserved. The failed first DDP harness attempt is retained in evidence
separately from the five successful live scenarios. Disposable install environments
were removed; isolated source snapshots and evidence remain for integration.

Fresh independent source review approved the snapshot with one corrected documentation
sentence. Architecture acceptance validation returned exit 1 solely for the declared
native scheduled-execution check; actual scheduler execution remains unverified.
Final integration must also reconcile the external lint-config split and the stable-cache
prerequisite. Full/static/import/docs checks passed for this isolated snapshot. Reconcile only feature-owned
changes after prerequisite delivery, then run commit hooks and sequential Git-only
release. No feature commits, tags, pushes or package publication have occurred.

## Resumed integration and release — 2026-10-19

The user renewed release authorization after the scheduler limitation was disclosed.
This authorizes Git-only delivery with that limitation recorded; it does not turn
the missing scheduled-execution evidence into passed acceptance. The declared native
check remains not-run.

Recovery uses an isolated clone of the released queue-fix baseline. Prerequisite
036 is committed first, followed by this feature. Its 60-path patch applied cleanly
both in a read-only check against the canonical concurrent changes and on the
prerequisite commit. The canonical index and dirty files remain untouched. The
concurrent lint-configuration split, local dependency sources and unrelated draft
are excluded. A reproduced queue test-fixture readiness race was corrected in the
prerequisite; production queue behavior and deadlines are unchanged. The old
temporary raw archives are unavailable, so earlier dated results above are retained
as historical observations rather than claimed fresh downloads.

Fresh persistent native evidence covers an actual CPU controller-cache miss/hit/miss
and paired baseline/candidate pipelines. Server reads while both pipelines were
in progress established early General/run/run_overrides, effective ground truth,
completed calibration thresholds and annotated model/split dashboards. Predictions
were absent until every enabled contributor finished, then visible before statistics
and final reports. The baseline produced 72 prediction rows and six annotated
workbooks; the candidate produced 96 rows and eleven workbooks. Ground truth retained
12 images including three empty images, with requested validation/test membership
verified. Baseline thresholds remained frozen, both models inferred the same four
test images, and strictness at equal thresholds was checked. Every artifact uploaded
once, all early downloads matched final hashes and downloaded best checkpoints
matched native files. The parent independently rehashed all 301 pipeline archive
files and all 23 controller-cache evidence files. Cleanup confirmed zero owned
processes, tagged tasks and projects. Synthetic random-weight CPU execution does
not establish model accuracy.

The first pipeline observer expected training images although only validation/test
splits were requested. The application completed; the observer assumption was
corrected and the entire paired run repeated successfully. That failed observation
and its cleanup are retained separately. No application change was needed. Shared
GPU memory remained above normal admission limits, so no scheduled run or admission
bypass was attempted. Physical multi-GPU and real export-runtime coverage remain
limited as described above. Portable skill recovery and fresh behavioral evaluation
passed; its release follows application delivery. Integrated checks and final review
are recorded below when complete.

Final integrated source checks passed through the normal contributor commit hooks:
full pytest, Ruff, mypy, Vulture and import-linter, followed by the normal post-commit
helper. Feature commit `fd395d3` follows prerequisite `2e4b5f2`. Separate architecture
tests passed 246; Markdown/local-link validation checked 531 files with zero issues.
Fresh independent integrated review accepted the source without blockers; see
[review.md](review.md). All 87 changed paths reconcile with the architecture records.
The original 56 dirty application files and index remain unchanged. The release
clone has no local uv source section; original source overrides remain untouched.
