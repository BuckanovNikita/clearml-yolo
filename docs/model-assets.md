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

Bulk preparation reuses valid native files, then seeds missing assets from the
project's pinned `weights-*` GitHub Release before ordinary upstream resolution.
The packaged `adapters/assets/weights-manifest.json` selects the release in
`BuckanovNikita/clearml-yolo`; preparation does not discover a moving latest release.
Source checkouts can precede initial publication: the manifest and dated publication
evidence, rather than a code version alone, identify an available snapshot.

Each independent `.tar` is below 2 GiB. Preparation verifies its byte size and
SHA-256 before reading it, rejects unsafe paths, links, duplicate members and special
files, and verifies each selected member before atomic native publication. Downloaded
archives are reused under `CY_HOME/.cache/clearml-yolo/weight-bundles/` with coordinated
locks. A partial or interrupted transfer is not a completed archive.

Hub assets include the native configuration, actual snapshot commit, requested
revision reference and blob metadata. Restoration requires no upstream metadata
request; ordinary timm discovery can use the restored cache offline. Original
upstream URL/revision identities remain provenance; the mirror URL does not replace
them. An unavailable or invalid mirror warns and falls back to the existing upstream
route. Future asset identities absent from the pin also retain that route. Standalone
selected-model execution retains its normal asset resolution.

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

Bulk preparation checks valid native content, then the pinned project archive using
`GHR` when configured and GitHub otherwise, then ordinary upstream resolution.
The upstream route checks local/cache content, a configured proxy and the original
URL. Missing or empty proxy variables use the corresponding original endpoints.
Other sources keep their original endpoints except configured HF routing.

`HF_ENDPOINT` selects the Hugging Face endpoint, including an Artifactory Hugging
Face API endpoint. `HF_TOKEN` or the SDK's standard token configuration supplies
endpoint-scoped authentication. Credentials must not be sent to unrelated origins
or redirected hosts. Keep tokens out of command examples and diagnostic reports.
HF preparation retains the native Hub cache layout and metadata for offline timm
loading; successful HTTP transfer alone does not prove offline loader discovery.

`GHR` is the root of a Generic remote repository whose upstream URL is
`https://github.com`. The resolver appends the complete
`owner/repository/releases/download/tag/filename` suffix. For example,
`https://github.com/owner/repo/releases/download/tag/file.tar` becomes
`https://artifactory.example/artifactory/github-releases/owner/repo/releases/download/tag/file.tar`.
Supply the repository root, not a particular release/file URL or the GitHub API.
This follows Artifactory's [remote repository layout](https://docs.jfrog.com/artifactory/docs/remote-repositories).

`GH` is an Artifactory VCS repository root used by the original DEIM source fallback.
For `https://artifactory.example/artifactory/github-vcs`, CY constructs
`https://artifactory.example/artifactory/api/vcs/downloadCommit/github-vcs/owner/repo/commit?ext=tar.gz`
using the [downloadCommit API](https://docs.jfrog.com/artifactory/reference/downloadvcscommit),
not Git clone access. The complete project bundle can also supply DEIM source through
`GHR`, so `GH` is optional unless that fallback is needed. `CH` is not a supported
alias; use `GH`.

HTTP operations use bounded requests/retries, standard authentication/TLS settings,
per-asset locks, temporary files and atomic publication. Available checksums and
content checks reject incomplete or invalid downloads. Diagnostics redact proxy
credentials while retaining full original asset URLs.

### Configure a clean process and retry

Set network, authentication and endpoint variables in the shell or worker environment
**before starting** CY. Replace the public example hostname/repository keys with your
administrator-provided values. A minimal complete-bundle proxy setup is:

```bash
export GHR="https://artifactory.example/artifactory/github-releases"
```

For authenticated `GH`/`GHR` downloads, configure a private per-host `.netrc` entry for
the actual Artifactory hostname using the approved credential store, and restrict the
file to its owner (`chmod 600 ~/.netrc`). Requests uses that host entry; `HF_TOKEN`
is not GitHub/VCS proxy authentication. Do not put credentials in URLs, example
commands, experiment YAML or diagnostic reports.

Set these additional routes only if their original-source fallbacks are needed:

```bash
export GH="https://artifactory.example/artifactory/github-vcs"
export HF_ENDPOINT="https://artifactory.example/artifactory/api/huggingfaceml/hf-remote"
```

The Hugging Face endpoint must use the
[Artifactory Hugging Face API path](https://docs.jfrog.com/artifactory/docs/use-hugging-face-with-jfrog-cli),
not a Generic repository URL. If it requires `HF_TOKEN`, load the token through a
secret manager or a protected SDK token file. An interactive Bash alternative avoids
putting its value in command history:

```bash
read -r -s -p 'Hugging Face endpoint token: ' HF_TOKEN
export HF_TOKEN
```

Keep that token scoped to the selected HF endpoint; it is not forwarded to unrelated
public-origin fallback requests. If a private CA is required, set `SSL_CERT_FILE`
and/or `REQUESTS_CA_BUNDLE` to the administrator-provided CA bundle before launch.
Keep certificate verification enabled. Then start a fresh process:

```bash
cy-download-weights
```

An HTTP 401 points to missing/invalid authentication; 403 to repository/token read
permissions or access policy. For 404, check the repository root, key and full
upstream path as well as upstream availability or blocking; it does not by itself
prove that model bytes do not exist. For checksum/size/content failures, retain the
diagnostic, correct the proxy/cache response and retry; do not skip integrity checks
or clear valid native caches. Rerunning the explicit command reuses validated files
and retries incomplete preparation even after an automatic partial-attempt receipt.

Protocol fixtures verify URL construction, environment/authentication boundaries,
fallback and retry logic. They do not establish any live Artifactory connectivity,
credentials, repository permissions or server-side cache state. This setup guidance
does not require contacting a live stand to test the client logic.

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
