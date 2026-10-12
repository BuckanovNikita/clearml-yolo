# Implementation Plan: Module architecture planning

**Branch**: `027-module-architecture-planning` | **Date**: 2026-10-12

**Spec**: [spec.md](spec.md)

## Summary and technical context

Integrate `module-architecture-planning` into the existing Spec Kit workflow through
[AGENTS.md](../../AGENTS.md) and [workflow policy](../../docs/agent-workflow.md).
Use the shared record format and validator rather than copying checker code or editing
installed templates. No new data model, public interface or runtime dependency is needed.

## Constitution check

Preserve enforced module boundaries, proportional documentation verification, English
agent guidance, explicit scope and truthful evidence. Runtime contracts and the pinned
dependency stay unchanged. No constitution amendment is needed.

## Architecture

[architecture.json](architecture.json) records no module impact: only policy and native
planning/evidence prose change. Inspected [pyproject.toml](../../pyproject.toml) and
[architecture tests](../../tests/test_architecture.py) already enforce layer direction,
SDK ownership, exhaustive classification, effects, initialization and dynamic targets,
including prohibited-edge cases. Future runtime plans must map affected modules to this
actual coverage and add scoped checks when uncovered; documentation inventories are not authority.

## Workstreams and dependencies

This bounded documentation integration is sequential: establish scope and record, analyze
spec/plan/tasks consistency, edit policy, then validate and reconcile. The primary agent
can develop the shared skill independently; this workstream owns only AGENTS.md,
docs/agent-workflow.md and this feature directory. Parent integration, verification and
fresh independent review follow this workstream; this agent does not delegate or commit.

## Documentation and acceptance

Update AGENTS.md and docs/agent-workflow.md. Reviewed README and runtime contract scope:
no user-facing behavior or application contract changes, so neither needs an update.
Validate changed Markdown structure/local links and whitespace, validate the record in
planning and acceptance phases, and record actual results in [verification.md](verification.md).
Do not run application suites or synchronize an environment for this no-impact change.
Installed Spec Kit skills are applied proportionately; the explicit no-.specify scope
precludes feature pointer/setup mutations. Hook registration is empty.
