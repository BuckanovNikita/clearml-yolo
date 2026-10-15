# Training-first documentation verification — 2026-10-15

## Scope and reconciliation

Continued the completed README task from base `634f3e2`; appended the new intent,
plan/migration map and tasks without editing historical evidence. README is now a
Russian training-first guide; root TECH_DETAILS.md is the English technical entry
point. Navigation changes affect the contract index and development guide. The
maintained model guide's stale direct-GPU admission wording and three examples now
use explicit GPU 0. Runtime source, dependencies, CLI schemas and release tooling
are unchanged. The normal changelog hook added an Unreleased entry for the existing
base commit; that generated change is included in task ownership.

The [migration map](plan.md#content-migration-map) accounts for prior README topics.
Inspected `entrypoints/hydra/configs.py`, `core/models.py`, application contracts,
use cases, queue parsing and the maintained documentation. The
[no-impact record](training-first/architecture.json) passed planning validation before
README implementation. Final acceptance and review are recorded below.

The portable usage skill source was inspected at corp-skills commit
`e5c6512e7ac3a8fcd4dca6443dd9fed3df48c420`: `SKILL.md` and `references/usage.md`
already describe direct devices, queued allocation, inputs, labels and provenance
correctly. No CLI/API or contract change requires a companion skill edit; the
README presentation change does not change the skill interface. Its abbreviated
standalone YOLO training snippet omits the required model selection; the README now
supplies it explicitly. That pre-existing external-skill issue is outside this
repository documentation change, not a claim of full skill-package validation.

## Executed checks

Checks used an existing Python 3.12.13 environment without syncing or changing its
dependencies. `PYTHONPATH` selected this worktree's source; an explicit import-path
check confirmed it. `CY_HOME` and command working directories were isolated temporary
roots. Example paths and task IDs are illustrative: they were composed, not executed.

| Check | Result and scope |
| --- | --- |
| Architecture planning validator | Exit 0 for `training-first/architecture.json`, phase `plan` |
| README Hydra scenarios | 18 passed with `--cfg job --resolve`, with no missing mandatory config values |
| New training commands | YOLO, DEIMv2, RF-DETR and Faster R-CNN backend selections checked; DEIM source/backbone fields asserted |
| Generated YAML | Exported and edited exact README snippets while retaining defaults; YOLO model/epochs/batches/inherited image size/tracking values asserted; RF-DETR tree composed |
| Command export coverage | Nine selected command trees generated in isolated directories |
| Sweep examples | Both epochs values composed separately; no multirun workload executed |
| YOLO DDP example | Device-list configuration resolved; no distributed execution |
| Changed model-guide examples | RF-DETR pipeline, Faster R-CNN training and DEIMv2 training resolved with explicit GPU 0 |
| Queue/dedup help | Seven help invocations passed, including queue submit/worker/list/cancel/TUI |
| Queue parser/source | Seven argument cases passed through parsers only, including device-count/exact-device submission and multirun; no service constructed or job persisted |
| Mermaid | Mermaid 12.1.0 parsed and headless Chromium rendered all nine workflow nodes |
| Markdown | markdownlint-cli2 0.23.3 passed; only MD013 line length and MD060 table alignment disabled, matching prior documentation validation |
| Links, shell and YAML | Changed Markdown parsed with markdown-it; local paths/anchors, repository-wide incoming README links, Bash `bash -n` and YAML parsing passed |
| Normal pre-commit hooks | Initial changelog regeneration requested review; generated diff inspected and the repeated checks passed. Code gates were deselected by their documented file filters, not bypassed |
| Whitespace | `git diff --check` passed |

Documentation check totals before final review: nine authored Markdown files,
224 local paths/anchors including four incoming README links, 39 Bash blocks and
four YAML blocks. The generated changelog uses its own formatter and is excluded
from authored-prose linting.

An initial browser launcher expected a different cached Chromium revision; selecting
the available executable allowed diagram validation without installation changes.
An early draft's nonexistent queue `--command` option and two incorrect anchors were
removed/corrected during source/link inspection before final validation.

## Limits and ownership

No training, inference, calibration, queue submission/worker, GPU allocation, ClearML
service access or publication was performed. Composition does not verify real dataset
or weight availability, pretrained downloads, GPU capacity or upload success. No
application tests/build were required for this documentation-only diff. Source presets,
splits, model identity, frozen thresholds and output behavior were inspected directly.

The existing primary checkout has unrelated staged/unstaged work. This task remains
in its isolated worktree and does not integrate into or alter that checkout. Native
release evaluation/delivery will use this task's branch; documentation does not force
a version tag. Only task-owned temporary outputs/processes are eligible for cleanup.

## Independent review and architecture acceptance

Fresh native subagent review (`final_docs_review`, isolated context, requested
`gpt-6.1-sol` with high effort) returned **ship**, with no blocking findings.
The reviewer inspected completeness, Russian/English separation, command/source
accuracy, Python compatibility and no-impact architecture. It independently passed
10 Markdown files (including generated CHANGELOG), 224 local references including
four incoming README links, 39 Bash blocks, four YAML blocks, architecture acceptance
and `git diff --check`. It reviewed parent Hydra/export/queue/Mermaid evidence and
agreed that native workloads are outside scope. Requested model settings are recorded;
actual runtime settings were not separately observable.

Parent reconciliation covers README, TECH_DETAILS, generated CHANGELOG, three
maintained guide/navigation files and this feature's appended artifacts. There are
no runtime/dependency/tooling changes or unrelated staged paths in this worktree.
The architecture record includes the generated changelog. Parent acceptance-phase
validation passed after reconciliation.

## Commit and release

Documentation commit `3ae81a57a939a1cc7494e3c74c6930692e15358c`
(`docs: lead with training workflows and separate technical reference`) passed normal
pre-commit and post-commit hooks. Markdown-only paths correctly deselected application
lint/type/import/test gates. No hooks were bypassed. This isolated worktree had no
local `[tool.uv.sources]` section, so none was removed or restored; pyproject.toml and
uv.lock remain byte-for-byte unchanged.

The normal release helper was also invoked manually and exited 0 with the explicit
reason: only master receives automatic release tags. No version/tag, GitHub Release,
package asset or deployment was created. The task branch
`docs/training-first-readme` was pushed through the existing SSH remote; remote ref
readback matched the documentation commit. The primary checkout and its unrelated
work remain untouched. This final evidence/ledger update follows the same checked
commit and branch delivery procedure.

Task-owned validation scratch and diagram browser processes are cleaned up after
verification; no pre-existing services or environments are stopped or changed.

## Requested master landing — 2026-10-15

Integrated the reviewed documentation branch into target master `8a49323`, which
already includes Python compatibility and queue-worker logging releases through
`v0.30.1`. README conflicts retain the training-first structure while preserving
Python `>=3.12.13,<3.14`, Linux pidfd requirements and worker diagnostics. TECH_DETAILS
now reflects the same compatibility and logging behavior. The native changelog
helper regenerated the conflicted file; upstream source/dependencies remain intact.

Integrated validation passed: 10 Markdown files, 234 local links including five
incoming README references, 39 Bash blocks, YAML parsing, authored Markdown lint,
four training `--cfg job --resolve` scenarios, queue-worker help with `--log-level`,
architecture acceptance and staged whitespace. No workload was started. The unchanged
command/schema examples retain the earlier full validation evidence.

A fresh isolated integration reviewer (`landing_review`, requested gpt-6.1-sol at
medium effort) returned **ship**, with no blocking findings. It checked the conflict
resolution against both branches and current source/contracts, confirmed preserved
Python/queue guidance and no source/dependency diff against the master target, and
passed staged/working-tree whitespace checks. Actual runtime model settings were
not separately observable. Landing and release results follow after delivery.

Master landing completed at merge `c800c99` after incorporating concurrent upstream
commit `1ed8182` (queue release evidence only). The intermediate merge `9376fd4`
contains the reviewed README/technical-reference integration. Both merges passed
normal hooks. Master was fast-forwarded with its exact local source-override section
restored afterward and its unrelated untracked file verified unchanged. The native
release helper on master returned `No unreleased semantic changes`; version remains
0.30.1 and no new tag was made. The ordinary push succeeded and remote master readback
matched `c800c99`. This closing ledger/evidence commit uses the same normal hooks,
master fast-forward, release evaluation and verified push procedure.
