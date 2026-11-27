# ADR-0001 · Compose experiment workflows from independently runnable stages

A user can run the detector pipeline as one ClearML experiment or invoke a stage on its own. Both routes use the same stage implementation. The invocation owns its configuration, run directory and task, which lets the pipeline pass results between stages without creating another experiment.

## Pipeline stages and outcomes

`cy` runs [training](0200-model-training.md#training-inputs-and-failure-policy), [prediction](0110-prediction-and-evaluation.md#prediction-from-a-selected-checkpoint), [metrics](0110-prediction-and-evaluation.md#checkpoint-validation-and-threshold-calibration), [comparison](0140-comparison-and-reporting.md#model-selection-and-an-absent-baseline) and [reporting](0140-comparison-and-reporting.md#report-inputs-and-class-populations), with optional [FiftyOne publication](0306-fiftyone.md#dataset-and-run-overlays). A `skip_*` setting omits the corresponding stage. For example, `skip_train=true` accepts an existing checkpoint. If training and comparison are both skipped, reporting can use a comparison manifest already in the run directory. With no manifest, the outcome records the report as skipped.

A nonempty checkpoint establishes that training succeeded. If prediction then fails, the pipeline can preserve the model, mark dependent stages skipped and complete with warnings. An old predictions file cannot turn that failed stage into a success. The JSON outcome and text summary distinguish these cases from interruption, failure before the checkpoint, and failure in a run that skipped training. A standalone command reports its own failure directly. [Pipeline outcomes](../tests/test_pipeline_outcomes.py)

<details>
<summary>Sources and verification</summary>

- Run the detector pipeline as one experiment — [Command](../docs/commands/cy.md) · [Pipeline use case](../src/clearml_yolo/application/use_cases/pipeline.py) · [Decision history](https://linear.app/sip-ds-team/issue/SIP-212)
- Preserve a successful training result across downstream failures — [Outcome record](../src/clearml_yolo/core/pipeline_outcome.py)

</details>

## Configuration, help and editable YAML

Each experiment command composes its packaged Hydra defaults with the user's configuration directory and CLI overrides. The detector selection determines the active parameter groups. `--help` shows the public command and the groups it supports, `--hydra-help` describes Hydra, and `--cfg job` displays the composed job. Relative inputs resolve from the launch directory.

`cy-init-config` and the Python function `dump_config_tree` export an editable wrapper, command base and selected groups. Required inputs appear as `???`. The exporter checks all destinations before writing. Ordinary creation preserves existing files, and `--force` can replace eligible regular files. Export requires no ClearML task. [Configuration guide](../docs/configuration/README.md) · [Export command](../docs/commands/cy-init-config.md)

<details>
<summary>Sources and verification</summary>

- Compose one executable configuration for each experiment command — [Schema and defaults registration](../src/clearml_yolo/entrypoints/hydra/configs.py) · [Composition and precedence tests](../tests/test_release_config.py) · [Dependency injection tests](../tests/test_entrypoint_composition.py)
- Show each Hydra command’s selectable options — [Help composition cases](../tests/test_hydra_help_composition.py) · [Decision history](https://linear.app/sip-ds-team/issue/SIP-208)
- Export editable YAML for one command and detector selection — [Exporter](../src/clearml_yolo/entrypoints/hydra/config_tree.py) · [Export and fresh-process tests](../tests/test_config_tree.py)

</details>

## Validation and sequential sweeps

The owner validates wrapper keys, write destinations and applicable command values before creating the task, and revalidates settings restored by [Agent replay](0300-clearml-experiments.md#executable-inputs-attachments-and-controller-caching). File contents and remote selectors need later checks. Some value checks also occur later, including standalone comparison inference settings and certain training cache/output combinations. Attached configuration files resolve within the invocation context. File roots replace matching context roots, whole-value interpolation preserves types, and only file fields are published.

Direct multiruns expand through Hydra's basic sweeper and launcher. All members' destinations are checked before the first job. Each member then starts sequentially, validates its values and owns its task. Earlier jobs can therefore finish before a later member fails preflight. One launch tag groups the tasks. Concurrent admission belongs to [cy-queue](0309-runtime-and-queue.md#process-ownership-and-queue-admission). [Remaining preflight checks](https://linear.app/sip-ds-team/issue/SIP-276)

<details>
<summary>Sources and verification</summary>

- Validate composed settings before owning a remote task — [Technical contract](../DOCS.md#commands-and-configuration) · [Validators](../src/clearml_yolo/entrypoints/hydra/validation.py) · [Preflight tests](../tests/test_command_preflight.py) · [Original change](https://linear.app/sip-ds-team/issue/SIP-205)
- Run a direct Hydra sweep sequentially — [Configuration guide](../docs/configuration/README.md) · [Sweep expansion](../src/clearml_yolo/entrypoints/hydra/sweeps.py) · [Launch cases](../tests/test_hydra_sweep_configuration.py) · [Grouping tests](../tests/test_multirun_tags.py)
- Resolve file-backed configuration objects in the invocation context — [Resolver](../src/clearml_yolo/entrypoints/hydra/config_resolution.py) · [Publication call site](../src/clearml_yolo/adapters/clearml/session.py) · [Resolution cases](../tests/test_config_resolution.py) · [Configuration publication tests](../tests/test_configuration_publication.py)

</details>

## Composition and effect ownership

Entrypoints construct one dependency bundle per invocation. Application use cases call typed ports, adapters implement them and own SDK effects, and core owns scientific records and algorithms. Live capability objects stay outside the serialized Hydra settings. The same training use case can receive a backend-specific dataset adapter in production or an offline dependency in a test.

Imports and command discovery leave native runtimes and task creation to an explicit call. Import contracts check allowed dependencies. Fresh-process tests separately observe what importing the package actually does. [Composition root](../src/clearml_yolo/entrypoints/composition.py) · [Import behavior tests](../tests/test_architecture.py)

<details>
<summary>Sources and verification</summary>

- Keep scientific logic inside explicit import boundaries — [Architecture](../DOCS.md#architecture-and-data-flow) · [Import rules](../.importlinter) · [Application ports](../src/clearml_yolo/application/ports.py)
- Inject workflow capabilities once per invocation — [Entrypoint tests](../tests/test_entrypoint_composition.py)
- Defer runtime initialization until a capability is invoked — [Package root](../src/clearml_yolo/__init__.py) · [Console import tests](../tests/test_runtime_entrypoints.py)

</details>
