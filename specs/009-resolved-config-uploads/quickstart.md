# Validation: Resolved configuration uploads

## Prerequisites

Use the initialized submodules and current uv environment. Read the global clearml-yolo-environment skill and project running-end-to-end-tests skill before a real shared-stand run. Obtain changing endpoints, credentials and capacity from maintained environment sources; never put them here.

## Automated validation

Run resolver tests and ClearML session tests, including nested local/context references, strict resolver failures, null/type preservation, file root precedence, original-field projection, unchanged comments/source bytes, credential-bearing environment references and initial/replayed attachment copies. Integration tests must inspect the actual path passed to the fake publication boundary and prove the effective context is read after routing/replay changes.

Run `uv run pytest`, `uv run ruff check .`, `uv run mypy .`, and `uv run lint-imports`; complete applicable pre-commit checks before committing. These commands prove the mocked contract and repository gates, not real uploads.

## Real ClearML evidence

Use explicitly tagged task-owned validation with representative configuration-file references and download the uploaded configuration files. Parse active values and verify zero unresolved interpolation, expected effective command values, preserved comments and absent credentials. Follow the project end-to-end skill for any native execution prerequisites; preserve shared infrastructure and clean only task-owned resources.

Record commands, task identifiers, file evidence, results and limitations in a dated verification document. Do not record credentials. Run converge after implementation and finish any appended tasks before final review and release.

## Release validation

After passing checks and inspecting the task-owned diff, root stages explicit paths, creates the authorized Conventional Commit, verifies the documented local semantic-release hooks, pushes through the existing remote, and records commit/tag/release evidence. Read current release commands from README.md and scripts/local_release.py rather than duplicating changing operations here.
