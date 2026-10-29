# Documentation integration evidence

Date: 2026-10-29. Feature: [local Russian reference](../spec.md).

## Source scope and preservation

CY source baseline: `0037059dcf8a8ed16582f256b98036480cabd842`, branch `master`;
installed/source package metadata reports `0.41.0` before the feature release.
This evidence describes the working source implementation, not a released version.

Updated the Russian README with `cy-docs` navigation, offline reference/editor
behavior, startup/check commands and preview limitations. Added
[the maintained documentation contract](../../../docs/local-documentation.md)
and linked it from the project contract summary and current contract index.
The contract records declaration ownership, packaged tutorials, preview limits,
maintenance rendering, browser verification and the boundary with real execution.

The portable usage source is the separate `corp-skills` repository, baseline
`44426a6b6fce058ec9ab37588483eb4bc860ca0a`. Task-owned edits are:

- `skills/clearml-yolo/SKILL.md`: include local-reference discovery and route to
  the conditional reference.
- `skills/clearml-yolo/references/usage.md`: add the command and reference link.
- `skills/clearml-yolo/references/local-docs.md`: new portable command, preview,
  limits, failure handling and evidence guidance.
- `skills/clearml-yolo/references/evaluation.md`: two success cases, two failure
  cases and an unrelated-request case for fresh evaluation.

Inspected the pre-existing CY `007` and corp-skills edits before writing. Compared
the final files with snapshots taken at this documentation task's start: all
pre-existing content remains, except the two intentional additive list/description
replacements needed to name `cy-docs`. No installed skill copies, dependency
revisions, versions, changelogs or existing historical evidence were changed.
No commits, tags, pushes or skill installation were performed by this task.

## Executed checks

| Check | Observed result |
| --- | --- |
| `uv run --frozen --no-sync cy-docs --help` | Passed; exposes `--port`, `--no-browser`, `--check` and help |
| `uv run --frozen --no-sync cy-docs --check` | Passed; reported 452 fields, 156 configurations, 8 tutorials |
| `uv run --frozen --no-sync python scripts/verify.py --docs` | Passed; documentation log retained in Git-private verification storage |
| CY Markdown checker on README and the three affected contract documents | Passed; four files, zero issues |
| CY Markdown checker with corp-skills as root and the four changed skill source files | Passed; four files, zero issues |
| `DISABLE_TELEMETRY=1 npx --yes skills@1.7.1 add . --list` in corp-skills | Passed; all four collection skills listed, including the updated clearml-yolo description; discovery only |
| `npx --yes markdownlint-cli2@0.23.3 '*.md' 'skills/**/*.md' 'verification/**/*.md' 'docs/**/*.md'` in corp-skills | Passed; no lint issues |
| Installed skill-creator `quick_validate.py` on the source package | Passed |
| Strict YAML/frontmatter and package-link inspection | Passed; no duplicate keys, valid name/folder and schema bounds, all local references contained in the package and present |
| Task-scoped `git diff --check` in both repositories | Passed |
| Comparison against initial file snapshots | Passed; unrelated working edits preserved |

The first cross-repository Markdown invocation supplied paths relative to the CY
working directory and was rejected as outside the configured corp-skills root.
Rerunning with the actual absolute source paths passed; no content change was needed.

Tutorial authoring checks, performed earlier in this feature, parsed all required
sections and internal links, compiled six Python snippets, checked field links
against the live catalog and composed all 29 inventory cases without errors.
The tiny-dataset Python example was executed in an isolated temporary directory:
12 real image files, four in each disjoint split, with one background image per
split. Those temporary files were cleaned after verification. No training was run
by these example checks.

## Fresh behavioral evaluation and remaining boundaries

The parent subsequently ran all five new prompts in separate native Codex agents
with fresh context, no write ownership and no expected-answer criteria supplied.
Offline opening, expression inheritance, excessive/unsafe preview requests, older
installations and unrelated-request routing all satisfied the evaluated boundaries.
Each response distinguished observed evidence from unexecuted checks. Detailed
results are recorded in the companion source repository's dated
`verification/2026-10-29-local-docs.md`; its architecture record documents no runtime
impact. Actual delegate model/effort settings were not observable. This is not
live OpenCode/DeepSeek/GLM/Qwen evidence.

