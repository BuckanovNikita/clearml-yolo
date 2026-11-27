# ADR-0206 · Keep explicit training weights authoritative

For DEIMv2, RF-DETR, Faster R-CNN and FCOS, CY validates explicit training files and resolves assets for the selected preset. Without a supplied full detector checkpoint, explicit backbone weights initialize the supported backends even when `pretrained=false`. With neither file, `pretrained=false` requests random initialization. With automatic pretraining enabled, RF-DETR needs a full checkpoint and the other families need a backbone. Warm initialization starts a new training run.

The model guide's weight-selection sequence says training starts from scratch when full weights are absent and `pretrained=false`. The implementation still loads supplied backbone weights in this case. The technical reference describes the explicit-file precedence. [Detector contract](../DOCS.md#detector-families) · [Open discrepancy](https://linear.app/sip-ds-team/issue/SIP-344)

[Model configuration](../docs/configuration/model.md) · [Selected initialization inputs](../src/clearml_yolo/adapters/assets/execution.py) · [Backbone load](../src/clearml_yolo/adapters/torchvision/backbone.py) · [Full checkpoint load](../src/clearml_yolo/adapters/torchvision/training.py) · [Local weights and registry cases](../tests/test_model_assets_loading.py)

See [selected asset resolution](0212-selected-assets.md).
