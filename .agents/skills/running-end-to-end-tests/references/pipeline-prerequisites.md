# Pipeline prerequisites

Use Python and dependencies from `pyproject.toml` and `uv.lock`. Configure ClearML through
its supported SDK environment variables or user configuration before real execution.
Infrastructure access, resource capacity and cleanup are supplied by the environment,
not this repository.

Set `CY_HOME` to the invocation workspace (default: launch working directory) for project
datasets, task outputs and owned temporary files. General runner/library caches and Python
bytecode retain their normal defaults. Explicit output/cache paths remain valid elsewhere;
physically home-resident project write destinations warn without rejection. Follow the
[filesystem contract](../../../../docs/filesystem-policy.md).
Preserve source images and existing user configuration.

Build the ground-truth CSV before stages that consume it:

```bash
uv run cy-ground-truth data_yaml=data.yaml output=ground_truth.csv
```

`cy` composes the packaged wrapper configuration. Generate examples with
`cy-init-config configs`, then paste native YAML into `configs/ultralytics/default.yaml`.
Prediction overrides live in `configs/ultralytics_predict/default.yaml`. Invoke generated
examples with `--config-dir configs --config-name cy`; override shared values with
`ultralytics.key=value` and prediction values with `ultralytics_predict.key=value`.
Raw `cfg` loading and nested `train.ultralytics`/`predict.ultralytics` are removed.

ClearML is required for execution commands. Pass `clearml.project_name` and
`clearml.tags` explicitly when isolating runs. `run_dir` routes pipeline output;
conflicting stage paths or native training `project`/`name` values fail. Standalone
stages require explicit inputs. `cy-init-config DIRECTORY [--force]` writes only
editable configuration examples without creating a ClearML task.

Select native `device`, `batch`, `amp` and `compile` settings for the environment. The five model
commands derive whole-GPU demand from native `device` and poll availability before native/ClearML
initialization. There is no separate GPU-count setting. A training integer means one GPU, a list
uses its length, every automatic `-1` contributes one, null/empty/`cuda` means one, and `cpu`/`mps`
means zero. GPU inference requires one device; a pipeline waits for the maximum training/inference
demand. Keep inherited `CUDA_VISIBLE_DEVICES` accurate for the test environment; selected logical
indices follow its order without rewriting it.

Before a native wait test, establish that the request fits the visible whole-GPU set and that
unrelated compute processes do not own candidate devices. Verify busy-to-free waiting, no task
while waiting, interruption and direct calling-process execution. CPU/MPS bypass NVIDIA telemetry.
The own PID is ignored for sequential jobs; other compute users and unavailable telemetry prevent
selection. Availability gives no reservation or fairness guarantee between concurrent commands.
Multi-GPU acceptance must observe native training/DDP cleanup and confirm prediction/comparison
use the first selected logical device. A standard BasicLauncher sweep must execute sequentially
with separate tasks, Hydra output/environment/chdir behavior and normal failure propagation.
Record physical multi-GPU execution as unverified when it was not exercised. No queue state is
created or consumed; old state remains untouched. The application does not tune batches or support
MIG. See the [GPU execution contract](../../../../specs/022-simple-gpu-wait/contracts/execution.md).

Full comparison requires validation/test data and exact baseline thresholds. Candidate
thresholds come from validation only. Both checkpoints must use the same current test
image membership and inference settings; reports consume the resulting `comparison_dir`.

Preserve checkpoint `.identity.json` and prediction `.provenance.json` sidecars when
moving local inputs. Stored identity takes precedence over a fallback label and hashes
must match the consumed checkpoint/prediction bytes. For inputs without identity, set
`model_label` on prediction, validation, metrics or a pipeline with training disabled;
use `baseline_model.label`/`candidate_model.label` for local comparison references and
`baseline_label`/`candidate_label` for reports over legacy manifests. Such labels retain
`Training task: unavailable` and do not register models. Include source-identity readback,
real workbook banners/print titles and plot captions in acceptance; use project workbook
adapters when checking metric values beneath banners. See the
[identity contract](../../../../specs/014-evaluation-publication/contracts/publication.md#source-identity-on-new-results).
