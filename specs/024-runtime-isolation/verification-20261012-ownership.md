# File ownership and Torch compatibility — 2026-10-12

This evidence covers the approved amendments to [feature 024](spec.md) and
[feature 025](../025-multi-model-backends/spec.md), starting from release `v0.24.0`.
Earlier verification remains historical evidence. Parent implementation, static/native acceptance, documentation and fresh independent
review pass. Required commit/release gates remain pending.

## Implementation and preservation

- Bootstrap keeps `CY_HOME`, explicit project scratch and the existing user-wide GPU
  queue root. It no longer redirects SDK configuration, caches, downloads, credentials,
  bytecode or library temporary files, patches SDK constants, or changes import cwd.
- Invocation arenas are retained after every exit outcome. Startup neither scans old
  arenas nor interprets host/PID/ownership records as deletion authority. Operation
  scratch is removed only at a demonstrated consumer-completion boundary; failed
  uploads/finalization and uncertain process shutdown retain their inputs.
- Native callbacks remain owner-only. A native trainer subclass scopes fresh DDP
  construction/training in memory, without persisting callback switches to user settings.
- Dataset preparation preserves invalid entries and foreign staging, publishes atomically,
  and removes only its uniquely created staging directory. Native lock files persist;
  unavailable native locks fail clearly without soft-lock fallback.
