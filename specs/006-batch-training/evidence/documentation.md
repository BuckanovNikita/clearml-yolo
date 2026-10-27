# Documentation verification — 2026-10-26

## Scope and ownership

Feature 006 documentation was reconciled against current implementation, rather than
assuming its plan had already passed acceptance. The CY checkout was on `master`,
based on `9fd2294ab219c534fcce87b59eea7b56e9d01173`, with source metadata `0.40.0`
and uncommitted feature changes. This is not a release claim.

Updated the Russian README; native-model, runtime-isolation, project-contract,
current-contract, queue, filesystem and augmentation guides; and added the
[batch-estimation guide](../../../docs/batch-estimation.md). They describe FCOS's six
presets and default 800 resolution, global training microbatches, strict null lookup,
worker allocation resolution, saved synthetic bounds, local estimator options,
failure/ceiling semantics and self-contained configuration exports. Deployment export
remains limited to Faster R-CNN. Existing single-GPU-only statements were corrected.

The canonical `corp-skills` source was on `main`, based on
`44426a6b6fce058ec9ab37588483eb4bc860ca0a`. Updated only
`skills/clearml-yolo/SKILL.md` and its `references/usage.md`, `evaluation.md` and
`augmentation.md`. Those files already contained uncommitted work, including an
untracked augmentation reference. Their pre-edit bytes and SHA-256 inventory were
preserved in the ignored task workspace, and edits retained that earlier content.
No installed skill copies, commits, tags or releases were changed.

Documentation architecture impact: none beyond documenting the feature's existing
[architecture record](../architecture.json). This bounded documentation change adds
no runtime module, import edge, SDK owner, subprocess boundary or effect. Source
inspection covered the estimator entrypoint, pure search/compatibility, profile and
null resolution, atomic storage, FCOS/shared Torchvision modules and Hydra exporter.
The parent owns reconciliation of the integrated implementation and architecture
acceptance; documentation checks do not establish those gates.

## Executed checks

| Check | Result |
| --- | --- |
| `uv run --frozen --no-sync python scripts/check_docs.py` with the nine changed user/contract guides | Passed: 9 Markdown files, 0 issues |
| Final project Markdown/link check including this evidence file | Passed: 10 Markdown files, 0 issues |
| The same checker with `--root` pointing to the canonical skill collection and four absolute package paths | Passed: 4 Markdown files, 0 issues |
| Duplicate-key-rejecting YAML frontmatter validation | Passed: name/folder agreement, supported keys, name/description bounds |
| Packaged local-link containment and existence | Passed: 9 local references resolve inside the package; no external symlink dependency |
| `DISABLE_TELEMETRY=1 npx --yes skills@1.7.1 add . --list` from the canonical collection | Passed: discovered all 4 collection skills including the updated clearml-yolo description; discovery only, no installation |
| `npx --yes markdownlint-cli2@0.23.3 '*.md' 'skills/**/*.md' 'verification/**/*.md' 'docs/**/*.md'` from the collection | Passed: initial scan selected 53 files; final summary reported 0 issues |
| Estimator module `--help` | Passed: all 10 documented options present; no estimation workload |
| Three fresh exports: FCOS ResNet-50 pipeline, RF-DETR Small training, FCOS DINOv2 Small training | Passed: local command bases, both transform profiles and null batch preservation; composed with automatic-schema-matching warnings treated as errors |
| Direct configuration of all six FCOS presets | Passed: each defaulted to 800 and preserved explicit null batch |
| YOLO `ultralytics.model=yolo11n.pt ultralytics.imgsz=960 ultralytics.batch=null --cfg job` | Passed: explicit null preserved |
| Task-owned project documentation `git diff --check` and canonical collection `git diff --check` | Passed |

Examples ran through installed editable Python module entrypoints in isolated
`CY_HOME` directories with empty CUDA visibility. They did not start training,
estimation, queues, ClearML tasks or GPU probes. They check the current source
interfaces, not a released console-script installation. No application tests were
added or rerun for this documentation-only scope.

## Failed checks and limits

The initial example run used `PYTHONWARNINGS=error`. It stopped before export in
installed hydra-zen's `builds()` because its use of Pydantic `__fields__` raises
`PydanticDeprecatedSince20`. The successful rerun promoted automatic-schema-matching
warnings specifically to errors. This does not establish freedom from every
third-party deprecation and does not suppress a schema-matching collision.

An initial cross-repository link-check invocation supplied relative paths from the
CY working directory, so the checker correctly reported four paths outside the
selected root. Repeating with absolute canonical package paths passed.

The first repository-wide whitespace check reported an unrelated trailing blank
line in the concurrently edited `.importlinter`; its owner was notified. The bounded
documentation paths passed separately.

Native GPU, full estimator-matrix, pretrained download and real multi-GPU acceptance
remain outside this documentation verification. The parent reported an initial CUDA
FCOS probe that failed on skipped AMP updates and took ownership of its correction;
this report makes no success claim for that run or later CUDA work. Public guides
mark these additions unreleased and distinguish implemented interfaces from acceptance.

Fresh independent review and fresh-context behavioral evaluation of the three new
skill prompts remain for parent integration. This bounded agent did not delegate.
No OpenCode/provider evaluation was performed, so static validation and source checks
do not establish DeepSeek or other target-model behavior. The canonical collection's
separate publication and installed-copy synchronization remain unexecuted.

## Parent integration follow-up

A separate fresh-context Codex evaluator subsequently answered three custom operator
scenarios: two-GPU estimation followed by null-batch training, queued YOLO null
resolution, and a fresh FCOS export preserving older local edits. It read the skill
and relevant usage references before drafting, then compared the evaluation catalogue.
Routing, commands, compatibility rejection, worker-side resolution and export guidance
matched current source. The draft should explicitly retain fresh confirmation, the
estimator's lack of ClearML publication and default counts 1 through the selected
GPU count; these were already documented in the source package.

The evaluator executed estimator module help, queue submission help, FCOS tree
generation/composition and RF-DETR/FCOS/YOLO null-batch configuration composition,
all with CUDA hidden and no schema-matching warnings. All processes exited. The
source environment had no installed `cy-batch-estimate` executable yet; its module
entrypoint worked. This verifies unreleased source interfaces, not an installation
upgrade. The parent removed the evaluator-owned temporary configuration directory
after retaining its inventory.

This is fresh-context behavior for three custom scenarios, not a run of the exact
catalogue prompts and not OpenCode/DeepSeek/provider evaluation. No workload,
submission, installation or publication occurred. The final memory-accounting
clarification in the batch guide does not change these portable command interfaces.

## Integrated documentation gate

The parent also updated the validation guide with the opt-in four-backend physical
DDP commands and their representative-fixture limits. Dated evidence retains failed
or interrupted canonical attempts, partial native estimation, reviewer corrections
and proposed-pair resolution rather than converting them into success claims.
The canonical documentation command with CUDA hidden checked 128 Markdown files
with zero issues. Sibling queue task documentation passed separately (two files,
zero issues). Canonical source-skill validation remains as recorded above; no
installed-copy synchronization or publication is claimed.
