# Idea Research: Native ClearML tracking

- **Slug**: native-clearml-integration
- **Created**: 2026-09-30
- **Evidence confidence (overall)**: high for static behavior; real-run outcomes unverified.

## Users & Demand

- User explicitly requests live losses, progress, native best weights and performance-only artifacts — source: conversation (high, cited).

## Prior Art

- Owner native callbacks are already enabled and workers disabled; native pretrain reuses the task and sanitizes General — source: `src/clearml_yolo/native_runtime.py` (high, cited).
- DDP currently reads the complete journal in `replay()` after training, making mid-run DDP visibility unavailable — source: `src/clearml_yolo/native_ddp.py` (high, cited).
- File configuration uses `connect_configuration`, not artifact upload, and preserves resolved/sanitized replay behavior — source: `src/clearml_yolo/clearml_session.py`, `specs/009-resolved-config-uploads/plan.md` (high, cited).
- Publication receipts are retained locally and summarized in configuration — source: `src/clearml_yolo/tasks/publication.py` (high, cited).

## Market & Context

- Users otherwise wait until distributed training finishes to inspect progress — static inference from the complete-journal replay path (high).
- No external market claims are needed for this repository-specific improvement.

## Data & Constraints

- One owner task, owner-only publication, native Output Model identity, configuration-only replay and frozen validation thresholds are existing mandatory contracts — source: `.specify/memory/constitution.md` (high, cited).
- Current baseline: commit `7f59526`, release v0.10.0 — source: local git history and feature 009 release evidence (high, cited).

## Evidence Against the Idea

- Most configuration/model publication guarantees already exist; rewriting them risks regressing replay and creating duplicate uploads — sources above (high, cited).
- Physical multi-GPU availability is not established by these static reads; real DDP acceptance must be reported separately — assumption, medium.

## Gaps & Open Questions

No blocking product questions remain after the approved conversation. Real device availability and backend inventories require implementation-stage evidence.

## Sources

All sources are local repository reads and the user conversation; no URL fetch was performed.
