# Early integration reviews — 2026-10-11

These were bounded read-only reviews during implementation, followed by fixes from the
implementation owner. They are not the fresh independent completion review required by
T050 in [tasks.md](tasks.md). Native execution, publication/download, complete export and
quality matrices, final parent verification and release remain separate gates in the
[verification ledger](verification.md).

## First review: configuration and shared detector workflows

| Priority | Finding and impact | Resolution and regression evidence |
| --- | --- | --- |
| P1 | Native training recipe YAML treated a backend-owned `model` value as a checkpoint path. RF-DETR's nested model configuration and DEIM's registry name could fail recipe recording after training. | `DetectorRunner.write_native_yaml` limits checkpoint-path interpretation to prediction; training serializes the backend's effective recipe. The pipeline regression covers RF-DETR's mapping, DEIM's string and Faster R-CNN's backend fields. |
| P2 | Selecting a native backend left changed legacy `ultralytics`/`ultralytics_predict` groups inactive without rejecting the overrides, so a requested setting could have no effect. | Wrapper validation rejects changes to inactive YOLO groups before admission and directs the caller to `model.train`/`model.predict`. Unchanged composed defaults remain accepted; regression cases cover training epochs/device and prediction confidence/classes. |
| P2 | Mixed comparison could drop YOLO-only population controls while routing the native model, allowing class-filtered or otherwise different populations between the pair. | Native prediction translation accepts unchanged legacy defaults but rejects unsupported overrides, including `classes`, `single_cls`, `fraction`, `cls_remap`, `data` and `split`. Regression cases cover every listed control. |

