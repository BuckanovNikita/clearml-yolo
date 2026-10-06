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
