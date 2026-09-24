---
name: running-end-to-end-tests
description: Verify clearml-yolo with real native execution, ClearML artifact downloads, validation, and paired current-test comparison. Use for release or integration verification; unit tests alone do not establish these outcomes.
---

# Verify the detection workflow

Read [prerequisites](references/pipeline-prerequisites.md) for inputs and configuration.
Use the environment's applicable global skill for credentials, capacity and cleanup;
`clearml-yolo-environment` supplies this project's local environment when installed.
This skill defines product acceptance, not deployment or machine setup.

## Verification

1. Run the repository's pytest, Ruff, mypy and import-linter checks. Include applicable
   pre-commit hooks for release or commit work.
2. Configure an isolated ClearML project and output directory. Pass project name and
   tags explicitly. Keep dataset images external and credentials out of files and logs.
3. Build ground truth from a small YOLO dataset with disjoint validation/test images,
   including an empty image in each split. Exercise native YAML and embedded mappings
   with explicit CPU and available GPU devices.
4. Run a candidate without a baseline; verify evaluation succeeds and comparison is
   skipped. Promote a completed baseline with a `prod` tag, run a candidate and verify
   both checkpoints infer the same current test images under matching settings.
5. Confirm validation thresholds are frozen for test and baseline thresholds are loaded
   unchanged. Compare metrics, statistical results and report counts. Exercise `cy-val`,
   `cy-compare` and `cy-report` independently, including nondefault evaluation options.
6. Force-download every required artifact and verify its contents and manifest. Confirm
   one task per invocation, without native duplicate tasks or model uploads.
7. Check upload rejection and interruption with isolated test invocations. Both must fail
   the command and task while retaining local diagnostics until intentional cleanup.
8. Record commands, outcomes and limitations. Store machine-specific logs and task records
   with the environment skill; keep a portable verification summary in the repository.
   Clean up only owned resources according to that environment's instructions.

Build and install both distributions in fresh environments for release acceptance.
Verify eight command helps, removed entrypoints, and documented configuration examples.
CPU and single-GPU runs are required release gates; report an unavailable device as
an unverified gate. Describe physical multi-GPU execution as unverified unless exercised.
