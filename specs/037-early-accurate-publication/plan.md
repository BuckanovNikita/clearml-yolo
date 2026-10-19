# Implementation Plan: Accurate configuration and early complete publication

**Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

## Summary

Extend the partial configuration fix in [stable cache work](../036-stable-clearml-cache/plan.md).
Use the selected backend's resolved executable inputs for run, publish differences and General
early, and move complete artifact uploads to producer completion while retaining final barriers.

## Technical Context

Python >=3.12.13,<3.14; existing uv/uv_build, strict mypy, Ruff, pytest, Vulture and
import-linter. No dependency changes. Use the prepared environment with frozen/no-sync
verification. Queue snapshot composition is already preserved; verify its whole path.
The source checkout contains other agents' work. Work in an isolated snapshot and reconcile
only this task's delta after their release; never stage their uncommitted changes.

## Constitution Check

Typed ports keep application free of SDK effects. Hydra owns defaults/backend selection;
ClearML owns sanitization, detached configuration publication and artifact state. No new
third-party dependencies, workflow tooling edits or historical task rewrites. Existing
owner-only DDP, dataset validation and final upload/model barriers remain authoritative.

## Project Structure

See [architecture.json](architecture.json) for module responsibilities and executable boundaries.
Existing tracking, publication and export contracts are extended in [contracts/publication.md](contracts/publication.md).

### Workstreams and dependencies

1. Parent records spec, architecture and typed interfaces; validates plan before code.
2. Configuration agent owns Hydra common/default projection, ClearML session/cache,
   early General training hook and corresponding tests. It receives detached mappings.
3. Artifact agent owns results bundle, prediction/metrics/comparison/pipeline/report
   sequencing and tests. Contributor operations are fixed before parallel implementation.
4. Parent owns ports/composition, export callback producers/tests, architecture negatives,
   integration and documentation. Agents never delegate further or commit.
5. Parent verifies integrated behavior, static checks and real runs; a fresh independent
   reviewer checks the final diff/evidence. Resolve findings before acceptance/release.

### Documentation scope

Update specs 008/009/010/014/025 publication/replay/export contracts as affected, README,
TECH_DETAILS, docs/project-contracts.md, docs/current-contracts.md and backend/export guides
where needed. Inspect and update canonical corp-skills clearml-yolo usage/evaluation source
sequentially with other agent changes; preserve completed histories and machine isolation.

## Verification and acceptance

Run focused regressions then full pytest, Ruff, mypy, Vulture, lint-imports, separate
architecture tests, documentation checks and applicable hooks. Validate this record at
plan and acceptance. Verify live direct and queued native execution including DDP, reading
ClearML while running and downloading final files. Record unavailable backend/hardware
checks as gaps. Follow commit procedure and native Git-tag-only release after other agents
finish; preserve local uv source overrides exactly and verify remote refs.

## Complexity Tracking

No architectural exceptions. Configuration and artifact state stay with existing owners.
