# Pipeline prerequisites

Use Python and dependency bounds from `pyproject.toml` and selected versions from
`uv.lock`. Detector, ONNX export and queue TUI dependencies install by default;
project extras are removed. Keep development tools in the separate `dev` group. Configure ClearML
through normal SDK environment/user configuration; external selectors are valid.
Infrastructure access and resource capacity come from the environment, not this repository.

Set `CY_HOME` to the invocation workspace (default: launch directory) for project datasets,
outputs and scratch. Bootstrap preserves SDK configuration/cache selectors, cwd discovery,
credentials, bytecode and global temporary defaults. Project temporary callsites use an
explicit project-contained directory; `CY_RUNTIME_TEMP_ROOT` must remain under resolved
`CY_HOME`, including through symlinks. Arenas remain
retained after every exit outcome, with no startup scans/recovery or recursive deletion.
Deliberate maintenance requires an idle workspace and descendants. Invalid dataset entries
are preserved and fail clearly; native lock failures have no soft fallback. See the
[filesystem contract](../../../../docs/filesystem-policy.md). Preserve source images,
existing user settings and old local SDK caches; reuse old local selectors explicitly.

Supply a local ground-truth CSV or a finalized ClearML dataset containing only root
`dataset.csv`; additional files or linked entries must fail before download.
Select the dataset with `ground_truth={dataset_id:DATASET_ID}` or
`ground_truth={project_name:annotations,name:ground-truth,version:"1.2.0"}`;
quote the whole mapping override in a shell. Version is optional only for the
project/name pair. The materialized CSV is unchanged and image references are not
remapped. Absolute references remain absolute, and relative references resolve
beside the downloaded CSV. Preserve accessible media at those references. Use a fresh
CSV-only dataset lineage when testing transport exclusion of historical media,
because the SDK can fetch whole archive chunks into its cache.

