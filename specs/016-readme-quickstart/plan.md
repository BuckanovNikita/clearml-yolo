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
