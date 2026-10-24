# Feature Specification: Reduce code and verify each release once

**Feature Branch**: `master` (existing automatic release branch)

**Created**: 2026-10-24

**Status**: Approved for implementation from the supplied plan

**Input**: Reduce maintained code, consolidate architecture enforcement, add bounded mutation acceptance and reuse successful verification across automatic releases.

Baseline: [stage zero](../000-baseline/spec.md). Only removal of the unused runtime supervision API is an approved breaking change.

## User Scenarios & Testing

### User Story 1 - Maintain less code with the same behavior (Priority: P1)

Maintainers remove obsolete and duplicated implementation without losing active process ownership, asset validation or architectural rejection behavior.

**Why this priority**: Less maintained code with the same enforced contracts reduces maintenance cost.

**Independent Test**: Compare maintained line totals and run affected cancellation, asset, composition and architecture cases.

**Acceptance Scenarios**:

1. **Given** an owned process tree, **when** cancellation repeats or ownership becomes uncertain, **then** detached descendants remain accounted for and unrelated/reused processes remain protected.
2. **Given** valid or corrupt cached model assets, **when** validation runs, **then** nonempty valid tensors pass and malformed assets use the existing failure/fallback boundary.
3. **Given** an ordinary or dynamic forbidden dependency, **when** architecture checks run, **then** the dependency is rejected by retained enforcement.

### User Story 2 - Verify unchanged release inputs once (Priority: P1)

Contributors run one canonical verification and reuse trustworthy success through contributor commit, generated version commit and tag recovery.

**Why this priority**: Repeated full runs add substantial waiting without adding evidence for unchanged inputs.

**Independent Test**: Temporary Git repositories count actual check invocations across verification, commit, version and recovery.

**Acceptance Scenarios**:

1. **Given** unchanged verified inputs, **when** a contributor commit produces its expected version commit, **then** exactly one complete ordinary suite runs.
2. **Given** missing, malformed, failed, interrupted or stale evidence, **when** verification is requested, **then** fresh checks execute.
3. **Given** changed environment, dependencies, governed files or staged view, **when** reuse is considered, **then** evidence for the previous view is rejected.
4. **Given** documentation-only evidence changes, **when** documentation checks run, **then** application success remains independently reusable.

### User Story 3 - Detect weak offline assertions (Priority: P2)

Maintainers assess selected training-box, evaluation-policy and export-quality logic with bounded mutation testing outside commit hooks.

**Why this priority**: Mutation results expose plausible changes that existing assertions miss.

**Independent Test**: Run the selected baseline, inspect every result and retain reviewed equivalent explanations.

**Acceptance Scenarios**:

1. **Given** changed selected logic, its tests or dependencies, **when** acceptance runs, **then** affected mutation selection is rerun.
2. **Given** surviving, untested, timed-out or runner-error outcomes, **when** results are assessed, **then** unresolved gaps prevent acceptance; survivors need stronger assertions or reviewed equivalence evidence.

### Edge Cases

Partial staging and path-limited commits; untracked fixtures; byte-identical metadata hiding dependency content changes; concurrent edits and verification; release parent, changelog, metadata or tag conflicts; empty/truncated tensors, invalid dtype/shape and overlapping offsets; repeated signals, PID reuse and uncertain ownership.

## Requirements

### Functional Requirements

- **FR-001**: Remove only the approved obsolete API and preserve active process/queue scenarios, typed composition interfaces and binding behavior.
- **FR-002**: Replace redundant asset parsing and hashing while retaining nonempty validation, error translation, tracing and post-read identity checks.
- **FR-003**: Consolidate supported architecture rules under the maintained contract authority; retain unique checks, dynamic-edge rejection, cycles and representative negative coverage.
- **FR-004**: Provide canonical ordinary, documentation-only and forced verification with atomic success receipts and logs in private Git storage.
- **FR-005**: Bind reuse to all governed content, check settings, interpreter, installed and editable dependencies, environment and actual commit file view, including untracked inputs.
- **FR-006**: Reuse generated release verification only after exact parent, root-version-only metadata, release-path and changelog validation; preserve tag ownership, concurrency and conflict checks.
- **FR-007**: Add bounded offline mutation selection and a reviewed baseline; unresolved survivors or incomplete execution block acceptance.
- **FR-008**: Preserve dependency overrides exactly, the approved external revision, automatic release and Git-tag-only delivery; verify final source with overrides absent through review/release.
- **FR-009**: Update affected documentation, record real timings/check invocations and obtain fresh independent review after integrated verification.

### Key Entities

- Verification receipt: successful commands, input identity, results and log references.
- Release attempt: source parent, expected version metadata and changelog identity.
- Mutation evidence: selected scope, generated outcomes, reviewed survivor disposition and input identity.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Maintained Python lines decrease after counting new tooling and tests.
- **SC-002**: Unchanged verification-to-release-to-tag-recovery runs the full ordinary suite exactly once in executable lifecycle tests.
- **SC-003**: All original active behavior and prohibited-edge scenarios pass except the explicitly removed API.
- **SC-004**: Every selected mutant is killed or has a reviewed equivalent justification; no untested, timeout or runner-error outcome remains.
- **SC-005**: Documentation, architecture acceptance, independent review and authorized commit/tag delivery complete with recorded evidence.

## Assumptions

The supplied plan settles design direction; no further product decision is required. Authentication replacement, scientific bootstrap, ownership algorithms and workbook recovery remain out of scope. Existing local external dependencies remain authoritative. No distributions, GitHub Releases, packages or deployment are produced.
