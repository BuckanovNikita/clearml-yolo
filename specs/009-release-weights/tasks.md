# Tasks: Independently versioned weights

## Setup and contracts

- [x] T001 Inspect current preparation, native cache evidence, existing changes and upstream redistribution terms; record specs/009-release-weights/research.md.
- [x] T002 Write spec, manifest contract and architecture; validate specs/009-release-weights/architecture.json before implementation.
- [x] T003 Analyze requirement coverage and constitution compatibility; no unresolved blocking design finding.

## User Story 1 — Prepare from project releases

- [x] T004 [US1] Add manifest models, safe release seeding and corruption/traversal/cache tests in core/weight_bundles.py, adapters/assets/bundles.py and tests/test_weight_bundles.py.
- [x] T005 [US1] Restore native Hub snapshots/config without upstream access in adapters/assets/hub.py; integrate seeding/fingerprint into preparation.py and focused tests.

## User Story 2 — Publish reusable catalogue

- [x] T006 [P] [US2] Implement scripts/package_weights.py and tests/test_package_weights.py against the shared manifest contract; ensure complete inventory, deterministic independent archives below limit and separate DEIM non-commercial archive.
- [x] T007 [US2] Revalidate/retrieve all real native assets, assemble upstream notices, package all eligible files and pin adapters/assets/weights-manifest.json.
- [x] T008 [US2] Exercise actual archives into fresh caches, native offline loaders and failure fixtures; record specs/009-release-weights/verification.md.

## Documentation and delivery

- [x] T009 Update README.md, docs/model-assets.md, project/current contracts and release policy for dedicated weight releases; update portable usage source.
- [x] T010 Run canonical application/docs checks, assess mutation scope, verify latest paired sources/proposed versions and reconcile task-owned diff.
- [x] T011 Obtain fresh independent review of final integrated change/evidence and validate architecture acceptance.
- [x] T012 Publish the authorized weights release/assets; download/verify remote results and record immutable links/checksums.
- [ ] T013 Complete authorized task-scoped commit and native code release, verify branch/tag refs and preserve unrelated work/local overrides.

## Dependencies and coverage

T001–T003 precede implementation. T004–T005 and T006 may run in parallel using the manifest contract and disjoint ownership. T007 follows packaging implementation; T008 follows runtime integration and real archives. T009 may proceed using stable interfaces. T010 precedes fresh T011; publication T012 and final delivery T013 require their applicable verification. Final remote roundtrip updates evidence before closure.

FR-001/002/004/005/007/008 map to T004–T005,T008. FR-003 maps to T004,T006,T008. FR-006 maps to T006–T008,T012. SC-001/002 map to T007,T008,T012; SC-003 to T009–T011,T013. No requirement is uncovered. No framework, dependency or workflow-tool migration is needed. Native source provenance remains original upstream identity. Bounded agents must not delegate further.

## Requested Artifactory verification and recovery guidance

- [x] T014 [US1] Verify GH/GHR Artifactory-style HTTP routing, fallback and credential handling with tests/test_artifactory_assets.py; add conditional CLI setup/retry hints and failure tests. Covers FR-009/010.
- [x] T015 Update README, model-assets, packaged operations tutorial and portable usage/failure evaluation with environment examples and fixture-only verification limits. Covers FR-010.

T014/T015 precede final T010/T011 acceptance; no live Artifactory calls are authorized by this amendment.

- [x] T016 Close the inspected maintainer-script boundary gap with an exact import contract and negative tests in tests/test_tooling_boundaries.py; include it in final canonical and architecture review.
