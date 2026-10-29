# Native cache verification — 2026-10-29

## Scope and method

These checks exercise real prepared checkpoints through installed native loaders in
fresh CPU processes. They do not establish model quality, GPU AMP numerical parity,
ClearML publication, queued execution or the parent integration run's outcomes.

The retained private harness is `.tmp/cy007-native/native_probe.py`, with controller
`.tmp/cy007-native/run_native_probes.py`. Both are ignored task artifacts. Run from
the repository root:

```bash
uv run --frozen --no-sync python .tmp/cy007-native/run_native_probes.py
uv run --frozen --no-sync python .tmp/cy007-native/run_native_probes.py --recovered --rf-presets nano,small,medium,large
uv run --frozen --no-sync python .tmp/cy007-native/complete_native_preparation.py
```

The controller retains a separate log for every scenario and records exit codes,
commands, date and harness SHA-256 in `.tmp/cy007-native/native-results.json`.
All 12 initial scenarios exited zero. The recovered-checkpoint command additionally
records successful all-four RF-DETR and DEIM scenario exits in `recovered-results.json`.
The harness hides GPUs, caps CPU threads, sets explicit task-owned SDK selectors,
and disables network connections at Python socket/DNS and HTTP boundaries. Hub and
Transformers offline flags are also enabled. Denied SDK connectivity probes are
recorded; their presence does not mean a connection succeeded. Native settings
bytes are compared before and after each scenario.

Versions observed: Python 3.12.13, Ultralytics 8.4.184, Torch 2.14.1,
Torchvision 0.29.1, timm 1.0.30, RF-DETR 1.11.2 and Hugging Face Hub 2.2.0.

The parent's first real preparation pass reported **50 prepared assets and six
failures** in `.tmp/cy007-native/preparation.log`: DEIMv2 small/medium and all four
RF-DETR weight endpoints timed out. This is an incomplete bulk-download outcome,
independent of successful cache-discovery checks below. The harness does not
start another bulk pass.

## Observed native behavior

| Scenario | Result | Evidence under `.tmp/cy007-native/` |
| --- | --- | --- |
| All 44 maintained YOLO detection filenames, bare native lookup from a different working directory | Passed; each actual resolved checkpoint path and SHA-256 recorded | `yolo-names.log` |
| Suffixless maintained names `yolo11n` / `yolov5nu`, legacy `yolov5n.pt`, and explicit absolute local checkpoint | Passed native inference on a 97 × 129 image | `yolo-aliases.log` |
| The same lookups with a relative weights root in another working directory | Passed; native resolution follows the consuming process's cwd | `yolo-relative.log` |
| Arbitrarily named custom YAML plus `pretrained="yolo11n.pt"` | Passed one real CPU epoch; custom two-class architecture retained and initial first convolution exactly matches the named pretrained checkpoint | `custom-string.log` |
| Custom YAML plus relative explicit `pretrained="local-checkpoint.pt"` | Passed one real CPU epoch; relative checkpoint selected from the consuming cwd and initial pretrained convolution verified | `custom-relative.log` |
| Custom YAML plus boolean `pretrained=True` and `pretrained=False` | Both passed one real CPU epoch; boolean values retained and native YAML initialization preserved | `custom-true.log`, `custom-false.log` |
| Fresh spawned worker loading `yolov5n.pt` | Passed; native alias resolves to cached `yolov5nu.pt` | `worker.log` |
| Native AMP auxiliary `WEIGHTS_DIR / "yolo26n.pt"` lookup | Passed actual checkpoint loading; CPU `check_amp` returns false as expected | `yolo-aliases.log`, `yolo-relative.log` |
| Torchvision ResNet-50 / ResNet-101 default weights | Passed native pretrained initialization and finite CPU forward outputs of shape `[1, 1000]` | `torchvision.log` |
| timm ConvNeXt-Tiny, Swin-Tiny and DINOv2-Small, ordinary `pretrained=True` | Passed native pretrained initialization and finite CPU forward outputs | `timm.log` |
| `hf-hub:timm/convnext_tiny.fb_in22k_ft_in1k` model construction | Passed with native cached configuration and weights | `timm.log` |
| DEIMv2 pinned source and small/medium YAML execution preparation without pretrained backbone initialization | Passed offline; source is manifest-validated and supplied automatically | `deim-source.log` |
| All four RF-DETR ordinary pretrained model initializers | Passed offline using native files; SDK confirms each file's registered MD5 before constructing its real model | `rfdetr.log` |
| DEIMv2 small/medium pretrained execution preparation and model loading | Passed offline with recovered real backbones, strict native checkpoint loading and CPU 128 × 128 forward outputs `pred_logits` / `pred_boxes` | `deim.log` |