The final parent documentation check reported 467 fields after command-specific
metadata and installed Hydra CLI controls were added. It retained the 156 effective
configurations, eight tutorials and 29 tutorial composition cases. The main
documentation guide now explicitly maps every public command/group to its reference,
tutorial and named executable test cases.

Browser interaction, source installation outside the checkout, native CPU/GPU
pipelines and actual ClearML artifacts, and current-source paired CY/cy-queue checks
passed as recorded in the other feature evidence. Final review and authorized
delivery remain separate gates. Composition or a passing documentation check does
not substitute for them. The companion corp-skills source edits remained uncommitted
and uninstalled at that checkpoint. The subsequent source-commit result follows.

## Companion source commit

Fresh review of an isolated seven-path candidate identified missing explicit
unreleased labeling, CY source provenance and the collection's required pending
changelog entry. Corrected those records, rechecked package/schema/links, discovery
and full collection Markdownlint, then obtained independent approval from
`acceptance_review` for this source commit. The candidate excluded pre-existing
batch/augmentation/training additions from the three overlapping files.

Committed only the reviewed candidate as
`80ec2a037e008fafe401e39e9f1b507005cb9a0d`
(`docs(clearml-yolo): document the unreleased local Russian reference`) in
corp-skills. Compared every working-file hash before and after commit: all bytes
were preserved, including unrelated edits, and the index was clean afterward.
No version tag, push, package publication or skill installation occurred. Collection
release remains subject to its clean-tree/version/tag workflow and preserved
independent work; the new CY interface is explicitly described as unreleased.

## Portable release candidate after feature 007 publication

The original source-commit checkpoint above remains historical evidence. Feature
007 subsequently published CY 0.42.0 and collection 0.6.1 independently. Prepared
feature 008's portable guidance in a separate collection checkout from released
commit `1397314452c58fb115d451e6d7c1be02ac114a49`, reapplying only task-owned
`80ec2a037e008fafe401e39e9f1b507005cb9a0d` additions. Merge reconciliation preserves
released native-weight preparation, batch estimation, augmentation, Git-warning
instructions and every earlier collection changelog section. The original shared
collection checkout's HEAD, status and 74 captured file hashes remain unchanged.

The eight-path candidate prepares collection patch 0.6.2 and a CY 0.43.0 minimum
for `cy-docs`; installed-command checks remain mandatory. It is not yet committed,
tagged or pushed. Publication waits for final independent review and the actual CY
0.43.0 release identity. Existing dated implementation and native evidence remains
separate from that proposed-version delivery gate.

Discovery listed all four collection skills. Full collection Markdownlint passed
67 files; the CY local Markdown/link checker passed 66 governed collection files.
Skill validation, strict duplicate-aware YAML/schema checks, 14 contained local
links, no-symlink checks, architecture plan/acceptance validation and whitespace
checks passed. The five earlier independent native Codex behavioral cases and the
detailed local-reference behavior remain byte-identical; only the introductory
availability wording now identifies the intended supported version. Their earlier
recorded outcomes are reused; no new agent or live OpenCode evaluation is claimed.

Rechecked the integrated CY source's documentation help and full `--check`; both
passed, with 467 fields, 156 configurations and eight tutorials. Explicit
source-origin checks confirmed the integrated command module and documented parser
defaults/request/worker limits. These source-example checks used `PYTHONPATH` with
a prepared interpreter whose installed CY metadata remained 0.41.0; they are not
installed-release or normal-resolution evidence. Final installation/paired/canonical
acceptance remains owned by the parent delivery workflow.

The companion `verification/2026-10-29-local-docs.md` and architecture record contain
the candidate scope, full commands, preservation observations and pending review/
publication boundary. No skill installation, experiment, queue job or deployment
was performed by this documentation reconciliation.

## Portable guidance published

After independent approval and verified CY 0.43.0 publication, the isolated eight-path
collection change was committed as `6d8f8be4eb83bcd5ac05eae7386451c6b2dd3667`.
Collection 0.6.2 and annotated `v0.6.2` were pushed atomically; remote branch and
peeled tag both match that commit. Full discovery, Markdownlint and local links
passed, followed by checked final evidence text. No unrelated shared collection
edit or installed skill copy was changed. Exact identities and preservation are
recorded in [delivery](delivery.md#completed-git-only-delivery).
