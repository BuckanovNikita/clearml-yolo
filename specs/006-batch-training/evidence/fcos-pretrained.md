# All-six FCOS pretrained CPU round trips — 2026-10-26

## Scope

All six registered FCOS presets passed real pretrained initialization, finite
backward computation, one-epoch training, best-checkpoint selection and copied
checkpoint prediction in fresh processes. This closes the all-six **CPU native
round-trip** portion of T017. The separate [live record](fcos-live.md) covers
ClearML publication for ResNet-50; this run created no ClearML resources.

Execution used the uncommitted feature working tree based on
`9fd2294ab219c534fcce87b59eea7b56e9d01173`, with the existing approved dependency
environment. The worker changed only this evidence file and ignored acceptance
scripts/results. No application/test/dependency changes, installation, commits,
release operations or GPU use occurred. This documentation-only addition changes
no module interfaces, imports or effect ownership; the parent owns feature-wide
architecture acceptance.

## Method and commands

The fixture reused actual PNG bytes from the live record: twelve non-square
synthetic images, four per disjoint train/validation/test split, with literal
foreground strings `0`, `NA`, `класс-猫` and one empty image per split. COCO category
IDs were zero-based and the loaded first target label was exactly integer zero.
Image hashes were unchanged after execution.

Each preset ran sequentially with `CUDA_VISIBLE_DEVICES=''` before every Python
invocation. The harness asserted CUDA unavailable, used one Torch intra-op and
inter-op thread, and set OpenMP/MKL/OpenBLAS thread counts to one. Training used
CPU, one epoch, batch two, 128×128 letterbox canvas, zero workers, FP32, AdamW,
learning rate `0.0001`, seed zero and native EMA.

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

CUDA_VISIBLE_DEVICES='' CY_HOME="$NATIVE_WORKSPACE" \
  uv run --frozen --no-sync python "$EVIDENCE_DIR/acceptance.py" prepare

for preset in resnet50_fpn resnet101_fpn convnext_tiny swin_tiny \
  dinov2_small dinov3_small; do
  CUDA_VISIBLE_DEVICES='' CY_HOME="$NATIVE_WORKSPACE" \
    uv run --frozen --no-sync python "$EVIDENCE_DIR/acceptance.py" train "$preset"
  CUDA_VISIBLE_DEVICES='' CY_HOME="$NATIVE_WORKSPACE" \
    uv run --frozen --no-sync python "$EVIDENCE_DIR/acceptance.py" reload "$preset"