The parent recorded **57 SDK-free targeted tests passed** after these fixes, with the
exact command in the [dated continuation evidence](verification.md#lightweight-continuation-before-the-authorized-workload-window).
This review record confirms the current implementation and regression assertions by source
inspection; it does not claim a new execution of that historical test batch. The relevant sources are
[detector routing](../../src/clearml_yolo/adapters/integrations/detectors.py),
[wrapper validation](../../src/clearml_yolo/entrypoints/hydra/validation.py),
[workflow regressions](../../tests/test_detector_workflows.py),
[model configuration regressions](../../tests/test_model_configs.py) and
[detector integration regressions](../../tests/test_detector_integration.py).

## Follow-up review: programmatic prediction ownership

**P2:** Native `prediction_settings` accepted a caller-supplied image source, non-detection
task, wrong stage mode or conflicting checkpoint. Those inputs could bypass the shared
ground-truth membership and selected-checkpoint contract.

The parent reproduced **four failing cases**, then added explicit rejection of non-null
`source`, `task` other than `detect`, `mode` other than `predict`, and a `model` differing
from explicit `weights`. A matching explicit checkpoint remains accepted. These checks
are present in detector routing and in
`test_native_programmatic_prediction_rejects_ownership_conflicts` and
`test_native_programmatic_prediction_accepts_matching_explicit_checkpoint` in the
[integration tests](../../tests/test_detector_integration.py).

The parent recorded **81 focused tests passed** after the correction in the same dated
continuation evidence. The four-failure reproduction and passing count are parent-provided
historical evidence, not a new native or SDK execution performed by this documentation review.

## Documentation validation during this review

An inline read-only Python check used `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` and
`uv run --frozen --no-sync python` over changed tracked Markdown plus new task documentation.
It covered README, maintained guides/contracts, the project E2E skill/references and
feature 025 artifacts, including the amended native configuration and model guide.

- Markdown parsing, balanced fences, final newlines and trailing whitespace passed for
  27 files; all 255 local links and heading references resolved.
- The 42 fenced blocks included 32 shell blocks checked with `bash -n`, one Python
  example checked with `ast.parse`, and four YAML examples parsed with `yaml.safe_load`.
- All 32 detected project CLI examples composed from registered Hydra wrappers and their
  documented model selections. All 14 native preset selections validated against typed
  model configuration, as did the guide's local raw reference and both task-reference
  variants with explicit or recovered thresholds.
- The check asserted that Torch, Torchvision, timm, RF-DETR, Ultralytics, ClearML and
  TensorRT were absent from imported modules. It did not execute example workflows,
  generate configuration files, resolve model assets or load a detector runtime.

Generated configuration examples were represented by their declared wrapper and selected
model during composition; this check does not establish filesystem-export or native
execution behavior. It adds documentation evidence only.

## Scope and remaining review

The early findings above are addressed in the inspected source and targeted regression
cases. Their test evidence does not establish real detector training, GPU admission,
ClearML publication/download or TensorRT acceptance. Heavy execution remains subject to
the scheduled start and parent coordination described in the
[acceptance plan](trt-acceptance-plan.md). The parent must complete integration and the
required verification before commissioning the fresh independent final review; T050
remains open.

## Focused integration reviews — 2026-10-12

The independent reviewer inspected the live-clone replay correction after the parent
integrated it. The SDK maps both absent configuration and present empty text to `None`
through its dictionary reader. The first implementation therefore incorrectly accepted
present empty text as an absent canonical object. The owner added a public raw-text
presence check; the reviewer then found no residual issue in missing/empty/malformed
handling, detached execution copies, separate redaction, lifecycle propagation, file
configuration or legacy YOLO behavior. Ten direct mocked replay checks passed in the
review; the owner's broader affected suite passed 221 tests.

A separate read-only review of the structural geometry selector confirmed that it stops
at weighted convolutions/projections and preserves integer and Boolean output types.
Removing the invalid NMS computation constraint retains the floating producer seeds.
The reviewer explicitly required inspection of actual engine NMS formats: a constrained
producer alone cannot exclude a builder-inserted conversion. Native geometry validation
is still in progress; this review is not a quality or deployment acceptance claim.

Two public CPU exports subsequently failed when the installed ClearML SDK iterated an
unexpected `tasks=None` response during naming collision lookup. The reviewer repeated
the exact original queries and a nonexistent-name query through both the public SDK and
the underlying read-only response. All returned proper lists; both historical owners
remained failed. The historical raw response was not captured, so the upstream cause
is unproven. No product patch was recommended; fresh retries preserve the original
failures. Treating a missing result as an empty collision list would weaken the contract.

These bounded reviews do not satisfy T050. The final review must follow the complete
parent integration checks and acceptance matrix.

The subsequent FILL-boundary review found no actionable defect in floating payload/fill
casts, implicit-zero handling, nonzero value retention, integer shape ports or allocation
failure propagation. Thirteen focused tests and additional in-memory boundary/selector
probes passed without heavy SDK imports. The parent then extended committed coverage to
FP16 payloads and an absent fill port; all fifteen precision tests passed. Production
integration remained pending the separate NMS diagnostic at this review point.

The saved-evidence review accepted all six native cancellations, retained the excluded
observer failure and documented the external helper-version pinning limitation. It also
verified the naming-observer and geometry archives without claiming that the remaining
Half NMS formats or full quality gate had passed. Both reviews remain separate from T050.

The explicit ONNX precision helper received a separate read-only review. The reviewer
reproduced a generated tensor-name collision with an unused graph input. The parent
added that case to the real ONNX checker regression, observed the failure, then reserved
all graph declarations and initializer names. The reviewer confirmed the fix and found
no further actionable issue within the direct-FP32-initializer scope. Five tests and
additional pure ONNX probes covered multiple weighted nodes, omitted optional bias,
external declarations and rejection before mutation. This focused review preceded the
full production quality matrix and does not replace T050.

### Independent numerical diagnosis — 2026-10-12

A fresh read-only reviewer inspected the failed ResNet-101 Float-head policy, source,
saved validation captures and actual TensorRT inspectors. It found no concrete defect
in the lowering helper or builder, but identified substantial upstream tactic changes
between builds and numerical error beyond Half operand/output rounding. The parent
independently reproduced the 144 changed-tactic count and five CPU convolution replays.

The reviewer recommended a bounded FPN comparison that captures all four backbone inputs
and uses each convolution's own GPU inputs for Float and rounded-Float references. This
separates upstream tactic differences from local arithmetic. Reordered ROI rows cannot
establish matched-object error without proposal identity. A second small Conv cast-up
probe must establish the actual kernel's arithmetic, since numerical agreement alone
could mean Float fallback. NVIDIA's archived [TensorRT precision guidance](https://docs.nvidia.com/deeplearning/tensorrt/10.x.x/inference-library/precision-control.html#control-of-computational-precision)
documents cast-up fusion for GEMM; it does not establish a version-pinned Conv guarantee
for the installed 10.13.0 SDK. The exact versioned documentation URL was unavailable.

This diagnostic review made no repository changes or GPU runs and did not approve
release. The failed accuracy gate remains open; T050 still requires a fresh final review
after successful parent integration and acceptance.

A follow-up review located the exact [TensorRT v10.13.0 API source](https://github.com/NVIDIA/TensorRT/blob/v10.13.0/include/NvInfer.h)
and its [10.13.0.35 version header](https://github.com/NVIDIA/TensorRT/blob/v10.13.0/include/NvInferVersion.h),
matching the installed SDK. The weakly typed computation/output constraints can fail
closed with `OBEY_PRECISION_CONSTRAINTS`, but no separate convolution accumulator
control is exposed. Float output alone would not establish Float accumulation. The
bounded probe subsequently failed to find an implementation for its first requested
Half-computation/Float-output convolution; no engine or arithmetic result was produced.

The reviewer proposed a structural fallback if that probe failed: represent eligible
group-one, zero-padded 1×1 body convolutions as batched matrix multiplications, with
explicit Half-to-Float multiplication operands. A static census found 70 eligible
ResNet-101 body operations and 34 spatial convolutions; three eligible projections
need stride-two slicing. This avoids general im2col memory expansion. Actual TensorRT
execution must prove the exact layout and arithmetic before integration; Float FPN,
detection heads and geometry remain the intended boundary. A custom plugin or general
spatial-convolution decomposition was not recommended. This remains numerical design
review, not a quality result or T050 approval.

Review of the preliminary pointwise probe required an immediate Half result cast and
independent Float input bindings for the result-type variants. A Float consumer of the
uncast product would prevent that graph from isolating the proposed fusion. Both matrix
orientations are included in one corrected micro-engine. Actual Half operands/tactics
and agreement with the intended Float-accumulation reference are required together;
agreement from a Float fallback is insufficient. If the corrected variants all retain
Float kernels, this fusion investigation ends unless a concrete new mechanism is found.
The first corrected attempt exhausted its workspace cap before selecting a tactic, so
a workspace-only retry can answer the still-open question without a precision search.

The corrected 2 GiB probe demonstrated the intended mixed GEMM mechanism in both
layouts at all three shapes. Each detailed inspector exposes four Half-input/output
GEMMs with `f16f16_f16f32_f32` tensor-core tactics and fused Float MatMul/immediate Half
cast metadata, alongside eight actual Float candidate/control GEMMs. No ForeignNode
record obscures the operations. The parent independently reproduced these counts and
operand/result checks. Numerical residuals corroborate the result; neither numerical
agreement alone nor an instruction-level audit is claimed as its basis.

The numerical reviewer accepted a common structural policy using NCHW pointwise
convolutions and weighted linear products, with spatial convolutions retained in Float.
The immediate Half product cast must remain private, followed by Float restoration
before bias or coefficients. Implementation tests must cover odd spatial dimensions,
strides, nonzero bias, Gemm transposes/coefficient/bias broadcasting, and MatMul rank and
operand order. Full-model arithmetic and the fixed quality gate still require execution.

A fresh focused implementation reviewer then examined the completed helper and build
integration after the parent's 133-test and six-graph checks. It returned **ship** for
helper SHA-256 `2770d9adc128e34f56a9ffb0fdf14eca51f954ff2631c17f12fe01e7c7331988`,
with no actionable semantic, atomicity, scope or type findings. Its 36-test run and 12
additional CPU probes covered rejection without mutation, unequal channels, tiny and
asymmetric canvases, scalar MatMul outputs, valid Gemm bias broadcasts and negative
coefficients. Requested reviewer settings were GPT-6.1 Sol/high; runtime settings were
not exposed. The reviewer made no writes or GPU/server calls. Prefix-based FPN/head
selection remains bound to the validated exporter naming contract; full-model quality,
dynamic acceptance and the final T050 review remain separate gates.


## Focused QKV precision reviews — 2026-10-12

A fresh GPT-6 Astra/high read-only investigation found no semantic defect in the prior
pointwise rewrite and proposed validation boundaries that distinguish projection rounding,
attention amplification and residual/MLP effects. Its static source review established
that QKV weights have anonymous exported names; a bounded value-branch dataflow match
identifies the same 12 projections in each transformer graph. The subsequent diagnosis
and one candidate intervention used only the frozen first validation image, without
labels or AP. The parent independently verified the numerical decision criteria and
both diagnostic archives; see [verification.md](verification.md).

After integration and parent focused checks, a fresh GPT-6.1 Sol/high read-only reviewer
returned **ship** for precision helper
`e144ff0a801398ed4ea91d97de64b71c21723f14756dc50cd878730c258e3a1e` and attention selector
`027a2a112bf495d2d5c25bba2571c3a1dbb79183e64ec27dd494202323d1e8f3`.
It found no actionable defect. All 58 precision tests and seven additional malformed-path
probes passed. It also checked renamed nodes, reversed bias operands, Constant controls
and standard `ai.onnx` domains. The selector supports the documented direct attention
value layout; materially changed exporter layouts require renewed validation. Runtime
model/effort settings were not exposed, so the stated settings are requests only.

The independent six-graph audit confirms unchanged lowered bytes for ResNet-50,
ResNet-101 and ConvNeXt, and exactly 12 unchanged Float QKV operations in each transformer.
Other lowering is preserved modulo generated private names. A scratch candidate encoded
the default empty ONNX domain explicitly while the original omitted it; the initial
byte-comparison overconstraint and its audit-only correction are preserved. Production
nodes themselves remain byte-identical. These focused reviews do not satisfy final T050,
and no CPU check is presented as TensorRT quality acceptance.


## Final T050 independent review — 2026-10-12

**Verdict: ship.** A fresh-context reviewer inspected the final change set after the
parent's complete integration and native/export acceptance. No blocking correctness
or contract finding remains. Requested settings were GPT-6.1 Sol/high; actual runtime
model/effort settings were not exposed. The reviewer owned no writes and performed no
GPU execution, SDK service mutation, installation, commit or further delegation.

The review covered the approved spec/plan/contracts, native adapters, checkpoint
lineage/publication/recovery, independent comparison, scheduling/remapping/replay,
selected configuration export, dynamic ONNX and FP16/QKV conversion, standalone
geometry/runtime, documentation, packaging and version-only release lock updates.
Unrelated external dependency source copies were excluded.

Independent verification passed **206 tests** in 66.07 seconds with four dependency
deprecation warnings. The command used `PYTHONDONTWRITEBYTECODE=1 UV_NO_SYNC=1` and
`uv run --frozen --no-sync pytest -p no:cacheprovider -q` with
`test_checkpoint_descriptor.py`, `test_detector_recovery.py`, `test_model_replay.py`,
`test_model_scheduling.py`, `test_export_attention_precision.py`,
`test_export_precision.py`, `test_export_workflow.py` and `test_local_release.py`
under `tests/`, covering real release fixtures as well as the integration boundaries. `git diff --check` passed. All 125 final
review-inventory hashes and 280 full-suite source/configuration/test hashes match.
The reviewer independently recomputed all 132 saved current FP16 quality cases:
reported losses, positive references, corpus hashes, frozen controls and the fixed
0.005 gate agree. Native/GPU/standalone runs and the full regression suite were not
repeated by the reviewer; those conclusions use the preserved source-bound acceptance
evidence independently checked by the parent.

The reviewer accepted descriptor/conflict handling, the raw canonical replay boundary,
runtime input/geometry validation and the root-version-only lock update. No remedial
source changes were requested, so T051 closes without introducing unrelated changes.
The parent rechecked the review inventory before recording this verdict.

The fixed single-class 12-image corpus establishes relative export quality, not broader
accuracy. CUDA 11.8 target execution/binary portability and historical ClearML socket
causality remain unverified. The supported process-local thread-reporting control and
its successful fresh public runs do not erase the preserved failed attempts.

This verdict satisfies T050 for the implementation. Resource cleanup, documentation
validation after ledger edits and T057/T058 release gates remain parent-owned next steps;
the verdict alone does not establish a completed release.
