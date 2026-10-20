# Current contract index

For practical commands, start with the [usage guide](../README.md). For setup,
configuration, storage, provenance and operations, use the
[technical reference](../TECH_DETAILS.md).

Use this index to select the maintained contract for a topic. The
[stage-zero specification](../specs/000-baseline/spec.md) consolidates the pre-reset
contracts. New features amend that baseline and the affected topic guides. A contract describes required behavior; inspect implementation and
tests before claiming verification. Surface an unexplained mismatch
rather than silently changing the requirement or code.

The [project contract summary](project-contracts.md) provides the cross-cutting command,
configuration, output, tracking and evaluation rules formerly listed in `AGENTS.md`.

| Topic | Maintained contract | Implementation evidence | Check / limitation |
| --- | --- | --- | --- |
| Python installation compatibility | [Supported interpreter range](development.md#python-compatibility), [compatibility contract](../specs/000-baseline/spec.md#compatibility-and-module-interfaces) | [Package metadata](../pyproject.toml), [lockfile](../uv.lock), [supervision preflight](../src/clearml_yolo/adapters/runtime/process_tree.py) | [Linux capability preflight](../tests/test_process_capabilities.py), [executed matrix and limits](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/032-python-compatibility/verification.md) |
| Shared scientific and workbook capabilities | [Shared evaluation and reporting](shared-evaluation-reporting.md) | [Evaluation adapters](../src/clearml_yolo/adapters/evaluation), [reporting adapters](../src/clearml_yolo/adapters/reporting), [frozen compatibility tests](../tests/test_shared_extraction_compatibility.py) | [Frozen compatibility](../tests/test_shared_extraction_compatibility.py), [shared comparison](../tests/test_shared_comparison.py) |
| Python architecture and target migration | [Import boundaries](import-boundaries.md), [module/effect diagram](module-architecture.md), [Python import migration](python-import-migration.md) | [Executable import contracts](../.importlinter), [architecture checks](../tests/test_architecture.py), [workflow ports](../src/clearml_yolo/application/ports.py), [composition](../src/clearml_yolo/entrypoints/composition.py) | [Positive/negative architecture fixtures](../tests/test_architecture.py); [static limits](import-boundaries.md#initializers-and-runtime-targets) |
| Commands and output routing | [CLI](../specs/000-baseline/spec.md#commands-and-configuration) | [Entrypoints and checks](../pyproject.toml), [output identity](../src/clearml_yolo/adapters/storage/run_identity.py), [pipeline](../src/clearml_yolo/application/use_cases/pipeline.py) | [Command configuration](../tests/test_release_config.py), [output containment](../tests/test_project_output_containment.py) |
| Readable messages, links and report labels | [Readable output](readable-output.md), [readable shared queue specification](queue.md) | [Pure formatting](../src/clearml_yolo/core/presentation.py), [queue presentation](../src/clearml_yolo/entrypoints/queue_presentation.py), [workbook identity](../src/clearml_yolo/adapters/reporting/workbook_identity.py) | [Formatting and stream boundaries](../tests/test_readable_output.py), [queue readability](../tests/test_queue_readability.py), [workbook identity](../tests/test_workbook_identity.py) |
| Filesystem defaults and explicit destinations | [Filesystem ownership](filesystem-policy.md) | [Project bootstrap](../src/clearml_yolo/adapters/runtime/bootstrap.py), [Workspace policy](../src/clearml_yolo/adapters/storage/filesystem.py), [native runtime](../src/clearml_yolo/adapters/integrations/native_runtime.py) | [Filesystem boundaries](../tests/test_filesystem.py), [native containment](../tests/test_native_output_containment.py) |
| Explicit image cache deduplication | [Deduplication CLI](../specs/000-baseline/spec.md#explicit-cache-deduplication) | [Command](../src/clearml_yolo/entrypoints/dedup.py), [cache implementation](../src/clearml_yolo/adapters/storage/dedup.py) | [Deduplication behavior](../tests/test_dedup.py), [CLI checks](../tests/test_dedup_cli.py) |
| GPU scheduling, queue configuration, archives and execution controls | [Shared cy-queue](queue.md), [operator controls](queue.md#physical-gpu-operator-controls) | [Queue policy](../src/clearml_yolo/core/queue.py), [application ports](../src/clearml_yolo/application/queue.py), [settings](../src/clearml_yolo/adapters/queue/settings.py), [adapters](../src/clearml_yolo/adapters/queue) | [Settings](../tests/test_queue_settings.py), [archive](../tests/test_queue_archive.py), [handoff](../tests/test_queue_handoff.py), [generations](../tests/test_gpu_generations.py); [physical/NFS limits](implementation-status.md) |
| Selected export and runtime ownership | [Runtime isolation](runtime-isolation.md) | [Exporter](../src/clearml_yolo/entrypoints/hydra/config_tree.py), [bootstrap](../src/clearml_yolo/adapters/runtime/bootstrap.py), [bounded publisher](../src/clearml_yolo/adapters/fiftyone/bounded.py) | [Selected export](../tests/test_config_tree.py), [runtime ownership](../tests/test_runtime_bootstrap.py), [bounded publication](../tests/test_bounded_fiftyone.py) |
| Native training and prediction groups | [Native configuration and examples](../specs/000-baseline/spec.md#native-configuration) | [Native settings](../src/clearml_yolo/adapters/yolo/config.py), [registration](../src/clearml_yolo/entrypoints/hydra/configs.py), [export](../src/clearml_yolo/entrypoints/hydra/config_tree.py) | [Precedence/forwarding](../tests/test_native_config.py), [native settings validation](../tests/test_native_settings_validation.py) |
| Detector families and portable checkpoints | [Backend contract](../specs/000-baseline/spec.md#detector-backends-and-deployment-export), [model guide](multi-model-backends.md) | [Typed models](../src/clearml_yolo/core/models.py), [backend routing](../src/clearml_yolo/adapters/integrations/detectors.py), [checkpoint binding](../src/clearml_yolo/adapters/storage/checkpoint.py), [owner publication](../src/clearml_yolo/adapters/clearml/detectors.py) | [Workflow routing](../tests/test_detector_workflows.py), [checkpoint/recovery](../tests/test_detector_recovery.py); [native backend evidence/limits](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/025-multi-model-backends/verification.md) |
| Faster R-CNN ONNX/TensorRT export | [Export and deployment](tensorrt-deployment.md) | [Export workflow](../src/clearml_yolo/application/use_cases/export.py), [composition](../src/clearml_yolo/adapters/integrations/export_operations.py), [engine build](../src/clearml_yolo/adapters/export/build.py), [FP16 tensor types](../src/clearml_yolo/adapters/export/precision.py), [attention precision](../src/clearml_yolo/adapters/export/attention_precision.py), [standalone runtime](../src/clearml_yolo/adapters/export/runtime.py), [quality verification](../src/clearml_yolo/adapters/export/verification.py) | [Export workflow](../tests/test_export_workflow.py), [precision](../tests/test_export_precision.py), [quality gate](../tests/test_export_quality.py); [target-runtime limits](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/025-multi-model-backends/verification.md) |
| Detection CSV identity, media paths and dataset cache | [Input/provenance contract](input-provenance.md), [dataset inputs](../specs/000-baseline/spec.md#detection-inputs-dataset-cache-and-output-routing), [dataset cache](../specs/000-baseline/spec.md#detection-inputs-dataset-cache-and-output-routing) | [Storage reads](../src/clearml_yolo/adapters/storage/file_io.py), [cache](../src/clearml_yolo/adapters/storage/dataset_cache.py), [input regression evidence](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/.specify/bugs/input-evaluation-correctness/test.md) | [Input regressions](../tests/test_input_correctness.py), [cache checks](../tests/test_dataset_cache.py), [native/download evidence](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/docs/evidence/2026-10-15-correctness-cleanup/native-verification.md) |
| Configuration resolution and remote replay | [File resolution](../specs/000-baseline/spec.md#configuration-resolution-and-replay), [tracking and recovery](../specs/000-baseline/spec.md#required-publication-and-task-lifecycle) | [Resolution](../src/clearml_yolo/entrypoints/hydra/config_resolution.py), [session adapter](../src/clearml_yolo/adapters/clearml/session.py) | [Resolution](../tests/test_config_resolution.py), [upload commands](../tests/test_config_upload_commands.py), [replay](../tests/test_model_replay.py) |
| Stable experiment parameters and controller cache identity | [Parameter and cache contract](../specs/000-baseline/spec.md#stable-experiment-parameters-and-controller-caching), [controller setup](../TECH_DETAILS.md#clearml-pipeline-cache-identity) | [Native projection](../src/clearml_yolo/adapters/clearml/parameters.py), [hash projection](../src/clearml_yolo/adapters/clearml/cache.py), [dataset identity](../src/clearml_yolo/adapters/storage/dataset_cache.py) | [SDK cache hashing](../tests/test_clearml_cache.py), [native publication](../tests/test_native_runtime.py), [replay](../tests/test_model_replay.py); controller registration is explicit and mocked checks do not establish live cache reuse |
| Artifacts, native callbacks and task completion | [Publication inventory](../specs/000-baseline/spec.md#publication-inventory), [evaluation publication](../specs/000-baseline/spec.md#required-publication-and-task-lifecycle), [native tracking](../specs/000-baseline/spec.md#required-publication-and-task-lifecycle), [model metadata](../specs/000-baseline/spec.md#model-verification-and-source-identity) | [Artifact names](../src/clearml_yolo/core/artifact_names.py), [native runtime](../src/clearml_yolo/adapters/integrations/native_runtime.py), [model verification](../src/clearml_yolo/adapters/clearml/native.py), [display naming](../src/clearml_yolo/adapters/clearml/naming.py), [result bundle](../src/clearml_yolo/adapters/clearml/results.py), [DDP relay](../src/clearml_yolo/adapters/integrations/native_ddp.py), [fresh DDP trainer](../src/clearml_yolo/adapters/integrations/native_trainer.py) | [Tracking contract](../tests/test_native_tracking_contract.py), [result lineage](../tests/test_clearml_results.py), [lifecycle](../tests/test_execution_lifecycle.py); [native/download evidence](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/docs/evidence/2026-10-15-correctness-cleanup/native-verification.md) |
| Evaluation, comparison, thresholds and reports | [Task recovery](../specs/000-baseline/spec.md#evaluation-comparison-and-historical-model-recovery), [evaluation publication](../specs/000-baseline/spec.md#required-publication-and-task-lifecycle), [readable plots](../specs/000-baseline/spec.md#reports-and-readable-visualization), [Publication inventory](../specs/000-baseline/spec.md#publication-inventory), [CLI evaluation contract](../specs/000-baseline/spec.md#commands-and-configuration) | [Metrics](../src/clearml_yolo/application/use_cases/metrics.py), [comparison](../src/clearml_yolo/application/use_cases/compare.py), [comparison workbook](../src/clearml_yolo/adapters/reporting/comparison_workbook.py), [exact thresholds](../src/clearml_yolo/adapters/clearml/models.py), [source lineage](../src/clearml_yolo/core/evaluation/result_rows.py), [neutral payloads](../src/clearml_yolo/core/evaluation/schema.py), [interactive reporting](../src/clearml_yolo/adapters/clearml/report.py), [paired reports](../src/clearml_yolo/application/use_cases/report.py) | [Metrics](../tests/test_metrics.py), [comparison](../tests/test_comparison_scoring.py), [recovery](../tests/test_comparison_recovery.py), [workbook](../tests/test_comparison_workbook.py) |
| FiftyOne publication | [Publisher and native evaluations](../specs/000-baseline/spec.md#optional-fiftyone-publication), [current inventory](../specs/000-baseline/spec.md#publication-inventory) | [Owner publication](../src/clearml_yolo/application/use_cases/publication.py), [replaceable adapter](../src/clearml_yolo/adapters/fiftyone/publisher.py) | [Publisher checks](../tests/test_fiftyone_publisher.py), [native evaluation projection](../tests/test_fiftyone_evaluation_results.py); [dated native evidence](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/specs/015-fiftyone-native-evaluations/verification-2026-10-06.md) |
| Operation diagnostics and stalled-run capture | [Diagnostics](diagnostics.md) | [Tracing](../src/clearml_yolo/adapters/observability/tracing.py), [FD capture](../src/clearml_yolo/adapters/observability/capture.py), [publisher](../src/clearml_yolo/adapters/clearml/console.py), [guardian](../src/clearml_yolo/adapters/queue/guardian.py), [native cleanup](../src/clearml_yolo/adapters/integrations/native_runtime.py) | [Diagnostics](../tests/test_diagnostics.py), [console capture](../tests/test_console_capture.py), [queue logging](../tests/test_queue_logging.py) |
| Local dependency sources | [Development setup and local copies](development.md#external-dependencies) | [Ignore rules](../.gitignore), [package configuration](../pyproject.toml), [editable lock](../uv.lock) | [Metadata/tooling boundaries](../tests/test_tooling_boundaries.py), [installed dependency evidence](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/docs/evidence/2026-10-15-correctness-cleanup/packaging-verification.md) |
| Local versioning, changelog and release hooks | [Local release](../specs/000-baseline/spec.md#local-release-interface) | [Release helper](../scripts/local_release.py), [hook configuration](../.pre-commit-config.yaml), [generated changelog](../CHANGELOG.md) | [Release fixtures](../tests/test_local_release.py); actual delivery requires commit/tag ref verification |
| Markdown structure, local links and anchors | [Documentation checker contract](../specs/000-baseline/spec.md#verification-and-delivery-requirements), [development checks](development.md#verification) | [Read-only checker](../scripts/check_docs.py), [checker regressions](../tests/test_check_docs.py) | [Positive/negative fixtures](../tests/test_check_docs.py); external links/examples and Mermaid grammar excluded from parser checks |

## Authority and verification

Normative behavior belongs in the topic contracts above. Each rule needs a linked
executable check or an explicit verification limitation. The
[module](module-architecture.md), [queue](queue-lifecycles.md) and
[input provenance](input-provenance.md) diagrams explain ownership and invariants.
The [status map](implementation-status.md) separates implementation, verification,
release, acceptance disposition and unverified limits without rewriting completed task history.

## Maintaining consistency

Spec Kit implementation and bug-fix workflows require a **Documentation update**
stage before completion. Follow the [project workflow policy](agent-workflow.md#mandatory-documentation-stage)
to plan explicit documentation tasks, reconcile them with the actual changes and
validate the result. If no documentation changes are needed, record the reviewed scope
and reason in the workflow artifacts. Missing required updates or failed validation
blocks completion.

For a contract change, inspect this index, affected contracts, active specifications,
quickstarts, README, project-owned integration skills, the portable
[clearml-yolo usage skill](https://github.com/BuckanovNikita/corp-skills/tree/main/skills/clearml-yolo)
and any applicable environment skill. The
[skill maintenance stage](agent-workflow.md#portable-usage-skill-maintenance)
owns cross-repository updates and acceptance evidence.
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

The historical force/admission controls are superseded by direct native execution and
explicit queue resource requests. Regenerate old configuration examples; do not silently
translate their controls. See [migration and operations](queue.md).

Active executable configuration, informational differences and early validated General
follow the [startup contract](../specs/000-baseline/spec.md#configuration-resolution-and-replay).
Contributor completion controls [artifact timing](../specs/000-baseline/spec.md#required-publication-and-task-lifecycle);
source review and [dated acceptance limits](../specs/000-baseline/spec.md#historical-evidence-and-limits) remain distinct.
