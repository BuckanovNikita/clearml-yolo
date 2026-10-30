# Verification: weight Files remote recovery — 2026-10-30

## Scope and preservation

Implementation uses an isolated latest-source checkout at CY 2c494c6 (0.44.0).
The original dirty workspace and all pre-existing work are preserved. Verified code
release is 0.44.1; queue remains at latest 397753c (0.1.5). Approved digital-metrics
and report-generator sources and dependency versions remain unchanged. No live
Artifactory, GPU, training or ClearML publication was performed.

## Reproduced regressions and focused checks

Twelve new regressions failed before implementation, covering archive time limits,
ResNet version identity, release failures/missing pins and forbidden bulk upstream
fallback. After integration the bounded implementation agent executed:

```bash
uv run --frozen --no-sync python -m pytest -q tests/test_weight_bundles.py tests/test_artifactory_assets.py tests/test_weight_preparation.py tests/test_hub_weight_bundles.py tests/test_hub_assets.py tests/test_model_assets.py tests/test_model_assets_loading.py tests/test_native_assets.py
```

Result: 168 passed. Final CLI and bundle amendments separately passed 11 and 32 tests;
scoped strict mypy passed 15 files. Ruff/format and whitespace checks passed. These
checks use local fixtures, including loopback Files/VCS HTTP, original-host denial,
credential redaction, cache-only Hub metadata and manual retry. They do not verify
deployment permissions, certificates or connectivity.

## Artifact publication review

A fresh independent reviewer rehashed all four archives and all 59 model/source/config
members, verified 56 catalogue identities, the runtime/publication manifest match,
SHA256SUMS, safe unique regular members, archive sizes below 2 GiB and 15 matching
licence/provenance notices per tar. Verdict: ship for artifact readiness. New and old
manifests differ only in release tag; model payloads are unchanged. Their prior native
loader evidence is retained in [the original verification](../../../specs/009-release-weights/verification.md).

Remote inspection found weights-2026-10-29 public with six uploaded assets, while
v0.14.1 remained GitHub Latest. The user explicitly authorized a new visible snapshot.
An annotated weights-2026-10-30 tag points to the inspected catalogue lineage at
2c494c6; all six assets were uploaded to GitHub release 428749753 and independently matched
the local sizes and server SHA-256 digests. The release is public, non-prerelease and
confirmed by the releases/latest API as weights-2026-10-30. Publication notes preserve
original terms, AGPL source directions and DEIM restrictions. Hosted restoration is
running separately; upload completion alone is not counted as restoration evidence.

## Paired source verification

The latest queue remote was fetched and remains 397753c. An isolated proposed CY
0.44.1 snapshot contains the final runtime, tests, scripts and weights pin, with only
root version metadata normalized. Normal dependency resolution installed both source
packages and the approved externals without bypassing dependencies. Source/installed
versions, bounded requirement, editable origins and imports agreed before and after
checks; pip check passed for 285 packages. Queue passed 518 tests, with seven physical
opt-in cases deselected and 19 warnings in 125.15 seconds. Ruff, formatting, strict
mypy (69 files), two import contracts and CLI help passed. Installation used copy mode
to preserve the canonical verification environment's input identity. Actual released
metadata will be refreshed before push; no queue source change is required.

## Documentation and portable usage

Repository guides and rendered Russian operations tutorial reflect release-only bulk
preparation, GHR Files versus GH VCS routes, timeout scope and recovery. Initial full
Markdown/link validation passed. Portable collection candidate 0.6.4 passed discovery,
69-file Markdown lint, 68-file link validation, strict metadata and duplicate-key
negative control, 19 Bash syntax checks, source/example assertions and no-impact
architecture validation. A fresh read-only native-agent evaluation accepted both new
failure and unchanged-ResNet cases, correctly retained pending-release qualifications
and found no blocking guidance issue. This is not live OpenCode/DeepSeek evaluation.

## Remaining acceptance

At this checkpoint the canonical application suite, hosted new-release restoration,
final independent code/architecture review and actual release metadata checks were
pending. Later sections record their outcomes; no pending check is counted as passed.

## Canonical application acceptance

The parent ran `uv run --frozen --no-sync python scripts/verify.py` on the final
integrated runtime/tests. Ruff, strict mypy, Vulture and import-linter passed; pytest
passed 4,460 tests with 30 skips, 81 deselections and 182 warnings in 1,022.30 seconds.
The unchanged verifier issued its normal application success receipt after checking
stable source/dependency inputs. No hook or verification bypass was used. Changes
are outside the maintained mutation selection; selected core modules/tests and
dependency versions are unchanged, so no mutation run is claimed.

## Hosted restoration harness correction

The first actual public-release run restored all 56 assets with zero application
failures, exactly four archive requests, matching archive/member hashes and unchanged
SDK settings. Its final harness assertion incorrectly combined two blocked
Ultralytics import-time DNS connectivity probes (one.one.one.one and dns.google)
with download traffic. Inspection located those probes in the installed SDK. No
request reached either host, and no original model host was requested. The harness
now records those denied import probes separately, resets accounting before the
manual command, and repeats the entire hosted test in fresh caches. Runtime code
was not changed; this second run remains pending until its normal completion.

## Final hosted acceptance and timeout contract review

