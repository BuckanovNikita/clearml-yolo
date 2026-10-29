# Implementation Plan: Local Russian reference

**Date**: 2026-10-29 | **Spec**: [spec.md](spec.md) | **Working branch**: master

## Summary

Implement the supplied plan as feature 008, preserving uncommitted 007 work. Capture
configuration compatibility before replacing anonymous command declarations. Keep all
training terminal-driven and all documentation assets packaged and usable offline.

## Technical Context

Python >=3.12.13,<3.14; development interpreter 3.12.13. Retain uv_build, Hydra/hydra-zen,
OmegaConf, Pydantic and the installed Ultralytics defaults adapter. Standard-library HTTP
and subprocess adapters serve vanilla JavaScript. Existing markdown-it-py renders Russian
Markdown during maintenance; browser automation is a development dependency only.
No runtime rendering dependency, Node build, queue schema or plugin API is introduced.

Preview has a 1 MiB request limit, at most 32 named YAML files, at most 100 expanded sweep
jobs and a 15-second worker deadline. Binding is exclusively 127.0.0.1. Fresh workers use
only built-in Hydra plugins and configuration groups; no user plugin/search path discovery.
Resolver values involving environment/custom functions remain strings. Read-only schema
validation never resolves datasets, augmentation files, model assets or application targets.

## Constitution Check

Design satisfies typed boundaries, effect ownership and existing registration ownership.
Named dataclasses describe permissive Hydra inputs; existing Pydantic models retain runtime
validation and locations. Documentation records use Pydantic. No inner module imports
serving/rendering code. Package initializers remain inert. Required verification and final
independent review are acceptance gates; no claims are inferred from mocked tests.

## Architecture

[architecture.json](architecture.json) records `impact: modules` and executable contracts.

- `entrypoints/hydra/declarations.py`: named documented command dataclasses, projected by
  `configs.py` into identical permissive Hydra nodes. Utility declarations/parser factories
  remain in an entrypoint helper. Existing public Pydantic fields acquire descriptions.
- `core/documentation.py`: typed catalog, tutorial and preview records; data only.
- `entrypoints/documentation/`: catalog assembly, completeness checks and isolated Hydra
  composition. Depends inward on declarations, existing validation and docs records.
- `adapters/documentation/`: packaged assets, sockets, worker subprocesses and maintenance
  rendering. Receives typed records/callbacks and a worker invocation supplied by entrypoint;
  cannot import entrypoints. Owns worker cleanup and local file access.
- `entrypoints/docs.py`: inert CLI/parser, explicit composition/serving root.

Reuse inward-layer, core/application-effect, initializer and exhaustive module contracts.
Add documentation isolation and serving/assembly ownership tests with injected violations.
Public command modules may share inert parsers but must not depend on the docs entrypoint.

## Project Structure and Interfaces

See [data-model.md](data-model.md) and [contracts/local-site.md](contracts/local-site.md).
Packaged assets live in `adapters/documentation/assets/`; tutorials include source Markdown,
generated HTML and an inventory. No network asset loading. Test files use `test_docs_*.py`;
browser acceptance is a separate suite under `browser_tests/`.

## Sequence and Ownership

Parent owns artifacts, architecture, integration, preview/catalog and final gates.
Declarations owner first captures compositions/parser behavior, then refactors declarations.
After typed records and catalog shape settle, independent owners implement browser assets
and Russian tutorials. Agents have exclusive paths and cannot delegate. Parent integrates,
verifies, then dispatches a fresh read-only review. Final tasks cover documentation, separate
source installation, native YOLO/non-YOLO artifacts and paired CY/queue delivery checks.

## Acceptance and Documentation

Run focused docs tests during development, then canonical `uv run --frozen --no-sync python
scripts/verify.py`, `scripts/verify.py --docs`, `cy-docs --check`, and separate Python browser
tests. Run native acceptance using the installed end-to-end skill; configuration previews
are not execution evidence. Follow paired release checks and Git-only release procedure
after passing review and architecture acceptance. Do not build release distributions.

Update Russian README navigation, `docs/current-contracts.md`, `docs/project-contracts.md`,
new `docs/local-documentation.md`, and affected portable corp-skills sources/evaluation cases.
Preserve independent corp-skills and queue changes. Existing 007 files remain excluded from
008 ownership except explicitly additive shared-file hunks. No installed workflow files or
`.specify/feature.json` are changed; use explicit read-only feature path resolution because
the installed mutating setup helpers would overwrite 007's active feature state.
