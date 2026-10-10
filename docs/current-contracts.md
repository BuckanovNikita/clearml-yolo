# Current contract index

Use this index to select the maintained contract for a topic. Feature numbering and
release dates alone do not establish authority: later features amend specific parts of
earlier contracts. A contract describes required behavior; inspect implementation and
tests before claiming verification. Surface an unexplained mismatch
rather than silently changing the requirement or code.

The [project contract summary](project-contracts.md) provides the cross-cutting command,
configuration, output, tracking and evaluation rules formerly listed in `AGENTS.md`.

| Topic | Maintained contract | Implementation evidence |
|---|---|---|
| Python architecture and target migration | [Clean architecture specification](../specs/021-clean-architecture/spec.md), [Python import migration](python-import-migration.md) | [Workflow ports](../src/clearml_yolo/application/ports.py), [composition](../src/clearml_yolo/entrypoints/composition.py), [scientific validation](../src/clearml_yolo/core/validation/schemas.py), [evaluation records](../src/clearml_yolo/core/evaluation/models.py), [computation](../src/clearml_yolo/adapters/evaluation/scoring.py), [report rendering](../src/clearml_yolo/adapters/reporting/evaluation.py) |
| Commands and output routing | [CLI](../specs/001-release-030/contracts/cli.md) | [Entrypoints and checks](../pyproject.toml), [output identity](../src/clearml_yolo/adapters/storage/run_identity.py), [pipeline](../src/clearml_yolo/application/use_cases/pipeline.py) |
| Filesystem defaults and explicit destinations | [Filesystem ownership](filesystem-policy.md) | [Workspace policy](../src/clearml_yolo/adapters/storage/filesystem.py), [native runtime](../src/clearml_yolo/adapters/integrations/native_runtime.py) |
| Explicit image cache deduplication | [Deduplication CLI](../specs/018-cache-image-dedup/contracts/cli.md) | [Command](../src/clearml_yolo/entrypoints/dedup.py), [cache implementation](../src/clearml_yolo/adapters/storage/dedup.py) |
| GPU availability, device demand and direct execution | [GPU execution](../specs/022-simple-gpu-wait/contracts/execution.md), [quickstart](../specs/022-simple-gpu-wait/quickstart.md) | [Resource probe](../src/clearml_yolo/adapters/runtime/gpu_resources.py), [GPU wait](../src/clearml_yolo/adapters/runtime/gpu_wait.py), [configuration translation](../src/clearml_yolo/entrypoints/hydra/execution.py), [invocation](../src/clearml_yolo/entrypoints/hydra/common.py) |
| Native training and prediction groups | [Native configuration](../specs/005-explicit-detection-config/contracts/native-configuration.md), [example layout](../specs/007-detection-config-cleanup/contracts/configuration-and-artifacts.md) | [Native settings](../src/clearml_yolo/adapters/yolo/config.py), [registration](../src/clearml_yolo/entrypoints/hydra/configs.py), [export](../src/clearml_yolo/entrypoints/hydra/config_tree.py) |
| CSV training and dataset cache | [Dataset inputs](../specs/004-ground-truth-training/contracts/cli.md), [current publication](../specs/008-dataset-clearml-tracking/contracts/publication.md) | [Training](../src/clearml_yolo/application/use_cases/train.py), [cache](../src/clearml_yolo/adapters/storage/dataset_cache.py) |
| Configuration resolution and remote replay | [File resolution](../specs/009-resolved-config-uploads/contracts/configuration-files.md), [tracking and recovery](../specs/010-native-clearml-integration/contracts/tracking-publication.md) | [Resolution](../src/clearml_yolo/entrypoints/hydra/config_resolution.py), [session adapter](../src/clearml_yolo/adapters/clearml/session.py) |
| Artifacts, native callbacks and task completion | [Publication inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md), [evaluation publication](../specs/014-evaluation-publication/contracts/publication.md), [native tracking](../specs/010-native-clearml-integration/contracts/tracking-publication.md), [model metadata](../specs/008-dataset-clearml-tracking/contracts/model-metadata.md) | [Artifact names](../src/clearml_yolo/core/artifact_names.py), [native runtime](../src/clearml_yolo/adapters/integrations/native_runtime.py), [model verification](../src/clearml_yolo/adapters/clearml/native.py), [display naming](../src/clearml_yolo/adapters/clearml/naming.py), [result bundle](../src/clearml_yolo/adapters/clearml/results.py), [DDP relay](../src/clearml_yolo/adapters/integrations/native_ddp.py) |
| Evaluation, comparison, thresholds and reports | [Task recovery](../specs/012-remove-legacy-compatibility/contracts/task-recovery.md), [evaluation publication](../specs/014-evaluation-publication/contracts/publication.md), [readable plots](../specs/020-readable-evaluation-plots/contracts/plots.md), [Publication inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md), [CLI evaluation contract](../specs/001-release-030/contracts/cli.md) | [Metrics](../src/clearml_yolo/application/use_cases/metrics.py), [comparison](../src/clearml_yolo/application/use_cases/compare.py), [comparison workbook](../src/clearml_yolo/adapters/reporting/comparison_workbook.py), [exact thresholds](../src/clearml_yolo/adapters/clearml/models.py), [source lineage](../src/clearml_yolo/core/evaluation/result_rows.py), [neutral payloads](../src/clearml_yolo/core/evaluation/schema.py), [interactive reporting](../src/clearml_yolo/adapters/clearml/report.py), [paired reports](../src/clearml_yolo/application/use_cases/report.py) |
| FiftyOne publication | [Publisher](../specs/006-fiftyone-integration/contracts/publisher.md), [native evaluations](../specs/015-fiftyone-native-evaluations/contracts/native-evaluation.md), [current inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md) | [Owner publication](../src/clearml_yolo/application/use_cases/publication.py), [replaceable adapter](../src/clearml_yolo/adapters/fiftyone/publisher.py) |
| Operation diagnostics and stalled-run capture | [Diagnostics](diagnostics.md) | [Tracing and watchdog](../src/clearml_yolo/adapters/observability/tracing.py), [execution resource port](../src/clearml_yolo/application/ports.py), [composition](../src/clearml_yolo/entrypoints/composition.py), [GPU wait](../src/clearml_yolo/adapters/runtime/gpu_wait.py), [native cleanup](../src/clearml_yolo/adapters/integrations/native_runtime.py) |
| Local dependency sources | [Development setup](development.md#external-dependencies), [local copies](../specs/017-local-dependency-copies/spec.md) | [Ignore rules](../.gitignore), [package configuration](../pyproject.toml), [editable lock](../uv.lock) |
| Local versioning, changelog and release hooks | [Local release](../specs/003-semantic-release/contracts/local-release.md) | [Release helper](../scripts/local_release.py), [hook configuration](../.pre-commit-config.yaml), [generated changelog](../CHANGELOG.md) |

## Changes that must propagate

Python integrations use the `core`, `application`, `adapters` and `entrypoints`
packages. Application workflows receive explicit `WorkflowDependencies`; CLI
composition supplies them outside Hydra configuration. Old module paths and saved
Python `_target_` strings must migrate together; no compatibility aliases remain.
Regenerate editable YAML after backing up custom overrides as described in the
[import migration](python-import-migration.md).

`LOGURU_LEVEL=TRACE` enables the maintained [operation diagnostic contract](diagnostics.md):
lifecycle records preserve caller Loguru sinks; a separate watchdog writes 30-second
per-thread deepest-operation heartbeats and 60-second changed grouped location-only
stacks to captured stderr, bounded to eight groups and 12 frames. Scalar context is
redacted and bounded; full configuration/data/locals/source dumps are excluded.
Application workflows access tracing through the execution-resource port; evaluation
and FiftyOne adapters may depend on observability. Keep operation coverage and this
guide current when blocking boundaries change. Cleanup and `command.return` are
observable without altering execution, retry, timeout or GPU allocation policy.

Pandera validates scientific DataFrames by stage without coercing, dropping or
renumbering source rows. Storage adapters retain lexical CSV interpretation and
compatibility diagnostics. Raw invalid prediction geometry remains source evidence;
evaluation preparation warns and removes it before matching/AP. Native publication
continues to allow finite ordered boxes collapsed by clipping. Evaluation computation
returns project-owned metrics/matches/payloads; rendering alone writes dashboards and
plots, and paired significance calculations use pure core records.

Native model commands use complete top-level `ultralytics` and `ultralytics_predict`
groups. Prediction reads its resolved group; visible references provide inheritance.
Raw wrapper `cfg`, non-null native `cfg`, nested stage-native mappings and duplicate
native comparison inference fields are unsupported and fail ordinary strict validation.

The five model commands derive whole-GPU demand from native groups and poll availability
before ClearML/native initialization. The calling process executes directly; selected logical
indices follow inherited CUDA visibility. Requested values and effective devices remain separate.
CPU/MPS bypass inventory. Fail-closed NVML, own-PID reuse, demand validation, native DDP ownership,
memory cleanup and sequential standard BasicLauncher behavior are defined by the
[GPU execution contract](../specs/022-simple-gpu-wait/contracts/execution.md).
Feature 022 supersedes feature 013 FIFO/reservation/child execution requirements and the
queue-specific constitution amendment. Historical artifacts remain unchanged apart from
supersession notices; no queue data is read, migrated or deleted. Availability is not an
exclusive allocation, and simultaneous commands can select the same GPU.

ClearML publications follow the current inventory, not old artifact counts. Native
YAML, NDJSON, archives, manifests and diagnostic/publication receipts remain local.
Consumed dataset and explicit report configurations are Configuration Objects; canonical
`run` and native `General` support replay. Configuration copies are not artifacts.
Native owner callbacks may publish training/validation previews and non-PR plots; native
validation PR uploads are filtered with callback state restored on success/failure.
Native DDP descendants do not publish.
The native best checkpoint uses one Output Model, verified before completion.

The [evaluation publication amendment](../specs/014-evaluation-publication/contracts/publication.md)
defines invocation-owned `gt_csv`/`predicts_csv`, durable context enrichment, source lineage
and JSON pre/post-threshold relationships. Canonical CSVs upload once before completion.
Original full/DTRK dashboards and the three paired comparison/report workbooks remain
XLSX; exact validation thresholds and comparison exclusions remain CSV. Duplicate evaluation
summaries and separate match/threshold/methodology sidecars stay local. Missing automatic
baseline publishes candidate dashboards/plots and records its skip reason.

Each current-model split has one `Confusion matrix` chart with selectable `Counts`,
`Row %`, `Column %` and `Overall %` views of exact post-threshold counts; Counts is default.
One `Precision-recall` chart combines class traces at IoU 0.50 on test only.
Baseline charts and comparison/degraded-class/methodology tables are excluded from Plots;
baseline dashboards/rows, paired reports and headline single values remain available.
Matrix rows are true labels, columns predicted labels;
normalization preserves counts/order/background and shows zero-denominator observations.
PR uses authoritative geometry-valid AP populations and public matching, with AP50 parity
checks for methods, strategies and ties. No GT has unavailable recall/AP; GT without
predictions has empty PR/AP50 zero. Empty populations have explicit class-legend status
and null-gap traces without numerical points. Class legends retain AP/method; hover retains confidence and cumulative
TP/FP. Readable model/split series omit internal IDs and hashes; checkpoint/split slots
are reused, with model/context fallback and readable stage/ordinal collision suffixes.
Numeric and Unicode class labels remain distinct. See the
[presentation amendment](../specs/020-readable-evaluation-plots/contracts/plots.md).

Project-local exact display-name collisions include archived tasks/models and exclude
current IDs; shared readable suffixes are rechecked without changing paths or model IDs.
Calibration thresholds may enrich only an invocation-owned best model after checkpoint
hash association and metadata readback. Standalone metrics never mutates models.

New evaluation/report outputs carry the finalized source model name and full original
training task ID through checkpoint/prediction hash bindings, contexts and manifests.
Stored provenance wins over fallback labels; inputs without provenance require explicit
labels and display unavailable training provenance without registering a model.
The [identity presentation contract](../specs/014-evaluation-publication/contracts/publication.md#source-identity-on-new-results)
defines entrypoint labels, worksheet/local raster captions and repeated printed banners;
the readable plot amendment governs current ClearML chart captions.
Workbooks normalize horizontal print width to one page while preserving original body
styles/formulas and explicit row breaks. Project adapters expose original layouts to
report/threshold readers; pinned dependencies and historical artifacts are unchanged.

Validation, metrics and comparison warn and drop invalid prediction geometry before
preprocessing, calibration and mAP, preserving raw CSVs. All-invalid predictions are
scored as empty, with unmatched ground truth counted as false negatives. See the
[evaluation safety contract](../specs/001-release-030/contracts/cli.md#evaluation-input-and-output-safety).

Pipeline comparison uses the current `test` images. Standalone `cy-compare` defaults to
`split=test` and accepts another split present in the current ground truth. Both models
use the selected split under the same inference/evaluation settings; comparison does
not recalibrate thresholds. Reports consume that pair and its manifest split. Source
task/model links or task/artifact identities provide provenance from the same checkpoint
selection used for weights; artifact sources have no invented model link. The
[recovery amendment](../specs/012-remove-legacy-compatibility/contracts/task-recovery.md)
supersedes the 2026-10-02 current-only recovery restriction. Explicit maps take precedence,
then ordered named threshold payloads and dashboards; dashboard recovery warns about
rounding and unavailable calibration provenance. Present malformed sources fail strictly.
Historical predictions and source General/Configuration Objects are not imported over
current comparison settings. Available threshold precision is preserved; checkpoint
architecture compatibility with the installed runtime is not guaranteed.
All report workbooks preserve one-sided class metrics with `NA` for the unavailable
model/comparison. Model averages and business verdict inputs use each model's own eligible
classes; statistical comparisons use shared eligible classes. The maintained
[CLI evaluation contract](../specs/001-release-030/contracts/cli.md) defines those populations.
Developer/business reports show aggregate availability below each metric table as
`<metric>-valid-class-count` (for example `AP50-valid-class-count: 18/20`), preserving
finite-value counts including zero. Coverage columns and their empty class-row cells
are removed; missing actual metric values remain `NA`.

FiftyOne visualization is optional. Its setup or publication failures warn and continue
the owning computation; setup failure disables visualization for that invocation.
Successful publication retains one local receipt and the canonical run link, including
`evaluation_keys` for each evaluated split. Native evaluation registration consumes exact
source matches without rematching and persists original confusion/PR50/AP reports.
Native predictions use `evaluated_predictions`, excluding filtered boxes; the
`matched_predictions` audit overlay retains them without native evaluated status.
The explicit `@clearml-yolo/evaluation` extension supplies `native_evaluation` and
`evaluation_reports`; install it in the server/backend environment and restart App.
No global automatic install or historical migration occurs. Restricted subsets expose
fixed-threshold counts with unavailable AP/PR; mAR is unavailable. Legacy payloads with
no report remain readable with missing report values unavailable. Raw
predictions preserve finite, ordered zero-area boxes from native clipping and their
CSV indices; publication does not filter inference data or change metric inputs.
See the [publisher contract](../specs/006-fiftyone-integration/contracts/publisher.md).

## Maintaining consistency

Spec Kit implementation and bug-fix workflows require a **Documentation update**
stage before completion. Follow the [project workflow policy](agent-workflow.md#mandatory-documentation-stage)
to plan explicit documentation tasks, reconcile them with the actual changes and
validate the result. If no documentation changes are needed, record the reviewed scope
and reason in the workflow artifacts. Missing required updates or failed validation
blocks completion.

For a contract change, inspect this index, affected contracts, active specifications,
quickstarts, README, project-owned integration skills and any applicable
environment skill.
Update current normative text together. Preserve completed task history and dated
analysis/verification; annotate superseded intent and link to current guidance.
Do not turn historical observations into a claim about a new implementation.

Specs record intent, task ledgers record work, and dated evidence records checks
performed. Completed checkboxes alone do not establish live acceptance. Current status
must cite evidence and retain its limitations. Avoid copied artifact counts and
dependency versions; use the maintained inventory and package metadata.

Workflow instructions obey the active host mode and existing user authorization.
Planning permits inspection, not artifact writes or mutating hooks. A skill cannot
authorize commits, deployment, dependency updates or unrelated repairs. Verification is
required proportionally; adding new tests depends on affected behavior and risk.

Keep installed Spec Kit skills, commands, templates and `.specify/` files unchanged
unless the user explicitly requests modifying them. Project workflow overrides belong
in [agent workflow policy](agent-workflow.md), linked from [AGENTS.md](../AGENTS.md),
or separate project hooks. Feature specifications in
`specs/` remain maintained project documentation. Upstream regeneration must not erase
separate project policy or treat historical requirements as current authority.

Machine-specific setup and evidence stay in the applicable global environment skill.
The repository's [end-to-end skill](../.agents/skills/running-end-to-end-tests/SKILL.md)
defines portable acceptance. Historical releases and dated evidence describe
observations then; they are not current execution recipes.
