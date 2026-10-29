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

## Completed Git-only delivery

All required implementation, architecture, documentation, browser, installed-source,
native and paired gates are accepted. Fresh `release_final_review` returned ship;
its sole evidence-link correction was applied and checked. The stable integrated
canonical receipt covers 4,373 passing tests and all static/import checks. No hook
was bypassed. The first commit attempt performed ordinary whitespace/changelog
maintenance; those exact generated changes were inspected, staged and rechecked.

The feature commit is `60091649dd71087e5dac2a9a712098eaa5be5de6`. The native
post-commit hook created release commit `dbde23565a9938cfb7556819ab6a5beee24d5423`
and annotated tag **v0.43.0**, object
`877480264094557b82ae1166b1ebbbecbbd27011`. That release commit changes only the
generated changelog and root project/lock version. Dependency sources, revisions
and non-root lock metadata are unchanged; no local uv source override was committed.
The committed project metadata exactly matches the separately installed 0.43.0
proposal. The verifier accepted the validated release metadata transition and
retained both verified source fingerprints.

The [final committed pair](release-pair.md#final-committed-pair-refresh) passed
normal installation, exact metadata/origins, all 518 ordinary queue tests and its
static/import/isolation checks. Installed documentation coverage and catalog version
checks passed for 0.43.0. Those tests used a separate immutable environment;
the canonical environment remained unchanged through commit and release hooks.

CY master and `v0.43.0` were pushed atomically. Remote readback matched release
commit `dbde23565a9938cfb7556819ab6a5beee24d5423` and the annotated/peeled tag
identities above. This final evidence-only closure follows that implementation tag;
it does not change the tagged runtime or package metadata.

Queue 0.1.4's compatibility commit is
`114b97272ab5bb406a90c146ea62d8fdd19d75b1`. Its evidence-only closure is
`4e18ec622121c228474dd454b0b46d4af902cf92`; queue main was pushed and that remote
identity verified. Its functional/package files are unchanged from the final pair.
No queue version tag was invented because its workflow publishes source commits.

Portable usage guidance was published as collection **v0.6.2** at
`6d8f8be4eb83bcd5ac05eae7386451c6b2dd3667`, annotated tag object
`d3399c68df5922d5bac356deb91ddfb7390c2d13`. The eight-path update retains published
007 guidance and adds the reviewed local-documentation instructions/evaluation cases.
Collection main/tag were pushed atomically and remote readback matched. The legacy
corp-skills remote redirects to the collection's current custom-opencode-skills
location. Original shared working changes and installed skill copies were preserved.

The original shared CY checkout was not advanced or rewritten; delivery used the
isolated checkout of current published history. Task-owned verification processes
are stopped, temporary resources are cleaned after the closing checks, and private
logs/source manifests are retained for audit. The separately saved local uv source
section is restored only as an unstaged local override after hooks finish.
No GitHub Release objects, release assets, registry packages or deployment were
created. Optional physical queue/NCCL and other previously stated native capability
limits remain explicit in their evidence; they are not claimed as passing checks.
