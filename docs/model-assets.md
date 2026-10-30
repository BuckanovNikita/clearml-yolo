# Model assets and offline recovery

`cy-download-weights` prepares the maintained detection-model catalogue in the
locations used by ordinary native loaders. Check installed command help before using
this interface with an older package. Preparation does not install dependencies,
train a model, create a ClearML task or change SDK settings.

```bash
cy-download-weights
```

The command reports cache destinations, prepared assets and failures. It exits zero
only when the eligible catalogue is complete; incomplete preparation exits nonzero.
Rerunning it retries unresolved assets and reuses validated files. Existing compatible
CY-managed files may be copied into native caches without consuming their originals.
Shared backbones use the same native cache entry.

## Pinned project archives

Bulk preparation reuses validated native files, then restores missing assets only
from the project's pinned `weights-*` GitHub Release. The packaged
`adapters/assets/weights-manifest.json` selects the snapshot in
`BuckanovNikita/clearml-yolo`; preparation never discovers a moving latest release.
The current pin is `weights-2026-10-30`.

A missing, mismatched or unavailable pin produces a release-specific failure. Bulk
preparation does not fall back to Google Drive, Google Storage, download.pytorch.org
or Hugging Face. Both cache lookup and post-restoration verification are local-only,
including Hub metadata. Original URLs remain provenance and are not bulk download
routes. Standalone selected-model execution retains its ordinary resolution rules.

Each independent `.tar` is below 2 GiB. Preparation verifies its byte size and
SHA-256 before reading it, rejects unsafe paths, links, duplicate members and special
files, and verifies each selected member before atomic native publication. Downloaded
archives are reused under `CY_HOME/.cache/clearml-yolo/weight-bundles/` with coordinated
locks. A partial or interrupted transfer is not a completed archive.

The elapsed streaming budget for each archive attempt defaults to 1800 seconds.
Set `CY_WEIGHTS_DOWNLOAD_TIMEOUT` to a positive finite number of seconds before
launch when the connection requires more time. The budget is checked between
completed chunks; it is not a hard wall-clock deadline. Connection and socket-read
inactivity timeouts remain 10 and 30 seconds respectively. Continuously arriving
headers or a slowly completed chunk can exceed the streaming budget before a check.
Archive locks have a separate finite wait of four times the configured budget plus
60 seconds; that wait can expire while a slow writer is still active. Ordinary
selected-model downloads retain their existing 300-second streaming budget; this
setting applies to project weight archives only.

Hub assets include the native configuration, actual snapshot commit, requested
revision reference and blob metadata. Restoration requires no upstream metadata
request; ordinary timm discovery can use the restored cache offline. ResNet archives
remain usable across supported Torchvision versions when the original filename,
URL and checksum identity are unchanged. Changed weights or source revisions are
not treated as equivalent.

