# Implementation Plan: Read-only documentation checks

**Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

## Summary

Keep Markdown parsing, link/anchor validation and repository selection in one
maintenance module with a typed issue interface. It owns read-only filesystem
inspection and a fixed `git ls-files -z` subprocess; it imports no runtime modules.

## Technical Context

Python `>=3.12.13,<3.14`, existing uv/uv_build toolchain, pytest, Ruff and strict
mypy remain unchanged. Promote installed/locked markdown-it-py 4.2.0 to a direct
dev dependency. Keep the pre-existing local uv sources and upstream dependencies.
The command runs offline against local Markdown and linked assets.

## Constitution Check

Typed records, explicit effect ownership, scoped negative architecture tests and
direct dependency declaration satisfy the inspected constitution. No runtime API,
scientific algorithm or native execution behavior changes. The supplied user plan
authorizes the development dependency declaration. Hooks in extensions.yml are empty.
Use feature-local artifacts without modifying installed tooling, feature selector,
branch or templates, as required by the bounded parallel assignment.

## Architecture

[architecture.json](architecture.json) records the pre-implementation gate.
`scripts/check_docs.py` encapsulates repository document selection, Markdown parsing,
anchor identity and diagnostics. `check_documents(root, paths)` returns typed
findings; `main(argv)` owns exit status and output. Parser inputs are text; cached
target documents avoid repeated reads. Explicit paths and resolved local targets
must stay inside the repository. No writes, network or application imports are allowed.

`tests/test_check_docs.py` owns behavior and a static dependency allowlist with
negative imports, including deferred/type-only and dynamic-loading violations.
The independent architecture workstream owns runtime graph tests separately.

## Project Structure and Dependencies

Implementation: `scripts/check_docs.py`; tests: `tests/test_check_docs.py`;
metadata: the single dev dependency in `pyproject.toml` and its root lock metadata.
The sequential steps are specification → plan gate → tests/implementation → checks
→ documentation handoff → parent integration and fresh independent review.

## Documentation and Acceptance

Feature contract and quickstart live here; the parent owns integration into
development guidance and the contract index. The checker is internal maintenance
tooling and does not change portable application usage examples. Validate fixtures,
Ruff, strict mypy, Vulture, existing import/architecture tests, explicit feature
Markdown and `--all`. Existing all-document failures are findings for the parent,
not reasons to weaken validation. Architecture acceptance remains pending until
the parent integrates corrections and records fresh independent review.
