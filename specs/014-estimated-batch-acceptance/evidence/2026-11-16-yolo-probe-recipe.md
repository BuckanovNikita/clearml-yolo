# YOLO probe precision and explicit-recipe admission

This follow-up closes independent-review findings against ticket03 and feature
FR-001 (execute the identified recipe) and FR-005 (fail unsupported measurement
explicitly). It preserves the approved FP32 campaign baseline. It adds no training
mode, upstream change, service deployment, or physical-GPU claim.

## Installed-source findings and correction

The installed Ultralytics 8.4.184 trainer selects `torch.bfloat16` for `amp=bf16`
and enables GradScaler only when AMP is enabled and its requested mode is not BF16.
Its `torch_utils.autocast` additionally rejects BF16 without CUDA/native hardware
support. The CY probe previously recorded BF16 but used default FP16 autocast and
an enabled scaler. The optimizer loop now calls that installed autocast boundary
with the native dtype policy; scaler construction follows the same native policy.

The explicit recipe API could also identify settings the synthetic probe did not
execute. A shared pure helper in `adapters/yolo/config.py` now validates both profile
creation and standalone worker admission, before CUDA allocation. It rejects:

- Deviations from native defaults for `pretrained`, `distill_model`, `resume`,
  `single_cls`, `quantize`, `classes`, `task`, and `cls_pw`.
- Disabled channels-last layout, additional frozen layers, nonempty native
  `augmentations`, and a `model` override different from the catalogue architecture.

The probe constructs the catalogue detector, loads its standard asset, always uses
channels-last, and freezes only DFL. It does not build a distillation teacher, restore
training state, convert/filter classes, initialize QAT, or calculate native dataset
frequency class weights (`DetectionTrainer.set_class_weights`). Consequently these
explicit deviations are rejected rather than reported as exact measurements.
Omitted settings bind the selected catalogue architecture. `freeze=None/0/[]`,
`channels_last=None/True`, empty native augmentations, and resolved custom snapshots
remain supported. The existing native/default/JSON/Mosaic campaign composes unchanged.

The supported-scope paragraph in `docs/batch-estimation.md` reconciles the public
description with this admission boundary. Existing FR-001/005 and tasks T004/T005/T011
cover the fix; no competing specification or additional workflow is introduced.

## Red/green product evidence

The optimizer regression first failed because output dtype was float32 instead of
bfloat16 at the CPU test boundary. It now performs real CPU BF16 forward/backward,
uses the installed native optimizer step, and demonstrates changed parameters in
both eager and compiled-loss dispatch paths. The native autocast boundary alone is
substituted to permit CPU BF16; this does not claim CUDA BF16 or actual compilation.

The public probe scaler regression first observed an incorrectly enabled BF16
scaler. It now covers BF16, boolean AMP, explicit FP16, disabled AMP, and FP32.
Only CUDA allocation, model asset construction and scaler creation are replaced at
external SDK boundaries; native optimizer selection and AMP resolution execute.
The test exits at scaler construction, before a real GPU allocation or workload.

Parameterized unsupported-control regressions failed before the guard. They now
exercise both public profile creation and public probe entry, with a tripwire against
CUDA allocation. A separate real native-autocast test proves CPU BF16 rejection
remains intact without modifying model parameters. Product Hydra composition and
`prepare_transforms` feed actual native, JSON and JSON+Mosaic FP32 recipes through
profile creation successfully.

## Executed verification

All commands used the locked environment and CPU affinity 0,1 at nice19. No GPU or
remote service was used.

- **Passed**: focused pytest on `test_yolo_probe_precision.py`,
  `test_batch_profiles.py`, `test_batch_probe.py`, `test_native_config.py`, and
  `test_architecture.py`: 198 passed, 19 warnings, 17.08 seconds.
- **Passed**: strict mypy on the three affected product modules and new test module.
- **Passed**: Ruff check and format check on those four files. A new-test import sort
  was the only automatic mechanical correction.
- **Passed**: native `task --exit-code architecture`: 21 contracts kept, zero broken.
  The backend uses its own config helper rather than importing the integration layer.
- **Deferred to coordinator**: integrated full coverage, scoped mutation selection
  against staged inputs, and fresh independent review. Existing pre-fix mutation
  evidence does not establish the new admission helper or BF16 branches.
- **Unverified here**: physical CUDA BF16, compiled CUDA execution, GPU capacity,
  multi-GPU execution, and live training/publication. These remain separate campaign
  acceptance work; the CPU checks are not substitutes.

An initial focused invocation named nonexistent `test_yolo_config.py` and collected
no tests; it was corrected to the actual native configuration module. One expanded
test run had a test-only mismatch in the expected native BF16 error text; correcting
that expectation preceded the final passing run.

## Snapshot and cleanup

Final source/test SHA-256 values before coordinator integration:

| Path | SHA-256 |
| --- | --- |
| `src/clearml_yolo/adapters/yolo/config.py` | `3f35c0ac704aa645945a3326a5f9446c911f26734b7a389bca413ddbaa17762b` |
| `src/clearml_yolo/adapters/yolo/batch_probe.py` | `106ebb76be33c976c1fd5cc5a77cfe2831d10dd5f71f31208bb79e5d5f71dcb4` |
| `src/clearml_yolo/adapters/integrations/batch_profiles.py` | `87a681cc81d6cc1f092f8c74f680cc9fe73143c466ea5ba4be1ffc7a452098bc` |
| `tests/test_yolo_probe_precision.py` | `c713e9ed774983c0fa1f8b4e4be864bc9351d0c747007e0dd834aa8182092e25` |
| Installed `ultralytics/engine/trainer.py` | `7d060019b31e85ec429c16b7e728e9d7c5a9083b497fc2b362a76a543808dc60` |
| Installed `ultralytics/utils/torch_utils.py` | `274357cc6841205d1eb5a6016ff81bfd2ec961c53d1f689380bd0222ec3b1c33` |

All owned test/type-check processes exited. Task-owned `.tmp/yolo-precision-*`,
`.tmp/yolo-scaler-red`, and `.tmp/yolo-recipe-*` directories were removed after recording
results (about 2.4 MiB). No model assets, shared caches, other agents' artifacts or
environments were removed. No commit or staging change was made by this implementer.
