# Portable training integration, 2026-10-23

This is executed evidence for feature 003. Implementation is present in CY and the
sibling cy-queue checkout. The resumed acceptance checks below passed; Git delivery is recorded separately.
Source inspection, fixture tests and live execution are distinguished.

## Checks

| Scope | Executed check | Result |
| --- | --- | --- |
| CY broad regression before final asset integration | `uv run --frozen --no-sync pytest --ignore=tests/test_model_assets.py -q` | 2,995 passed, 30 skipped, 2 opt-in cases deselected |
| Final complete CY routine suite | Existing `uv run pytest` pre-commit hook, with `UV_NO_SYNC=1` inherited | Passed; final collection selected 3,079 cases and deselected 2 opt-in physical cases |
| Integrated architecture, recovered mixed-family DEIM, execution-copy provenance and Agent replay | Focused `pytest` over test_architecture, test_detector_workflows, test_asset_execution and test_agent_replay | 288 passed after correcting exact dynamic-import owner exceptions |
| CY imports | `uv run --frozen --no-sync lint-imports` | 41 kept, 0 broken; negative injected-edge tests passed |
| CY lint, typing and dead code | `ruff check .`, `mypy .`, `vulture` in the frozen prepared environment | Passed; strict mypy checked 327 source files |
| CY maintained documentation | `python scripts/check_docs.py --all` | 60 Markdown files, zero issues; new feature/evidence files checked separately |
| Queue integrated routine suite | Prepared CY interpreter, `python -m pytest -q` from queue | 500 passed, 7 physical cases deselected after final review correction |
| Queue other checks | Ruff, strict mypy, import contracts and Markdown | Passed; details in sibling docs/evidence/2026-10-23-extraction.md |

An intermediate CY run exposed four configured SDK-contract failures after dynamic
asset imports were introduced. Exact owner exceptions were restored; focused and
final full-suite checks pass. One later full run terminated with an unexplained
interpreter SIGILL; [15 bounded investigations](2026-10-23-interpreter-crash.md) did
not reproduce it, and the final full hook run passed without source workarounds or
test suppression. Whole-tree
Ruff formatting inspection also found existing formatting differences outside this
task; formatting is not a configured CY hook and unrelated files were preserved.

All configured pre-commit checks passed. The first overall hook command exited one
because its changelog hook regenerated a missing entry for already committed history;
the generated diff was inspected and that hook rerun successfully. Other hooks,
including the complete pytest suite, passed in that invocation. No hook was bypassed.

## Real ClearML Agent execution

Two tasks were created with canonical `run` configuration and bare recorded module
entrypoints, without the original Hydra CLI arguments. An externally prepared
ClearML Agent executed each in standalone CPU mode with dependency installation
disabled. No queue configuration or reservation was used. The tasks retained their
identities and complete script metadata, completed successfully, and published one
Output Model each. Verification force-downloaded every artifact and model before
exact-tag cleanup. Raw task-owned receipts remain in ignored `.tmp/portable-native/`
and `.tmp/portable-agent-pipeline/` archives.

| Entrypoint | Native backend | Task | Downloaded Output Model SHA-256 |
| --- | --- | --- | --- |
| `clearml_yolo.entrypoints.train` | Ultralytics, one CPU epoch | `4819e9db06d34f45a69454aa4741544e` | `4373c0c4a8e64828932d38cb91ad17509303c7964e0692f406ec8c012dc59906` |
| `clearml_yolo.entrypoints.pipeline` | Faster R-CNN/resnet50_fpn, one pretrained CPU epoch and prediction | `9ca70583f371432a8ac690a187ee1b5e` | `2180e01edaa1471cf3167543cec4626d88ae850e19b0ecb221d9a81d78e41dd5` |

