# Feature Specification: Extract queue and portable training

**Created**: 2026-10-23
**Status**: Approved user intent; implementation pending
**Input**: Extract cy-queue and support portable training execution.

## User Scenarios & Testing

### US1 — Independent queue installation (P1)

Operators install CY from source, then the separate CY-specific queue into the same environment. They can submit pipeline or standalone training without losing history, lock coordination, ownership checks or GPU handoff.

Acceptance: default submission launches pipeline; `--command train` launches training. Existing records remain readable. A changed installation rejects pending snapshots with instructions to resubmit. Direct CY works without queue imports, configuration or reservations.

### US2 — Agent replay (P1)

An externally managed ClearML Agent executes the recorded entrypoint without the original CLI arguments and restores inputs and backend before validation/runtime startup.

Acceptance: one detached remote snapshot restores canonical settings and scientific General precedence; execution joins the same task and preserves script metadata, failure reporting and publication. An absent canonical configuration allows complete explicit inputs; malformed or empty canonical configuration fails. Agent CUDA visibility and logical devices remain authoritative.

### US3 — Automatic and offline model assets (P1)

Non-YOLO users request pretrained initialization without manually discovering assets; restricted networks can use configured proxies or offline placement.

Acceptance: DEIMv2, RF-DETR and every Faster R-CNN preset use matching assets. Explicit local inputs are authoritative and missing inputs fail. Automatic resolution occurs only at execution. Valid caches precede proxy and upstream; unset/empty proxy values use upstream. Failure lists every known missing asset with full original URL, exact absolute destination, override and access requirement. Manual placement works without online receipts.

### Edge Cases

Corrupt/interrupted downloads, redirects, authentication failure, timeouts, concurrent consumers, unsafe archives, modified extracted source, missing explicit files, null selectors, absent versus empty replay, installation changes, cancelled jobs and uncertain process cleanup retain explicit failure semantics.

## Requirements

- FR-001: Separate `cy-queue` distribution and `cy_queue` namespace depend on a compatible CY; reverse imports are forbidden. Move queue policy, records, storage, GPU inventory/probe, guardians, CLI/TUI, Hydra queue composition and tests; move queue-only Textual/NVML dependencies.
- FR-002: Keep shared process supervision/lifecycle in CY and document/test consumed interfaces. Preserve locations, coordination namespaces, locks, history, record compatibility, owner checks, cancellation/recovery and acknowledged handoff. Installation identity includes both packages.
- FR-003: Support `cy-queue submit --command {pipeline,train}` with pipeline default and existing CY entrypoints.
- FR-004: Restore one detached Agent snapshot before required-input validation/backend choice; join the same task through invocation lifecycle, preserving replay precedence and metadata.
- FR-005: Canonical replay retains original selectors including null defaults; resolved asset paths, URLs and hashes are separate provenance. No queue dependency for Agent execution.
- FR-006: Typed asset descriptions and an outer resolver own HTTP/cache/locks/extraction. Native backend adapters retain checkpoint loading and transformations. No YOLO changes or dependency auto-installation.
- FR-007: Resolve local/cache, then configured proxy, then original URL. GHR preserves owner/repository/releases/download/tag/filename; GH derives Artifactory downloadCommit for the approved pinned DEIM source. Non-GitHub endpoints stay unchanged.
- FR-008: Preserve explicit checkout validation; managed DEIM code/configuration is checked against a packaged approved-revision manifest and unsafe archive entries are rejected.
- FR-009: Managed weights use CY_HOME/.cache/clearml-yolo/models/<backend>/<preset>/<asset-id>/<filename>; DEIM source uses CY_HOME/.cache/clearml-yolo/sources/DEIMv2/<revision>.tar.gz and adjacent revision directory. Identity uses canonical source, revision and checksum; valid library caches may be reused without global SDK changes.
- FR-010: Downloads use bounded requests/retries, per-asset locks, temporary files, atomic publication, checksum/content validation, standard TLS/authentication and credential-redacted errors. Offline manual placement needs no receipt.
- FR-011: Document source-first installation and coordinated offline upgrade with stopped workers, preserved records and resubmission of pending work after environment changes.

## Success Criteria

- SC-001: Existing queue behavior and standalone training pass compatibility and installation tests.
- SC-002: Bare Agent entrypoints select the correct backend, reuse the task and complete publication.
- SC-003: Every affected preset resolves and loads its native assets; each family completes short native training.
- SC-004: Offline users can recover from actionable errors by placing named files and rerunning.
- SC-005: Both repositories pass their tests, lint, strict typing, import contracts (including negative cases), documentation checks and independent review.

## Assumptions and exclusions

The approved DEIM revision is 1d2ca42171570c713e78fc6a766ec5104b7f4724 unless an official compatible distribution is verified. Dependency installation remains externally managed and approved upstream revisions remain unchanged. No new ClearML submission interface, Artifactory uploads, deployment, registry publication or remote creation. Live Artifactory connectivity is unavailable and must remain explicitly unverified. CY follows its Git-only release workflow after acceptance; cy-queue ends with a verified Conventional Commit.
