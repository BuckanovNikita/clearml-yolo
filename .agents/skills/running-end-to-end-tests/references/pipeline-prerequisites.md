# Pipeline prerequisites

Use Python and dependencies from `pyproject.toml` and `uv.lock`. Configure ClearML through
explicit supported SDK environment variables or ignored project configuration before
real execution; ambient home/system library configuration is not read.
Infrastructure access, resource capacity and cleanup are supplied by the environment,
not this repository.

Set `CY_HOME` to the invocation workspace (default: launch working directory) for project
datasets, task outputs, runtime library config/cache and invocation-owned scratch.
A stdlib bootstrap runs before SDK imports, preserves `HOME`, confines library config
selectors to the physical project root and scopes temporary files through finalization/uploads.
External runners retain their own defaults. Explicit output/cache paths remain valid elsewhere;
physically home-resident project write destinations warn without rejection. Follow the
[filesystem contract](../../../../docs/filesystem-policy.md).
Preserve source images and existing user configuration.

Build the ground-truth CSV before stages that consume it:

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

New detectors use typed `model.train` and `model.predict` settings, derive COCO working
data from the same CSV and require the optional detector dependencies. DEIMv2 also requires
its verified source checkout and compatible explicit pretrained assets. Follow the
[model guide](../../../../docs/multi-model-backends.md) for presets and restrictions and
the [multi-model acceptance guide](../../../../specs/025-multi-model-backends/quickstart.md)
for the native/download/comparison matrices. Use `uv run --frozen --no-sync` after preparing
an optional-backend environment so verification does not remove its installed extras.

Select the backend's supported device, batch and precision controls for the environment.
Model commands and `cy-export` default `queue.enabled=true` and `autogpu.enabled=true`: whole-GPU FIFO
reservations, fresh supervised children and automatic selection. Queue disabled retains
direct availability waiting; automatic selection disabled retains exact queued identities
and training order using the enabled-phase UUID union. Both disabled preserves native
settings without project GPU discovery/waiting/replacement. CPU/MPS bypass telemetry.
Automatic mode treats native IDs as demand: one for an integer/null/empty/`cuda`, list
length for lists, one per `-1`, zero for CPU/MPS; GPU inference requires one. No separate
GPU-count setting. Exact queued mode requires concrete selectors within inherited CUDA
visibility and rejects ambiguous automatic values. Neither switch disables tracking.
CPU ONNX export has zero GPU demand; engine build and verification require one GPU.

Before acceptance, establish sufficient whole-GPU visibility and preserve unrelated compute
users. Verify no task while waiting, one runner/two waiters on one GPU, interruption with
owned process cleanup before capacity release, compatible cross-project coordination and
replay admission limits. Verify multi-GPU cleanup/contraction retains the intended inference
device; record physical multi-GPU execution unverified when unavailable. Queued sweeps use
the concurrent project launcher; queue-disabled sweeps use sequential BasicLauncher.
Mixed queue modes fail before admission. Unknown telemetry, unsupported MIG and excessive
demand fail clearly in scheduling modes. See the
[GPU execution contract](../../../../specs/022-simple-gpu-wait/contracts/execution.md).

Optional FiftyOne workers use finite preflight/publication/lock deadlines of 60/900/30
seconds and no GPU/queue/ClearML ownership. Fault injection must prove bounded import,
work and shutdown plus at most ten seconds cleanup; publication success requires zero
exit and a matching complete receipt. Errors warn and preserve computation; cancellation
remains cancellation. Project config access tracing and scratch cleanup are required
acceptance evidence. See [runtime isolation](../../../../docs/runtime-isolation.md).

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
