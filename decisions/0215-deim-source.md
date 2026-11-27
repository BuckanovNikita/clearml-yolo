# ADR-0215 · Require a verified DEIMv2 source revision

DEIMv2 executes implementation and preset files from upstream. The selected configuration can supply a source checkout. CY validates the pinned revision and the relevant upstream trees. Without a checkout it reuses a verified managed tree or extracts a verified source archive under the workspace cache.

Source preparation also applies when a checkpoint is recovered for inference. An incompatible revision or altered managed source cannot silently change the detector implementation. The source revision accompanies the model's descriptor.

[Model configuration](../docs/configuration/model.md) · [Upstream source admission](../src/clearml_yolo/adapters/deim/source.py) · [Managed tree resolution](../src/clearml_yolo/adapters/assets/sources.py) · [DEIM asset cases](../tests/test_deim_assets.py) · [Revision mismatch cases](../tests/test_dinov3_hf_weights.py) · [Detector integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/43f9e7dc85672bbb25f29e6abcb27344201ac443)
