# Delivery boundary — 2026-10-29

Feature 008 implementation is available in the working source, with `cy-docs`
installed in the prepared development environment. Verification and review outcomes
are recorded in [verification](verification.md), [review](review.md),
[installation](installation.md), [native execution](native.md) and
[paired checks](paired.md). A passing implementation check is not a released version.

## Preserved prerequisite

CY remains on `master`, baseline `0037059dcf8a8ed16582f256b98036480cabd842`, version
`0.41.0`. The existing, uncommitted `007-download-weights` feature supplies the
weight-preparation interface documented by 008. Its own tasks T016–T019 remain
open, including independent acceptance and delivery. This task does not silently
accept, stage or publish that other feature.

Read-only checks of the actual repository gates confirmed:

- `require_index_view` rejects the preserved 007 `core/assets.py` because its
  checked working contents differ from the index. Staging only 008 cannot satisfy
  the full-source hook while that prerequisite remains outside the commit.
- `require_clean` defers release while tracked source/index changes remain.

The user was offered the choice to retain verified 008 for integration or expand
scope to complete 007 acceptance before releasing both. No expansion is inferred
from elapsed time or from standing authorization to release task-owned changes.
Until that prerequisite is settled, no CY commit, version bump, tag or push is
performed. No hooks are bypassed, and no unrelated files are stashed or reset.

The current source pair (CY 0.41.0 / queue 0.1.3) passed normal resolution,
matching installed/source metadata and 518 queue tests. The intended final release
versions cannot be finalized independently of the prerequisite release sequence;
their required paired check remains an explicit delivery gap.

## Companion guidance

The isolated portable skill addition was reviewed, verified and committed as
corp-skills `80ec2a037e008fafe401e39e9f1b507005cb9a0d`. Its seven-path commit excludes
earlier augmentation/training changes; all original working bytes were preserved.
The changelog and guidance explicitly mark the CY interface unreleased.

No collection version, tag, push or installed-copy change was made. The collection's
separate release workflow requires a clean tree and consistent version/changelog/tag;
preserved independent working changes remain there. No GitHub Release objects,
release assets or registry packages were created in either repository.

## Authorized release resumption

The user subsequently requested “commit push make new release”. Fetching the
latest source refs established that feature 007 had already completed its own
acceptance and Git-only release in an isolated checkout: remote master
`f8eb8a3c198806c08c0a41161aa4e8034dec0273`, release commit
`335370d28cc2f066bc3ccec897ecb38c63efe9dc`, annotated `v0.42.0`.
Its final native-cache diagnostic fixes and acceptance records supersede the
older preserved 007 working snapshot described above.

Feature 008 was integrated into a fresh isolated checkout of that remote master.
The captured initial 007 tracked patch reconstructed the pre-008 baseline; a
three-way merge applied only the 008 delta. All 18 modified paths and 65 added
paths were reconciled without conflicts. Released 007 runtime/tests/evidence
were retained, including its HF credential-redaction and progress fixes. The
only 007 command change is the reviewed inert parser-factory refactor. Original
shared CY and portable-skill working changes remain intact.

The next feature release is therefore CY **0.43.0**. Queue **0.1.4** is the proposed
compatible companion, with a bounded CY requirement `>=0.38,<0.44`, subject to
normal-resolution and complete ordinary queue checks. Fresh integrated canonical,
browser, installed-source, paired and independent-review evidence is required
before commit/tag/push. This paragraph records authorization and the selected
release sequence, not successful delivery.

The remaining work already maps to T023; convergence inspection found no new
implementation requirement to append. Prior completed tasks and historical
verification remain unchanged. The portable guidance is being reconciled with
its separately published 0.6.1 collection baseline in another isolated checkout.
