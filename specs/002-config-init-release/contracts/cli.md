# Initializer and Annotation Contracts

The complete execution contract remains [the current CLI contract](../../001-release-030/contracts/cli.md).

```text
cy-init-config DIRECTORY [--command NAME] [--force]
```

- Required positional directory, standard `--help`, optional explicit replacement.
- Accepts `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`,
  `cy-compare` and `cy-ground-truth`; defaults to `cy`. Creates one `<command>.yaml`.
  Five model selections add `ultralytics/default.yaml` and
  `ultralytics_predict/default.yaml`; other commands add no group files.
- Each command example is consumed by its matching command with
  `--config-dir DIRECTORY --config-name COMMAND`; model command examples select the applicable
  native group files through their Hydra defaults.
- Missing inputs remain `???`. The shared native group covers installed upstream defaults;
  the prediction group contains explicit overrides and inherits applicable shared values.
  Relative inputs use the execution working directory. Comments describe usage, tracking
  identity, and native overrides.
- Selected example paths/parents are preflighted; collisions fail without force. Force refuses symlink
  and directory destinations and only replaces regular example files. Other contents survive.
- Success exits zero. argparse argument/filesystem errors exit 2 with a diagnostic.
- No task, credential lookup, training, prediction, or model import occurs during initialization.

All first-party Python modules omit the future-annotations import. Self references and
stub-only generics use explicit compatible annotations. This changes annotation evaluation
inside the package, not the supported command or artifact interfaces.

Dependency pins, required ClearML tracking, native precedence and pipeline output ownership
remain unchanged. Feature 024 restores controlled queue/GPU execution; see the
[execution contract](../../022-simple-gpu-wait/contracts/execution.md).

These native-group details supersede this feature's original sparse-mapping design. The
[current configuration contract](../../003-ultralytics-config-groups/contracts/configuration.md)
defines accepted overrides, stage filtering, removed `cfg` forms, and effective YAML records.