Weight snapshots have a separate release cadence from application versions. Ordinary
code releases reuse the existing pin and do not build or upload weights. See the
[maintainer procedure](development.md#model-weight-releases) and
[licence inventory](../specs/009-release-weights/licenses.md). Each file retains its
own terms: YOLO uses AGPL-3.0; DEIMv2 materials permit non-commercial use and
redistribution only. Bundled notices do not grant a common licence to the collection.

## Catalogue and automatic execution

The catalogue covers maintained YOLO detection names, RF-DETR, eligible Faster R-CNN
and FCOS backbones, and DEIMv2 small/medium plus its pinned source. Bulk preparation
excludes DEIMv2 large/xlarge and `dinov3_small`; explicitly selecting those models
retains their normal execution behavior and access requirements.

Actual `cy` pipeline execution attempts the catalogue before model construction,
including when the selected model already has local weights. It records a completed
attempt per catalogue/asset-identity/native-destination fingerprint under
`CY_HOME/.cache/clearml-yolo/preparation/`. Partial failures also complete an attempt:
automatic failures warn and continue, and the selected model retains normal failure
handling. Use `cy-download-weights` to retry without waiting for a fingerprint change.
Changed catalogue identities, pinned bundle manifest or effective native destinations
trigger another attempt.
Concurrent starts coordinate through a lock. An interrupted pass remains unfinished
and can be retried; a completed attempt is not proof that every asset is available.

Help, configuration inspection, queue submission and standalone stage commands such
as `cy-train` do not perform the bulk pass. A worker executing `cy` applies the same
pipeline policy. Stage execution may still resolve assets required by its selected
model. Ordinary package imports do not initiate preparation.

## Inputs and replay

YOLO architecture YAML, boolean or filename `pretrained` values, explicit model and
checkpoint paths, resume behavior, and Hydra configuration remain authoritative.
Custom architecture names are not replaced or matched to weights by their basename.
Legacy native aliases retain library discovery, including auxiliary AMP assets.
Relative paths keep the consuming process's working-directory semantics. Non-null
`ultralytics.cfg` remains unsupported.

Explicit `model.train.weights`, `model.train.backbone_weights` and `model.source_dir` values
remain authoritative; a missing explicit input fails. Selected-model pretrained assets
are requested only for training with pretrained initialization enabled and without
superseding explicit weights. Prediction/checkpoint loading does not request
pretrained initialization. DEIM source remains necessary for its native runtime.

Canonical ClearML `run` settings preserve the original selectors, including null
defaults. Only an execution copy receives resolved local paths. Asset provenance
uses the separate `model_assets` ClearML Configuration Object to record original
source URLs, resolved paths and content SHA-256 values. It is not a replay input.
File records hash the file bytes. Reused verified source-tree records identify their
content kind and hash the packaged manifest of file hashes.
Native backend adapters still own checkpoint loading and checkpoint transformations.
Full detector weights and random initialization are not substitutes for a requested
pretrained backbone.

## Cache locations

Native asset destinations follow the installed libraries' effective settings:

| Asset | Native destination |
| --- | --- |
| Ultralytics named weights, including AMP lookup | Effective Ultralytics `weights_dir` |
| Torchvision URL backbones | `torch.hub.get_dir()/checkpoints` |
| timm Hugging Face backbones | Effective Hugging Face Hub cache, with native repository/revision metadata and discoverable snapshots |
| RF-DETR weights | RF-DETR's configured model cache |

Do not copy a timm/HF weight into an arbitrary similarly named directory: native
repository/revision discovery and metadata must be preserved. The installed timm
pretrained configuration determines whether a backbone uses a URL or HF Hub.
HF readiness also requires valid native `config.json` at the weights' actual snapshot
commit. If config preparation failed, retry repairs it while retaining validated
weights; a cached weight file alone is not a complete preparation result.

DEIM weights remain under the selected [CY_HOME](filesystem-policy.md):

```text
.cache/clearml-yolo/models/<backend>/<preset>/<asset-id>/<filename>
.cache/clearml-yolo/sources/DEIMv2/<revision>.tar.gz
.cache/clearml-yolo/sources/DEIMv2/<revision>/
```

Asset identity incorporates canonical source, revision and available checksum. DEIM
source is verified against a packaged manifest from the approved revision. Unsafe
archive members and modified managed source contents fail verification. Explicit
source checkouts retain revision/content validation. Resolved source/weight paths
are supplied only to execution configuration.

Native model asset writes may use configured caches outside `CY_HOME`; this narrow
exception does not permit external application outputs, datasets, logs, scratch or
preparation state. SDK configuration roots, cache selectors and environment remain
unchanged. See [filesystem ownership](filesystem-policy.md#library-configuration-and-storage).

## Proxies

Bulk preparation checks valid native content, then the pinned project archive via
`GHR` when configured, with public GitHub as a fallback for that same archive.
Failure stays on this release route and is reported with the archive and sanitized
transport/status details. It does not switch to the model's original host.

`GHR` is the root of an Artifactory **Files (Generic) remote repository** whose
upstream URL is `https://github.com`. The complete GitHub path is appended directly:

```text
GHR/BuckanovNikita/clearml-yolo/releases/download/weights-2026-10-30/weights-001.tar
```

For example, a root `https://artifactory.example/artifactory/github-files` yields
`https://artifactory.example/artifactory/github-files/BuckanovNikita/clearml-yolo/releases/download/weights-2026-10-30/weights-001.tar`.
Supply the repository root, not a file URL, browser UI URL, GitHub API or VCS API.
This follows Artifactory's [remote file access](https://docs.jfrog.com/artifactory/docs/remote-repositories).

`GH` is a separate **VCS remote repository** of the same `https://github.com` upstream.
Ordinary selected-model DEIM source resolution uses its
[downloadCommit API](https://docs.jfrog.com/artifactory/reference/downloadvcscommit):
`https://artifactory.example/artifactory/api/vcs/downloadCommit/github-vcs/owner/repo/commit?ext=tar.gz`.
The project release includes DEIM source, so bulk preparation needs neither `GH`
nor a separate HF endpoint. `CH` is not an alias for `GH`.

### Configure a clean process and retry

Set the environment before starting CY. Replace the example hostname and repository
key with the actual Files remote root:

```bash
export GHR="https://artifactory.example/artifactory/github-files"
# Optional for a slow connection; seconds per archive attempt:
export CY_WEIGHTS_DOWNLOAD_TIMEOUT=3600
cy-download-weights
```

For authenticated Files/VCS requests, configure a private per-host `.netrc` entry
using the approved credential store and restrict access (`chmod 600 ~/.netrc`).
`HF_TOKEN` is not Files/VCS authentication. Keep credentials out of URLs, YAML and
reports. For a private CA, set `SSL_CERT_FILE` and/or `REQUESTS_CA_BUNDLE` to the
administrator-provided CA bundle before launch; keep TLS verification enabled.

HTTP 401 indicates authentication failure; 403 concerns permissions or access policy.
For 404, check the Files repository root and full project release path, including
repository access rules. A working proxy for another GitHub owner does not prove
access to this project's release. For timeout failures, increase the archive budget
if appropriate. For checksum/size/content failures, correct the proxy/cache response
and retry; do not disable integrity checks or delete valid native files.

A missing packaged manifest requires an installation containing the pin. A matching
release archive is required for missing catalogue weights; changing `GH` or
`HF_ENDPOINT` does not repair a failed bulk release download. Rerunning the explicit
command retries incomplete preparation even after an automatic partial-attempt receipt.

### Ordinary selected-model source routes

Standalone model execution may resolve original sources when its local inputs are
missing. That resolver retains its existing cache/proxy/original behavior:

```bash
export GH="https://artifactory.example/artifactory/github-vcs"
export HF_ENDPOINT="https://artifactory.example/artifactory/api/huggingfaceml/hf-remote"
```

The Hub endpoint uses the [Artifactory Hugging Face API](https://docs.jfrog.com/artifactory/docs/use-hugging-face-with-jfrog-cli).
Load `HF_TOKEN` through a secret manager or protected SDK token file, scoped to the
configured Hub endpoint. It is not forwarded to unrelated origins or redirected hosts.

Protocol fixtures verify Files/VCS URL construction, authentication, release recovery
and absence of upstream traffic during bulk preparation. They do not establish live
Artifactory connectivity, credentials, repository permissions or server cache state.

## Offline placement and access

If selected-model resolution fails, the error lists every known missing asset with its full original
URL, exact absolute local destination and applicable configuration override. For gated
assets it also identifies access requirements. Preserve this report when preparing an
offline installation.

Copy each required file to its named destination, or place the DEIM source archive
at its exact archive path, then rerun. No receipt from an earlier online download is
required. The same content checks apply to manually placed files. Obtain any required
upstream access grant rather than substituting an incompatible checkpoint.

See [backend selection](multi-model-backends.md) for the supported presets and
[Agent execution](runtime-isolation.md) for remote replay ownership.

## Safetensors validation

The asset adapter uses `safetensors.safe_open(framework="numpy")` to validate the
header, dtype, shapes and non-overlapping payload offsets. At least one named tensor
is required; legal zero-element tensors retain their existing support. Empty tensor
maps, truncated payloads and malformed descriptors are invalid. Library format errors
are translated to the existing `ValueError` boundary so invalid native-cache entries
still fall through to normal resolution. Hashing uses `hashlib.file_digest` while
retaining traced reads and caller identity checks.
