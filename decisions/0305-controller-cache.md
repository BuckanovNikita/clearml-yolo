# ADR-0305 · Project ClearML step identity before controller cache lookup

Controller caching happens before workers start. Machine-specific output routes can differ between two otherwise equivalent computations, and some apparent routes select inputs.

**Decision.** A controller explicitly registers `normalize_task_hash`. For recognized CY module entry points the callback copies the task representation, removes `run_overrides`, projects known routing fields, device selectors and prepared-dataset paths, and retains project or run-directory fields when they select an input. Conservative fallback preserves ambiguous input distinctions.

**Consequences.** The callback changes cache identity only. [Agent replay](0304-agent-replay.md) independently resolves the executable configuration. Unknown scripts are copied intact. The reference calls `run` the sole cache input. The implementation also preserves other hash material, including unrelated configuration objects such as `model_assets` when present, and normalizes some `General` and `dataset` fields.

[Controller projection and invariants](../src/clearml_yolo/adapters/clearml/cache.py) · [Cache identity tests](../tests/test_clearml_cache.py) · [Technical contract](../DOCS.md#clearml-publication) · [Controller setup](../docs/publication.md) · [Contract discrepancy SIP-350](https://linear.app/sip-ds-team/issue/SIP-350) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/2e4b5f2fa3c3e9dc90920af75fe3edb8e346bcd0)
