# Implementation Plan: Git workspace startup warning

**Branch**: `002-git-workspace-warning` | **Date**: 2026-10-20
**Spec**: [spec.md](spec.md)

## Summary

Add one advisory Git working-tree check at the shared experiment-command launch
boundary before Hydra composition. Keep stdout, workload behavior and source
identity unchanged. The user approved this design and Git-only master delivery.

## Technical Context

Python >=3.12.13,<3.14; existing uv environment, Hydra/hydra-zen, Loguru via the
observability adapter, pytest, Ruff, mypy, Vulture and import-linter. No dependency,
persistence or configuration changes. Git is optional; probe timeout is five seconds.

## Constitution Check

Typed outer adapter owns subprocess I/O and delegates warning rendering to the
observability adapter. Core/application remain effect-free. No SDK imports or
bootstrap effects are added. Existing import contracts cover runtime ownership,
classification, command independence and inward dependencies. Add a prohibited
runtime-to-ClearML import case to the actual-contract negative tests.

## Architecture

[architecture.json](architecture.json) indexes scope, boundaries and acceptance.
`adapters.runtime.git_workspace.warn_if_unversioned_launch(directory: Path) -> None`
owns the shell-free read-only Git probe, sanitized subprocess environment, timeout
and nonfatal warning. `entrypoints.hydra.common.launch` captures cwd and invokes
it inside console capture before `_launch`; this is once per command invocation,
not once per pipeline stage or sweep job. Package initializers and stdlib bootstrap
stay inert. Existing ClearML source identity is deliberately a separate concern.

## Project Structure and Ownership

Runtime change: new git_workspace adapter and the shared Hydra launch boundary.
Tests: workspace behavior and actual CLI subprocesses plus one architecture case.
Parent owns application, tests and native Spec Kit artifacts. A bounded delegate
owns the companion corp-skills update in an isolated worktree and must not delegate.
Documentation can proceed independently against the approved behavior; parent
verification precedes a fresh independent final review covering both diffs.

## Documentation and Acceptance

Update README in Russian, baseline commands, runtime isolation, and contract-index
navigation. Update corp-skills clearml-yolo usage/evaluation guidance and follow its
maintenance checks/release rules without touching its pre-existing dirty checkout.
Run focused tests, full routine pytest (including CPU DDP, excluding opt-in GPU),
Ruff, mypy, Vulture, lint-imports, architecture tests, docs checker and commit hooks.
Record actual results, review and complete diff reconciliation before architecture
acceptance. No training/GPU/upload success is inferred from command checks.

## Delivery

Use a task-scoped feat(cli) commit, integrate into master, run the existing release
helper and explicitly push/verify master plus the generated annotated tag. Preserve
local uv source overrides exactly around all commit attempts and release hooks.
No build distributions, GitHub Release objects or registry publication. Expected
version from v0.36.0 is v0.37.0; the release helper owns the final calculation.