done
```

`prepare_model_assets(..., training=True)` resolved each actual approved asset
from the existing cache while leaving the caller's null asset selector unchanged.
The genuine FCOS builder loaded those bytes; no fabricated state, monkeypatch or
random-weight substitute was used. A nontrivial backbone tensor matched its
corresponding asset tensor exactly before training: ResNet convolution, ConvNeXt
stem, Swin patch projection, or DINO class token.

Before the native backend training call, a real forward/backward pass included
both a foreground-zero sample and an empty sample. Losses and observed gradients
were finite; the backbone tensor and class-zero classifier channel both had
nonzero gradients. P3–P7 spatial shapes were 16, 8, 4, 2 and 1, with one compatible
anchor per location. Native backend training then selected epoch-zero `best.pth`
by `val/map50_95`, and the selected backbone tensor changed from the verified
pretrained value.

The actual checkpoint-binding routine embedded model metadata. Each checkpoint
was copied without a descriptor sidecar and reloaded in a fresh Python process
through the FCOS prediction backend. Original and copied checkpoint SHA-256 values
matched; both produced exactly equal prediction tables on all four held-out test
images. Embedded backend, preset, vocabulary and preprocessing survived, tensor
keys had no `module.` prefix, predictions were finite and bounded by source image
dimensions, and all three exact foreground strings were retained.

## Results

All six native training commands and the final six fresh-process reload commands
exited **0**.

| Preset | Native training loss | Nonzero backbone gradient elements | Nonzero class-zero gradient elements | Maximum trained tensor change | Copied-checkpoint parity |
| --- | ---: | ---: | ---: | ---: | --- |
| `resnet50_fpn` | 3.023613453 | 8967 | 2302 | 0.0001001358 | Exact |
| `resnet101_fpn` | 2.919170856 | 9114 | 2303 | 0.0001001358 | Exact |
| `convnext_tiny` | 2.835254669 | 4608 | 2298 | 0.0001001060 | Exact |
| `swin_tiny` | 2.869791508 | 4608 | 2295 | 0.0001001060 | Exact |
| `dinov2_small` | 2.880576730 | 384 | 2304 | 0.0001001023 | Exact |
| `dinov3_small` | 2.998260379 | 384 | 2303 | 0.0001001060 | Exact |

The initial reload pass used `conf=0.001,max_det=300`. DINOv2's copied/original
tables were equal, but its top 300 detections did not contain class zero, violating
an overly strong harness assertion about ranking. The same six frozen checkpoints
were rerun uniformly with `max_det=1500`, above the tiny canvas's full class/anchor
population, to verify label retention without requiring a particular ranking.
All passed with class-zero predictions. The initial failure/logs remain retained;
no training rerun, checkpoint alteration or product fix was needed. The final
larger cap is a verification setting, not an accuracy or production recommendation.

## Asset and checkpoint identities

| Preset | Resolved pretrained asset SHA-256 |
| --- | --- |
| `resnet50_fpn` | `11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca` |
| `resnet101_fpn` | `cd907fc2a0de2292b2ba2b27d2216bc672d84632d1cf20058d01c0c03b5e020e` |
| `convnext_tiny` | `7ff80975b63ddbd30cdeb2f5c4b02ed537b1ba3f790d489817b7188fb2c3107a` |
| `swin_tiny` | `9f71c168d837d1b99dd1dc29e14990a7a9e8bdc5f673d46b04fe36fe15590ad3` |
| `dinov2_small` | `b938bf1bc15cd2ec0feacfe3a1bb553fe8ea9ca46a7e1d8d00217f29aef60cd9` |
| `dinov3_small` | `b7e7b7d1518a4dad2d92304ff47967c3dfee806f863552a06870de1e7498e7a2` |

| Preset | Selected and copied checkpoint SHA-256 |
| --- | --- |
| `resnet50_fpn` | `29c1e15c2ab51dfa756d4315b598a32fc4428677d86dc62a886e8dfa1659321f` |
| `resnet101_fpn` | `64f5a37616e0a629238c9133a8c2b79fde56e558fe242923cbb3748effcd3ce2` |
| `convnext_tiny` | `8f4fc8a9bb7c6165fcbfdbc052f063f998436445cd1b9c887e5335ab4c7c8d49` |
| `swin_tiny` | `24a01dde1441c7a2161f50c208b00444b7fa6c0442b50232baca41e19477a179` |
| `dinov2_small` | `3f85d98c44e9a2ba757e3cb5842c41c5a236bf58254a8ee53c735bd6ae71098d` |
| `dinov3_small` | `5f6b8cfa10dbd45580782a73b0baf453e01ad97eb91283a584c74394d7333b4a` |

## Limits and retained evidence

This verifies execution at resolution 128 on synthetic images. Native validation
mAP was zero for every preset; no useful accuracy, default-resolution performance,
production batch capacity, CUDA/DDP, queue, cross-family comparison or all-six
ClearML publication claim follows. GPU acceptance remains the parent's separate
workstream.

The ignored evidence bundle retains the exact harness, per-process exit statuses
and logs, resolved asset provenance, source/input hashes, metrics, native and copied
checkpoints, descriptors, prediction CSVs and full JSON results. Machine-local paths
are recorded only in that bundle and were communicated to the parent. All owned
training and reload processes exited; no background worker or service was started.
The shared pretrained cache and other workers' files/processes were preserved.