The corrected fresh-cache hosted test completed normally in 208.93 seconds:
56 assets, zero failures, exactly four project archive GETs, all archive/member hashes
matching the pin, automatic follow-up skipped without another transfer, and native
SDK settings unchanged. Preparation made zero original-host or other denied-host
attempts. Two SDK import-time DNS connectivity probes were denied and recorded
separately before command execution. Only GitHub and its release CDN hosts carried
downloads. No Artifactory endpoint was contacted.

The first preferred final reviewer could not start because of model capacity. A fresh
Terra reviewer then found the advertised total timeout stronger than Requests actually
enforces. Parent accepted the finding and explicitly revised the contract to an
elapsed streaming budget checked between chunks, separate connection/read-inactivity
timeouts, and an independent finite archive lock wait. The user did not request a hard
wall-clock deadline; no such guarantee is now claimed. Runtime/tests remain identical
to the canonical passing inputs; only documentation was clarified. Final review of
that revision and ordinary release metadata remain pending.

## Final package-data verification gate

The timeout clarification also changed the packaged operations Markdown/HTML. The
repository verifier governs those resource bytes, so the parent repeats the canonical
check on the final package data even though Python runtime/tests are unchanged. The
previous passing result remains recorded above; it is not used to waive this gate.
No verifier policy or receipt was changed or fabricated.

## Independent review and original-workspace reconciliation

The fresh Terra reviewer returned ship for the corrected source and architecture,
then rechecked the precise timeout wording and portable guidance. No unresolved
source finding remains. Delivery stays conditional on the final canonical package
input gate, documentation/architecture acceptance and actual release-pair metadata.

Task-owned changes were also merged into the original workspace from preserved
base/original/updated inputs. Existing branch, version and local dependency overrides
remain untouched. Conflicting failure-report and tutorial hunks were reviewed; only
the merged operations tutorial was rendered. An initial private merge helper consumed
conflict-tail text incorrectly; the original files were reconstructed from the saved
inputs before acceptance, and focused verification was repeated. The final original
workspace check passed 92 tests in 6.40 seconds. This does not replace release-checkout
canonical acceptance or validate unrelated pending work in the original checkout.

## Intermittent interpreter crash during the final gate

The first repeat on the final packaged tutorial stopped with native SIGILL at
`test_concurrent_download_and_offline_placement`, during garbage collection in a
Requests/urllib3 worker while the other workers waited for the asset lock. There was
no Python assertion failure. The failed canonical log is retained privately as
`application-028cb92c466a41d4861c09d96abdb58f-4.log`. Its test/stack pattern resembles
the [2026-10-23 interpreter-crash record](../../../specs/003-portable-training/evidence/2026-10-23-interpreter-crash.md);
the native cause remains unconfirmed, and this similarity does not establish that
the crash is unrelated to the current work.

The exact test passed separately with faulthandler enabled (one passed in 1.87 seconds).
The parent then started one unchanged full canonical retry with a process-local
256 MiB core-file cap. The default core limit was zero; no global kernel setting,
dependency, test selection, hook or application input was changed. No native debugger
was available. The isolated test cannot rule out suite-order effects or replace the
full gate. A fresh independent reviewer accepted a clean full retry with its normal
stable-input receipt as sufficient check evidence, conditional on retaining this
unresolved crash record and the separate documentation, architecture and pair gates.
A successful retry would not prove the crash fixed.

## Final canonical acceptance

The unchanged full retry completed normally: Ruff, strict mypy, Vulture and
import-linter passed, followed by 4,460 passed tests, 30 skips, 81 deselections and
182 warnings in 1,004.57 seconds. The unmodified verifier issued its normal stable-input
success receipt (`application-af23c323163b4585a740330de8275cd6-*` logs). No further native
crash was observed. The intermittent native SIGILL above remains unresolved; this passing
run is not presented as a crash fix. Both remotes were fetched again before release;
CY and queue still matched the source identities recorded above.

The task-owned diff includes five asset-adapter modules, the CLI, packaged weights pin,
three regression-test files, current documentation and rendered tutorial, plus these
bug artifacts. Existing import contracts and their negative tests remain unchanged
and passed in the full suite. No approved dependency source or version changed.
Final Markdown/local-link validation and architecture acceptance validation passed.

## Released-source pair and delivery

Normal hooks accepted fix commit `254e988`, generated release commit
`ad7204c10baf00abafe23b92bb8882e2fea22171` and created annotated tag `v0.44.1`.
The generated release diff contains only the changelog and project/root-lock version
updates; dependency sources, versions and metadata are otherwise unchanged. The
hook's first changelog refresh was reviewed and staged before the successful retry.
There was no local UV source-override section in this isolated checkout; the original
workspace's overrides remain intact.

Normal dependency resolution then installed that exact released source alongside
queue `397753c123f379ade50f06a2babf5e4b1476b9d2` (0.1.5) in the isolated pair environment.
Pip check, matching source/installed versions, editable origins, imports and queue
help passed before/after verification. Ruff, formatting, strict mypy and both import
contracts passed. The final queue suite passed 518 tests, with seven physical opt-in
cases deselected and 19 warnings in 121.78 seconds. This replaces the proposed-pair
qualification above; no queue source or requirement change was needed.

Code delivery uses the normal master branch and
[v0.44.1 tag](https://github.com/BuckanovNikita/clearml-yolo/tree/v0.44.1).
The independently versioned
[weights-2026-10-30 release](https://github.com/BuckanovNikita/clearml-yolo/releases/tag/weights-2026-10-30)
contains the verified archives, manifest and checksums. No code GitHub Release,
project distribution assets or package-registry publication is part of this delivery.
