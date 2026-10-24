# Model assets and offline recovery

Non-YOLO execution prepares matching native model assets for DEIMv2, RF-DETR and
Faster R-CNN. Dependency installation remains externally managed. Ultralytics
configuration, downloads and initialization remain unchanged. Help, configuration
inspection and queue submission do not resolve assets.

## Inputs and replay

Explicit `model.train.weights`, `model.train.backbone_weights` and `model.source_dir` values
remain authoritative; a missing explicit input fails. Automatic pretrained assets
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

Under the selected [CY_HOME](filesystem-policy.md), managed weights use:

```text
.cache/clearml-yolo/models/<backend>/<preset>/<asset-id>/<filename>
```

Asset identity incorporates the canonical source, revision and available checksum.
DEIM source uses:

```text
.cache/clearml-yolo/sources/DEIMv2/<revision>.tar.gz
.cache/clearml-yolo/sources/DEIMv2/<revision>/
```

The archive and extracted code/configuration are verified against a packaged
manifest from the approved source revision. Unsafe archive members and modified
managed source contents fail verification. Explicit source checkouts retain their
revision/content validation. Valid native library caches may be reused without
changing global SDK cache settings.

## Proxies

Resolution first checks valid local/cache content, then a configured proxy, then
the original upstream URL. Missing or empty proxy variables select upstream
directly. Non-GitHub sources keep their original endpoints.

`GHR` is a repository root. For a GitHub release URL the resolver preserves the
complete `owner/repository/releases/download/tag/filename` suffix beneath that root.
Do not supply a filename-specific URL as the repository root.

`GH` is an Artifactory VCS repository root. Pinned DEIM source uses Artifactory's
[downloadCommit API](https://docs.jfrog.com/artifactory/reference/downloadvcscommit),
not Git clone access. Local fixture tests establish request construction and
fallback; connectivity and authentication to a particular deployment require
separate verification.

HTTP operations use bounded requests/retries, standard authentication/TLS settings,
per-asset locks, temporary files and atomic publication. Available checksums and
content checks reject incomplete or invalid downloads. Diagnostics redact proxy
credentials while retaining full original asset URLs.

## Offline placement and access

If resolution fails, the error lists every known missing asset with its full original
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