- Requirements are `torch>=2.13.0` and `torchvision>=0.28.0`, locked at 2.14.1/0.29.1.
  Only their required cuDNN, NCCL and Triton lock entries changed. All 271 package
  names and local editable dependency lock entries remain intact; local sources and
  their documented approved revisions were not changed. Copied external source trees
  have no independent Git metadata, so equality to upstream commits was not re-audited.
  The compatible pair and relaxed Torch requirement are documented in the
  [upstream Torchvision release](https://github.com/pytorch/vision/releases/tag/v0.29.1).

## Parent checks

| Check | Result |
| --- | --- |
| Lock resolution and prepared all-extras environment | Passed |
| Installed dependency compatibility (`uv pip check`) | Passed, 267 installed packages |
| Torchvision compiled NMS and ROIAlign | Passed on CPU and CUDA |
| Full pytest, including native CPU/Gloo DDP | Passed: 2,115 tests, 30 optional skips; no failures |
| Ruff | Passed |
| Strict mypy | Passed, 277 sources |
| Import-linter | Passed, 40 contracts |
| Wheel and source distribution | Built; each fresh installation passed 11 command helps and nine selected configuration exports/compositions |
| Documentation and local links/examples | Passed: 32 Markdown files, 264 local references, two Python and 42 shell examples |
| Fresh independent review | Ship; no actionable findings, 50 independently run focused tests passed |

The initial full run exposed nine failures: stale cleanup assertions/mock signatures and
an existing-checkpoint string regression. The latter was reproduced separately, then fixed
by recognizing existing local files without redirecting unresolved model names. Its targeted
pipeline/filesystem/publication/lock-tracing suite passed all 62 tests. Publication/workbook/
ClearML scratch checks passed 230 tests. Failure-path tests now verify retained file contents
and stopped consumers, rather than merely removing obsolete assertions.

An additional 16-test bootstrap run covered the expanded four-outcome overlapping-parent
matrix. The CPU DDP helper now inspects retained invocation arenas instead of an obsolete
empty directory pattern; all five real native scenarios passed separately (two-/four-rank success and failure paths).

Runtime subprocess coverage includes overlapping scopes, delayed descendants, successful
exit, exceptions, interruption/SIGTERM, malformed records and duplicate host/PID metadata.
SDK subprocesses exercise native HOME configuration and explicit files outside `CY_HOME`.
External selectors, cwd, bytecode and global temporary defaults remain unchanged. Prepared
cache tests cover invalid directories/files/symlinks, foreign staging, lock unavailability,
persistent lock inodes, concurrent consumers and current-operation cleanup.

## Real native and publication acceptance

The current dependency pair completed one native YOLO GPU pipeline through training,
prediction and evaluation with explicit project output routing. This used a random local
architecture and establishes execution, callback ownership and publication, not accuracy.
Real FiftyOne persistence/reload/native-evaluation checks passed 27 tests against an isolated
test database. Both used explicit environment selectors; tagged ClearML resources were
cleaned after completion and zero remaining tagged tasks/projects were verified.

Three representative detector presets each completed training, forced server checkpoint
retrieval, standalone checkpoint reload, prediction and validation:

| Preset | Train task | Predict task | Validation task |
| --- | --- | --- | --- |
| RF-DETR Nano | `ce35f0b06854486ca92d7263570d3fe5` | `d49251d50865466eb11f282886eba9d8` | `a030c6f10e9941dd97709e706acec1c0` |
| DEIMv2-S | `0235e4df06aa484a95ff07f7a510f846` | `0b203bf22b2c4d63b94b302a272ba066` | `9c87b46f8aa6411183f59c2d4a86d0ed` |
| Faster R-CNN ResNet-50 FPN | `af0259d585a44e6eb8c96ae45fe38c06` | `f67698acafd9434e8ea3164173727498` | `c200db37c6f0424cbfbe879e730135d7` |

All nine owners completed. An independent archive audit rehashed three best Output Models,
30 required artifact copies and embedded checkpoint descriptors containing Torch 2.14.1 /
Torchvision 0.29.1 and exact class `0001`. Prediction rows matched source multisets. Every
invocation reported no live owned processes. Cleanup left zero tagged tasks/projects.
Preserved native archive SHA256:
`ccb25709039788bc6454d9b888c6075ed06f22b94548a710102039633ec97fef`.

These short runs cover three representative presets, not the complete historical 14-preset
matrix. ResNet-50 returned zero detections; no model-quality claim follows. The native
three-preset driver supplied explicit stand credentials/endpoints but did not set an explicit
`CLEARML_CONFIG_FILE`; its normal SDK discovery was therefore not isolated. No user
configuration contents were inspected. Other new live launches explicitly isolated config.

## Current export acceptance

Representative ResNet-50 ONNX export, FP32/FP16 TensorRT build/verification, forced
publication readback and fresh Torch-free standalone execution all passed. Both engine
precisions passed 22 frozen verification cases on a 12-image, one-class corpus. Native mAP
ranged from 0.084692718 to 0.140860787. Worst mAP loss was 0.0 for FP32 and 0.004711744866
for FP16, below the respective 0.001 and 0.005 limits. This is fixed-corpus relative export
acceptance, not general accuracy.

The checkpoint and all frozen image/label hashes were verified before execution. Input
checkpoint SHA256:
`8a73a207372c5aada69de247035c2f1f86a0a8866f91c18511e2e321a111c766`.
Its embedded training descriptor correctly retains Torch 2.13 provenance. Newly generated
ONNX metadata and verification runtime record Torch 2.14.1 / Torchvision 0.29.1, so old
training provenance is not mistaken for the current exporter execution identity.

Final detection agreement uses class-aware one-to-one matching at IoU 0.99. Across repeated
case/image comparisons, FP32 had one unmatched reference detection and one unmatched export
detection; maximum matched box/score errors were 0.011261 pixels / 0.0001092. FP16 had
1,287 unmatched reference and 1,215 unmatched export detections; maximum matched box/score
errors were 0.96627 pixels / 0.0073326. The mAP gate passed; exact output equality is not
claimed. Raw pre-NMS tensors are not exposed by this interface. Preprocessing maximum
absolute error was 0.000091434, within `atol=1e-4, rtol=1e-5`.

Each fresh standalone run completed 118 batch executions covering 24 unique batch/canvas
configurations and repeated profile/shape transitions, plus nine incompatibility/shape
rejection controls. The installed runtime had no Torch, Torchvision, timm or ClearML imports.
This stress set contains crowded scenes, not a dedicated zero-detection fixture. TensorRT
was 10.13.0.35 with its compatible CUDA runtime; this does not establish CUDA 11.8 deployment.

The first export-environment attempt failed before computation because its dependency
path overlay omitted editable-source discovery. Only the fresh temporary environment was
corrected, and the retry used a fresh output directory. Failed and successful evidence are
retained. All tagged export tasks/projects were cleaned and zero remaining resources verified.
Five completed export owners supplied ten hash-verified forced-download artifacts. Preserved
export archive SHA256:
`5faee1c00dc092bbc3cfda97ab7ed259c57205fc3af254966993432ff09c3b4a`.

## Scope and remaining limits

No local NFS mount or second test host is available. Local process overlap and simulated
host/PID records establish local preservation only; a real two-machine NFS test remains
required before claiming cross-host validation. Physical multi-GPU/NCCL and CUDA 11.8 target
execution are also unverified. The unchanged queue remains per-host and cross-project;
this work adds no distributed GPU scheduling.

Documentation was reconciled across README, filesystem/runtime/current contracts, migration,
backend guidance, affected quickstarts and the end-to-end skill. Completed feature history
was preserved; the new requirements and tasks are dated amendments. Machine-specific
commands, raw logs, archives and cleanup receipts remain in external dated evidence.

## Independent review

A fresh read-only reviewer inspected the combined source/test/doc/dependency diff and
parent evidence after verification. Its bootstrap/cache/native-runtime suite passed 50
tests; whitespace checks passed. The reviewer confirmed installed native trainer
serialization and synchronous inference-manifest consumption. Verdict: **ship**, no
actionable findings. Cross-host, hardware and acceptance-matrix limits remain as above.
