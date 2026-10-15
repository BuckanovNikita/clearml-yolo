# Feature Specification: Read-only documentation checks

**Created**: 2026-10-15

**Status**: Approved for implementation from the supplied cleanup plan.
**Input**: Add a read-only Markdown structure, local-link and GitHub-anchor checker.

## User Scenarios & Testing

### User Story 1 - Validate maintained documentation (Priority: P1)

A maintainer runs one offline command before accepting documentation changes.
Valid prose and fenced examples pass; broken local destinations, invalid heading
fragments, undefined explicit references and unclosed fences report file and line.

**Independent Test**: Temporary repositories include valid and broken documents,
Unicode and duplicate headings, reference links, code examples and local assets.

1. Given a missing local target, validation exits 1 with a location and target.
2. Given valid links, including duplicate-heading suffixes, validation exits 0.
3. Given fenced shell commands or Markdown examples, validation never executes them.

### User Story 2 - Preserve ownership boundaries (Priority: P2)

A maintainer checks all project-owned tracked Markdown without inspecting ignored
evidence, an untracked draft, generated changelog or installed workflow templates.
Explicit paths allow checking newly authored project documents before staging.

**Independent Test**: A temporary Git index contains included and excluded files;
the command preserves file bytes and Git index state.

## Requirements

- **FR-001**: Provide `uv run --frozen --no-sync python scripts/check_docs.py --all`;
  also accept explicit project Markdown paths, with deterministic diagnostics.
- **FR-002**: Resolve local links relative to their document, percent-decode paths
  and fragments, and validate Markdown heading anchors using rendered inline text,
  lowercase Unicode and GitHub-style duplicate suffixes.
- **FR-003**: Support inline/image/reference links, explicit HTML anchors and links,
  repeated headings, Unicode, inline code and fenced/indented code examples.
- **FR-004**: Report missing destinations/anchors, repository escapes, unreadable
  documents, undefined explicit or collapsed references and unclosed code fences.
- **FR-005**: `--all` selects project-owned Git-tracked Markdown. Exclude symlinks,
  generated `CHANGELOG.md`, installed Spec Kit skills/commands/templates and other
  vendored assets. Keep project assessments, bugs and constitution in scope.
- **FR-006**: Do not fetch external links, execute examples, rewrite files or load
  application runtimes. Mermaid grammar requires separate rendered review.
- **FR-007**: Declare the already locked `markdown-it-py==4.2.0` directly in the
  development group without changing other dependency versions or sources.

## Success Criteria

- **SC-001**: Positive fixtures pass; each reproduced violation produces nonzero
  status and identifies the owning document and source line.
- **SC-002**: All-file selection and explicit-path runs preserve files and index.
- **SC-003**: Dependency negative fixtures reject application/model imports and
  dynamic loaders; permitted parser and standard-library imports pass.

## Assumptions

Markdown is CommonMark with tables/strikethrough enabled. Structural checks target
unclosed fences and ambiguous reference definitions, not stylistic heading-level
rules. Bare unresolved shortcut references remain ordinary prose. URI schemes and
protocol-relative URLs are external and are not fetched. Markdown anchors do not
claim complete GitHub HTML sanitization or Mermaid grammar enforcement.
