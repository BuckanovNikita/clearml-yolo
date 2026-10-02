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
   CPU and available GPU devices.
4. Run a candidate without a baseline; verify evaluation succeeds and comparison is
   skipped. Promote a completed baseline with a `prod` tag, run a candidate and verify
   both checkpoints infer the same current test images under matching settings.
5. Confirm validation thresholds are frozen for test and baseline thresholds are loaded
   unchanged. Compare metrics, statistical results and report counts. Exercise `cy-val`,
   `cy-compare` and `cy-report` independently, including nondefault evaluation options.
6. Force-download every required artifact and verify the explicit publication inventory.
   Confirm every `metrics_evaluation_<split>.xlsx` contains only `summary`, `per_class` and
   `confusion_matrix`, with `_ground_truth_matches.csv`, `_prediction_matches.csv`,
   `_thresholds.csv` and `_methodology.csv` sidecars. Confirm a completed comparison workbook
   contains only `Сравнение`, with `_excluded.csv` and `_methodology.csv`; for a skipped
   automatic baseline, confirm the candidate workbook contains only `Classes` and `Summary`,
   with `_thresholds.csv` and `_methodology.csv`. Verify JSON and PNG outputs retain their
   established formats and that table deduplication still satisfies every required alias.
   Download the single native best Output Model, load it, and compare model fields with
   checkpoint/trainer data. Verify canonical run and native General parameters support
   replay; when used by the invocation, verify the consumed-dataset and explicit-report
   configurations too. Inspect native Scalars, Plots and Debug
   Samples. Confirm one task per invocation, owner-only training/validation callbacks,
   and no duplicate checkpoint artifacts.
   Repeat CSV training against one dataset cache: filenames and extension casing remain
   intact, and image copies and NDJSON conversion do not repeat. Internal manifests and
   diagnostic receipts remain local. For native-YAML training, verify real image/label copies
   and native caches remain under the locked workspace cache while original source bytes remain
   unchanged. Inspect the workspace after success and injected failure for owned temporary files.
   Explicit output/cache paths outside `CY_HOME` must remain selected; a physical-home destination
   warns without rejection or relocation.
7. Check artifact/model upload rejection, callback-registration failure, flush failure and
   interruption with isolated test invocations. Each must fail
   the command and task while retaining local diagnostics until intentional cleanup.
8. Record commands, outcomes and limitations. Store machine-specific logs and task records
   with the environment skill; keep a portable verification summary in the repository.
   Clean up only owned resources per that environment's instructions.

Build and install both distributions in fresh environments for release acceptance.
Verify nine command helps, absence of `cy-queue`, and documented configuration examples.
Check `cy-init-config` generation and overwrite protection without a ClearML task.
CPU and single-GPU runs are required release gates; report an unavailable device as
an unverified gate. Describe physical multi-GPU execution as unverified unless exercised.
