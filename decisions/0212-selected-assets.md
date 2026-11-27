# ADR-0212 · Resolve only the selected detector's execution assets

A saved model selection must remain portable across hosts. CY validates explicit paths and populates an execution copy with the source and weights needed by that operation. The canonical run retains its selectors. Resolved paths, source revisions and content digests are provenance.

Resolution checks usable local caches before trying the configured mirror and original source. Publication into the cache is coordinated and validated. A failed selected asset reports its source, intended destination and override so a user can supply it offline. The selected-asset path and the bulk catalogue have distinct download policies.

[Model configuration](../docs/configuration/model.md) · [Execution copy](../src/clearml_yolo/adapters/assets/execution.py) · [Asset resolver](../src/clearml_yolo/adapters/assets/resolver.py) · [Resolution, integrity and recovery cases](../tests/test_model_assets.py) · [File loading cases](../tests/test_model_assets_loading.py) · [Native-cache integration history](https://github.com/BuckanovNikita/clearml-yolo/commit/9266772328422e3f6131144a3b1008327e1d83af)

See [bulk preparation](0213-bulk-weights.md) and [training initialization](0206-training-initialization.md).