The training task's downloaded `gt_csv` SHA-256 was
`a37e7d0611ef7a38740e74d5df05e310abb6667126a8e8aa399e0a3e03e7759d`.
The pipeline downloaded both `gt_csv` and `predicts_csv`, with SHA-256
`20ee13affa8ee205ecd11c1f0bc1163fb5fa84afaf2bc674eb291278e98e5d38` and
`cda8f53349d68d0ef39f43e67d5f11f70c21d85f2d24adf464c10ad9595d5cde`.
Pipeline canonical configuration still contained `model.train.backbone_weights=null`;
the separate `model_assets` Configuration Object recorded the resolved Torchvision
backbone, its original upstream URL and content hash. Both cleanup audits reported
zero remaining tagged projects and tasks. This does not claim shared Agent scheduler
or multi-GPU execution.

## Native model families and assets

[Direct family evidence](2026-10-23-native-families.md) records successful pretrained
CUDA training, publication, forced downloads and fresh native checkpoint prediction
for DEIMv2/s, RF-DETR/nano and Faster R-CNN/resnet50_fpn. Asset tests additionally
exercise native local-file construction for all six Faster R-CNN presets, native
asset registry selection, HTTP faults/authentication/redirects/fallback, concurrent
cache use, offline manual placement and unsafe or modified DEIM archives.

The complete approved DEIM archive manifest covers 161 files. Local source extraction
and imports succeeded; an official matching S backbone was downloaded successfully.
Tests do not claim gated upstream access for every preset or all-preset training.
Live Artifactory connectivity is unavailable by the accepted task scope. Local HTTP
fixtures verify proxy request construction and fallback, not deployment connectivity.
The [dependency floor check](2026-10-23-dependencies.md) resolved both supported Python
minors independently and verified the new minimum Requests API and typing boundary.

## Resumed queue acceptance and delivery conditions

The initial production preflight found every GPU above the unchanged admission
limit of strictly less than 2 GiB used memory, so no job was started at that checkpoint.
The resumed [live queue verification](2026-10-23-live-queue.md) separately confirmed
normal busy rejection, then completed both real train and pipeline commands under
a task-owned 16 GiB inventory ceiling with real telemetry, shared coordination,
guardians and acknowledgement. Published artifacts and models were force-downloaded,
checked and reloaded. All owned processes, claims and tagged remote resources were
cleaned. This single-GPU evidence does not establish idle admission under the default
limit or release/reassignment of additional physical GPUs.

Source installation and command ownership were checked in isolated offline
environments. CY source currently declares 0.37.0; the extracted queue requires
the intended compatible CY release `>=0.38,<0.39`. For the compatibility test only,
copies of the current source used intended CY 0.38.0 metadata and queue 0.1.0.
Externally prepared dependencies were reused through isolated links and copied
distribution metadata. CY was installed first, followed by queue. `uv pip check`
verified 280 compatible packages. Installed commands were owned by their respective
packages, the DEIM manifest was present, and queue help plus DEIM configuration
inspection succeeded outside the checkout without creating asset caches. Temporary
environments were cleaned. Neither original source version nor shared environment
was changed. The shared environment retains stale CY metadata 0.34.0; final release
installation and readback remain a delivery step, not an already released upgrade.

Fresh independent code review returned [ship for code/architecture](2026-10-23-review.md).
Its finding, optional arguments in custom train YAML causing a queue submission
KeyError, was corrected and independently rechecked with regression evidence.
The portable skill has a separate fresh review with no blocking
findings; its evaluation was native-agent source/application review, not a live
OpenCode/DeepSeek run. The OpenCode executable was unavailable. The resumed independent live-evidence review returned ship after auditing actual
archive bytes, native execution, acknowledgement and cleanup. Both architecture
acceptance records now include this scoped passing evidence. Live Artifactory and
physical multi-GPU coverage remain explicitly unverified. Git delivery and the active
environment refresh are the remaining steps at this checkpoint.

## Acceptance closure

Both reconciled module records passed `validate_architecture.py --phase acceptance`
on 2026-10-23. The final queue Markdown/link pass checked eight documents with zero
issues. The portable skill's corrected candidate, based on current upstream v0.4.2,
passed fresh independent review, collection discovery, all metadata validators,
Markdown/local-link/package containment checks and no-impact architecture acceptance.
It is committed locally as `05b515655c468a2a4d58ec71ce065fce4d7959a9` in an isolated
clone, preserving unrelated edits in the original checkout. Its v0.4.3 publication
follows the CY implementation release. No code changed after final review.
