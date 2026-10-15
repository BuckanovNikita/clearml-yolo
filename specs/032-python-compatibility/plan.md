# Implementation Plan: Python compatibility

**Branch**: `master` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

## Summary

Change package and lock metadata to `>=3.12.13,<3.14`, preserve Python 3.12 as
the development and static-analysis baseline, and verify both supported minors.
Keep native supervision capability checks and approved dependency sources intact.

## Technical Context

The project is a uv/uv_build Python CLI/library with Hydra, Pydantic, Pandera,
Ultralytics and optional detector/export dependencies. Existing locked versions
are preferred during re-resolution. Linux native execution still requires pidfd,
subreaper and proc capabilities. There is no data model or runtime interface change.
No new performance target is introduced. The native release policy additionally
requires scoped real CPU and single-GPU verification; it does not require repeating
all unchanged detector/export acceptance matrices.

## Constitution Check

Authorized compatibility change satisfies the constitution's version exception.
No layer, SDK ownership, runtime effect or scientific algorithm moves. Preserve
local editable sources exactly and never change approved external source revisions.
Use existing import and negative dependency tests. Gates are checked again against
the final diff and fresh independent review.

## Project Structure and Architecture

The package manifest and lockfile own installation compatibility and dependency
selection. Runtime effects remain in existing adapters, injected through application
ports; core and application acquire no new outer dependencies. The
[architecture record](architecture.json) maps packaging configuration to existing
dependency ownership and import checks, including forbidden-edge negative tests.

Affected maintained prose: `AGENTS.md`, `README.md`, `docs/development.md`,
`docs/current-contracts.md`, `docs/multi-model-backends.md`,
`docs/tensorrt-deployment.md` and `docs/queue.md`. Historical evidence/specs remain
unchanged. The portable clearml-yolo skill was inspected: its capability guidance
does not pin a Python version, so no companion edit is needed for this project.
The companion cveta2 skill requires its separate prerequisite update.

## Verification and Delivery

Run lock consistency, build and metadata boundary checks; install the built wheel
and source distribution outside the package source on 3.12 and 3.13 and invoke all
installed command helps and configuration selections
and the actual supervision probe. Run the routine suite on both minors, existing
architecture tests/import-linter and standard lint/type/dead-code gates. Validate
changed Markdown and local links. Run short native CPU and single-GPU training and
prediction with isolated tagged ClearML tasks, verify uploaded outputs by download,
and clean owned resources. Other detector families, physical multi-GPU execution,
compilation and export remain outside this compatibility change. Static/packaging
checks alone do not establish those native outcomes.

Preserve the unrelated `docs/cls-cls-pw-grid-search.md` and local source overrides.
After acceptance, follow `docs/development.md` commit and release procedure; restore
the exact sources section unstaged and deliver only Git commit/tag refs. Keep the
canonical checkout on master as requested.

## Dependencies and Ownership

The parent owns clearml-yolo and companion skill documentation. Independent agents
own cveta2 and ed-killer; their branches integrate only after checks and fresh review.
Within this repository: plan -> metadata/lock -> matrix/packaging checks -> final
documentation/review -> commit/release. Independent static checks may run together;
CPU distributed matrix tests run sequentially to avoid competing native workers;
other isolated regression checks may overlap across interpreters.

## Workflow Adaptation

Spec Kit templates were resolved through the installed resolver. Project policy
forbids modifying `.specify/`; use explicit feature selection with read-only path
resolution and render the resolved templates directly instead of setup helpers
that persist `.specify/feature.json`. Extension hooks are empty. No parallel workflow
or installed tooling changes are introduced.
