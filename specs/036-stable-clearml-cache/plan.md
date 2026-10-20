# Implementation Plan: Stable ClearML parameter identity

**Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Filter the native General projection, preserve full canonical replay inputs, and expose
a pure opt-in normalization callback for the controller's pre-launch cache lookup.
Use existing dataset cache identity to bind generated path normalization.

## Technical Context

Python >=3.12.13,<3.14; existing uv/uv_build, ClearML, Hydra, Pydantic and pytest.
No dependency changes. Linux execution and existing owner/upload contracts apply.
ClearML hashes hyperparameters and serialized Configuration Objects before task launch.
This project has no PipelineController; registration belongs to the external caller.

## Constitution Check

Retain typed inward interfaces, adapter SDK/effect ownership and inert imports.
The approved change narrows General to scientific settings while storing full execution
configuration in run, preserving native General ownership of scientific overrides.
No installed workflow or constitution changes are required. Preserve local uv sources
and the unrelated grid-search document.

## Project Structure and Module Architecture

See [architecture.json](architecture.json) for scope, executable contracts and checks.
ClearML parameters owns native publication projection; ClearML cache owns serialized
hash projection. Integrations owns callback adaptation; Hydra owns replay composition.
Storage owns existing dataset identity; PreparedDataset conveys it to the training
use case, which records it through the tracking port. No new SDK imports in application.

## Workstreams and Dependencies

1. Parent records approved specification, contract, tasks and architecture; validates plan.
2. Publication agent owns parameters/native callback/detector/Hydra replay and regressions.
3. Cache agent owns cache normalizer and installed-SDK hashing regressions, consuming
   the shared contract. It must not edit publication files.
4. Parent owns dataset identity propagation, integration, architecture tests, docs and
   live CPU evidence. Parent integrates and runs checks after both streams finish.
5. Fresh independent reviewer checks the integrated diff and evidence; fixes precede
   acceptance and authorized commit/tag/push.

## Documentation and Acceptance

Update the tracking contract, current contract index, technical/user guidance and
canonical corp-skills usage/evaluation references. Validate Markdown/local links and
examples. Run focused and full pytest, Ruff, mypy, Vulture, lint-imports, architecture
checks, live ClearML CPU cache/publication smoke and required hooks. Track real results
in verification.md; unavailable requirements are gaps, not passes.

## Release verification amendment — 2026-10-19

The resumed full hook exposed a queue-process test setup race: the synthetic owner
exits immediately after spawning its detached rank, allowing correct guardian cleanup
to terminate that rank before it installs its signal handler and writes readiness.
The persisted job is completed, while the test times out waiting for readiness.
Synchronize this existing fixture on the rank readiness file before owner exit,
with a bounded condition wait and early child-failure detection. Production queue
code, cleanup deadlines, assertions and import contracts remain unchanged. The
existing real-process regression and a delayed-start diagnostic cover the boundary.
This verification-only correction is included in the final independent review.
