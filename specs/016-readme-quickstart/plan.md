# Implementation Plan: README quickstart

## Summary

Implement the approved conversation plan as a documentation-only change. Rewrite
README.md around setup, a YOLO-to-CSV conversion and one cy invocation; explain results,
map manual stages and native options, and summarize auxiliary commands.

## Technical Context

Markdown, Mermaid, Bash examples and existing Hydra configuration on Python 3.12.
No runtime API, schema, dependency or architecture changes. Preserve existing local
pyproject.toml overrides and all installed workflow files. Use explicit feature paths
without changing .specify/feature.json; setup helpers that persist it are not needed.

## Constitution Check

The current single-task ownership, CSV input, native configuration, pinned dependency,
paired comparison and publication contracts remain authoritative. Checks are limited
to documentation and configuration composition, with no claim of native execution.

## Implementation

1. Inspect runtime/configuration and setup evidence, with a parallel read-only agent.
2. Rewrite README.md using short Russian instructions and one Mermaid diagram.
3. Preserve the installation and FiftyOne anchors used by existing documents.
4. Reconcile docs/development.md installation cross-references. Retain detailed
   release guidance in the existing release contract and development documentation.
5. Validate Markdown, links/anchors, shell syntax, Mermaid and resolved CLI examples.
6. Obtain a fresh independent read-only review after parent verification.

## Documentation Update

Affected: README.md, stale setup references in docs/development.md and the
001/003 quickstarts, and the relocated viewing example in the 006 quickstart. Review
docs/current-contracts.md and linked contracts; no authority or behavior change means
no contract amendments. Record checks and limitations in dated feature evidence.

## Workflow

Use the approved plan without reopening design decisions. Spec Kit specify, plan,
tasks, analysis and implementation are proportionate documentation stages; hooks are
empty. Do not run helpers that mutate installed .specify state. Execute tasks in order;
investigation can run alongside artifact preparation, final review follows validation.

## Follow-up plan — 2026-10-06

Revise README.md for the user's CSV-first clarification and friendlier Russian wording.
Remove conversion from onboarding and the diagram. Replace GPU setup/device-index
guidance with automatic `-1` requests, repeated entries for native DDP and queue behavior.
Update this feature's existing specification/tasks and append dated validation evidence;
preserve prior completed history. Validate Markdown/links, changed diagram and actual
single-device/DDP configuration composition, then obtain an independent read-only review.
No application code or maintained runtime contract changes are needed.
Remove the README source-overrides block per subsequent user steering. Use frozen
lockfile installation/execution, check it against clean committed metadata in a
temporary checkout layout, and reconcile installation references in development/001.

Clarify repeated baseline inference in the README comparison paragraph and table;
verify against comparison execution and recovery contracts. Validate documentation
and obtain a bounded independent review; no runtime change is needed.
Also replace the FiftyOne enable/disable guidance with a concise capability note,
retaining the link to the dedicated viewing guide.
Remove clone/checkout instructions from README; redirect the 001 validation guide's
submodule setup link to existing development guidance. Check the resulting prose/links.
Remove the subsequently selected clearml-init step and renumber the remaining steps.
Apply final scope: remove all general setup material from README, use direct installed
cy entrypoints, retain usage-specific guidance, and fix the development guide's removed
installation-anchor reference. Check direct command composition without execution.
Expand the YAML usage section with cy-config generation, native-key training/prediction
examples and the exact requested launch command. Validate exported-and-edited YAML
composition in a task-owned temporary directory without starting a ClearML task.
Promote YAML generation/editing/launch to the primary numbered quickstart, with one
secondary override example. Update DDP guidance to edit the native YAML files. Verify
the exact snippets, generated defaults, ordinary/override/DDP composition and docs.
After independent review, commit and create the explicitly requested minor Git release
through existing release checks, preserving dependencies and local source overrides.

## Training-first documentation follow-up — 2026-10-15

The approved follow-up supersedes the earlier YAML-first presentation, without
rewriting that completed history. README becomes a Russian practical guide beginning
with four direct training commands (YOLO, DEIMv2, RF-DETR, Faster R-CNN), followed by
training controls, full experiments, independent stages, reusable YAML/sweeps/DDP,
queue execution and auxiliary tools. TECH_DETAILS.md is the English technical entry
point. Runtime behavior, dependencies and interfaces remain unchanged.

