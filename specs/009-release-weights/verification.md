# Verification — 2026-10-29

## Scope and source isolation

The delivery checkout starts at remote CY `0b5f3f725fd65c760f21ea428faf2bbb5e2b6376` (0.43.0). Only new task files and incremental task-owned hunks were integrated by three-way merge from a byte-preserved starting snapshot. The original workspace remains on its prior commit with pre-existing 007/008 work preserved. No approved external dependency revision changed. Proposed code release is CY 0.44.0 with cy-queue 0.1.5; weights have their own `weights-2026-10-29` tag.

## Real asset preparation and packaging

All 56 unique catalogue requests were resolved and revalidated: 55 weight files plus the original pinned DEIM source tar. Existing validated native files were reused; no retraining or checkpoint modification occurred. Total original payload bytes: 4,843,707,161. The maintainer command completed with four independent tar assets and a complete manifest/checksum file. Archive sizes are 1,885,511,680; 1,871,441,920; 1,025,710,080; and 61,747,200 bytes. The final archive is separately named for DEIM non-commercial material. Every archive is below 2 GiB and includes upstream notices and per-file source/licence mapping.

Pinned manifest SHA-256: `aef07c51af700ce3f171e7cb0d3606c19e6c053380650a7b825afb585171daae`. Packaging tests cover determinism, partition overhead, oversized inputs, incomplete discovery, malformed/replaced files, original DEIM source selection, Hub metadata/config consistency and unsafe notices. No user data, credentials or machine configuration are in the manifest.

## Fresh-cache native round-trip

The real archives were served over loopback HTTP through the supported GHR request construction. All other network access was denied. The actual manual command restored every catalogue entry into empty task-owned native caches; normal resolvers then matched each weight/source hash to the manifest. Exactly four archive GETs were observed. Subsequent automatic preparation returned a completed receipt with zero failures and no second transfer. Ultralytics settings remained unchanged by preparation.

With network blocked, all 44 YOLO native filenames loaded. Both Torchvision ResNets, three timm backbones plus HF model/config construction, all four RF-DETR constructors, and both DEIMv2 small/medium source/backbone models executed their native CPU loader checks. Torchvision/timm/DEIM forwards produced finite outputs where probed. These synthetic inputs establish loading/execution, not model quality.

A separate native GPU probe used the archive-restored YOLO11n checkpoint, two non-square images and device 0. The actual predictor backend and output tensors were CUDA and finite. The first harness assertion incorrectly inspected the retained CPU wrapper model; inspection identified Ultralytics' separate predictor backend, and the corrected probe passed. No application fix was needed. This check establishes GPU inference, not training or accuracy.

## Automated and paired checks

The initial canonical checks passed Ruff, strict mypy, Vulture, import-linter and pytest (4,407 passed, 30 skipped, 81 deselected). Its final input comparison detected input instability, so no success receipt was recorded. The completed Artifactory/tutorial/tooling amendment was then integrated, and the final canonical run was started against fixed inputs. The final focused command passed 179 tests; documentation validation passed after rendering the amended tutorial. An earlier focused invocation via the pytest console script could not import the repository scripts package; the documented `python -m pytest` invocation passed without a source change.

The isolated proposed CY 0.44.0 / queue 0.1.5 pair resolved normally with both approved external source packages. Installed/source versions, requirements and origins matched; pip consistency passed. Queue checks passed Ruff, formatting, strict mypy (69 files), both import contracts, command help, composition isolation, and 518 ordinary tests; 7 physical-GPU queue tests were deselected. All 17 CY modules consumed by queue retain their CY 0.43.0 interfaces and source bytes. Final committed metadata will be refreshed before delivery.

## Documentation and review

Repository and portable skill guides describe independent weight cadence, original source identity, native Hub restoration and retry behavior. A fresh native-agent skill evaluation correctly distinguished a completed attempt from a complete cache, preserved SDK settings, selected manual retry and explained that code releases reuse weight snapshots. It executed no model work and is not a live target-model evaluation.

The new core manifest and asset adapters are outside the maintained mutation selection (`core/datasets.py`, `core/evaluation/policy.py`, `core/export_quality.py`); selected modules, selected tests and approved dependency versions remain unchanged. Direct fault-injection tests cover the changed transport/cache behavior. No mutation run is claimed.

