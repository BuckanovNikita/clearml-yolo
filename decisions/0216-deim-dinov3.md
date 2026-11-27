# ADR-0216 · Translate official DINOv3 backbones for DEIMv2 large presets

DEIMv2 large and extra-large expect a native backbone state dictionary. If selected pretrained initialization needs that backbone, CY first accepts a valid original Meta checkpoint. Otherwise it resolves the pinned Hugging Face weights and converts their tensors into the native DEIMv2 representation.

The conversion validates tensor coverage and shape against the intended model, reloads the resulting checkpoint, and records both source and derived identity. A valid converted cache can be reused. A gated download failure requires access or a suitable explicit local file.

[Model configuration](../docs/configuration/model.md) · [Backbone conversion and validation](../src/clearml_yolo/adapters/deim/hf_weights.py) · [Selection conditions](../src/clearml_yolo/adapters/assets/execution.py) · [Conversion and cache cases](../tests/test_dinov3_hf_weights.py) · [Official DINOv3 acquisition history](https://github.com/BuckanovNikita/clearml-yolo/commit/c16dbb19d0b59df30c173696406a5f76ec1ac768)