The loaded YOLO26n auxiliary checkpoint SHA-256 is
`9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`.
The DEIM source revision is `1d2ca42171570c713e78fc6a766ec5104b7f4724`;
its source-tree manifest digest is
`f3dc7b1fd6ba46b3a495b5367a4a890c7e4bd6ef5355cb5f3f68fdaed15fd823`.
These identify observed artifacts; synthetic training metrics are not quality evidence.
DEIMv2 small backbone SHA-256 is
`2053b865f4e2673fba3f95f7e7e54ad5ee18143885e3ad27eaabb5b3b9919738`;
medium is `470b65d9a7704973ae105057f7ec7a4c85f853bc379a7bfbcc49ecc80a17e25b`.
Those checkpoints and RF-DETR nano/large were recovered by the parent from prior
validated native caches, then resolved into the new task's normal destinations.
Their offline reuse succeeds; the first attempt's upstream timeout remains an
observed download failure.

## RF-DETR small/medium recovery provenance

The original Google-hosted objects timed out, including alternative official
Google Storage API probes. Recovery used public, pinned Hub mirrors containing
the exact original registry-approved checkpoint bytes. The resolver receives each
file as an explicit `cache_candidates` input; its canonical RF-DETR URL, approved
registry MD5, SDK revision and destination remain unchanged. Source files are
preserved, and both recovered and published files are revalidated through the
project's normal structural/checksum validator.

| Preset | Pinned mirror | Bytes | Official registry MD5 |
| --- | --- | --- | --- |
| small | [LibreYOLO/LibreRFDETRs at 7c58adde8546c5352eec0ffb8b4ba3c0be25a838](https://huggingface.co/LibreYOLO/LibreRFDETRs/resolve/7c58adde8546c5352eec0ffb8b4ba3c0be25a838/rf-detr-small.pth) | 386045550 | `fb37061c1af7bace359c91b723a8d5c1` |
| medium | [LibreYOLO/LibreRFDETRm at 1ce01da1d8a1367922685ef4ae9619a91637acc8](https://huggingface.co/LibreYOLO/LibreRFDETRm/resolve/1ce01da1d8a1367922685ef4ae9619a91637acc8/rf-detr-medium.pth) | 404992918 | `7223f764a87b863f02eb8d52bf0ce2ee` |

Small SHA-256:
`d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33`.
Medium SHA-256:
`749ff6071828aaffac63e204c4f4135ed3d6cdae4d702e086c360edc3b5768c8`.
Native canonical URLs remain
`https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth`
and `https://storage.googleapis.com/rfdetr/medium_coco/checkpoint_best_regular.pth`.
Detailed recovery evidence is retained in `.tmp/cy007-native/recovery.json`.

## Completed offline preparation and receipt reuse

After recovery, `complete_native_preparation.py` invoked the real manual command
entrypoint with all socket and HTTP access blocked. It exited zero and reported
**56 prepared assets, zero failures**. A subsequent actual
`prepare_catalogue(automatic=True)` call returned `skipped=True`, the same 56
resolved records and no failures for fingerprint
`968f0ed58567cac86b7110c3193895f76eec5ea531dd8bd61ded434bf88a95c3`.
The successful manual retry replaced the earlier partial-failure receipt.

This establishes complete cache reuse and unchanged-catalogue automatic
suppression against real native assets. The process denied Ultralytics' optional
`one.one.one.one` / `dns.google` connectivity detection; it needed no asset
transfer and made no successful connection. The separate denied optional
Albumentations version probe during RF-DETR import is retained in the evidence.
Ultralytics settings remained byte-for-byte unchanged. Logs and structured records
are `.tmp/cy007-native/final-offline-preparation.log` and
`.tmp/cy007-native/final-offline-results.json`.

Each native training run uses four synthetic training images and two validation
images, with empty examples, one epoch and CPU execution. External experiment
integrations are disabled only in memory for these direct SDK probes, then
restored. Persisted Ultralytics settings remain byte-for-byte unchanged. The
custom YAML retains the native `scales` order: sorting those keys alphabetically
would change the SDK's fallback scale for an unrelated filename and invalidate
the fixture's expected pretrained tensor shapes.

## Native limitations and remaining checks

- Ultralytics 8.4.184 does not recognize the suffixless legacy form `yolov5n`:
  it raises `FileNotFoundError`. Its supported legacy filename `yolov5n.pt` and
  supported suffixless canonical form `yolov5nu` both load offline. The explicit
  characterization is retained in `legacy-suffixless.log`; the harness does not
  rewrite user inputs to broaden SDK behavior.
- GPU AMP numerical checks were not run by this CPU harness. The exact auxiliary
  cache lookup used by the installed check was exercised separately.
- All maintained asset families now have separately observed offline native
  loading evidence. The initial upstream download timeouts remain recorded;
  recovery does not imply those endpoints became reachable.
- Pipeline/ClearML integration, native GPU execution and paired CY/queue checks
  belong to the parent's separately recorded verification.
