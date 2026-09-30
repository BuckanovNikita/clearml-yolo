# Current contract index

Use this index to select the maintained contract for a topic. Feature numbering and
release dates alone do not establish authority: later features amend specific parts of
earlier contracts. A contract describes required behavior; inspect implementation and
tests before claiming verification. Surface an unexplained mismatch
rather than silently changing the requirement or code.

| Topic | Maintained contract | Implementation evidence |
|---|---|---|
| Commands and output routing | [CLI](../specs/001-release-030/contracts/cli.md) | [Entrypoints and checks](../pyproject.toml), [output identity](../src/clearml_yolo/run_identity.py), [pipeline](../src/clearml_yolo/tasks/pipeline.py) |
| Native training and prediction groups | [Native configuration](../specs/005-explicit-detection-config/contracts/native-configuration.md), [example layout](../specs/007-detection-config-cleanup/contracts/configuration-and-artifacts.md) | [Native settings](../src/clearml_yolo/native_config.py), [registration](../src/clearml_yolo/configs.py), [export](../src/clearml_yolo/config_tree.py) |
| CSV training and dataset cache | [Dataset inputs](../specs/004-ground-truth-training/contracts/cli.md), [current publication](../specs/008-dataset-clearml-tracking/contracts/publication.md) | [Training](../src/clearml_yolo/tasks/train.py), [cache](../src/clearml_yolo/dataset_cache.py) |
| Configuration resolution and remote replay | [File resolution](../specs/009-resolved-config-uploads/contracts/configuration-files.md), [tracking and recovery](../specs/010-native-clearml-integration/contracts/tracking-publication.md) | [Resolution](../src/clearml_yolo/apps/config_resolution.py), [session adapter](../src/clearml_yolo/clearml_session.py) |
| Artifacts, native callbacks and task completion | [Publication inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md), [native tracking](../specs/010-native-clearml-integration/contracts/tracking-publication.md), [model metadata](../specs/008-dataset-clearml-tracking/contracts/model-metadata.md) | [Artifact names](../src/clearml_yolo/artifact_names.py), [native runtime](../src/clearml_yolo/native_runtime.py), [model verification](../src/clearml_yolo/clearml_native.py), [DDP relay](../src/clearml_yolo/native_ddp.py) |
| Comparison, thresholds and reports | [CLI evaluation contract](../specs/001-release-030/contracts/cli.md) | [Comparison](../src/clearml_yolo/tasks/compare.py), [exact thresholds](../src/clearml_yolo/clearml_models.py), [paired reports](../src/clearml_yolo/tasks/report.py) |
| FiftyOne publication | [Publisher](../specs/006-fiftyone-integration/contracts/publisher.md), [current inventory](../specs/008-dataset-clearml-tracking/contracts/publication.md) | [Owner publication](../src/clearml_yolo/tasks/publication.py), [replaceable adapter](../src/clearml_yolo/publishing/fiftyone_adapter.py) |
| Local versioning, changelog and release hooks | [Local release](../specs/003-semantic-release/contracts/local-release.md) | [Release helper](../scripts/local_release.py), [hook configuration](../.pre-commit-config.yaml), [generated changelog](../CHANGELOG.md) |

## Changes that must propagate

Native model commands use complete top-level `ultralytics` and `ultralytics_predict`
groups. Prediction reads its resolved group; visible references provide inheritance.
Raw wrapper `cfg`, non-null native `cfg`, nested stage-native mappings and duplicate
native comparison inference fields are removed. See the [migration](migration-ultralytics-groups.md).

ClearML publications follow the current inventory, not old artifact counts. Native
YAML, NDJSON, archives, manifests and diagnostic/publication receipts remain local.
Consumed dataset and explicit report configurations are Configuration Objects; canonical
`run` and native `General` support replay. Configuration copies are not artifacts.
Native owner callbacks may publish training/validation previews. Workers do not publish.
The native best checkpoint uses one Output Model, verified before completion.

Pipeline comparison uses the current `test` images. Standalone `cy-compare` defaults to
`split=test` and accepts another split present in the current ground truth. Both models
use the selected split under the same inference/evaluation settings; comparison does
not recalibrate thresholds. Reports consume that pair and its manifest split. Source
task/model links provide provenance; comparison retrieves weights and exact thresholds,
and does not automatically import the source task's General or Configuration Objects
over current comparison settings.

## Maintaining consistency

Spec Kit implementation and bug-fix workflows require a **Documentation update**
stage before completion. Follow the [project workflow policy](../AGENTS.md#mandatory-documentation-stage)
to plan explicit documentation tasks, reconcile them with the actual changes and
validate the result. If no documentation changes are needed, record the reviewed scope
and reason in the workflow artifacts. Missing required updates or failed validation
blocks completion.

For a contract change, inspect this index, affected contracts, active specifications,
quickstarts, README, migrations, project-owned integration skills and any applicable
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
in [AGENTS.md](../AGENTS.md) or separate project hooks. Feature specifications in
`specs/` remain maintained project documentation. Upstream regeneration must not erase
separate project policy or treat historical requirements as current authority.

Machine-specific setup and evidence stay in the applicable global environment skill.
The repository's [end-to-end skill](../.agents/skills/running-end-to-end-tests/SKILL.md)
defines portable acceptance. Historical releases and dated evidence describe
observations then; they are not current execution recipes.
