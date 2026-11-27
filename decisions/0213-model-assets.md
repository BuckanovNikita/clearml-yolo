# ADR-0213 · Prepare verified model assets for training and inference

A model selection must work across hosts while retaining the identity of the files actually used. CY keeps portable selectors in the executable run and resolves them into local weights and source for the selected operation. A separately versioned bulk release lets operators prepare common assets ahead of time.

## Resolving assets for a selected model

CY validates explicit paths, checks usable local caches and then tries the configured mirror and original source. It coordinates cache writes and validates the resolved bytes. Paths, source revisions and digests are recorded as provenance. A failed resolution reports the source, intended destination and available override so the operator can supply a file offline.

Ultralytics can store a relative weights directory. Catalogue preparation and YOLO batch-estimator setup resolve it against the working directory, serialize the SDK settings update, and read back the complete stored settings. Other settings are preserved. Importing the package, viewing help or inspecting configuration leaves those settings alone.

<details>
<summary>Sources and verification</summary>

- Resolve only the selected detector's execution assets — [Model configuration](../docs/configuration/model.md) · [Execution copy](../src/clearml_yolo/adapters/assets/execution.py) · [Asset resolver](../src/clearml_yolo/adapters/assets/resolver.py) · [Resolution, integrity and recovery cases](../tests/test_model_assets.py) · [File loading cases](../tests/test_model_assets_loading.py) · [Native-cache integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/9266772328422e3f6131144a3b1008327e1d83af)
- Persist a stable Ultralytics weight-cache directory — [Weight preparation guide](../docs/commands/cy-download-weights.md) · [Settings update and verification](../src/clearml_yolo/adapters/yolo/assets.py) · [Persistence and failure cases](../tests/test_yolo_weights_settings.py) · [Cache directory decision](https://github.com/BuckanovNikita/clearml-yolo/commit/597985fa39476b262bc05daa66ee3fb3e468724a)

</details>

## Preparing and publishing the catalogue

`cy-download-weights` reuses valid assets and fills misses from the pinned weights release, using the release mirror or GitHub. It checks archive and member sizes and digests before installation. The command reports per-asset failures and exits unsuccessfully if any asset fails. The automatic preparation pass before `cy` can reuse a previous attempt receipt and warns on ordinary failures. Neither creates an extra experiment task. Selected-model resolution has separate download rules.

The release packager creates size-bounded archives, a manifest, checksums and licence notices under `LICENSES/`. A new weights tag is published explicitly and a code change then pins those bytes. A timm-backed entry names the producing timm version and model, so packaging and consumption must agree on that version. The catalogue omits DEIMv2 large and extra-large backbones from bulk preparation. [Weight preparation guide](../docs/commands/cy-download-weights.md) · [Packaging decision](https://linear.app/sip-ds-team/issue/SIP-327)

Redistribution conditions follow the selected asset and its upstream terms. The model guide identifies Ultralytics YOLO's AGPL-3.0 terms, DEIMv2's non-commercial restriction and Meta's separate DINOv3 agreement. DEIMv2 non-commercial assets have their own archive group. [Model and weight licences](../docs/configuration/model.md)

<details>
<summary>Sources and verification</summary>

- Prepare the maintained weight catalogue from a pinned release — [CLI outcome](../src/clearml_yolo/entrypoints/download_weights.py) · [Catalogue and receipts](../src/clearml_yolo/adapters/assets/preparation.py) · [Bundle restore](../src/clearml_yolo/adapters/assets/bundles.py) · [Integrity and release-only cases](../tests/test_weight_bundles.py) · [Preparation receipt cases](../tests/test_weight_preparation.py)
- Package verified weights and licence notices as a separately versioned release — [Release procedure](../DOCS.md#release) · [Archive packager](../scripts/package_weights.py)
- Keep upstream licences attached to pretrained model assets — [DINOv3 access handling](../src/clearml_yolo/adapters/deim/assets.py) · [Unauthorized backbone access cases](../tests/test_dinov3_hf_weights.py)

</details>

## DEIMv2 source and large backbones

DEIMv2 executes upstream implementation and preset files. An explicit source checkout must match the pinned revision and relevant upstream trees. Otherwise CY reuses a verified managed tree or extracts a verified archive under the workspace cache. The same source contract applies when a checkpoint is recovered for inference. Its descriptor carries the source revision.

When a large or extra-large preset needs a pretrained backbone, CY accepts a valid original Meta checkpoint first. Otherwise it converts the pinned Hugging Face snapshot into the native DEIMv2 state dictionary, validates tensor coverage and shapes, reloads the result and records the source and derived identities. A valid converted entry can be reused. A gated download requires upstream access or an explicit local file.

<details>
<summary>Sources and verification</summary>

- Require a verified DEIMv2 source revision — [Model configuration](../docs/configuration/model.md) · [Upstream source admission](../src/clearml_yolo/adapters/deim/source.py) · [Managed tree resolution](../src/clearml_yolo/adapters/assets/sources.py) · [DEIM asset cases](../tests/test_deim_assets.py) · [Revision mismatch cases](../tests/test_dinov3_hf_weights.py) · [Detector integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/43f9e7dc85672bbb25f29e6abcb27344201ac443)
- Translate official DINOv3 backbones for DEIMv2 large presets — [Backbone conversion and validation](../src/clearml_yolo/adapters/deim/hf_weights.py) · [Selection conditions](../src/clearml_yolo/adapters/assets/execution.py) · [Official DINOv3 acquisition history](https://github.com/BuckanovNikita/clearml-yolo/commit/c16dbb19d0b59df30c173696406a5f76ec1ac768)

</details>
