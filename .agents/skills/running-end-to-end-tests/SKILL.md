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
   owned temporary files per the filesystem contract. Bootstrap initializes project paths
   while preserving ordinary SDK environment, user configuration/cache discovery and global
   temporary defaults. Project temporary callsites pass their directory explicitly.
   Invocation arenas remain retained through and after final uploads/task closure.
   Keep credentials out of published configuration and diagnostic logs; native callback
   image previews are permitted.
3. Build ground truth from a small YOLO dataset with disjoint validation/test images,
   including an empty image in each split. Exercise the top-level `ultralytics` and
   `ultralytics_predict` groups through locally editable generated YAML, with explicit
   CPU and available GPU devices. Verify direct execution preserves native settings and
   ordinary Hydra multiruns remain sequential without queue imports/storage/workers.
   Follow the [shared queue contract](../../../docs/queue.md) for immutable sweep submission,
   earliest-runnable admission, exact ordered UUID bindings, concurrent disjoint jobs,
   cross-root GPU exclusion, ownership, stale reorder revisions and guardian recovery.
   Verify acknowledged post-training contraction: unless explicitly freed, the first GPU remains reserved through
   pipeline/descendant exit, and released extra GPUs admit other eligible jobs during
   inference. Without a training-finished notification the full allocation stays held.
   Verify lost acknowledgement after durable shrink stops inference and preserves the
   remaining durable claim without restoring released extras. Verify repeated
   signals, worker/guardian forced death and retained uncertain-cleanup evidence. Verify
   active allocations stay exclusive, stale unlocked records do not veto capacity, and
   automatic admission uses only used VRAM strictly below 2 GiB with a fresh launch check.
   Verify physical-index `gpu free`/`release` clears only the selected device's reservations
   and holds without tokens, reasons, force flags, confirmation, memory/process checks,
   signals or original queue access. Existing processes, sibling reservations and job
   outcomes stay intact; older guardians cannot affect newer allocations. Verify public
   queue text, JSON, TUI, logs and errors omit full GPU UUIDs and claim tokens. Real two-user,
   two-host NFS and physical one/five-GPU eager/compiled acceptance require target evidence;
   record unavailable targets and unresolved native failures as gaps. Compare matching direct
   and queued settings without treating scheduling as a compiler fix.
4. Run a candidate without a baseline; verify evaluation succeeds and comparison is
   skipped. Promote a completed baseline with a `prod` tag, run a candidate and verify
   both checkpoints infer the same current test images under matching settings.
5. Confirm validation thresholds are frozen for test and baseline thresholds are loaded
   unchanged. Compare metrics, statistical results and report counts. Exercise `cy-val`,
   `cy-compare` and `cy-report` independently, including nondefault evaluation options.
