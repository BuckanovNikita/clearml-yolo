# Feature Specification: Download weights into native discovery locations

**Feature Branch**: `master` (native release workflow)

**Created**: 2026-10-29

**Status**: Implemented and verified; release in progress

**Input**: Implement the supplied download-weights plan, retaining the current
[baseline](../000-baseline/spec.md) and existing configuration semantics.

## User Scenarios & Testing

### User Story 1 - Prepare models for offline use (Priority: P1)

A user runs `cy-download-weights` once and can then use supported named models
through their normal loaders without network access or configuration rewrites.

**Independent Test**: Prepare actual weights, disable network, and load/infer from
fresh processes using ordinary names, configured caches and custom architectures.

**Acceptance Scenarios**:

1. A successful command reports native destinations and exits zero; missing required
   assets are reported together and produce a nonzero exit.
2. Existing validated native or compatible legacy CY files are reused or promoted
   without another download; shared backbones use one native cache entry.
3. Configured mirrors are tried before upstream; credentials never appear in reports.

### User Story 2 - Prepare automatically on first execution (Priority: P1)

Actual `cy` execution attempts the eligible catalogue before model construction.
Help, configuration inspection, queue submission and standalone stages do not.

**Independent Test**: Observe attempts across repeated, interrupted, concurrent and
partially failed runs and changed catalogue/cache-location combinations.

**Acceptance Scenarios**:

1. A completed attempt, including partial failures, suppresses another automatic pass
   for the same catalogue and destinations. Manual preparation retries unresolved assets.
2. Catalogue additions, changed identities or native destinations trigger another pass.
3. Interruptions remain unfinished; concurrent starts coordinate. Automatic failures
   warn and continue, leaving selected-model failures to existing handling.

### User Story 3 - Preserve custom configuration (Priority: P1)

Users retain Hydra trees, command overrides, local checkpoint paths, resume settings,
architecture YAML and boolean or filename pretrained values.

**Independent Test**: Compose and execute custom YAML plus explicitly named pretrained
weights with network blocked, including worker execution and auxiliary AMP lookup.

**Acceptance Scenarios**:

1. No architecture is replaced or matched to weights by its basename.
2. Native names and legacy aliases resolve from the library's configured cache.
3. Relative paths use the consuming process's working directory. Native settings and
   environment selectors remain unchanged; non-null `ultralytics.cfg` stays unsupported.

### Edge Cases

Corrupt files, permission errors, invalid caches, concurrent publication, interrupted
passes, unavailable mirrors, authentication failure, and different working directories
must retain explicit failure/retry behavior and atomic published files.

## Requirements

### Functional Requirements

- **FR-001**: Prepare the maintained YOLO detection catalogue, RF-DETR, eligible
  Faster R-CNN/FCOS backbones and DEIMv2 small/medium with pinned source.
- **FR-002**: Exclude DEIMv2 large/xlarge and `dinov3_small` from bulk preparation,
  preserving their explicitly selected execution behavior.
- **FR-003**: Populate native Ultralytics, Torchvision, timm/HF and RF-DETR caches;
  retain managed DEIM locations and automatically supply its execution configuration.
- **FR-004**: Validate, lock and atomically publish assets; reuse compatible caches
  without redownload and preserve source/revision provenance.
- **FR-005**: Provide explicit command reports/retries and nonzero incomplete status.
- **FR-006**: Implement once-per-catalogue/location automatic execution policy with
  partial-failure receipts, unfinished interruption and coordinated concurrent starts.
- **FR-007**: Preserve custom configuration and native discovery, including AMP weights.
- **FR-008**: Retain GH/GHR proxies and support HF endpoint/token and Artifactory HF
  API endpoints, with endpoint-scoped credentials and redacted errors.
- **FR-009**: Permit only native asset storage outside CY_HOME; keep project outputs
  and preparation state contained. Do not rewrite SDK settings or cache selectors.

### Key Entities

- Asset: native filename, source/revision, validation identity and destination.
- Catalogue: eligible model selections and required unique assets.
- Preparation result: successful assets, failures, catalogue/location fingerprint.
- Attempt record: completed fingerprint and effective locations, including failures.

## Success Criteria

- **SC-001**: Real prepared assets are discovered offline by all affected native loaders.
- **SC-002**: Repeated unchanged automatic runs perform no second bulk pass; manual
  retries recover missing assets without redownloading valid assets.
- **SC-003**: Configuration-preservation and failure/concurrency scenarios pass their
  executable checks, including fresh processes and changed working directories.
- **SC-004**: Application, documentation, architecture, applicable mutation and paired
  CY/queue gates pass; fresh independent review accepts the integrated change.

## Assumptions

The supplied plan is the approved design. No dependency-source changes, SDK settings
rewrites, deployment, package publication or GitHub Release objects are authorized.
Completion includes native verification, portable skill updates and Git-only release.
