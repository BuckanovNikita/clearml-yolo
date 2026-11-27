# ADR-0326 · Resolve attached configuration files at the point of use

Ground-truth conversion and report generation consume structured files. Their original paths may no longer exist on the host running a cloned task.

**Decision.** After resolving [file-backed configuration](0008-file-configuration.md), publish sanitized source files as named ClearML configuration objects. `cy-ground-truth` reads the connected `dataset` and `cy-report` reads the connected `report` file when configured. The tracking adapter returns the effective file path, which can refer to an Agent-supplied attachment. Training publishes its prepared `dataset` with remote overrides disabled.

**Consequences.** A remote attachment can supply the effective file even when the original path is absent. With neither a usable original nor a remote attachment, the consuming operation fails. An execution copy can carry local values needed at runtime while the published copy is redacted. The [replay record](0304-agent-replay.md) covers the surrounding run configuration.

[Named source resolution](../src/clearml_yolo/adapters/clearml/session.py) · [Ground-truth consumer](../src/clearml_yolo/application/use_cases/ground_truth.py) · [Report consumer](../src/clearml_yolo/application/use_cases/report.py) · [Training policy](../src/clearml_yolo/application/use_cases/train.py) · [Attachment replay scenarios](../tests/test_config_upload_commands.py) · [Documented configuration objects](../docs/publication.md) · [Configuration source decision](https://github.com/BuckanovNikita/clearml-yolo/commit/6aefaa354e2f20ef05e3d62b7901399548045133)
