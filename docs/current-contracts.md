# Current contract index

For practical commands, start with the [usage guide](../README.md). For setup,
configuration, storage, provenance and operations, use the
[technical reference](../TECH_DETAILS.md).

Use this index to select the maintained contract for a topic. Feature numbering and
release dates alone do not establish authority: later features amend specific parts of
earlier contracts. A contract describes required behavior; inspect implementation and
tests before claiming verification. Surface an unexplained mismatch
rather than silently changing the requirement or code.

The [project contract summary](project-contracts.md) provides the cross-cutting command,
configuration, output, tracking and evaluation rules formerly listed in `AGENTS.md`.

| Topic | Maintained contract | Implementation evidence | Check / limitation |
| --- | --- | --- | --- |
| Python installation compatibility | [Supported interpreter range](development.md#python-compatibility), [compatibility contract](../specs/032-python-compatibility/contracts/python.md) | [Package metadata](../pyproject.toml), [lockfile](../uv.lock), [supervision preflight](../src/clearml_yolo/adapters/runtime/process_tree.py) | [Linux capability preflight](../tests/test_process_capabilities.py), [executed matrix and limits](../specs/032-python-compatibility/verification.md) |
| Shared scientific and workbook capabilities | [Shared evaluation and reporting](shared-evaluation-reporting.md), [compatibility specification](../specs/028-shared-extraction/spec.md) | [Evaluation adapters](../src/clearml_yolo/adapters/evaluation), [reporting adapters](../src/clearml_yolo/adapters/reporting), [frozen compatibility tests](../tests/test_shared_extraction_compatibility.py) | [Frozen compatibility](../tests/test_shared_extraction_compatibility.py), [shared comparison](../tests/test_shared_comparison.py) |
| Python architecture and target migration | [Import boundaries](import-boundaries.md), [module/effect diagram](module-architecture.md), [Python import migration](python-import-migration.md) | [Executable import contracts](../pyproject.toml), [architecture checks](../tests/test_architecture.py), [workflow ports](../src/clearml_yolo/application/ports.py), [composition](../src/clearml_yolo/entrypoints/composition.py) | [Positive/negative architecture fixtures](../tests/test_architecture.py); [static limits](import-boundaries.md#initializers-and-runtime-targets) |
| Commands and output routing | [CLI](../specs/001-release-030/contracts/cli.md) | [Entrypoints and checks](../pyproject.toml), [output identity](../src/clearml_yolo/adapters/storage/run_identity.py), [pipeline](../src/clearml_yolo/application/use_cases/pipeline.py) | [Command configuration](../tests/test_release_config.py), [output containment](../tests/test_project_output_containment.py) |
| Filesystem defaults and explicit destinations | [Filesystem ownership](filesystem-policy.md) | [Project bootstrap](../src/clearml_yolo/adapters/runtime/bootstrap.py), [Workspace policy](../src/clearml_yolo/adapters/storage/filesystem.py), [native runtime](../src/clearml_yolo/adapters/integrations/native_runtime.py) | [Filesystem boundaries](../tests/test_filesystem.py), [native containment](../tests/test_native_output_containment.py) |
| Explicit image cache deduplication | [Deduplication CLI](../specs/018-cache-image-dedup/contracts/cli.md) | [Command](../src/clearml_yolo/entrypoints/dedup.py), [cache implementation](../src/clearml_yolo/adapters/storage/dedup.py) | [Deduplication behavior](../tests/test_dedup.py), [CLI checks](../tests/test_dedup_cli.py) |
| GPU scheduling, device demand and execution controls | [Shared cy-queue](queue.md), [queue specification](../specs/029-shared-cy-queue/spec.md), [operator amendments](../specs/031-test-quality-gpu-controls/spec.md#operator-simplification-amendment--2026-10-15) | [Queue policy](../src/clearml_yolo/core/queue.py), [application ports](../src/clearml_yolo/application/queue.py), [adapters](../src/clearml_yolo/adapters/queue), [direct invocation](../src/clearml_yolo/entrypoints/hydra/common.py) | [Handoff](../tests/test_queue_handoff.py), [generations](../tests/test_gpu_generations.py), [process checks](../tests/test_shared_queue_processes.py); [physical/NFS limits](implementation-status.md) |
| Selected export and runtime ownership | [Runtime isolation](runtime-isolation.md), [feature 024](../specs/024-runtime-isolation/spec.md) | [Exporter](../src/clearml_yolo/entrypoints/hydra/config_tree.py), [bootstrap](../src/clearml_yolo/adapters/runtime/bootstrap.py), [bounded publisher](../src/clearml_yolo/adapters/fiftyone/bounded.py) | [Selected export](../tests/test_config_tree.py), [runtime ownership](../tests/test_runtime_bootstrap.py), [bounded publication](../tests/test_bounded_fiftyone.py) |
| Native training and prediction groups | [Native configuration](../specs/005-explicit-detection-config/contracts/native-configuration.md), [example layout](../specs/007-detection-config-cleanup/contracts/configuration-and-artifacts.md) | [Native settings](../src/clearml_yolo/adapters/yolo/config.py), [registration](../src/clearml_yolo/entrypoints/hydra/configs.py), [export](../src/clearml_yolo/entrypoints/hydra/config_tree.py) | [Precedence/forwarding](../tests/test_native_config.py), [native settings validation](../tests/test_native_settings_validation.py) |
| Detector families and portable checkpoints | [Backend contract](../specs/025-multi-model-backends/contracts/backend.md), [model guide](multi-model-backends.md) | [Typed models](../src/clearml_yolo/core/models.py), [backend routing](../src/clearml_yolo/adapters/integrations/detectors.py), [checkpoint binding](../src/clearml_yolo/adapters/storage/checkpoint.py), [owner publication](../src/clearml_yolo/adapters/clearml/detectors.py) | [Workflow routing](../tests/test_detector_workflows.py), [checkpoint/recovery](../tests/test_detector_recovery.py); [native backend evidence/limits](../specs/025-multi-model-backends/verification.md) |
| Faster R-CNN ONNX/TensorRT export | [Export contract](../specs/025-multi-model-backends/contracts/export.md), [deployment guide](tensorrt-deployment.md) | [Export workflow](../src/clearml_yolo/application/use_cases/export.py), [composition](../src/clearml_yolo/adapters/integrations/export_operations.py), [engine build](../src/clearml_yolo/adapters/export/build.py), [FP16 tensor types](../src/clearml_yolo/adapters/export/precision.py), [attention precision](../src/clearml_yolo/adapters/export/attention_precision.py), [standalone runtime](../src/clearml_yolo/adapters/export/runtime.py), [quality verification](../src/clearml_yolo/adapters/export/verification.py) | [Export workflow](../tests/test_export_workflow.py), [precision](../tests/test_export_precision.py), [quality gate](../tests/test_export_quality.py); [target-runtime limits](../specs/025-multi-model-backends/verification.md) |
| Detection CSV identity, media paths and dataset cache | [Input/provenance contract](input-provenance.md), [dataset inputs](../specs/004-ground-truth-training/contracts/cli.md), [cache specification](../specs/008-dataset-clearml-tracking/spec.md) | [Storage reads](../src/clearml_yolo/adapters/storage/file_io.py), [cache](../src/clearml_yolo/adapters/storage/dataset_cache.py), [input regression evidence](../.specify/bugs/input-evaluation-correctness/test.md) | [Input regressions](../tests/test_input_correctness.py), [cache checks](../tests/test_dataset_cache.py), [native/download evidence](evidence/2026-10-15-correctness-cleanup/native-verification.md) |
| Configuration resolution and remote replay | [File resolution](../specs/009-resolved-config-uploads/contracts/configuration-files.md), [tracking and recovery](../specs/010-native-clearml-integration/contracts/tracking-publication.md) | [Resolution](../src/clearml_yolo/entrypoints/hydra/config_resolution.py), [session adapter](../src/clearml_yolo/adapters/clearml/session.py) | [Resolution](../tests/test_config_resolution.py), [upload commands](../tests/test_config_upload_commands.py), [replay](../tests/test_model_replay.py) |
| Artifacts, native callbacks and task completion | [Publication inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md), [evaluation publication](../specs/014-evaluation-publication/contracts/publication.md), [native tracking](../specs/010-native-clearml-integration/contracts/tracking-publication.md), [model metadata](../specs/008-dataset-clearml-tracking/contracts/model-metadata.md) | [Artifact names](../src/clearml_yolo/core/artifact_names.py), [native runtime](../src/clearml_yolo/adapters/integrations/native_runtime.py), [model verification](../src/clearml_yolo/adapters/clearml/native.py), [display naming](../src/clearml_yolo/adapters/clearml/naming.py), [result bundle](../src/clearml_yolo/adapters/clearml/results.py), [DDP relay](../src/clearml_yolo/adapters/integrations/native_ddp.py), [fresh DDP trainer](../src/clearml_yolo/adapters/integrations/native_trainer.py) | [Tracking contract](../tests/test_native_tracking_contract.py), [result lineage](../tests/test_clearml_results.py), [lifecycle](../tests/test_execution_lifecycle.py); [native/download evidence](evidence/2026-10-15-correctness-cleanup/native-verification.md) |
| Evaluation, comparison, thresholds and reports | [Task recovery](../specs/012-remove-legacy-compatibility/contracts/task-recovery.md), [evaluation publication](../specs/014-evaluation-publication/contracts/publication.md), [readable plots](../specs/020-readable-evaluation-plots/contracts/plots.md), [Publication inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md), [CLI evaluation contract](../specs/001-release-030/contracts/cli.md) | [Metrics](../src/clearml_yolo/application/use_cases/metrics.py), [comparison](../src/clearml_yolo/application/use_cases/compare.py), [comparison workbook](../src/clearml_yolo/adapters/reporting/comparison_workbook.py), [exact thresholds](../src/clearml_yolo/adapters/clearml/models.py), [source lineage](../src/clearml_yolo/core/evaluation/result_rows.py), [neutral payloads](../src/clearml_yolo/core/evaluation/schema.py), [interactive reporting](../src/clearml_yolo/adapters/clearml/report.py), [paired reports](../src/clearml_yolo/application/use_cases/report.py) | [Metrics](../tests/test_metrics.py), [comparison](../tests/test_comparison_scoring.py), [recovery](../tests/test_comparison_recovery.py), [workbook](../tests/test_comparison_workbook.py) |
| FiftyOne publication | [Publisher](../specs/006-fiftyone-integration/contracts/publisher.md), [native evaluations](../specs/015-fiftyone-native-evaluations/contracts/native-evaluation.md), [current inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md) | [Owner publication](../src/clearml_yolo/application/use_cases/publication.py), [replaceable adapter](../src/clearml_yolo/adapters/fiftyone/publisher.py) | [Publisher checks](../tests/test_fiftyone_publisher.py), [native evaluation projection](../tests/test_fiftyone_evaluation_results.py); [dated native evidence](../specs/015-fiftyone-native-evaluations/verification-2026-10-06.md) |
| Operation diagnostics and stalled-run capture | [Diagnostics](diagnostics.md) | [Tracing](../src/clearml_yolo/adapters/observability/tracing.py), [FD capture](../src/clearml_yolo/adapters/observability/capture.py), [publisher](../src/clearml_yolo/adapters/clearml/console.py), [guardian](../src/clearml_yolo/adapters/queue/guardian.py), [native cleanup](../src/clearml_yolo/adapters/integrations/native_runtime.py) | [Diagnostics](../tests/test_diagnostics.py), [console capture](../tests/test_console_capture.py), [queue logging](../tests/test_queue_logging.py) |
| Local dependency sources | [Development setup](development.md#external-dependencies), [local copies](../specs/017-local-dependency-copies/spec.md) | [Ignore rules](../.gitignore), [package configuration](../pyproject.toml), [editable lock](../uv.lock) | [Metadata/tooling boundaries](../tests/test_tooling_boundaries.py), [installed dependency evidence](evidence/2026-10-15-correctness-cleanup/packaging-verification.md) |
| Local versioning, changelog and release hooks | [Local release](../specs/003-semantic-release/contracts/local-release.md) | [Release helper](../scripts/local_release.py), [hook configuration](../.pre-commit-config.yaml), [generated changelog](../CHANGELOG.md) | [Release fixtures](../tests/test_local_release.py); actual delivery requires commit/tag ref verification |
| Markdown structure, local links and anchors | [Documentation checker contract](../specs/033-documentation-checks/spec.md), [development checks](development.md#verification) | [Read-only checker](../scripts/check_docs.py), [checker regressions](../tests/test_check_docs.py) | [Positive/negative fixtures](../tests/test_check_docs.py); external links/examples and Mermaid grammar excluded from parser checks |

## Authority and verification

Normative behavior belongs in the topic contracts above. Each rule needs a linked
executable check or an explicit verification limitation. The
[module](module-architecture.md), [queue](queue-lifecycles.md) and
[input provenance](input-provenance.md) diagrams explain ownership and invariants.
The [status map](implementation-status.md) separates implementation, verification,
release and outstanding external acceptance without rewriting completed task history.

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
