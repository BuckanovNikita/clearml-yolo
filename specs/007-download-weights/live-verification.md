# Live native-preparation acceptance — 2026-10-29

## Scope and inspected source

Two actual CY pipeline invocations ran on the shared ClearML stand: a CPU
candidate without a baseline, followed by a single-GPU candidate against the
promoted CPU baseline. This supplements the [offline native-cache evidence](native-verification.md)
and checks the maintained [publication contract](../000-baseline/spec.md#required-publication-and-task-lifecycle).
No product code, tests, dependencies, server configuration or scheduling policy
were changed by this acceptance task.

Execution used the current source tree based on commit
`0037059dcf8a8ed16582f256b98036480cabd842`, including the uncommitted feature
implementation. `source-state.json` records hashes of the actual affected runtime
modules and evaluator/result-export modules; HEAD alone does not identify those
local changes. Observed installed versions were CY 0.40.0, Ultralytics 8.4.184,
Torch 2.14.1, Torchvision 0.29.1, timm 1.0.30, RF-DETR 1.11.2,
ClearML 2.1.10 and the approved digital-metrics 0.7.0 integration.

## Inputs and native settings

The final isolated project tag was
`clearml-yolo-codex-20261029-cy007-native-20vr`. Its twelve synthetic images have
twelve different SHA-256 hashes, with four images in each of train, validation
and test. Each split includes one deliberately empty image. Validation and test
have disjoint paths, names and content hashes. The generator uses related simple
scenes; this is functional acceptance, not evidence of statistical independence
or model accuracy.

`inputs.json` binds every image's name, split, dimensions, empty status and hash
to ground-truth CSV SHA-256
`1805b56d24f471836cc515954cfffcb524248d027e8319fde319a677928ed73c`.
Both runs use the same current input bytes and labels `rectangle` / `other`.

The editable Hydra tree was generated with the real `cy-init-config` command.
Its native group selects an unrelated filename, `unrelated-live-design.yaml`,
and explicit `pretrained=yolo11n.pt`. Both invocations use one epoch, image size
64, batch two, zero loader workers and `compile=false`. Training/prediction
devices are CPU for the first invocation and device zero for the second.
The requested model, pretrained filename and other custom fields remain present
in ClearML's independently read-back executable configuration. The downloaded
best models retain the two-class native architecture and reload for inference.

The stand preflight reported GO. Before direct GPU training, device zero had
29,052 MiB free, zero utilization and no observed competing training or held
queue GPU lock. Existing desktop memory use and the parent's idle pytest CUDA
context were preserved. Direct CY execution uses explicit native device
selection; the queue's automatic admission threshold was not applied to this
direct invocation. No unrelated service or process was stopped.

## Observed outcomes

| Invocation | Completed task | Best Output Model | Forced artifact downloads |
| --- | --- | --- | --- |
| CPU candidate; automatic baseline absent | `5ff1b3cc590547529ab3a85b98bb783c` | `fdd83344e4a44eb6b98d754b68c9ad0b` | Nine required artifacts |
| GPU candidate; CPU task promoted with `prod` | `1443a54ce9e14dc2955fe84e572cff28` | `62d96c4753564fccb230e390bf841e56` | Fifteen required artifacts |

Both commands exited zero and finalized exactly one owner task and one best
Output Model each. The CPU run retained candidate metrics and candidate-only
comparison dashboards while recording the missing-baseline skip. The GPU run
automatically selected the promoted CPU task and produced the paired comparison,
excluded-class CSV, and developer/business reports. The paired XLSX retains its
`Сравнение` sheet.

Every applicable publication was force-downloaded through the real SDK and
checked for a nonempty file; workbooks were opened. The downloaded model hashes
match the respective local native best checkpoint:

- CPU: `6068dbe00d49fef6193c8aac4d252d63fbe5a745d3867a4c71c925bcc3111650`.
- GPU: `0ad613eeeb9ff5587d3166af2562e28ccfea91f42331b4baceb1026aaad64fd5`.

The publication/provenance checks also passed:

- Ground-truth publication preserves all twelve source rows, image identities,
  labels, geometry and unique source-row IDs. Combined prediction contexts retain
  all selected validation/test images, including empty images.
- Full-precision calibration CSV values equal the frozen validation/test maps
  and best-model threshold metadata, associated with the actual checkpoint hash.
  Comparison baseline rows use the CPU thresholds unchanged; candidate rows use
  the GPU thresholds. Published below-threshold flags follow strict `<`.
- Both checkpoints reinfer the same four current test images. Prediction
  provenance hashes match the consumed checkpoint and prediction bytes. Effective
  paired inference matches at confidence 0.001, IoU 0.7, normalized 64 × 64,
  batch two, device zero, rectangular preprocessing and compilation disabled.
- Real SDK plot readback contains one current-model confusion chart per selected
  split and one test precision-recall chart, without baseline chart series.
  Confusion payloads have Counts, Row %, Column % and Overall % controls with
  exactly one heatmap initially visible.
- The independent monitor observed GPU-task console and scalar output while the
  task was still in progress. Native GPU AMP checks passed using the prepared
  auxiliary checkpoint.
- A boundary observer delegated to the real startup preparation function in each
  invocation. Each pipeline called it once with `automatic=True` and received
  `skipped=True`, 56 assets and zero failures for fingerprint
  `968f0ed58567cac86b7110c3193895f76eec5ea531dd8bd61ded434bf88a95c3`.
  Persisted Ultralytics settings stayed byte-for-byte unchanged.

The complete offline manual preparation probe was also rerun against the final
Hub implementation before these live results: 56 assets, zero failures, exit
zero, followed by an automatic skip with the same fingerprint.

## Evidence, reproduction and cleanup

Retained private evidence is beneath
`.tmp/cy007-native/live-evidence/clearml-yolo-codex-20261029-cy007-native-20vr/`:
`inputs.json`, `source-state.json`, `provenance-verification.json`, live scalar/
console observations, exact harness snapshots, and each invocation's command,
console, configuration, automatic-preparation result, settings hash, artifact/
model hashes and downloaded bytes. `local-run/` preserves the generated Hydra
tree, inputs, native outputs and comparison provenance after stand cleanup.

With the installed environment skill supplying a fresh Codex tag, credentials
and task-owned run directory, the private controller executes these stages:

```bash
uv run --frozen --no-sync python .tmp/cy007-native/live_acceptance.py setup
uv run --frozen --no-sync python .tmp/cy007-native/live_acceptance.py run --label cpu --device cpu
uv run --frozen --no-sync python .tmp/cy007-native/live_acceptance.py verify --label cpu
uv run --frozen --no-sync python .tmp/cy007-native/live_acceptance.py promote --label cpu
uv run --frozen --no-sync python .tmp/cy007-native/live_acceptance.py run --label gpu --device 0
uv run --frozen --no-sync python .tmp/cy007-native/live_acceptance.py verify --label gpu --paired
uv run --frozen --no-sync python .tmp/cy007-native/live_contracts.py
```

An earlier exploratory fixture used distinct filenames for duplicate image bytes
across splits. Its outputs are retained under the separate `h49i` tag's private
evidence directory and are excluded from final split-independence acceptance.
The corrected runs above use a fresh isolated project and hash-checked inputs.

The environment cleanup helper removed both owned stand projects and their
tag-named local run directories after evidence backup. Readback confirmed zero
projects and zero tasks under each prefix. The previously minted, unused Claude
tag was also checked empty and its owned local directory removed. Logs are
`live-initial-cleanup.log` and `live-final-cleanup.log` under
`.tmp/cy007-native/`. Cached assets, preparation receipts, downloaded evidence and
unrelated workloads remain intact. Task/model IDs above are retained lineage;
the disposable stand objects have been deleted.

Interactive browser behavior and a strict telemetry delivery-latency bound were
not measured; chart checks inspect actual published SDK payloads. Optional
FiftyOne publication was explicitly disabled. This task does not establish
physical multi-GPU execution, queued execution, representative accuracy,
CPU/GPU numerical parity, paired-package release compatibility or the parent's
canonical-check/review outcomes.
