# Implementation Plan: Per-user queue settings and NFS coordination

## Summary

Amend the current queue configuration contract with per-user config discovery and
bounded NFS filesystem validation. Preserve the completed feature history in
[feature 034](../034-readable-shared-queue/spec.md).

## Technical Context

Python >=3.12.13,<3.14; uv/uv_build, existing Pydantic strict TOML boundary, pytest,
Ruff, strict mypy and import-linter. No dependency or persisted schema change.
Inspect current source rather than assuming historical planning is implemented.
The main checkout has unrelated local uv source overrides and an untracked user
report: preserve both and stage only task-owned changes. Confined edits do not
require an isolated checkout. Stop after native checked Git-tag release and push;
no deployment, package publication or skill installation.

## Constitution Check

Typed explicit interfaces, outer-adapter effects, unchanged dependency direction,
no new abstraction or ignore exception, strict validation, evidence preservation,
readable errors and truthful verification. No constitution amendment required.

## Project Structure

- `src/clearml_yolo/adapters/queue/settings.py`: config lookup and effective mount checks.
- `src/clearml_yolo/entrypoints/queue.py`: help wording; existing frozen composition.
- `tests/test_queue_settings.py`: settings boundary and existing recovery regressions.
- `tests/test_queue_commands.py`: CLI read-only setup failure/help behavior if needed.
- This directory: specification, plan, tasks, research, contract and evidence.

## Architecture

[Architecture record](architecture.json) is authoritative scope/check mapping.
Settings owns environment, TOML and mountinfo reads, returns frozen QueueSettings,
and performs no writes. Entrypoint composes effects only after settings succeed.
Core/application remain unaffected. Existing import and negative architecture tests
cover the two modules; no new contract is needed. Configuration schema, guardian
payload, lock protocol and fixed local bootstrap remain unchanged.

## Documentation and verification

Update README (Russian), queue/project/filesystem contracts, current-contract index,
TECH_DETAILS and canonical corp-skills clearml-yolo usage/evaluation references.
Run focused settings/CLI and existing process/guardian/recovery regressions, static
checks, separate import/architecture commands and docs/examples. Use simulated
mountinfo solely for validation acceptance. No real NFS mount is available; no
mount provisioning is within scope. Required review follows parent integration and
verification. Native hooks and release packaging checks remain applicable.

## Dependencies and useful parallel work

Parent owns specification, implementation and application docs. Independent NFS
research is read-only; companion usage source edits can proceed once this contract
is fixed. Fresh independent review/evaluation follows integrated checks. Release
application first, then companion guidance. Bounded agents cannot delegate.

## Complexity Tracking

No new modules, dependencies or architectural exceptions. Read-only composed-template
resolution replaces setup helpers because those helpers persist protected
`.specify/feature.json`; no installed workflow file is modified. No extension hooks
are registered. Clarification is unnecessary after the user's explicit scope correction.