### Task contract and architecture

Inspected Python compatibility is `>=3.12,<3.13`, the package is under
`src/clearml_yolo`, and the build backend is `uv_build`. Inspect current entrypoint
schemas, model presets, use cases and maintained contracts for examples; use the
existing installed environment without dependency synchronization. The adjacent
[architecture record](training-first/architecture.json) classifies impact as `none`:
code/configuration inspection informs documentation only. Existing import contracts
and architecture tests are unchanged and need no execution for this prose-only task.

The parent owns README, technical reference, navigation, ledger and validation. A
bounded read-only command audit can run alongside drafting; integrate its findings
before validation. A fresh independent read-only review follows parent verification.
No training, inference, GPU admission, queue submission or service publication runs.
Follow normal documentation commit/release evaluation; do not force a version bump.

### Content migration map

| Existing README topic | Destination and treatment |
| --- | --- |
| Introduction and library roles | README opening and complete experiment |
| Installation, dependency versions and external source setup | TECH_DETAILS setup; maintained development/model/deployment links |
| Generated YAML, native groups, overrides and config collisions | README reusable experiments; TECH_DETAILS configuration and migration |
| CSV columns, paths, splits and native dataset ownership | README everyday training; TECH_DETAILS input contract links |
| Pipeline, Mermaid, baseline selection/re-inference and result locations | README complete experiment |
| Detector presets, pretrained assets, source checkout and native checkpoints | README training table and DEIM command; TECH_DETAILS backend reference |
| Manual-script migration table and native-parameter mapping/defaults | README training controls and workflow progression; TECH_DETAILS migration table |
| Command inventory | README actionable independent workflows and auxiliary sections |
| Model labels, sidecars and provenance | README local-model guidance; TECH_DETAILS provenance/checksum details |
| Plot semantics, XLSX identities, valid-class summaries and publication inventory | TECH_DETAILS publication, linking maintained contracts |
| Reflink eligibility, metadata, dry-run and error semantics | README brief safe usage; TECH_DETAILS cache maintenance and contract |
| Direct devices, DDP, queue basics and multirun tags | README reusable experiments and queue |
| Queue ordering, memory limits, recovery, physical GPU controls and TUI keys | TECH_DETAILS queue operations; maintained queue guide |
| Process cleanup, pidfd requirements and DDP acceptance tests | TECH_DETAILS process ownership and development/DDP links |
| CY_HOME, output/cache/scratch ownership and SDK selector migration | README result routing; TECH_DETAILS filesystem and setup |
| FiftyOne inspection and bounded optional publication | README capability; TECH_DETAILS isolation and maintained viewing guide |
| Python imports, explicit deps and obsolete Hydra targets | TECH_DETAILS Python integration and generated-YAML migration |
| Troubleshooting, TRACE capture, error redaction and console publication | README concise triage; TECH_DETAILS diagnostics and maintained capture recipe |

Check incoming README anchors and add navigation from the contract index and
development guide. Correct stale automatic-waiting prose encountered in maintained
model guidance; preserve historical evidence. The portable usage skill source was
inspected and already describes direct execution, queue allocation, labels and input
contracts correctly; presentation-only changes do not require a companion skill edit.

### Acceptance

Validate this no-impact record in plan phase before drafting and acceptance phase
after diff reconciliation. Parse/lint changed Markdown, verify local paths/anchors
including incoming README links, parse Bash/YAML and Mermaid. Compose new Hydra
examples with `--cfg job --resolve`, export/edit YAML in temporary isolated roots,
and inspect queue help/source without submitting jobs. Record actual results and
review in dated evidence. Application tests and native acceptance are outside scope.

## Master integration follow-up — 2026-10-15

Land the reviewed documentation on master after integrating upstream `8a49323`.
Preserve its Python `>=3.12.13,<3.14` compatibility and queue-worker diagnostics in
the rewritten guides. The existing no-impact architecture scope remains accurate:
resolve documentation conflicts only, regenerate CHANGELOG through the native hook,
validate the integrated prose/links and unchanged example schemas, obtain scoped
fresh review, fast-forward local master while preserving its local source overrides
and untracked work, then evaluate the native release helper and push master.
