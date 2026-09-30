# Research: Resolved configuration uploads

**Date**: 2026-09-30

## Resolution placement

**Decision**: Use an apps-layer OmegaConf resolver injected into invocation as a typed callback.

**Rationale**: Existing import contracts prohibit Hydra/OmegaConf dependencies in the ClearML adapter. A closure reads command configuration at attachment time, so replay and routing changes are reflected.

**Alternatives considered**: Importing Hydra directly into clearml_session violates module boundaries; eagerly snapshotting command context misses later changes.

## Publication ordering

**Decision**: Resolve first, discover secrets from resolved values, then sanitize the upload copy; preserve an independent execution copy.

**Rationale**: Environment interpolation can conceal secrets until resolution. Reusing a sanitized file for execution changes runtime behavior.

**Alternatives considered**: Sanitization before resolution leaves newly materialized secrets unprotected; resolving source files in place damages local reproducibility.

## Context composition and preservation

**Decision**: File roots override command roots as whole values, then project original fields only. Use existing comment-preserving YAML handling; no-interpolation files preserve the original execution path even when a sanitized upload copy is needed.

**Rationale**: File-local reference semantics must remain authoritative, while command context is available only for external references. Publication must not gain unrelated fields.

**Alternatives considered**: Recursive merges introduce command fields into source-local mappings; resolving serialized text rewrites comment examples and loses scalar types.

## Workflow and evidence

**Decision**: Complete the core SDD cycle plus clarify, analyze and post-implementation converge, with bounded resolver, attachment and workflow audits and exclusive implementation ownership.

**Rationale**: The user requested subagents and the full workflow. The installed workflow includes explicit spec/plan reviews, supplied by the approved plan. No extension hooks are registered.

**Alternatives considered**: The assessment extension is optional discovery work; the bug extension does not fit this new requirement. Neither is required by the installed Full SDD Cycle.

All material clarification decisions were supplied by the user-approved plan; no open research blocker remains. Implementation and verification are separate evidence stages.
