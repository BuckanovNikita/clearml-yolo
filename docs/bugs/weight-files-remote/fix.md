# Bug fix: release-only weight preparation

- Slug: weight-files-remote (from assessment)
- Fixed: 2026-10-30
- Assessment: [assessment.md](assessment.md)
- Status: applied and verified; final delivery metadata recorded in [test.md](test.md)

## Changes

Bulk preparation first resolves validated native caches with explicit local-only
semantics, then seeds from the pinned project release and verifies locally again.
This includes Hub config/snapshot discovery and existing DEIM source trees.
Missing/failed/mismatched archives cannot trigger original-host downloads. Standalone
resolver defaults remain unchanged. The receipt fingerprint includes the new policy.

Archive errors retain safe release tag, archive, route and HTTP-status/type details;
transport secrets are excluded. ResNet matching accepts an unchanged URL/checksum
across Torchvision versions while preserving other identity/revision checks.
Archive streaming budgets default to 1800 seconds, configurable through positive
finite CY_WEIGHTS_DOWNLOAD_TIMEOUT; locks have a separate finite wait. This is checked
between chunks, not a hard wall-clock deadline. Ordinary
selected-model transfers retain their existing 300-second budget.

GHR remains a Files remote root of GitHub. GH remains a separate VCS remote of the
same upstream. No alternate URL layout was invented. CLI failure guidance now shows
only relevant release recovery; repository and portable instructions distinguish
bulk from standalone resolution. The packaged pin selects weights-2026-10-30.

## Initial checks

The implementation agent reproduced twelve failing regression cases before changing
runtime code. Its broad local asset suite passed 168 tests; final CLI fixtures passed
11 and final bundle tests passed 32. Ruff, formatting and scoped strict mypy passed.
These focused results precede parent canonical verification and fresh review.
No live Artifactory checks were run. Independent artifact review rehashed every tar
and all 59 weight/source/config members, checked full catalogue coverage, safe members,
notices and checksums, and approved artifact publication readiness.

## Deviations and user steering

The initial assessment retained bulk upstream recovery. The user explicitly clarified
that bulk preparation must use this repository's release artifacts; the assessment
and runtime were changed before acceptance. The user also requested a new visible
release. Inspection found yesterday's complete weights release existed publicly but
old code release v0.14.1 was still GitHub Latest. The newly authorized
[weights snapshot](https://github.com/BuckanovNikita/clearml-yolo/releases/tag/weights-2026-10-30)
is now published as Latest; its original model payload bytes remain unchanged.

[Architecture record](architecture.json) includes the two existing resolver modules
needed for a local-only boundary. No dependency or approved external source changed.
