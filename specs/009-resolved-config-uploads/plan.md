# Implementation Plan: Resolved configuration uploads

> **Snapshot note:** This is the approved pre-implementation plan and retains its original
> upload terminology. The completed system attaches consumed files as Configuration Objects
> and publishes no configuration artifacts; see [current contracts](../../docs/current-contracts.md)
> and [dated verification](verification-2026-09-30.md).

**Branch**: `master` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Resolve active values in every uploaded configuration file using file-local values and the effective command context before credential sanitization. Preserve source files, comments and existing publication identities. The user approved this design and authorized implementation, commit, push and release after verification.

## Technical Context

- Python 3.12+, existing uv toolchain, strict mypy, Ruff, pytest and import-linter.
- Existing OmegaConf/Hydra provide resolution; ruamel.yaml retains YAML comments; ClearML remains behind existing adapters.
- Local original, unredacted execution and sanitized upload files remain distinct.
- No new CLI arguments, public configuration schemas or external dependency revisions.
- Scope includes YAML/JSON configuration-file attachment preparation, remote replay returns, and every execution command using the shared entrypoint.

## Constitution Check

**Before research: PASS. After design: PASS.**

- Typed callbacks keep the ClearML layer independent of Hydra/OmegaConf imports.
- Resolution belongs to the permitted apps layer; SDK publication remains in clearml_session.
- One-task ownership, credential protection, verified uploads, preserved local diagnostics and canonical Configuration Object identities remain intact.
- Source files, comments, runtime values and unrelated work are preserved.
- Verification includes behavioral tests, configured code gates, independent review and dated real ClearML file evidence.
- This requirement strengthens existing replay guarantees and requires no constitution amendment.

## Research and Design

[research.md](research.md) consolidates the bounded resolver, attachment and workflow audits. [data-model.md](data-model.md) defines the publication states; [configuration-files.md](contracts/configuration-files.md) defines behavior; [quickstart.md](quickstart.md) describes validation.

## Implementation

### Resolution boundary

Keep pure primitive resolution and add a provenance-aware CLI wrapper `resolve_config_file` returning the frozen adapter value `ResolvedConfigFile(values: Any, secrets: frozenset[str])`. The adapter may accept this result or plain values; `configuration_secrets` exposes existing secret discovery without model/Hydra imports.

Add `resolve_config_document(document: Any, command_config: DictConfig | Mapping[str, Any] | None = None) -> Any` in the apps layer. Compose a detached resolution root from current command configuration and whole-key file root overrides, resolve strictly, and project only original document fields. Preserve nested types and reject unresolved active values. Resolve interpolation only in active data, never in YAML comments. Do not pass artificial markers to registered resolvers. Preserve escaped literals and direct aliases, normalize tuple results for recursive strict validation, and reject resolver-emitted active interpolation. Read context after app-level replay/output derivation; task-internal native routing is outside this context contract.

### Invocation and attachments

Extend `invocation(..., *, config_resolver: Callable[[Any], Any] | None = None)` and retain its callback in invocation state. Shared CLI wiring supplies a closure evaluating the current composed config at attachment time after replay and routing mutations. Direct invocation attachments without an injected resolver reject interpolated inputs with guidance while accepting concrete files; clearml_session does not import Hydra or OmegaConf.

Resolve before discovering and redacting secrets; provenance metadata retains sensitive context/environment values even when aliases use innocuous keys. Retain comments using existing round-trip YAML handling. Produce separate unredacted execution copies beside the source to preserve relative-path semantics, with unique task-owned paths and cleanup, and sanitized upload copies when transformation is required, and preserve the no-interpolation original execution path even when the upload copy is sanitized. Handle initial files and ClearML-returned replay files using the same strict preparation contract. Propagate failure through existing invocation failure/finalization handling.

### Subagent ownership

- Resolver agent: apps resolution module, shared apps/common.py integration and new resolver unit tests.
- Attachment agent: clearml_session.py and tests/test_clearml_session.py.
- Documentation agent: this feature directory and .specify/feature.json; consolidate workflow artifacts and dated evidence only.
- Root integrator: shared dependency/import configuration, lockfile if required, integration tests, real verification and release operations.

Ownership is exclusive; shared interface changes require coordination. Tests precede implementation, root integrates combined results, independent review checks observable contracts, and converge records any remaining work.

## Delivery and Gates

Run specify → clarify → approved spec review → plan → approved plan review → tasks → analyze → implement → converge. Existing user approval supplies both review decisions; no redundant approval is required. Extensions currently register no hooks. Complete repository gates and real evidence, review/stage explicit task-owned paths, commit using Conventional Commits, push through the established remote, and verify the documented local semantic-release workflow and resulting release evidence. Never bypass hooks.

## Project Structure

Retain the existing src/clearml_yolo and tests layout. Feature artifacts live in specs/009-resolved-config-uploads; no scaffold or new runtime service is required.

## Complexity Tracking

No constitution deviations or additional infrastructure are required.
