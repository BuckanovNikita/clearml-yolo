# Feature Specification: Independently versioned model-weight releases

**Created**: 2026-10-29
**Status**: Released as CY 0.44.0 with weights-2026-10-29
**Input**: Download the supported catalogue, publish multiple tar archives in this repository, and make weight preparation use those releases without republishing weights for every code release.
**Baseline**: [stage zero](../000-baseline/spec.md); extends the existing [native preparation](../007-download-weights/spec.md).

## User Scenarios & Testing

### User Story 1 — Obtain the catalogue from this repository (P1)

Users run the existing weight-preparation command and receive verified weights in the native locations required by their installed libraries.

**Independent test**: Start with empty native caches, allow only the project's weight-release downloads, prepare the catalogue, then load native models offline.

**Acceptance**: Existing valid files are reused. Missing files come from the pinned weights release. Original source identities and native Hub configuration/revision discovery survive restoration. Corrupt or unsafe archives never publish files. Uncovered future asset identities and unavailable mirrors retain explicit upstream fallback and existing failure reporting.

### User Story 2 — Publish a reusable catalogue snapshot (P1)

Maintainers publish model assets once and reuse the same snapshot across code releases.

**Independent test**: Package the complete supported catalogue into independently readable tar files below the hosting limit; verify downloaded release files against the published manifest.

**Acceptance**: Release tags are independent of application versions; normal code-release hooks do not build or upload weights. Each weight retains upstream provenance, applicable licence and checksum. Publication checks completeness and refuses partial or oversized bundles.

## Requirements

- **FR-001**: Preserve the eligible catalogue, exclusions, explicit-path precedence and native-cache contract of feature 007.
- **FR-002**: Prefer valid native caches, then the project's pinned weights release, then existing upstream resolution with visible mirror failure diagnostics.
- **FR-003**: Verify archive and member byte sizes and SHA-256 values; reject path escapes, links, duplicate members and special files before native publication.
- **FR-004**: Restore HF weights, configuration, real snapshot commit and requested revision reference without upstream metadata requests.
- **FR-005**: Reuse archive downloads, coordinate concurrent readers/writers, publish atomically, preserve original files and make interruption retryable.
- **FR-006**: Publish all eligible weight identities and pinned DEIM source in multiple independent tar assets, each under 2 GiB, with manifest and upstream notices.
- **FR-007**: Pin a separately versioned weight snapshot in package data; include its identity in automatic-preparation fingerprints. Code releases do not republish assets.
- **FR-008**: Preserve configured release proxy routing and credential-safe diagnostics; no application credentials enter the archives.

## Success Criteria

- **SC-001**: Every eligible asset is packaged, retrievable from this repository and usable from native caches after network access is disabled.
- **SC-002**: Repeated preparation reuses valid files without asset transfer, while corrupt caches and interrupted attempts are recoverable.
- **SC-003**: Required behavior, architecture, documentation, paired compatibility and fresh independent review gates pass before code delivery.

## Assumptions and authority

The user explicitly authorized model-weight GitHub Release assets on 2026-10-29, overriding the general no-GitHub-Releases rule for this purpose only. No project distributions or registry publication are authorized. The latest clarification selects the existing supported catalogue, including its prior exclusions. Unrelated local documentation work is preserved. Upstream licence conditions remain attached to redistributed files.

## Artifactory verification amendment — 2026-10-29

The user additionally requires preserving GH/GHR Artifactory routing and clean environment setup instructions after failed downloads. They explicitly limited verification to logic/fixtures, with no live Artifactory check. `CH` in the request is treated as the existing `GH` variable; no new alias is introduced.

- **FR-009**: Preserve exact GHR repository-relative release paths and GH downloadCommit VCS requests, including proxy failures, authentication boundaries and credential-safe diagnostics. Verify with local fixtures, not a live Artifactory deployment.
- **FR-010**: Failed manual preparation prints concise conditional Artifactory setup and retry instructions. Documentation explains repository roots, GH/GHR roles, optional HF API endpoint/authentication, TLS/permissions failures and native-cache recovery without exposing credentials.
