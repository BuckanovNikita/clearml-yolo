# ADR-0004 · Show each Hydra command’s selectable options

A shared configuration registry also contains private schema groups. Each experiment command installs a help template using its public name and the choices exposed by its defaults. This lets a user discover model or transform selections they can actually override. Internal composition groups stay hidden. Hydra retains its own help through `--hydra-help`.

For example, training help lists training choices, while commands without a model selection omit it. [Command configuration](../docs/configuration/README.md) · [Help builder](../src/clearml_yolo/entrypoints/hydra/configs.py) · [Help composition cases](../tests/test_hydra_help_composition.py) · [Decision history](https://linear.app/sip-ds-team/issue/SIP-208)
