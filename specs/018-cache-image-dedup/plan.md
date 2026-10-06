# Implementation Plan: Cache image deduplication

**Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

## Summary

Implement the approved standalone command with an argparse CLI and a filesystem-only
core. Group exact filenames, sizes and streamed content hashes, confirm equality,
then clone into a sibling temporary file, restore metadata and atomically replace.

## Technical Context

Python 3.12; standard-library filesystem, hashing and Linux ioctl support; no new
dependencies. Tests use pytest and temporary directories; native reflink checks skip
explicitly on unsupported filesystems. Existing Ruff, mypy and import contracts apply.
Core resides in `src/clearml_yolo/dedup.py`; CLI in `src/clearml_yolo/dedup_cli.py`.
The CLI is outside apps because apps/__init__.py eagerly creates application directories.

## Constitution Check

Pass: filesystem utility has no model, tracking or Hydra dependency; execution-stage
tracking contracts remain unchanged. User explicitly approved this local utility.
No dependency revisions or installed workflow tooling change. Source content remains
immutable; only duplicate storage allocation changes. Use existing release workflow.

## Implementation and Verification

1. Core and behavioral tests (FR-002 through FR-006), delegated with exclusive ownership.
2. CLI registration, import contracts and subprocess CLI tests (FR-001, FR-005, FR-006).
3. Parent integration checks: targeted and full pytest, Ruff, mypy, import contracts,
   installed help/dry-run and native reflink evidence; independent fresh review.
4. Documentation stage: README.md, docs/filesystem-policy.md, docs/project-contracts.md,
   docs/current-contracts.md and specs/001-release-030/contracts/cli.md; validate
   Markdown, local links and CLI examples. Record evidence and release after checks.

## Workflow Notes

Use SPECIFY_FEATURE_DIRECTORY explicitly, preserving installed .specify files.
Extension registry has no hooks. Existing approved conversation resolves material
clarifications. No additional design approval is needed for this authorized scope.
