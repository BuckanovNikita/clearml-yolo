---
name: running-end-to-end-tests
description: Defines real-run acceptance for clearml-yolo - native CPU/GPU training, prediction and validation, direct and cy-queue execution, ClearML artifact download and readback, reports and charts, baseline/candidate comparison, FiftyOne publication, and detector ONNX/TensorRT export. Use for release or integration verification and whenever a claim about native execution, GPU use or ClearML publication needs evidence; mocked unit tests do not establish these outcomes.
---

# Verify the detection workflow

## Contents

- Authority and modes
- Verification checklist
  - 1\. Static checks
  - 2\. Isolated run setup
  - 3\. Direct execution and queue acceptance
  - 4\. Baseline and candidate
  - 5\. Thresholds and standalone commands
  - 6\. Publication and artifact acceptance
  - 7\. Live telemetry and failure handling
  - 8\. Record and clean up
- Release gates
- Multi-model and deployment acceptance

## Authority and modes

Read [prerequisites](references/pipeline-prerequisites.md) for inputs and configuration,
and use the repository's [current contract index](../../../docs/current-contracts.md)
to select each acceptance claim's maintained contract.
Use the project-local [clearml-yolo-environment](../clearml-yolo-environment/SKILL.md)
for this machine's credentials, capacity and cleanup.
This skill defines product acceptance, not deployment or machine setup.

Terms: CY is clearml-yolo; the queue is the separate `cy-queue` package.

Follow the host's active mode and the user's current instructions. In host Plan Mode,
inspect prerequisites and return a read-only verification plan, then stop: do not
start runs, mutate resources, commit, push or deploy; no runs or generated evidence
are required. Outside Plan Mode, an explicit invocation authorizes the documented
verification work; do not request authorization already given. Invoking this skill
grants no commit or deploy authority: commits and deployments still require an explicit
user request for those actions.

## Verification checklist

### 1. Static checks

Run `uv run --frozen --no-sync prek run --all-files`; the hook configuration owns
the verification tool inventory. Follow the native Spec Kit workflow for documentation.

### 2. Isolated run setup

- Configure an isolated ClearML project and output directory. Pass project name and
  tags explicitly.
- Set `CY_HOME` to the task-owned invocation workspace for project data and owned
  temporary files per the filesystem contract.
- Bootstrap initializes project paths while preserving ordinary SDK environment, user
  configuration/cache discovery and global temporary defaults. Project temporary
  callsites pass their directory explicitly.
- Invocation arenas remain retained through and after final uploads/task closure.
- Keep credentials out of published configuration and diagnostic logs; native callback
  image previews are permitted.

### 3. Direct execution and queue acceptance

*Inputs and direct execution*

- Build ground truth from a small YOLO dataset with disjoint validation/test images,
  including an empty image in each split.
- Exercise the top-level `ultralytics` and `ultralytics_predict` groups through locally
  editable generated YAML, with explicit CPU and available GPU devices.
- Verify direct execution preserves native settings and ordinary Hydra multiruns remain
  sequential without queue imports/storage/workers.

*Queue contract*

- Follow the [shared queue contract](../../../docs/queue.md) for immutable sweep
  submission, earliest-runnable admission, exact ordered UUID bindings, concurrent
  disjoint jobs, cross-root GPU exclusion, ownership, stale reorder revisions and
  guardian recovery.

*GPU contraction and recovery*

- Verify acknowledged post-training contraction: unless explicitly freed, the first GPU
  remains reserved through pipeline/descendant exit, and released extra GPUs admit other
  eligible jobs during inference.
- Without a training-finished notification the full allocation stays held.
- Verify lost acknowledgement after durable shrink stops inference and preserves the
  remaining durable claim without restoring released extras.
- Verify repeated signals, worker/guardian forced death and retained uncertain-cleanup
  evidence.

*Admission and operator controls*

- Verify active allocations stay exclusive, stale unlocked records do not veto capacity,
  and automatic admission uses only used VRAM strictly below the configured threshold
  (default 2.0 GiB), with the same frozen value in the fresh guardian launch check.
- Verify physical-index `gpu free`/`release` clears only the selected device's
  reservations and holds without tokens, reasons, force flags, confirmation,
  memory/process checks, signals or original queue access.
- Existing processes, sibling reservations and job outcomes stay intact; older guardians
  cannot affect newer allocations.
- Verify public queue text, JSON, TUI, logs and errors omit full GPU UUIDs and claim tokens.

*Target evidence*

- Real two-user, two-host NFS and physical one/five-GPU eager/compiled acceptance require
  target evidence; record unavailable targets and unresolved native failures as gaps.
- Compare matching direct and queued settings without treating scheduling as a compiler fix.

### 4. Baseline and candidate

- Run a candidate without a baseline; verify evaluation succeeds and comparison is
  skipped.
