# ADR-0217 · Classify the installed Ultralytics settings by stage

An upstream Ultralytics upgrade can change the meaning of a run by adding a key or changing its default. CY explicitly classifies the installed template's keys as shared, training, prediction or inactive. It uses the active projection for each stage, validates the composed values and supplies its pinned detection defaults. Unknown upstream keys fail registration or YOLO measurement-profile construction.

The tiling settings illustrate this policy. They are accepted as inactive and dropped before execution. CY also retains its explicit NMS IoU when the upstream template supplies a null default. The same classification drives generated configuration and execution.

[Ultralytics settings](../docs/configuration/ultralytics.md) · [Classification and projections](../src/clearml_yolo/adapters/yolo/config.py) · [Installed template and changed-default cases](../tests/test_native_config.py) · [Tiling and IoU compatibility decision](https://linear.app/sip-ds-team/issue/SIP-325)

See [prediction settings](../docs/configuration/ultralytics-predict.md).