6. Force-download every required artifact and verify the explicit publication inventory.
   Use the [evaluation publication contract](../../../specs/000-baseline/spec.md#required-publication-and-task-lifecycle)
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
   [readable plot contract](../../../specs/000-baseline/spec.md#reports-and-readable-visualization).
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
   remain local. Inspect the workspace after success, failure and cancellation: invocation
   arenas must remain present, including overlapping processes and children starting after
   parent scope exit. Startup must not scan, recover or recursively delete old arenas,
   even with malformed/duplicate owner records. Reject application output/cache/temp paths
   outside resolved `CY_HOME`, including symlink escapes, before creating destination files.
   Explicit shared queue metadata is the exception; host-local coordination contains only
   small records/locks. Trace normal SDK configuration reads from selected user/home/external
   settings; require unchanged SDK selectors, cwd, bytecode and global temp defaults.
   Verify restored in-memory native ClearML switches, fresh DDP callback scopes and unchanged
   Ultralytics settings files. Preserve invalid existing dataset entries and peer staging;
   native lock failures must not use soft-lock fallback. Old project-local SDK settings/caches
   are reused only by explicit opt-in, with no migration/deletion. Shared queue locks remain
   host-local and outside invocation scratch. Retained files are expected; unsafe descendant cleanup remains
   a failure or limitation. Deliberate scratch maintenance requires confirmed idle descendants.
   For enabled FiftyOne publication, verify one local owner receipt and canonical run
   link with per-split `evaluation_keys`. Confirm native evaluations register existing
   source matches without rematching, preserve backgrounds/filtered overlays, and survive
   fresh-process reload. Confirm `matched_predictions` retains filtered audit labels,
   `evaluated_predictions` excludes them, and native patches do not count them as FP. Check exact wrong-class/duplicate counts and confusion cells,
   persisted label click-through, native rename/delete, interrupted same-task retry and
   concurrent-task isolation against the
   [native evaluation contract](../../../specs/000-baseline/spec.md#optional-fiftyone-publication).
   Explicitly install `@clearml-yolo/evaluation` in the server/backend Python environment
   using `install_evaluation_plugin()` and restart App; publication must not install it.
   Inspect `native_evaluation` and `evaluation_reports` for original PR50 and
   AP50/AP75/AP50_95 parity, no-GT unavailable/empty-prediction zero AP, unavailable mAR
   and subset AP/PR, and full-report restoration after exiting a subset. Historical
   payloads without reports remain readable; only new publication/reruns add native
   results. Exercise disabled publication and warn-and-continue behavior. Inject real
   worker hangs/crashes during import, database access, locking, writes and shutdown.
   Require finite preflight/publication/lock deadlines (defaults 60/900/30 seconds),
   operation timeout plus at most ten seconds cleanup, no GPU/task/queue ownership in
   publication children, and no success without zero exit plus a matching complete receipt.
   Preserve cancellation semantics. Containment does not confirm the original hang cause.
7. Read console and epoch scalars independently while the task remains active. Under healthy
   service conditions require visibility within ten seconds; include FD/native child output,
   partial lines, pre-epoch failures and watchdog diagnostics. Verify quiet prediction image
   coverage/numerical parity, one operation progress bar and retained warnings/final summary.
   Force publisher failure and shutdown timeout: retain local append-only logs, preserve the
   original failure, fail required incomplete publication and never retry uncertain deliveries.
   Check artifact/model upload rejection, callback-registration failure, flush failure and
   interruption with isolated test invocations. Each must fail
   the command and task while retaining local diagnostics until intentional cleanup.
8. Record commands, outcomes and limitations. Store machine-specific logs and task records
   with the environment skill; keep a portable verification summary in the repository.
   Clean up only owned resources per that environment's instructions.

Build and install both distributions in fresh environments for release acceptance.
Verify every installed command help and documented configuration example.
Check every `cy-init-config --command` selection and omitted selection (only `cy`),
both YOLO groups on existing model commands, selected new-model group inventory,
Faster R-CNN-only `cy-export`, non-model wrapper-only inventory,
composition, selected-file overwrite protection and unrelated-file preservation without a task.
CPU and single-GPU runs are required release gates; report an unavailable device as
an unverified gate. Describe physical multi-GPU execution as unverified unless exercised.

## Multi-model and deployment acceptance

When detector integration changes, follow the
[multi-model acceptance guide](../../../specs/000-baseline/spec.md#detector-backends-and-deployment-export)
and its backend/export contracts in addition to the shared workflow checks above.
Exercise every advertised preset with real short training, pretrained initialization,
best selection, standalone copied/downloaded checkpoint reload, prediction and validation.
Use non-square images, exact string labels and empty-image records. Check one owner task,
one best Output Model, descriptor/hash integrity, telemetry and required upload/flush failure
behavior. Synthetic random-weight smoke tests establish execution only.

Run new-family comparisons against YOLO and another native family on identical current
images with frozen thresholds. Inspect independent backend routing, common device/settings,
checkpoint-owned vocabulary and recorded effective preprocessing. Verify raw-reference
assertions, cache separation and checkpoint/source conflicts. Repeat both execution
paths (direct and queued), replay guards, mixed-family sweeps, cancellation and owned-process cleanup.

For every Faster R-CNN preset and FP32/FP16, generate the actual ONNX graph, build the
engine and execute all required size/batch cases, profile transitions, empty/crowded inputs
and rejection cases. Separately execute in a fresh runtime without Torch or ClearML.
Freeze labeled corpus/checkpoint bytes and actual evaluator source identity; require
meaningful nonzero native mAP and the documented precision-specific mAP loss limits.
Report preprocessing, class-aware detection matching, unavailable raw tensors, latency
and scoped memory evidence separately. A quality report alone does not prove standalone
execution or all numerical/scene cases. CUDA 11.8 deployment requires separate target
evidence; a newer-CUDA local engine does not prove target compatibility.
