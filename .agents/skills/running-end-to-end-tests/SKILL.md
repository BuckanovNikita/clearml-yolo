---
name: running-end-to-end-tests
description: Verify clearml-yolo with real native execution, ClearML artifact downloads, validation, and paired current-test comparison. Use for release or integration verification; unit tests alone do not establish these outcomes.
---

# Verify the detection workflow

Read [prerequisites](references/pipeline-prerequisites.md) for inputs and configuration,
and use the repository's [current contract index](../../../docs/current-contracts.md)
to select each acceptance claim's maintained contract.
Use the environment's applicable global skill for credentials, capacity and cleanup;
`clearml-yolo-environment` supplies this project's local environment when installed.
This skill defines product acceptance, not deployment or machine setup.

Obey the host's active operating mode and the user's current instructions. In host
Plan Mode, inspect prerequisites and prepare the verification plan only; do not start
runs, mutate resources, commit, push, or deploy. Outside Plan Mode, an explicit
invocation authorizes the documented verification work. Commits and deployments still
require an explicit user request for those actions. Do not request authorization
already given in the conversation.

**Plan Mode exit**: Prepare only the read-only verification plan in the response and
stop before the execution steps below; no runs or generated evidence are required in
this branch.

## Verification

1. Run the repository's pytest, Ruff, mypy and import-linter checks. Include applicable
   pre-commit hooks for release or commit work.
2. Configure an isolated ClearML project and output directory. Pass project name and
   tags explicitly. Set `CY_HOME` to the task-owned invocation workspace for project data and
   owned temporary files per the filesystem contract. General runner/library caches and
   interpreter temporary/bytecode settings retain their defaults unless explicitly selected.
   Keep credentials
   out of files and logs; native callback image previews are permitted.
3. Build ground truth from a small YOLO dataset with disjoint validation/test images,
   including an empty image in each split. Exercise the top-level `ultralytics` and
   `ultralytics_predict` groups through locally editable generated YAML, with explicit
   CPU and available GPU devices. Verify stateless busy-to-free GPU waiting before task
   creation, direct calling-process execution and a sequential standard BasicLauncher
   sweep with separate tasks and normal failure propagation. Availability is not a
   reservation; do not infer exclusive GPU ownership from a successful wait.
4. Run a candidate without a baseline; verify evaluation succeeds and comparison is
   skipped. Promote a completed baseline with a `prod` tag, run a candidate and verify
   both checkpoints infer the same current test images under matching settings.
5. Confirm validation thresholds are frozen for test and baseline thresholds are loaded
   unchanged. Compare metrics, statistical results and report counts. Exercise `cy-val`,
   `cy-compare` and `cy-report` independently, including nondefault evaluation options.
