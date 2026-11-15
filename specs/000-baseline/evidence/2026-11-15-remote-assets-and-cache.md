# Remote model assets and dataset cache — 2026-11-15

Ticket: [90: Verify remote assets and dataset caches](../../../.scratch/verification-gap-closure/issues/90-verify-remote-assets-and-dataset-caches.md).
Contracts: [native asset resolution](../../../docs/model-assets.md),
[input and cache provenance](../../../docs/input-provenance.md),
and [baseline model behavior](../spec.md#models-augmentation-and-training-capacity).
All selected execution checks passed; ticket 90 was accepted after fresh independent
review on 2026-11-15. The reviewer rechecked evidence checksums, registry coverage,
retained asset identities, all 161 pinned source files, containment, and archive
cleanup. No blockers remained.
Source HEAD: `bce7df823f85f4c52ad7785ca2800dce691e20c1`; package versions are in the local `versions.json`.
No product behavior, dependency, or model revision was changed.

## Ownership and isolation

All task-owned state is under `runs/verification-gap-closure/assets-v1/`.
The run selects isolated native destinations through `CY_HOME`, `YOLO_CONFIG_DIR`, `TORCH_HOME`, `HF_HOME`,
`HF_HUB_CACHE`, `RF_HOME`, `MPLCONFIGDIR`, and `XDG_CACHE_HOME`; it does not replace `HOME` or edit user SDK settings.
The new Ultralytics settings file explicitly selects the campaign weights directory before production discovery.
Every discovered native destination is checked for containment before downloads. The process working directory
is also fresh, preventing fallback to current-directory user weights. No user cache was copied into these caches.

Execution uses CPU only (`CUDA_VISIBLE_DEVICES=`), low scheduler/I/O priority, and two library threads at most.
Offline construction runs beneath `unshare --user --map-root-user --net`; an actual external TCP connection
attempt fails with `ENETUNREACH` before any model is loaded. Hub offline flags additionally request local SDK
lookup. Sockets or download functions are not mocked. No training or optimizer updates are performed.

## Registry and remote route

`registry.json` captures the maintained 64 model selections and 57 unique bulk requests: 44 YOLO assets,
four RF-DETR weights, six shared Faster R-CNN/FCOS backbones, two DEIM tiny backbones and the pinned DEIM source.
The packaged `weights-2026-10-31` manifest has the same 57 entries. The production `prepare_catalogue(automatic=False)`
route retrieves pinned public GitHub release archives; `GHR` is not configured for this execution. Native destinations
and all source/asset identities are retained in the local registry and product result receipts.

DEIM L/X lie outside that bulk catalogue. Their supported `prepare_model_assets(..., training=True)` route separately
retrieved the approved official HF snapshots, verified and converted them into the native DEIM layout, and retained
source/converted hashes and revision provenance in `selected-deim-results.json`. Both full native DEIM models then
constructed with their pretrained backbones in the disconnected namespace; `selected-deim-offline-results.json`
records passed construction for both. This establishes native loading, not detector quality.

The fresh bulk preparation completed in 1,258.4 seconds: **57 assets prepared, zero failures**. One 1.889 GB
archive transferred slowly but completed within the unchanged 1,800-second per-attempt budget. No proxy change
or timeout extension was needed. While it transferred, the same production restoration path prepared independent
assets from already-complete fresh archives in a disconnected namespace. An initial containment assertion
rejected the fresh SDK's default weights directory before downloads; selecting the isolated absolute weights
directory resolved that setup issue without changing user settings.

All **57 bulk assets** passed native loading: 44 YOLO constructors, four RF-DETR constructors with product
pretrained tensor verification, two Torchvision and four timm native pretrained backbones, two DEIM model
constructions, and verified DEIM source loading. With the additional L/X models, this establishes **59 unique
asset outcomes covering 64 model selections**; Faster R-CNN and FCOS share six backbone assets.
The final audit rechecked native bytes against the successful loading evidence. No required asset check remains
failed or deferred.

The local `registry.json`, `preparation-result.json`, `native-load-results.json`, `selected-deim-results.json`,
and `selected-deim-offline-results.json` record every selection, outcome, path, hash, revision and native loader.
Execution logs retain construction output. `archive-verification.json` binds all four archive sizes and hashes
to the maintained pin. A completed automatic-attempt receipt alone was not treated as successful preparation.

## Native dataset-cache checks

`dataset-check.py` called the real `cached_dataset` product interface with ticket 01's frozen 160/40/40 inputs.
`dataset-cache-results.json` records:

| Check | Outcome |
| --- | --- |
| Cold construction for NDJSON, flat, and COCO | passed |
| Warm reuse for each format, unchanged file bytes and modification times | passed |
| Different formats select distinct cache identities | passed |
| Same CSV bytes with absolute image references at another CSV location reuse the original entry | passed |
| Changed CSV bytes create a distinct entry while preserving the original | passed |
| Identical relative-reference CSV bytes in two directories resolving to different images separate entries | passed |
| Invalid completion metadata is rejected and preserved for explicit repair | passed |
| Frozen source CSV bytes remain unchanged | passed |
| Changed source pixels at an unchanged path retain the existing warm cache | passed |
| Explicit removal of an idle owned cache entry rebuilds using changed pixels | passed |

These are real local filesystem/product operations, with no mocked readers or preparation functions. Per the
maintained contract, warm hits do not provide automatic image-content/mtime invalidation. A second native check
using two disposable copies from the frozen population demonstrated this behavior and explicit invalidation;
its receipt is `media-invalidation-results.json`. No physical NFS topology or concurrent-host behavior is inferred.

After recording the checks, all exclusively owned dataset-cache entries and disposable relocated source copies
were deleted, reclaiming 194,355,408 bytes of file contents, plus 239,606 bytes from the media-invalidation check.
The frozen campaign fixtures remain intact.

## Retention

After successful identity verification and native loading, all four redundant archive copies were deleted,
reclaiming **4,930,928,640 bytes**. A fresh production preparation pass in the disconnected namespace then
resolved **all 57 assets with zero failures without any archive copies**. The receipts are
`offline-warm-preparation.json` and `final-audit.json`.

About 5.0 GiB of native caches, selected-model conversion inputs/outputs, source and small evidence files remain
for downstream consumers. `consumer-bindings.json` supplies isolated cache selectors and per-model paths;
the consumer still owns its `CY_HOME`. Supply retained DEIM source/backbone paths explicitly when that workspace
differs. Retain shared assets until dependent consumers and ticket 93 finish.

All launched checks exited. The two empty runtime scratch directories were removed with explicit `rmdir`
calls after execution; derived dataset copies and archive staging are also absent. A combined documentation
and scratch-cleanup shell command was rejected by the host control hook; documentation was then edited directly
and cleanup narrowed to empty-directory removal, without modifying or bypassing host controls.
Original datasets, user caches, approved revisions and historical evidence remain
untouched. No GPU work, training, service mutation, release or push was performed. These checks establish native
loading and local cache behavior, not detector quality, training, remote filesystem topology, or GPU execution.