- Promote a completed baseline with a `prod` tag, run a candidate and verify both
  checkpoints infer the same current test images under matching settings.

### 5. Thresholds and standalone commands

- Confirm validation thresholds are frozen for test and baseline thresholds are loaded
  unchanged.
- Compare metrics, statistical results and report counts.
- Verify dashboard training counts come from the exact trained checkpoint's population:
  unknown counts stay unavailable and valid zero stays zero. Classes with unavailable
  counts keep their metrics in the `Unknown training count` worksheet, are excluded from
  eligibility-dependent aggregates and are explained in the issues worksheet; this is a
  report warning, not invented zeros. Use the
  [report contract](../../../specs/000-baseline/spec.md#reports-and-readable-visualization).
- Exercise `cy-val`, `cy-compare` and `cy-report` independently, including nondefault
  evaluation options.

### 6. Publication and artifact acceptance

*Evaluation artifacts*

- Force-download every required artifact and verify the explicit publication inventory.
  Use the [evaluation publication contract](../../../specs/000-baseline/spec.md#required-publication-and-task-lifecycle)
  for canonical names.
- Download `gt_csv` and `predicts_csv`; confirm one upload per invocation, every original
  source row/ID, exclusions, strict threshold flags and JSON pre/post-threshold
  relationships.
- Check standalone prediction is not evaluated and comparison reinference contexts
  remain separate.
- Verify full/DTRK dashboard contents, exact validation thresholds, paired `Сравнение`
  workbook/exclusions CSV and unchanged developer/business reports.
- Missing automatic baseline must retain candidate dashboards/plots and its recorded skip
  reason without fabricated paired outputs.
- Confirm duplicate evaluation summaries and separate match/threshold/methodology
  sidecars are absent from new uploads while necessary local diagnostics remain.

*Confusion matrix and PR charts*

- Inspect one current-model `Confusion matrix` chart per evaluated split. In a browser,
  select `Counts`, `Row %`, `Column %` and `Overall %`; verify Counts is initially active,
  exactly one heatmap is visible, exact post-threshold counts, class order/background,
  true-row/predicted-column orientation, percentage scaling and zero denominators.
- Inspect one `Precision-recall` chart on test only, combining all classes. Toggle class
  traces through the legend; inspect AP50/method legends and observation hover.
- Inspect PR for authoritative prepared/deduplicated GT and geometry-valid raw prediction
  populations, AP50 parity for both integration methods, supported strategies/ties,
  confidence/cumulative TP/FP hover, empty predictions and unavailable recall/AP without GT.
- Empty classes retain null-gap traces and explicit class-legend status without numerical
  points; confirm their legend entries remain visible and toggleable in the actual browser.
- Confirm readable model/split series and persistent captions survive actual SDK
  publication without context/model IDs, checkpoint hashes or training task IDs.
- Repeat checkpoint/split publication across prediction and comparison candidate and
  verify slot reuse; check unknown identity and colliding names use readable
  fallback/stage/ordinal labels.
- Verify zero baseline chart events, zero comparison/degraded-class/methodology table
  events and zero non-test PR events, while baseline CSV contexts, dashboards, paired
  reports and headline single values remain available. Use the
  [readable plot contract](../../../specs/000-baseline/spec.md#reports-and-readable-visualization).

*Models and native ClearML outputs*

- Verify unused names remain intact and active/archived project-local collisions receive
  shared task/model suffixes without changing IDs/paths.
- Check owned best-model threshold metadata against exact val thresholds and actual
  prediction checkpoint SHA-256 with fresh server readback; standalone metrics must not
  create or mutate models.
- Download the single native best Output Model, load it, and compare model fields with
  checkpoint/trainer data.
- Verify canonical run and native General parameters support replay; when used by the
  invocation, verify the consumed-dataset and explicit-report configurations too.
- Inspect native Scalars, Plots and Debug Samples. Confirm one task per invocation,
  owner-only training/validation callbacks, and no duplicate checkpoint artifacts.
- Enable native plots and verify native validation PR images are excluded while other
  native figures, previews, scalars and the single best model remain; exercise callback
  failure cleanup and the same filter in DDP owner replay.

*Dataset cache and workspace retention*

- Repeat CSV training against one dataset cache: filenames and extension casing remain
  intact, image copies and NDJSON conversion do not repeat, source bytes remain unchanged,
  and the returned prepared paths are present.
- Internal manifests and diagnostic receipts remain local.
- Inspect the workspace after success, failure and cancellation: invocation arenas must
  remain present, including overlapping processes and children starting after parent
  scope exit.
- Startup must not scan, recover or recursively delete old arenas, even with
  malformed/duplicate owner records.
- Reject application output/cache/temp paths outside resolved `CY_HOME`, including
  symlink escapes, before creating destination files. Explicit shared queue metadata is
  the exception; host-local coordination contains only small records/locks.
- Trace normal SDK configuration reads from selected user/home/external settings; require
  unchanged SDK selectors, cwd, bytecode and global temp defaults.
- Verify restored in-memory native ClearML switches, fresh DDP callback scopes and
  unchanged Ultralytics settings files.
- Preserve invalid existing dataset entries and peer staging; native lock failures must
  not use soft-lock fallback.
- Old project-local SDK settings/caches are reused only by explicit opt-in, with no
  migration/deletion.
- Shared queue locks remain host-local and outside invocation scratch.
- Retained files are expected; unsafe descendant cleanup remains a failure or limitation.
  Deliberate scratch maintenance requires confirmed idle descendants.

*FiftyOne publication*

- For enabled FiftyOne publication, verify one local owner receipt and canonical run link
  with per-split `evaluation_keys`.
- Confirm native evaluations register existing source matches without rematching,
  preserve backgrounds/filtered overlays, and survive fresh-process reload.
- Confirm `matched_predictions` retains filtered audit labels, `evaluated_predictions`
  excludes them, and native patches do not count them as FP.
- Check exact wrong-class/duplicate counts and confusion cells, persisted label
  click-through, native rename/delete, interrupted same-task retry and concurrent-task
  isolation against the
  [native evaluation contract](../../../specs/000-baseline/spec.md#optional-fiftyone-publication).
- Explicitly install `@clearml-yolo/evaluation` in the server/backend Python environment
  using `install_evaluation_plugin()` and restart App; publication must not install it.
- Inspect `native_evaluation` and `evaluation_reports` for original PR50 and
  AP50/AP75/AP50_95 parity, no-GT unavailable/empty-prediction zero AP, unavailable mAR
  and subset AP/PR, and full-report restoration after exiting a subset.
- Historical payloads without reports remain readable; only new publication/reruns add
  native results.
- Exercise disabled publication and warn-and-continue behavior.
- Inject real worker hangs/crashes during import, database access, locking, writes and
  shutdown.
- Require finite preflight/publication/lock deadlines (defaults 60/900/30 seconds),
  operation timeout plus at most ten seconds cleanup, no GPU/task/queue ownership in
  publication children, and no success without zero exit plus a matching complete receipt.
- Preserve cancellation semantics. Containment does not confirm the original hang cause.

### 7. Live telemetry and failure handling

- Read console and epoch scalars independently while the task remains active. Under
  healthy service conditions require visibility within ten seconds; include FD/native
  child output, partial lines, pre-epoch failures and watchdog diagnostics.
- Verify quiet prediction image coverage/numerical parity, one operation progress bar and
  retained warnings/final summary.
- Force publisher failure and shutdown timeout: retain local append-only logs, preserve
  the original failure, apply the outcome policy below to required incomplete publication
  and never retry uncertain deliveries.
- Check artifact/model upload rejection, callback-registration failure, flush failure and
  interruption with isolated test invocations, retaining local diagnostics until
  intentional cleanup. Follow the
  [task lifecycle contract](../../../specs/000-baseline/spec.md#required-publication-and-task-lifecycle):
  - Standalone commands and pipelines with `skip_train=true`: each failure must fail the
    command and task.
  - Interruptions and training failures must fail the command in every mode.
  - A pipeline with a verified nonempty trained checkpoint must preserve training success
    when downstream prediction, metrics, comparison, reporting or publication fails, and
    finish with warning completion (the command may exit zero). Verify
    `pipeline_outcome.json`, its text summary and the `pipeline_outcome` artifact record
    the failed/skipped stages and unavailable artifacts; missing uploads stay unverified
    and unreachable ClearML status updates remain explicit local warnings. Queue
    completion alone does not establish full publication.

### 8. Record and clean up

- Record commands, outcomes and limitations.
- Store machine-specific logs and task records with the environment skill; keep a
  portable verification summary in the repository.
- Clean up only owned resources per that environment's instructions.

## Release gates

Verify command help and documented configuration examples from the source checkout.
Project wheels (`.whl`) and source archives (`.tar.gz`) may be built and installed
only to investigate a concrete packaging/install problem; they are not release
deliverables or routine acceptance gates. Follow the
[project release policy](../../../docs/development.md#local-releases).

- Check every `cy-init-config --command` selection and omitted selection (only `cy`),
  both YOLO groups on existing model commands, selected new-model group inventory,
  Faster R-CNN-only `cy-export`, non-model wrapper-only inventory, composition,
  selected-file overwrite protection and unrelated-file preservation without a task.
- CPU and single-GPU runs are required release gates; report an unavailable device as
  an unverified gate.
- Describe physical multi-GPU execution as unverified unless exercised.

## Multi-model and deployment acceptance

When detector integration changes, read
[multi-model acceptance](references/multi-model-acceptance.md) and apply it in addition
to the checklist above.
