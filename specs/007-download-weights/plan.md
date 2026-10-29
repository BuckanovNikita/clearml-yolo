# Implementation Plan: Native weight preparation

**Branch**: `master` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

## Summary

Populate each consumer's native discovery cache, preserving configuration. Reuse
`model_catalogue`, `AssetSpec`, the existing resolver and backend discovery adapters.
Run a coordinated, fingerprinted preparation pass only inside actual pipeline
execution, plus an explicit retrying command.

## Technical Context

Python >=3.12.13,<3.14; uv/uv_build, strict mypy, Ruff, pytest, import-linter.
Existing Requests/FileLock handle URL assets; Hugging Face Hub owns native HF
cache downloads and metadata. Add its direct dependency because it becomes a direct
import, retaining the existing locked version and approved external sources.
Filesystem assets and receipts are persistent; receipts remain under CY_HOME.
No new runtime framework, scheduler, deployment or package-build release gate.

## Constitution Check

Inspected constitution, current contracts, actual resolver/loaders, SDK source and
existing changes. Core remains effect-free; adapters own SDK/storage/network;
entrypoints own invocation policy. Narrow native asset writes are an intentional
change to asset storage, not relaxation of project output containment. SDK settings
and custom configuration are preserved. Existing local uv source overrides remain
uncommitted. Canonical checks, documentation, native loaders, paired queue and fresh
review precede authorized Git-only release. No constitutional violation is needed.

## Architecture

See [architecture.json](architecture.json) for machine-validated boundaries.

- `core.assets`: immutable native cache/Hub requests and preparation results; pure
  catalogue filtering/fingerprint input uses the existing core model catalogue.
- `adapters.assets.resolver`: validation, URL retrieval and atomic legacy promotion;
  native roots are explicit discovery inputs. Managed DEIM remains contained.
- `adapters.assets.hub`: HF API endpoint/auth handling, metadata, native cache
  download/reuse, actual representation and revision provenance. No SDK globals change.
- `adapters.assets.storage`: narrow native asset leaf validation/publication boundary.
- Backend asset adapters discover SDK-native names/locations. A new YOLO asset module
  reads settings and native release identity without constructing a model.
- `adapters.assets.preparation`: eligible catalogue assembly, per-entry failures,
  deduplication, coordinated pass and atomic completed receipt. Interrupted passes
  remain unfinished. Discovery and effects occur only when explicitly invoked.
- `entrypoints.download_weights` reports/retries; `entrypoints.hydra.common` calls
  automatic preparation only for pipeline execution before model construction.
- Import contracts add exact SDK owners/peer bridges and entrypoint classification;
  existing graph and injected-negative tests cover inward boundaries and effects.

Shared interfaces are established before parallel implementation: `HubAsset`,
`AssetSpec.native_cache`, `AssetSpec.hub`, `PreparationFailure`, `PreparationResult`;
`prepare_catalogue(*, automatic: bool) -> PreparationResult`; `resolve_asset` keeps
its signature, routing Hub requests to the Hub adapter. A result includes fingerprint,
resolved assets, failures, effective locations and skipped status.

## Project Structure and Work Ownership

Native feature artifacts live here. Parent owns core types, resolver/storage/YOLO,
architecture integration and verification. A bounded agent owns Hub discovery and
resolution; another owns preparation/CLI/startup and its tests after shared types.
These writes are disjoint. Parent integrates before final checks and fresh review.

## Verification and Documentation

Focused tests first, then `uv run --frozen --no-sync python scripts/verify.py` and
`--docs`. Mutation selection is reviewed against actual changed code/dependencies.
Real downloads followed by network-disabled native loading cover YOLO names/aliases,
custom YAML/pretrained, inference and AMP lookup; other native backbones, RF-DETR
and DEIM source/weight execution reuse. Fresh process/cwd/worker probes supplement
unit failure, interruption, concurrency, proxy/auth and redaction checks.

Update README (Russian), model-assets/filesystem/project contracts and portable
`clearml-yolo` source SKILL.md plus usage/evaluation references in the companion
collection. Validate links, Markdown, examples, skill metadata/discovery. Record
current-source paired CY/queue normal resolution, metadata and integration checks.
No failed/unavailable gate is a success; release follows acceptance and review.
