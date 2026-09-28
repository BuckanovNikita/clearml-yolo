# Initializer and Annotation Contracts

The complete execution contract remains [the current CLI contract](../../001-release-030/contracts/cli.md).

```text
cy-init-config DIRECTORY [--force]
```

- Required positional directory, standard `--help`, optional explicit replacement.
- Creates `cy.yaml`, `cy-train.yaml`, `cy-predict.yaml`, `cy-val.yaml`, `cy-metrics.yaml`,
  `cy-report.yaml`, `cy-compare.yaml`, and `cy-ground-truth.yaml`, plus
  `ultralytics/default.yaml` and `ultralytics_predict/default.yaml`.
- Each command example is consumed by its matching command with
  `--config-dir DIRECTORY --config-name COMMAND`; model command examples select the applicable
  native group files through their Hydra defaults.
- Missing inputs remain `???`. The shared native group covers installed upstream defaults;
  the prediction group contains explicit overrides and inherits applicable shared values.
  Relative inputs use the execution working directory. Comments describe usage, tracking
  identity, and native overrides.
- Existing example paths fail before writes unless force is supplied. Force refuses symlink
  and directory destinations and only replaces regular example files. Other contents survive.
- Success exits zero. argparse argument/filesystem errors exit 2 with a diagnostic.
- No task, credential lookup, training, prediction, or model import occurs during initialization.

All first-party Python modules omit the future-annotations import. Self references and
stub-only generics use explicit compatible annotations. This changes annotation evaluation
inside the package, not the supported command or artifact interfaces.

The existing dependency pins, ClearML execution requirement, removed queue/GPU automation,
native precedence, and pipeline output ownership remain unchanged.

The native-group details above supersede this feature's original sparse-mapping design. The
[current configuration contract](../../003-ultralytics-config-groups/contracts/configuration.md)
defines accepted overrides, stage filtering, removed `cfg` forms, and effective YAML records.
