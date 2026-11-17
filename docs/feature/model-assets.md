# Model assets

Model assets are the pretrained weights and pinned source code that detector families
need before they can train: YOLO detection weights, RF-DETR weights, Faster R-CNN and FCOS
backbones, DEIMv2 backbones and the approved DEIMv2 source. `cy-download-weights` prepares
the maintained catalogue in the caches that the native libraries already read, `cy`
attempts the same preparation automatically before a pipeline run, and stage commands
resolve only the assets their selected model needs. Preparation never installs
dependencies, trains a model or creates a ClearML task, and the executable configuration
always keeps the user's original model selectors.

## Behavior

### Catalogue and bulk preparation

- The catalogue covers the maintained YOLO detection weight names, every RF-DETR preset,
  every Faster R-CNN and FCOS backbone (shared backbones use one cache entry), DEIMv2
  `s` and `m`, and the DEIMv2 source. DEIMv2 `l` and `x` are excluded from bulk
  preparation; selecting them uses selected-model resolution below.
- `cy-download-weights` takes no options besides `--help`. It prints each cache
  destination, each prepared asset, each failure and a summary line, and exits `0` only
  when every eligible asset is prepared. Any failure prints recovery hints and exits `1`.
  `--help` downloads nothing and needs no ClearML server.
- Bulk preparation first reuses valid files already in the native caches. A missing
  asset is restored only from the project's pinned weight release (see
  [Source routes](#source-routes)); bulk preparation never contacts an asset's original
  host. Valid CY-managed copies are copied into native caches without consuming the
  originals.
- An explicit run always retries every unresolved asset and reuses validated files.

### Automatic preparation before `cy`

- `cy` (the pipeline command, including a ClearML Agent or queue worker executing it)
  runs the bulk pass before model construction, even when the selected model already has
  local weights. Help, configuration inspection, queue submission, imports and stage
  commands such as `cy-train` do not run it.
- A completed pass is recorded per fingerprint of catalogue identities, the pinned
  manifest and effective native destinations, under
  `CY_HOME/.cache/clearml-yolo/preparation/`. A pass with failures still completes:
  automatic failures are logged as warnings, the run continues and the selected model
  keeps its normal failure handling. A later `cy` with the same fingerprint skips the
  pass; a changed catalogue, pin or destination triggers a new one.
- Concurrent starts share a lock. An interrupted pass leaves no completed record and is
  retried. A completed record does not prove every asset is present; run
  `cy-download-weights` to retry without waiting for a fingerprint change.

### Selected-model resolution

- Stage commands resolve only what the selected model needs now: pretrained assets only
  for training with `pretrained` enabled and no explicit `model.train.weights`, and the
  DEIMv2 source whenever DEIMv2 runs without `model.source_dir`. Prediction and
  checkpoint loading never request pretrained initialization. YOLO weights are resolved
  by Ultralytics itself.
- Explicit `model.train.weights`, `model.train.backbone_weights` and `model.source_dir`
  are authoritative; a missing explicit file fails. An explicit DEIMv2 `model.source_dir`
  must be a Git checkout of revision `1d2ca42171570c713e78fc6a766ec5104b7f4724` whose
  `engine/` and `configs/` have no changes or untracked files; keep other assets outside
  them. A managed source archive is checked against the packaged content manifest
  instead. Help, configuration inspection and queue submission resolve nothing.
  Pretrained RF-DETR training rejects `model.train.backbone_weights`; use
  `model.train.weights`.
- Resolution checks valid local and cached files first, then configured proxies, then
  the original URL, with two attempts per route. Downloads use per-asset locks,
  temporary sibling files, content validation and atomic publication, so concurrent
  consumers never see an incomplete file.
- DEIMv2 `l`/`x` training prefers a locally validated original Meta `.pth` backbone.
  Without it, CY resolves the pinned official Hugging Face snapshot
  (`facebook/dinov3-vits16-pretrain-lvd1689m` for `l`,
  `facebook/dinov3-vits16plus-pretrain-lvd1689m` for `x`), converts it on CPU to the
  native DEIM layout and caches it as `hf-dinov3-to-deim-v1.pth` under its own asset
  identity. Reuse re-verifies the conversion against the pinned source; a corrupt
  derived file is rebuilt. Explicit weights keep precedence and no flag is needed.
- YOLO architecture YAML, `pretrained` values, explicit checkpoint paths, resume and
  custom architecture names are never rewritten or matched to weights by basename.
  Relative paths keep the consuming process's working directory.

### Provenance

The canonical `run` configuration keeps the original selectors, including null defaults;
only an execution copy receives resolved paths. Resolved assets are published in the
separate `model_assets` ClearML Configuration Object as an `assets` list with original
URL, resolved path, content kind, SHA-256, override key and revision (plus conversion
source and converter for derived files). A file record hashes the file bytes; a verified
source-tree record hashes the packaged manifest of its file hashes. It is provenance,
never a replay input.

### Source routes

- **Bulk preparation:** valid native cache, then the pinned release archive through
  `GHR` when set, then the same archive from public GitHub. Failure stays on this route
  and reports the archive name with sanitized status (for example `HTTP 404` or
  `download timeout`). Changing `GH` or `HF_ENDPOINT` does not repair it.
- **`GHR`** is the root of an Artifactory Files (Generic) remote repository whose
  upstream is `https://github.com`. The full GitHub path is appended to it:
  `GHR/BuckanovNikita/clearml-yolo/releases/download/<release-tag>/<archive>.tar`. Supply
  the repository root, not a file, browser, GitHub API or VCS API URL.
- **`GH`** is a separate Artifactory VCS remote of `https://github.com`. Selected-model
  DEIMv2 source resolution downloads
  `<prefix>/api/vcs/downloadCommit/<repository-key>/<owner>/<repo>/<revision>?ext=tar.gz`.
  `GHR` also proxies GitHub release URLs during selected-model resolution.
- **Hugging Face:** selected-model Hub resolution honours `HF_ENDPOINT`, such as an
  Artifactory Hugging Face remote. `HF_TOKEN` or the standard token file authenticates
  only to the configured Hub endpoint; it is not forwarded to unrelated origins or to
  redirected hosts.
- **Authentication and TLS:** Files/VCS credentials come from a per-host `~/.netrc`
  entry (keep it `chmod 600`); `HF_TOKEN` is not Files/VCS authentication. Keep
  credentials out of URLs and YAML. For a private CA set `SSL_CERT_FILE` or
  `REQUESTS_CA_BUNDLE`; TLS verification stays enabled.
- HTTP 401 is authentication, 403 permission, 404 a wrong root or release path. For
  checksum or size failures fix the proxy response; never disable integrity checks.

### Weight bundles and the pin

- The packaged manifest `adapters/assets/weights-manifest.json` pins one immutable
  `weights-*` GitHub Release of `BuckanovNikita/clearml-yolo`; preparation never follows
  a moving "latest" release. The pin changes only with an installed package update.
- Each bundle is an independent `.tar` below 2 GiB. Preparation checks its byte size and
  SHA-256 before reading it, rejects unsafe paths, links, special files, duplicate and
  unexpected members, verifies each member before atomic publication and caches
  verified archives under `CY_HOME/.cache/clearml-yolo/weight-bundles/`.
- Assets sit under `assets/<identity>/` in their archive, next to the release's licence
  notices under `LICENSES/`. DEIMv2 weights and the DEIMv2 source are packed into
  separate `deim-noncommercial-NNN.tar` archives; all other assets are in
  `weights-NNN.tar` archives.
- Hub-backed assets restore the real snapshot commit, requested revision, blob metadata
  and `config.json` from the same snapshot without any upstream metadata request, so
  timm can discover them offline. ResNet archives remain valid across supported
  Torchvision versions while filename, URL and checksum are unchanged. Changed weights
  or source revisions are never treated as equivalent.
- Published weight bundles carry the collected upstream licence notices under
  `LICENSES/` (a release obligation, see
  [model-weight releases](../development.md#model-weight-releases)); those notices are
  authoritative. Each file retains its own terms: YOLO uses AGPL-3.0; DEIMv2 materials
  permit non-commercial use and redistribution only. DINOv3 retains its separate Meta
  agreement and use restrictions; its notices include the exact model licence, linked
  Meta agreement and model card. Bundled notices do not grant a common licence to the
  collection.
- **Built with DINOv3.** The DINOv3 small backbone is the unmodified timm conversion
  with its genuine Hub provenance, shared by Faster R-CNN and FCOS and shipped once.

### Cache locations

| Asset | Native destination |
| --- | --- |
| Ultralytics named weights, including AMP check weights | Effective Ultralytics `weights_dir` |
| Torchvision URL backbones | `torch.hub.get_dir()/checkpoints` |
| timm Hugging Face backbones | Effective Hugging Face Hub cache, with native repository and revision metadata |
| RF-DETR weights | RF-DETR's configured model cache |
| DEIMv2 backbones | `CY_HOME/.cache/clearml-yolo/models/<backend>/<preset>/<asset-id>/<filename>` |
| DEIMv2 source | `CY_HOME/.cache/clearml-yolo/sources/DEIMv2/<revision>.tar.gz` and its extracted directory |

The asset identity combines canonical source, revision and available checksum. These
native writes are the only model-asset writes outside `CY_HOME`; preparation records and
archives stay under it.

Before discovery, every preparation pass (`cy-download-weights` and the automatic pass
before `cy`) and YOLO batch-estimator setup persist an absolute Ultralytics
`weights_dir`: a relative value resolves against the invocation working directory, an
absolute value is kept. CY holds an adjacent settings-file lock, verifies the saved
settings by reading them back and updates the live SDK value. It preserves unrelated
settings, process-only callback switches and cache files, and does not rewrite an
already-correct value. Imports, help and configuration inspection never touch these
settings.

### Offline placement

When selected-model resolution fails, the error lists every missing asset with its
original URL, exact absolute local destination, override key and any access requirement
(for example accepting the DINOv3 licence), without credentials. Copy each file to its
listed destination, or place the DEIMv2 source archive at its exact archive path and
leave `model.source_dir=null`, then rerun. No online download receipt is needed; manually
placed files pass the same content checks. Obtain the required upstream access rather
than substituting an incompatible checkpoint. For timm Hugging Face backbones keep the
native Hub cache layout: a weight file copied into a similarly named directory is not
discoverable, and a cached weight without a valid `config.json` at the same snapshot
commit is incomplete (a retry repairs the configuration and keeps the weight).

## Configuration

| Control | Default | Effect |
| --- | --- | --- |
| `GHR` | unset | Artifactory Files remote root for GitHub release archives |
| `GH` | unset | Artifactory VCS remote root for selected-model DEIMv2 source |
| `HF_ENDPOINT`, `HF_TOKEN` | library defaults | Hub endpoint and token for selected-model Hub assets |
| `CY_WEIGHTS_DOWNLOAD_TIMEOUT` | `1800` | Seconds of streaming per release-archive attempt; positive and finite |
| `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE` | unset | CA bundle for proxies with a private CA |

Set environment variables before starting CY. The archive budget is checked between
received chunks, so it is not a hard wall-clock deadline; connection and read
inactivity timeouts are 10 and 30 seconds. The archive lock wait is four times the
budget plus 60 seconds. Selected-model downloads keep a fixed 300-second streaming budget
and a 4 GiB size bound.

## Failure behavior

- `cy-download-weights` exits `1` when any asset fails; automatic preparation only warns.
- A missing packaged manifest fails with a request to reinstall a package that contains
  `weights-manifest.json`; an asset absent from the pin fails with a release-specific
  message. An invalid `CY_WEIGHTS_DOWNLOAD_TIMEOUT` or `GHR` fails that archive.
- If the Ultralytics settings cannot be persisted, the error names the settings file;
  check its JSON and directory permissions, then rerun `cy-download-weights` from the
  original preparation directory. Do not delete settings or caches to hide the error.
- Checksum, size, archive-safety and safetensors failures never publish a file. Invalid
  native-cache entries are ignored and resolution continues normally.
- Unauthorized Hub access and checksum mismatches stay explicit errors.

## Limits

- Bulk preparation never falls back to original model hosts and excludes DEIMv2 `l`/`x`.
- The packaged weights manifest pins one release; a newer release needs a package update.
- Tests mock transport: they cover URL construction, authentication, release recovery
  and the absence of upstream traffic during bulk preparation, but not live restoration
  from the hosted release, Artifactory connectivity, credentials, permissions or server
  cache state.
- Non-null `ultralytics.cfg` stays unsupported.

## Code and tests

- [`adapters/assets/preparation.py`](../../src/clearml_yolo/adapters/assets/preparation.py) — catalogue pass and attempt records
- [`adapters/assets/bundles.py`](../../src/clearml_yolo/adapters/assets/bundles.py) — pinned release restoration
- [`core/weight_bundles.py`](../../src/clearml_yolo/core/weight_bundles.py) — manifest format
- [`adapters/assets/resolver.py`](../../src/clearml_yolo/adapters/assets/resolver.py) — selected-model routes and offline report
- [`adapters/assets/hub.py`](../../src/clearml_yolo/adapters/assets/hub.py) — native Hub cache population
- [`adapters/assets/execution.py`](../../src/clearml_yolo/adapters/assets/execution.py) — execution copy and provenance
- [`adapters/yolo/assets.py`](../../src/clearml_yolo/adapters/yolo/assets.py) — Ultralytics `weights_dir` persistence
- [`entrypoints/download_weights.py`](../../src/clearml_yolo/entrypoints/download_weights.py) — command
- Tests: [`test_weight_preparation.py`](../../tests/test_weight_preparation.py),
  [`test_weight_bundles.py`](../../tests/test_weight_bundles.py),
  [`test_hub_weight_bundles.py`](../../tests/test_hub_weight_bundles.py),
  [`test_model_assets.py`](../../tests/test_model_assets.py),
  [`test_model_assets_loading.py`](../../tests/test_model_assets_loading.py),
  [`test_native_assets.py`](../../tests/test_native_assets.py),
  [`test_hub_assets.py`](../../tests/test_hub_assets.py),
  [`test_artifactory_assets.py`](../../tests/test_artifactory_assets.py)
