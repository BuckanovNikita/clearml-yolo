# Feature Specification: Accurate configuration and early complete publication

**Date**: 2026-10-19 | **Status**: implementation authorized

## User Scenarios & Testing

### User Story 1 - Inspect executable configuration (Priority: P1)

An operator can inspect selected training inputs and meaningful changes as soon as a
new direct or queued invocation starts. YAML and CLI settings, allocated devices and
supported remote overrides must match execution. Unused backend defaults do not appear.
Independent test: trace non-default weight decay from YAML/CLI and queue snapshots to
published run, General and training arguments, including multirun and historical replay.

### User Story 2 - Retrieve complete results during execution (Priority: P1)

An operator can download each complete artifact while later stages are still running.
Incomplete combined predictions remain local; a later failure retains completed uploads.
Independent test: inspect an active invocation before training, later evaluation,
comparison statistics, reports and optional publication, and verify canonical contents.

### User Story 3 - Preserve completion and replay guarantees (Priority: P1)

Cloning uses run; the informational differences view does not change execution or cache
identity. Upload rejection, cancellation and failed final flush cannot report success.
Independent test: cache projection, replay, duplicate completion, failure and flush cases.

### Edge Cases

False, zero, null, explicit empty collections and list order remain meaningful. Selected
preset defaults govern differences. Skipped training creates no General parameters.
Skipped comparison completes its contributor without fabricating predictions. Ground truth
may repeat only when identical. DDP workers never access ClearML. Historical tasks stay intact.

## Requirements

### Functional Requirements

- FR-001: Full run records resolved executable inputs after supported override precedence,
  selected backend settings only, with native normalization recorded separately.
- FR-002: run_overrides contains recursively pruned differences from built-in defaults for
  the same command and selected preset, including YAML/CLI changes and meaningful empty values.
- FR-003: run_overrides is sanitized, deterministic and informational; exclude routing,
  result provenance, inactive groups and this object from recognized-task cache projection.
- FR-004: Publish validated sanitized General before dataset preparation for training only,
  after remote overrides; retain parameter exclusions and owner-only observed refreshes.
- FR-005: Publish effective validated ground truth once written, exact thresholds once
  calibrated, each annotated dashboard before subsequent evaluation/statistics, and each
  final annotated workbook and finalized export file as soon as complete.
- FR-006: Explicitly declare all result contributors and publish combined predictions once
  their final contributor completes, before reports/optional publication; handle standalone
  and skipped stages, and reject later row mutation or invalid completion transitions.
- FR-007: Best Output Model publication follows final best checkpoint selection and retains
  existing verification. Finalization verifies all uploads and flushes; errors fail the task.
- FR-008: Preserve existing cache/replay work and unrelated edits; use typed inward interfaces,
  complete documentation and checks, and release sequentially after other agents' releases.

### Key Entities

Executable run; informational run_overrides; selected preset defaults; sanitized General;
result contributor; complete artifact; invocation verification barrier.

## Success Criteria

- SC-001: Published scientific inputs equal execution inputs for direct/queued and remote
  replay scenarios; inactive settings and unchanged defaults never appear as overrides.
- SC-002: Active-task observations establish each specified earliest publication point;
  canonical files are uploaded once and downloaded content matches completed local output.
- SC-003: Every declared contributor completes before combined predictions publication;
  failure/cancellation leaves incomplete aggregates unpublished and tasks unsuccessful.

## Assumptions

Changes apply only to newly executed tasks. Approved dependency revisions and infrastructure
remain unchanged. Existing native normalization is evidence, not replacement executable
configuration. Required unavailable live checks remain documented acceptance gaps.