Local CSV execution warns once; nested stages reuse the resolved source. Verify
help/configuration inspection and queue submission do not download datasets, while
execution and replay resolve once and preserve the requested selector alongside
actual dataset identity, version and CSV digest. Compare a task-owned CSV-only
dataset's downloaded bytes and downstream results with its local source before
claiming retrieval or parity. See the
[source contract](../../../../docs/input-provenance.md#ground-truth-sources).

For existing YOLO annotations, build the CSV before consuming it:

```bash
uv run --frozen --no-sync cy-ground-truth data_yaml=data.yaml output=ground_truth.csv
```

`cy` composes the packaged wrapper configuration. For default YOLO, generate examples with
`cy-init-config configs`, then paste native YAML into `configs/ultralytics/default.yaml`.
Prediction overrides live in `configs/ultralytics_predict/default.yaml`. Invoke generated
examples with `--config-dir configs --config-name cy`; override shared values with
`ultralytics.key=value` and prediction values with `ultralytics_predict.key=value`.
Raw `cfg` loading and nested `train.ultralytics`/`predict.ultralytics` are removed.

ClearML is required for execution commands. Pass `clearml.project_name` and
`clearml.tags` explicitly when isolating runs. `run_dir` routes pipeline output;
conflicting stage paths or native training `project`/`name` values fail. Standalone
stages require explicit inputs. `cy-init-config DIRECTORY [--command NAME] [--model PRESET] [--force]`
writes one selected wrapper (default `cy`) without creating a task. Existing model commands
include both native groups for default YOLO; new detector selections write only their
`model/<backend>/<preset>.yaml`. `cy-export` defaults to Faster R-CNN ResNet-50-FPN and
accepts only Faster R-CNN presets; `cy-metrics`, `cy-report` and `cy-ground-truth` use no model group.
Only selected files/parents participate in overwrite checks.

New detectors use typed `model.train` and `model.predict` settings and derive COCO working
data from the same CSV using the default runtime dependencies. DEIMv2 also requires
its verified source checkout and compatible explicit pretrained assets. Follow the
[model guide](../../../../docs/multi-model-backends.md) for presets and restrictions and
the [multi-model acceptance guide](../../../../specs/025-multi-model-backends/quickstart.md)
for the native/download/comparison matrices. Use `uv run --frozen --no-sync` after preparing
a backend environment so verification does not remove additional external runtime packages.

Select the backend's supported device, batch and precision controls for the environment.
Direct commands and `cy-export` run their explicit native devices without queue discovery,
reservation or waiting. `cy -m` uses ordinary sequential Hydra BasicLauncher. Queue count
or exact-device selection belongs to `cy-queue submit --gpus N -- ...` or
`cy-queue submit --devices 0,2 -- ...`; remove native GPU overrides from queued configurations.
Explicit CPU phases remain CPU. Queued training uses the complete allocation and inference
its first GPU. After native training returns and unused model memory is released,
the external guardian durably shrinks the claim, releases extra GPU locks and updates
public allocation before acknowledging. Verify another eligible job can use released
GPUs during inference. Unless explicitly freed, retain the first GPU through pipeline/descendant exit; absent
a training-finished notification, retain the full allocation. If acknowledgement is
lost after durable shrink, verify the pipeline stops before inference and cleanup
follows the remaining durable claim without restoring released extras.
Verify cleanup uncertainty retains recovery evidence without retroactively failing a
completed successful ClearML task, while
required computation/upload failures still fail. Live guardian discovery is scoped
to its descendants; recovery keeps conservative global ownership proof.

A persistent same-user worker executes private immutable snapshots in fresh processes;
closing a submission terminal or TUI does not stop it. No ClearML task exists while waiting.
Automatic availability uses only NVML used VRAM strictly below 2 GiB (2048 MiB),
independently of model/compiler memory fit. The limit is fixed and checked again
immediately before launch; exactly 2 GiB is busy. Current reservations and explicit
holds stay excluded across queue roots. Stale unlocked records alone do not veto
admission. Unknown telemetry/protocol, unsupported MIG and damaged
coordination stop admission. Excessive whole-GPU demand remains pending with its reason.
CPU ONNX export needs no GPU; engine build and verification require one GPU.

Operator commands use physical `nvidia-smi` indexes independently of CUDA visibility;
public output uses those indexes or short absent-device labels, with full GPU UUIDs
and claim tokens kept internal. Verify `gpu disable INDEX`, `enable INDEX`, `free INDEX`
and `release INDEX` require no supplementary arguments. Free/release clears only the
selected GPU's existing reservations and holds across roots without memory/process
checks, signals or original queue access. It preserves sibling reservations, processes
and job outcomes, and older guardian writes cannot affect newer reservations. The next
job still needs fresh memory admission; manual freeing grants no persistent bypass.

Before acceptance preserve unrelated compute and establish available hardware. Verify
matching direct/queued settings, one/five physical GPUs eager/compiled, independent live
ClearML console/scalar readback, cancellation and repeated signals. Exercise worker death,
guardian death, detached native ranks and fail-closed owner recovery. Two real users must
reorder each other's pending jobs without executing/cancelling the other's work; two hosts
sharing NFS retain independent order/capacity. Mount aliases and multiple queue roots must
not duplicate local GPU allocation. Record unavailable hardware/NFS and unresolved native
errors as acceptance gaps. See the [queue contract](../../../../docs/queue.md).

Optional FiftyOne workers use finite preflight/publication/lock deadlines of 60/900/30
seconds and no GPU/queue/ClearML ownership. Fault injection must prove bounded import,
work and shutdown plus at most ten seconds cleanup; publication success requires zero
exit and a matching complete receipt. Errors warn and preserve computation; cancellation
remains cancellation. Normal SDK configuration discovery, unchanged selectors/global temp
settings and retained project scratch are required acceptance evidence; process cleanup and
receipt validation remain independent requirements. See [runtime isolation](../../../../docs/runtime-isolation.md).

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

Native detector metadata is embedded in the checkpoint archive, so standalone copies retain
backend, preset, foreground labels and preprocessing even without a `.model.json` sidecar.
When present, that sidecar's hash must match. This descriptor is distinct from training
provenance in `.identity.json`. Raw comparison checkpoints need explicit backend, preset,
class strings and preprocessing assertions, plus DEIM source access when applicable.

## Detection identity acceptance

Use the [input/provenance contract](../../../../docs/input-provenance.md) for relative
media resolution, literal CSV identities and version 2 cache separation. Exercise
standalone prediction/comparison and `skip_train` from another cwd, including Hydra
chdir and a conflicting same-named file. Preserve `NA`, `NULL`, `nan`, `None`, numeric
strings, Unicode and empty backgrounds in source/cache/published rows. Compare unchanged
cases with identical CSV, checkpoint and settings; test corrected cases separately.
Require canonical `name` for evaluation; raw `stem`/`path` exports retain their names
and `not_evaluated` status. Download hash-bound provenance and canonical result rows
before claiming publication preserves naming mode and source lineage.
