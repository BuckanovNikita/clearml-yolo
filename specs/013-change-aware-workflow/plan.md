# Implementation Plan: Change-aware workflow

**Branch**: `013-change-aware-workflow` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

## Summary

Implement the approved workflow simplification in existing Task/prek tooling. One
classifier chooses staged or latest-commit paths. A bounded selector collects only
candidate unit files, validates cached node IDs, excludes heavy markers and executes
explicit IDs with testmon selection disabled. Separate explicit commands keep full scope.

## Technical Context

Python compatibility and tool versions remain in pyproject.toml; Bash, Task, prek,
pytest/testmon and semantic-release remain the owning tools. Existing ignored local
external packages and environment are reused. Tests are disposable command-level
scenarios, static gates and retained product collection/acceptance. No new tooling tests.
The target is the existing Linux developer/release workflow; product import simplification is included in the approved architecture reduction.

## Constitution Check

Pass before and after design: preserve typed Python, product module boundaries and effect
ownership guidance, dependency pins, user authorization and task-owned cleanup. Removing
custom effect detection reduces automation, not the purity rule. Task scripts own checks;
Spec Kit owns documentation analysis. No installed Spec Kit edits or package builds.

## Project Structure

- `scripts/verification.py`, `scripts/hygiene.py`: classifier, bounded selection and hygiene.
- `Taskfile.yml`, `.pre-commit-config.yaml`, `scripts/git-hook.sh`: ordered dispatch/staging.
- `Taskfile.ops.yml`, `scripts/release.py`, release build configuration: explicit release.
- `scripts/architecture*.py`, `tests/`: remove requested machinery/coverage, preserve product.
- `docs/`, six maintained `.agents/skills/`: authoritative procedures and decision guidance.
- This feature directory: native specification, design, task ledger and dated evidence.

## Implementation Order and Ownership

Root owns routing/hygiene and shared configuration. Release agent owns operations/release
helper and release skill. Coverage agent owns architecture/tests. Documentation agent
owns guidance/five other skills. No child delegation or commits. Root integrates and
verifies, then assigns fresh independent review. Release build/config edits are sequential
through root. All task commits precede the canonical automatic hook pass.

## Verification

Disposable repos exercise route/refusal behavior, bounded fresh/stale/missing history,
empty selections and release failures. Static checks run after automatic corrections.
Explicit product collection proves retained tests remain collectable; applicable explicit
acceptance remains full, preflight first. No real release/publish. Record measured line/test
reductions, exact checks, review and any deferred external outcomes in dated evidence.

## Architecture reduction implementation

Convert fixed dynamic imports while preserving guards and lazy timing; retain computed
DEIM targets. Adapt product mocks and add actual import/target coverage. Replace custom
architecture scripts with native import-linter contracts and Ruff restrictions, removing
unused direct tooling dependencies. Reconcile authoritative documentation with explicit
retired enforcement. Root owns shared configuration, integration and commits; bounded
agents own source/matching tests and independent runtime tests. Verify focused paths,
full ordinary suite and applicable live gates, then canonical committed-tip hooks and
fresh independent review. No scanner implementation migrates into tests.

## Approved consolidation implementation

Use an isolated worktree based on 5044d23. Root owns native artifacts, property-stage
removal outside Taskfiles, integration, checks and commits. Bounded agents own:
(1) scripts/release.py and Taskfiles, (2) lifecycle/smoke/helpers/environment contract,
(3) skills and active documentation. No child delegation or commits. Integrate before
fresh independent review. Native policy overrides the older blanket constitutional
verification/skill-count requirements under explicit user authority; preserve installed
.specify files. Verify with disposable release scenarios (no tooling tests), two live
CPU smoke runs in one adopted owned environment, focused product tests, static gates
and committed-tip prek. Report deferred checks honestly. No packaging or publishing.