6. Force-download every required artifact and verify the explicit publication inventory.
   Use the [evaluation publication contract](../../../specs/014-evaluation-publication/contracts/publication.md)
   for canonical names. Download `gt_csv` and `predicts_csv`; confirm one upload per
   invocation, every original source row/ID, exclusions, strict threshold flags and JSON
   pre/post-threshold relationships. Check standalone prediction is not evaluated and
   comparison reinference contexts remain separate. Verify full/DTRK dashboard contents,
   exact validation thresholds, paired `Сравнение` workbook/exclusions CSV and unchanged
   developer/business reports. Missing automatic baseline must retain candidate
   dashboards/plots and its recorded skip reason without fabricated paired outputs.
   Confirm duplicate evaluation summaries and separate match/threshold/methodology
   sidecars are absent from new uploads while necessary local diagnostics remain.
   Inspect one current-model `Confusion matrix` chart per evaluated split. In a browser,
   select `Counts`, `Row %`, `Column %` and `Overall %`; verify Counts is initially active,
   exactly one heatmap is visible, exact post-threshold counts, class order/background,
   true-row/predicted-column orientation, percentage scaling and zero denominators.
   Inspect one `Precision-recall` chart on test only, combining all classes. Toggle class
   traces through the legend; inspect AP50/method legends and observation hover.
   Inspect PR for authoritative prepared/deduplicated GT and
   geometry-valid raw prediction populations, AP50 parity for both integration methods,
   supported strategies/ties, confidence/cumulative TP/FP hover, empty predictions and
   unavailable recall/AP without GT. Empty classes retain null-gap traces and explicit
   class-legend status without numerical points; confirm their legend entries remain visible
   and toggleable in the actual browser. Confirm readable model/split series and
   persistent captions survive actual SDK publication without context/model IDs,
   checkpoint hashes or training task IDs. Repeat checkpoint/split publication across
   prediction and comparison candidate and verify slot reuse; check unknown identity and
   colliding names use readable fallback/stage/ordinal labels. Verify zero baseline chart
   events, zero comparison/degraded-class/methodology table events and zero non-test PR
   events, while baseline CSV contexts, dashboards, paired reports and headline single
   values remain available. Use the
   [readable plot contract](../../../specs/020-readable-evaluation-plots/contracts/plots.md).
   Verify unused names remain intact and active/archived project-local collisions receive
   shared task/model suffixes without changing IDs/paths. Check owned best-model threshold
   metadata against exact val thresholds and actual prediction checkpoint SHA-256 with
   fresh server readback; standalone metrics must not create or mutate models.
   Download the single native best Output Model, load it, and compare model fields with
   checkpoint/trainer data. Verify canonical run and native General parameters support
   replay; when used by the invocation, verify the consumed-dataset and explicit-report
   configurations too. Inspect native Scalars, Plots and Debug
   Samples. Confirm one task per invocation, owner-only training/validation callbacks,
   and no duplicate checkpoint artifacts. Enable native plots and verify native validation
   PR images are excluded while other native figures, previews, scalars and the single best
   model remain; exercise callback failure cleanup and the same filter in DDP owner replay.
   Repeat CSV training against one dataset cache: filenames and extension casing remain
   intact, image copies and NDJSON conversion do not repeat, source bytes remain unchanged,
   and the returned prepared paths are present. Internal manifests and diagnostic receipts
   remain local. Inspect the workspace after success and injected failure for owned temporary files.
   Explicit output/cache paths outside `CY_HOME` must remain selected; a physical-home destination
   warns without rejection or relocation.
   For enabled FiftyOne publication, verify one local owner receipt and canonical run
   link with per-split `evaluation_keys`. Confirm native evaluations register existing
   source matches without rematching, preserve backgrounds/filtered overlays, and survive
   fresh-process reload. Confirm `matched_predictions` retains filtered audit labels,
   `evaluated_predictions` excludes them, and native patches do not count them as FP. Check exact wrong-class/duplicate counts and confusion cells,
   persisted label click-through, native rename/delete, interrupted same-task retry and
   concurrent-task isolation against the
   [native evaluation contract](../../../specs/015-fiftyone-native-evaluations/contracts/native-evaluation.md).
   Explicitly install `@clearml-yolo/evaluation` in the server/backend Python environment
   using `install_evaluation_plugin()` and restart App; publication must not install it.
   Inspect `native_evaluation` and `evaluation_reports` for original PR50 and
   AP50/AP75/AP50_95 parity, no-GT unavailable/empty-prediction zero AP, unavailable mAR
   and subset AP/PR, and full-report restoration after exiting a subset. Historical
   payloads without reports remain readable; only new publication/reruns add native
   results. Exercise disabled isolation and optional-publication warning behavior.
7. Check artifact/model upload rejection, callback-registration failure, flush failure and
   interruption with isolated test invocations. Each must fail
   the command and task while retaining local diagnostics until intentional cleanup.
8. Record commands, outcomes and limitations. Store machine-specific logs and task records
   with the environment skill; keep a portable verification summary in the repository.
   Clean up only owned resources per that environment's instructions.

Build and install both distributions in fresh environments for release acceptance.
Verify all ten command helps and documented configuration examples.
Check `cy-init-config` generation and overwrite protection without a ClearML task.
CPU and single-GPU runs are required release gates; report an unavailable device as
an unverified gate. Describe physical multi-GPU execution as unverified unless exercised.
