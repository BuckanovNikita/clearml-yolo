# Feature Specification: Static analysis policy audit

**Feature Branch**: existing checkout; preserve concurrent staged work
**Created**: 2026-10-12
**Status**: Specified
**Input**: Revise ignored Ruff and mypy rules, including Ruff rules not selected;
add Vulture to pre-commit and explain the quality/readability tradeoffs.

## User Scenarios & Testing

### User Story 1 — Understand and tighten exclusions (Priority: P1)

A contributor can identify every category of disabled lint checks, distinguish
deliberate tradeoffs from gaps, and run the revised checks successfully.

**Independent Test**: Compare the installed rule catalog and effective configuration
against the report, then run lint and type checks over the repository.

**Acceptance Scenarios**:

1. Given an explicit ignore or unselected rule, the report explains its disposition
   with concrete project evidence instead of asserting that all checks harm readability.
2. Given an obsolete or unnecessarily broad exception, the revised policy removes or
   narrows it while preserving public behavior and unrelated work.

### User Story 2 — Detect dead code before committing (Priority: P1)

A contributor gets a reproducible dead-code check through the existing commit tooling.

**Independent Test**: Run the hook on the current tree and a temporary known-dead
sample; the sample must fail while intended dynamic callbacks remain usable.

**Acceptance Scenarios**:

1. The hook scans first-party source, tests and scripts together, independent of the
   staged filename list, using the project's declared development dependency.
2. Intentional unused fixture/callback parameters remain explicit without blanket
   symbol exclusions or removal of required framework interfaces.

### Edge Cases

- Preview, removed and conflicting rules are distinguished from stable omissions.
- Runtime annotation consumers and dynamic third-party callbacks retain their contracts.
- Existing staged changes and protected editable dependencies remain intact.

## Requirements

- **FR-001**: Audit all explicit and implicit Ruff exclusions, including preview status.
- **FR-002**: Review mypy import overrides and suppression policy without weakening strictness.
- **FR-003**: Enable useful compatible checks and justify retained exceptions with examples.
- **FR-004**: Add a reproducible Vulture commit gate and verify actual failure detection.
- **FR-005**: Publish a maintained policy report and dated verification evidence.

## Success Criteria

- **SC-001**: Every omitted rule family and explicit project exception has a documented disposition.
- **SC-002**: Revised lint, type and dead-code checks pass; a known dead-code sample fails.
- **SC-003**: Relevant regression checks and fresh independent review find no behavior regression.

## Assumptions

- This is tooling maintenance; public CLI, model behavior and dependency revisions are unchanged.
- Generated files and external dependencies are outside first-party dead-code scope.
- A confidence threshold may exclude uncertain dynamic-use findings if its limitation is explicit.
