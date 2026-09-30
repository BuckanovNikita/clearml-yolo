# Feature Specification: Resolved configuration attachments

**Feature Branch**: `master` (feature directory is independent of the branch)

**Created**: 2026-09-30

**Status**: Implemented, verified and released; see
[verification-2026-09-30.md](verification-2026-09-30.md)

**Input**: User requirement: all configuration parts uploaded to ClearML files must be resolved without interpolation. The user approved the implementation plan and requested implementation using subagents and the full Spec Kit workflow.

## Clarifications

### Session 2026-09-30

- Scope is consumed YAML/YML/JSON files attached as ClearML Configuration Objects, including
  remote clone/replay files. Configuration files are not duplicated as artifacts; native
  General parameters retain their current contract.
- Resolve active values while preserving comments, including interpolation examples inside comments.
- Resolve file-local references and references to the effective command configuration after
  replay and output-routing updates. File root keys override command root keys as whole values;
  retain only original file fields in the stored Configuration Object.
- Effective command context means composed values after replay and app output/output_dir derivation; task-internal native normalization/routing does not redefine this context, and explicit nulls retain their meaning.
- Registered resolver arguments receive original resolved values without artificial markers. Escaped literals and aliases retain their meaning; tuple outputs undergo the same strict checks as other sequences, and resolver-emitted active interpolation is rejected.
- Resolution failures, including missing references, cycles, unknown resolvers and unavailable environment variables, fail publication and invocation. Computed node targets such as `${${key}}` fail confidentially because their credential provenance cannot be established without reevaluation; nested resolver arguments remain supported.
- Resolve before credential sanitization, preserve the original source file, and keep separate unredacted execution and sanitized upload copies.
- Files without interpolation retain their original execution return path even when the upload copy requires credential sanitization.

## User Scenarios & Testing

### User Story 1 - Replay attached configuration files (Priority: P1)

An operator inspects a consumed file's ClearML Configuration Object and sees the concrete values
used by that command without needing its original Hydra configuration or a configuration artifact.

**Why this priority**: Unresolved references prevent standalone interpretation and replay of published files.

**Independent Test**: Attach a file containing local and command-context references through a
fake ClearML boundary, then inspect the actual Configuration Object payload.

**Acceptance Scenarios**:

1. **Given** nested mapping and list references, **When** the file is published, **Then** active values are resolved and typed scalars, nulls and collections retain their meaning.
2. **Given** a file referencing a command value changed by replay or output routing, **When** it
   is attached, **Then** the stored value matches the effective command configuration.
3. **Given** overlapping file and command root keys, **When** the file is resolved, **Then** file roots override command roots without importing unrelated command fields.
4. **Given** a comment containing interpolation syntax, **When** active values are resolved, **Then** the comment survives unchanged.

### User Story 2 - Preserve private execution inputs (Priority: P2)

An operator retains original local configuration and can run with its original values while ClearML receives only a sanitized resolved copy.

**Why this priority**: Publication must preserve credential protection and local reproducibility.

**Independent Test**: Resolve a credential-bearing environment reference, inspect uploaded bytes and original bytes, and assert execution input remains unredacted.

**Acceptance Scenarios**:

1. **Given** an environment reference resolving to a credential, **When** the file is attached,
   **Then** the resolved storage copy is sanitized and the source is unchanged.
2. **Given** a configuration without interpolation or credentials, **When** it is prepared for
   attachment, **Then** its original execution path is returned.
3. **Given** an invalid reference or resolver, **When** attachment is attempted, **Then** the
   invocation fails and no unresolved Configuration Object is stored.

### Edge Cases

- Missing references, resolver errors, cycles, mandatory missing values and unavailable environment variables fail explicitly.
- Nested lists, explicit nulls, booleans, numbers and string-valued interpolations preserve their intended resolved types.
- File-local roots take precedence over command roots, and projection retains original fields only.
- Serialization must not modify comment examples or unrelated literal text.

## Requirements

### Functional Requirements

- **FR-001**: Every consumed configuration file attached as a Configuration Object MUST contain
  resolved active values without unresolved interpolation and MUST NOT be duplicated as an artifact.
- **FR-002**: Resolution MUST cover nested mappings and sequences, file-local references, supported registered resolvers and effective command-context references.
- **FR-003**: File root keys MUST override command root keys as whole values, and published content MUST retain only original file fields.
- **FR-004**: Resolution MUST occur before credential sanitization; execution and storage copies
  MUST remain separate at unique paths, and credentials, including aliases under innocuous keys,
  MUST NOT be stored.
- **FR-005**: Preparation MUST preserve original source files and existing YAML comments, including commented interpolation examples.
- **FR-006**: Resolution failures MUST fail the invocation before unresolved content is attached;
  local diagnostics MUST remain available under existing failure handling without printing
  configuration contents or credential values.
- **FR-007**: Files without interpolation MUST retain their original execution return path even when credential sanitization requires a separate upload copy.
- **FR-008**: All execution commands MUST provide effective configuration context after replay and output-routing changes. Direct invocation attachments without an injected resolver MUST reject interpolated or mandatory-missing inputs with actionable guidance while accepting concrete files.
- **FR-010**: Resolution MUST preserve custom-resolver argument values and escaped literals, validate all sequence outputs including tuples, and reject resolver-emitted active interpolation.
- **FR-011**: Credential redaction MUST retain provenance from sensitive command values and sensitive environment references even when published under innocuous keys.
- **FR-009**: Resolution integration MUST preserve ClearML adapter boundaries, Configuration
  Object identities and completion guarantees without creating configuration artifacts.

### Key Entities

- **Source configuration file**: Original local YAML configuration, comments and field topology.
- **Effective command context**: Current composed command values, including replay and routing updates.
- **Storage configuration copy**: Resolved, sanitized file retaining the source field topology
  and comments for the Configuration Object boundary.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Regression scenarios for every supported configuration-file attachment path publish zero unresolved active values.
- **SC-002**: Source file bytes remain unchanged in successful and failing preparation scenarios.
- **SC-003**: Credential-bearing interpolation fixtures publish no fixture credential values.
- **SC-004**: Invalid references fail publication, and valid resolved files preserve typed values and comments.
- **SC-005**: Dated real-run evidence verifies ClearML Configuration Objects contain resolved
  active values and no configuration artifacts are present; mocked evidence is reported separately.

## Assumptions

- Editable configuration exports may continue to contain interpolation because they are local authoring inputs.
- Existing Configuration Objects and General parameters use their established resolved serialization paths.
- Historical ClearML tasks are unchanged, and external dependencies are not modified.
- No new CLI options or output configuration schemas are introduced.
