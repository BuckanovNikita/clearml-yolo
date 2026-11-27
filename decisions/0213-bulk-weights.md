# ADR-0213 · Prepare the maintained weight catalogue from a pinned release

An operator can populate native caches before a run with `cy-download-weights`. CY reuses valid local assets, then fills misses only from the project's pinned weight release via the configured release mirror or GitHub. Archive and member size and digest checks precede installation. Catalogue entries for timm backbones are bound to the pinned timm version. DEIMv2 large and extra-large backbones use a separate selection path.

The command prints per-asset failures and exits unsuccessfully if any asset fails. The automatic preparation pass for `cy` logs ordinary failures and can reuse a prior attempt receipt. Neither mode creates a separate experiment task. Catalogue inclusion and access to particular weights remain subject to the licensing terms in the guide.

[Weight preparation guide](../docs/commands/cy-download-weights.md) · [CLI outcome](../src/clearml_yolo/entrypoints/download_weights.py) · [Catalogue and receipts](../src/clearml_yolo/adapters/assets/preparation.py) · [Bundle restore](../src/clearml_yolo/adapters/assets/bundles.py) · [Integrity and release-only cases](../tests/test_weight_bundles.py) · [Preparation receipt cases](../tests/test_weight_preparation.py) · [timm identity decision](https://linear.app/sip-ds-team/issue/SIP-327)

See [Ultralytics cache selection](0214-yolo-weight-cache.md), [selected asset resolution](0212-selected-assets.md), [DEIMv2 source preparation](0215-deim-source.md) and [weight licences](0241-weight-licences.md).
