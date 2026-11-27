# ADR-0005 · Export editable YAML for one command and detector selection

A user can start from the same defaults as the installed command. `cy-init-config` and the Python function `dump_config_tree` write the command wrapper, its base and the groups needed by the requested selection. The wrapper can be composed again with the normal [configuration interface](0003-hydra-composition.md).

The exporter checks destinations before writing. An existing file blocks ordinary creation. With `--force`, only eligible regular files are replaced. Unrelated files survive. An invalid selection fails before writing, and the export does not require a ClearML task. [Command](../docs/commands/cy-init-config.md) · [Exporter](../src/clearml_yolo/entrypoints/hydra/config_tree.py) · [Export and fresh-process tests](../tests/test_config_tree.py)