## Artifactory verification boundary

The user explicitly requested logic verification only, with no live Artifactory check. The loopback-only fixture tests passed: prefixed GHR archive routing, GH VCS downloadCommit routing, native upstream GHR fallback, proxy 401/503/corrupt-response recovery, malformed mirror configuration recovery, per-host netrc credentials, cross-origin credential stripping, original provenance and secret-free failure guidance. Existing Hub tests also passed; no deployment credentials or endpoints were requested again or used. Live Artifactory connectivity/authentication is unverified by design.

## Remaining acceptance

Code commit/tag/push remains open. No unfinished or unavailable gate is reported as passed.

## Companion and asset reviews

Fresh asset-only review found no blocking issue in catalogue completeness, archive/member structure, manifest, provenance and notices; actual hosted-byte verification remains required. Fresh companion review accepted queue compatibility metadata and portable guidance. It independently passed 31 Artifactory/Hub tests, checked 67 portable-package Markdown files and both queue task documents, and correctly answered the new GH/GHR recovery evaluation case. These native-agent evaluations are not live target-model or Artifactory evidence.

## Public weight snapshot

Published [weights-2026-10-29](https://github.com/BuckanovNikita/clearml-yolo/releases/tag/weights-2026-10-29) as an independent model-assets release, not latest application release. Its annotated tag points at the inspected CY 0.43.0 catalogue source. All four archives, manifest.json and SHA256SUMS report uploaded status; every server-side asset size and SHA-256 digest matches the original local file. The actual manual CLI then completed from public GitHub URLs into empty native caches: 56 assets, zero failures, exactly four archive requests. Every downloaded archive and every restored asset matched the packaged size/hash inventory. Only GitHub and its release CDN hosts were permitted; download.pytorch.org, Hugging Face and all other upstream hosts were blocked. The automatic follow-up skipped preparation without another transfer, and native Ultralytics settings stayed unchanged. No Artifactory host was involved. This independently verifies the hosted bytes and production restore path, including the ResNet-50/101 backbones originally hosted on download.pytorch.org.

## Verification-environment stabilization

The final integrated check commands all passed (4,445 pytest passes, 30 skipped, 81 deselected), but the verifier rejected their success receipt because an installed dependency changed filesystem identity during the run. Inspection found 35 pathspec files with changed ctime at the paired installation timestamp. The main and paired environments referenced the same inode and unchanged SHA-256 through uv hard links. The owned verification environment was detached into private copies (46,331 files, unchanged package versions and bytes); no verifier exemption or receipt was fabricated. Canonical verification was restarted after this environment correction. The application source remained unchanged.

## Final integrated source review

A fresh read-only reviewer returned ship for the complete integrated source, with no blocking code or architecture findings, conditional on the outstanding canonical receipt and delivery gates. The reviewer inspected all tracked/untracked task paths, schema validation, archive/member integrity and containment, native/Hub cache locking and publication, authentication/fallback, complete packaging, architecture contracts and docs. Manifest identities/hashes matched the public roundtrip. The reviewed 31-path aggregate was `8acea8533b6ac3445b58afb14e5222ac432894dc14de8ed2892d3017f65c9306` (sorted path, NUL, per-file SHA-256 and newline); later task evidence annotations do not alter runtime/test content. Architecture planning and whitespace checks passed independently. A non-blocking efficiency edge remains: manual preparation may retrieve the original DEIM tar when only its valid extracted source tree remains; it preserves that tree. No unavailable or pending check was counted as passing.

## Canonical acceptance

The stabilized final run completed successfully on 2026-10-29 and recorded its normal verifier receipt. Ruff, strict mypy, Vulture and import-linter passed; pytest passed with 4,445 passed, 30 skipped, 81 deselected and 182 upstream/expected warnings in 1,023.82 seconds. The receipt was produced by the unchanged canonical verifier after its full before/after input comparison, without exemptions or bypasses. The previous source-only ship review applies to the same runtime/test files. All requested native, public-download, Artifactory-fixture and paired-source behavior checks are complete; live Artifactory remains deliberately untested. Documentation and architecture are reconciled below before code delivery.
