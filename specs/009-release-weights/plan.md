# Implementation Plan: Independently versioned weight bundles

**Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

## Summary and decisions

Reuse feature 007 preparation and its native loaders. Add a pinned packaged manifest and an adapter that seeds missing native assets from independent uncompressed tar archives before existing resolution. Use immutable `weights-2026-10-29` release identity; archive target size is 1,900,000,000 bytes. Compression is optional maintenance work, not required for native tensor storage. Prefer complete native files; archive errors warn and retain existing upstream fallback. No latest-release API or per-code-release asset upload occurs.

The alternative of LFS was superseded by the user's explicit tar-release choice. A single split byte stream would require every part for any recovery; independent tar archives allow bounded retrieval and verification. The manifest is packaged with code, making exact archive/member checksums the trust root. Changing a snapshot is an explicit manifest update.

## Technical Context and Constitution Check

Python >=3.12.13,<3.14, existing uv/uv_build, strict mypy, Ruff and pytest/import-linter. No new dependencies or upstream revisions. Core records are pure Pydantic values; file/network/SDK effects remain in adapters. Imports remain inert. No GPU or ClearML task is needed for packaging, transport or offline native-loader checks. Existing feature 007 and unrelated 008 changes must be preserved and distinguished at delivery. The explicit user exception permits weight assets only; ordinary software release remains Git-only.

## Architecture and shared interface

See [architecture.json](architecture.json) and [manifest contract](contracts/manifest.md).

- `core.weight_bundles`: immutable, strictly validated manifest/archive/asset/Hub metadata; no IO.
- `adapters.assets.bundles`: packaged manifest loading, native cache readiness, bounded GitHub/proxy archive download, locks, safe member copying, checksums and atomic placement. Existing resolver still owns normal final validation and upstream recovery.
- `adapters.assets.hub`: public mirror restoration helper reuses its native publication primitives, snapshot metadata and config validation; no metadata network request during restoration.
- `adapters.assets.preparation`: calls bundle seeding before native resolution; includes manifest identity in receipt fingerprint. Per-asset fallback and automatic/manual semantics remain.
- `scripts/package_weights.py`: explicit maintainer command discovers/resolves the eligible catalogue, emits independent archives and manifest, checks completeness and max size; never uploads or changes pinned manifest implicitly.

## Work ownership and dependencies

Parent owns workflow, packaging inputs/notices, actual downloads/publication, documentation, package-data pin, integration, architecture and release. Bounded implementation agent owns core.weight_bundles, adapters.assets.bundles, hub/preparation integration and focused tests. A second bounded agent may own scripts/package_weights.py and its tests after the manifest interface is established. Licence investigator is read-only. No child delegation. Final fresh review follows parent checks.

## Verification and Documentation

Focused tests cover archive/member corruption, path traversal/links/duplicates, retry/cache reuse, HF metadata/config restoration, proxy fallback, fingerprint updates and unchanged CLI/native behavior. Canonical `uv run --frozen --no-sync python scripts/verify.py` and `--docs` follow. New asset adapters are outside existing mutation selection; inspect selection before claiming applicability. Run real archive roundtrip from fresh native caches and offline family loaders, then verify actual GitHub bytes/metadata. Complete latest paired CY/queue checks and independent review before code release.

Update README in Russian, model-assets/project/current contracts, development release policy and portable usage source. Record licence origins and publication checks in dated evidence. Build/publish weights only on explicit maintenance invocation; code-release hooks remain unchanged. Preserve unrelated work and do not bypass hooks.

## Artifactory amendment

Existing GH/GHR routing remains unchanged. Add local protocol fixtures for release bundle retrieval through a prefixed Artifactory-style GHR root, VCS downloadCommit routing and authentication/redirect redaction. Add conditional setup hints at the manual CLI failure boundary; adapters retain transfer/error ownership. Documentation includes safe placeholder roots and endpoint-specific authentication guidance. User explicitly excludes live Artifactory verification.
