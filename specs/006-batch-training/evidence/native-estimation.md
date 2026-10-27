# Native estimator evidence — 2026-10-26

These are serialized single-GPU execution observations from feature 006's
uncommitted working tree. They do not establish multi-GPU acceptance, useful
detector accuracy or an unconstrained maximum batch. Machine identities, exact
requests, logs, receipts and catalogue snapshots remain in the private task bundle.
No unrelated workload was stopped; failed telemetry was not waived.

## Resolution-960 catalogue attempt

The CLI attempted all 64 registered cases: 44 pretrained YOLO variants and 20
native presets. Native families were ordered first through the documented model
filter. Settings were nominal resolution 960, selected GPU count one, synthetic
150 classes and 300 objects per image, default precision/compilation/EMA, 90%
memory budget, search ceiling one and 300-second trial-group timeout.

```bash
uv run --frozen --no-sync python -m clearml_yolo.entrypoints.batch_estimate \
  --imgsz 960 --devices 0 --search-limit 1 --trial-timeout 300
```

The actual invocation additionally supplied the complete catalogue through
`--models` to order native families first. Its exact argv is retained. It exited
1 after processing every case. The implementation fingerprint was
`batch-v1:6cdab16d1f5987950e5dbf1c9b3933babc8ec818dd3cec9d06fa0f1e32426003`.

| Outcome | Cases |
| --- | ---: |
| Independently confirmed, ceiling-limited global/per-GPU batch one | 13 |
| Busy GPU or unavailable idle telemetry | 41 |
| Active utilization without attributable compute PIDs | 8 |
| PID absent from the ownership snapshot | 1 |
| Numeric telemetry replaced by a driver error string | 1 |

The thirteen confirmed cases were DEIMv2 Small, RF-DETR Large, all six Faster
R-CNN presets, and FCOS ResNet-50, ResNet-101, Swin-Tiny, DINOv2-Small and
DINOv3-Small. Each completed five warm-up and ten measured actual optimizer
updates plus native bounded validation, then repeated successfully in a fresh
process group. Both per-rank receipts and aggregate whole-device memory envelopes
were retained. No confirmed result claims capacity beyond the imposed ceiling.

The other 51 cases have no usable estimate. Many were rejected before model
execution, so this is complete **attempt coverage**, not complete native model
execution coverage. In particular, no YOLO case obtained a confirmed recommendation
in this run. Some YOLO worker/optimizer paths completed actual training and native
validation before a later path or repeat was rejected; those partial receipts do
not promote the failed case to success.

## Additional checks and corrections

Before that matrix, FCOS ResNet-50 at nominal 800 passed two fresh CUDA trials
with five warm-up and ten measured optimizer updates and bounded validation.
The aggregate recorded peak in each was 4,618,977,280 bytes, including whole-device
telemetry; worker receipts kept allocator and non-allocator observations separately.
The result was ceiling-limited at global batch one.

Earlier probes exposed native AMP update accounting and YOLO compiled-loss/validation
issues, subsequently corrected and tested. The ordinary test suite had previously
created a CUDA context when visibility was not hidden; contamination detection
correctly rejected overlapping probes. Subsequent ordinary tests used empty CUDA
visibility. Interrupted catalogue runs retained failed/incomplete snapshots and
their owned workers were cleaned up.

A later deterministic CPU process test confirmed an ownership-snapshot race: an
owned compiler child can start after the snapshot but before GPU process telemetry.
It was falsely rejected as foreign; a fresh birth-validated scan recognizes it.
This does not identify the vanished PID from the matrix. The correction refreshes
ownership after telemetry collection and retains conservative rejection of unknown
activity. Malformed driver telemetry receives an explicit unavailable-telemetry
failure. These implementation changes invalidate prior catalogue compatibility;
old receipts remain historical evidence, not current reusable recommendations.

A fresh nominal-resolution-128 catalogue invocation after that correction exited
2 at the idle preflight, without launching a trial. Windows GPU engine counters
subsequently attributed continuing video/graphics activity to existing playback
processes. Their identities and read-only observations are kept in the private
task bundle. No process was stopped and the idle requirement was not relaxed.

## Remaining physical gates

The final catalogue run, a search reaching an actual capacity boundary and the
new four-family physical DDP harness remain separate acceptance work. The selected
host exposes only one GPU. Real NCCL execution across multiple devices, rank-fault
recovery and single-owner publication during native multi-GPU training are not
established by CPU/Gloo tests or by these single-GPU observations.

All-six real pretrained CPU round trips are recorded separately in
[FCOS pretrained evidence](fcos-pretrained.md); actual tagged ClearML publication
and artifact downloads are in [FCOS live evidence](fcos-live.md).
