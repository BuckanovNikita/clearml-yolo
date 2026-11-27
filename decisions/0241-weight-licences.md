# ADR-0241 · Keep upstream licences attached to pretrained model assets

Selecting a detector or downloading a CY weight bundle does not grant a uniform licence across assets. CY's model guide identifies Ultralytics YOLO's AGPL-3.0 terms, DEIMv2's non-commercial restriction and Meta's separate DINOv3 agreement. For gated DINOv3 assets the resolver carries instructions for obtaining access or supplying a local file. The user's selected distribution and asset determine which upstream terms apply.

Weight archives carry notices under `LICENSES/`. DEIMv2 non-commercial assets have their own archive group. Operators can consult the notices for the asset they intend to deploy. The implementation links below describe packaging and access handling.

[Weight licences](../docs/configuration/model.md) · [DINOv3 access handling](../src/clearml_yolo/adapters/deim/assets.py) · [Archive member admission](../src/clearml_yolo/adapters/assets/bundles.py) · [Unauthorized backbone access cases](../tests/test_dinov3_hf_weights.py)

See the [archive packager](../scripts/package_weights.py) and [weight release decision](0413-weight-release.md).
