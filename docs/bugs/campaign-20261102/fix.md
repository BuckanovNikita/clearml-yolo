# Campaign repair implementation

- Date: 2026-11-02.
- Assessment: [assessment.md](assessment.md).
- Status: partial; underlying numerical computation unresolved.

## Applied changes

Bulk source-row conversion replaces a pandas Series allocation/conversion per row,
retaining canonical columns, source IDs, exclusions, threshold flags and relationship
JSON. Original scalar and shared Torchvision loss guards remain fatal and now
include the native event/batch/loss context. Scientific settings and dependencies
are unchanged. No native model surgery or numerical fallback is applied.

Private campaign source adds actual child-environment preflight, explicit fresh
attempt/provenance helpers, measured budgets, matching baseline eligibility and
failure-kind classification. Original runtime, schedules and old outcomes remain
unchanged. Machine restoration updates belong to that private source.

## Deviations and blockers

Fresh original-AMP YOLO11x pipeline reproductions fail on val/box_loss. Model and
EMA tensors are finite before validation; first-batch loss is NaN. An isolated
GPU diagnostic of the same historical best checkpoint and actual validation image
shows the first BatchNorm FP16 activation overflowing: equivalent FP32 range
[-93596.54, 73430.04] exceeds FP16 +/-65504. This does not establish a permitted
correction under the strict original-AMP requirement. The other three original
YOLO scalar failures need independent causal verification. Numerical failures
remain blockers; diagnostic improvements do not fix the underlying computation.

## Documentation

Updated the model guide with preserved fatal guard behavior and numerical
investigation boundaries. Inspected corp-skills portable usage/evaluation guidance:
no CLI, configuration, artifact, scientific recipe or public interface changed;
its existing instruction to preserve settings and distinguish workload failures
remains correct, so no portable skill source change is needed. Runtime/environment
procedures stay in the authoritative private automation source.

## Latest-source integration

Only task-owned code/tests/docs were applied to latest CY 0.44.7; queue 0.1.7 was
installed through normal resolution in an isolated environment. Public application
interfaces and dependency pins remain unchanged. The effect checker rejected the
initial pandas rename spelling, so the implementation uses pure set_axis without
adding an ignore or weakening the contract. Exact source-row/matching/CSV parity
and the existing architecture check were rerun after that correction.

## Resumed CPU-stage outcome

The patch is now integrated on current CY 0.44.8, with canonical CPU verification,
exact output parity and current queue 0.1.7 integration passing. The CPU observer
test fixture reports no accelerator so AdamW cannot initialize CUDA against its
synthetic readiness properties; real CPU updates and hashes remain tested. Its
original failure path was verified by a no-GPU negative control. Helper tooling is
released/exported independently. The application patch is not committed or released
because native numerical/deadline recovery remains incomplete.

## Independent original-AMP operation evidence, 2026-11-03

All five original numerical cases reproduced with original preprocessing and AMP.
Live model/EMA/optimizer state and actual native inputs were retained before the
first nonfinite operation. Separate CPU FP32 single-operation references remained
finite; casting those results to FP16 exactly reproduced each native infinity mask.

| Original case | First nonfinite native operation | Native infinity count |
| --- | --- | ---: |
| Severstal YOLOv10x | Attention matrix multiplication | 52,685 |
| Severstal YOLO11x | Batch normalization | 5 |
| Severstal YOLO12x | Attention matrix multiplication | 654,330 |
| CoatingDet YOLO12x | Attention matrix multiplication | 5,293,049 |
| CoatingDet FCOS ResNet101-FPN | Layer4.2 convolution | 163 |

FCOS retained preceding updates and reproduced batch 809 / image 3902. Inputs,
target geometry, model state and optimizer state were finite before its forward.
The CPU convolution reference reached 74,456.27, beyond FP16's finite range.
The four YOLO references likewise exceeded FP16 range with finite operands. These
are diagnostic results, not fallback inference or successful native acceptance.

Plain native YOLO training controls exposed an important replay caveat: saved
effective arguments contain the optimizer chosen by `auto`, but omit an internal
momentum rewrite. Replaying them as explicit AdamW changed optimizer beta1 from
0.9 to 0.937. Those controls are retained as scientifically mismatched evidence,
not proof of original-training parity; corrected controls must use the original
constructor arguments and verify actual optimizer groups. No permissible CY
computation correction has yet been demonstrated.

A separate current-environment YOLO11x failure was traced to overlapping OpenCV
distributions selecting a different import despite identical installed metadata.
An isolated original native namespace restored exact input pixels and the original
training/validation values. This repaired the recovery environment binding and
allowed full original-recipe acceptance, without changing installed dependencies
or the scientific recipe. It does not explain the five original numerical cases.

## Corrected independent native controls completed, 2026-11-03

Four corrected plain DetectionTrainer controls use the original constructor recipe,
including optimizer=auto, and verify actual optimizer groups before training. Each
uses beta1=0.9, original AMP and original preprocessing. At the first validation
input, every model/EMA tensor byte, complete optimizer metadata/tensor state, scaler,
EMA update count and Python/NumPy/CPU/CUDA RNG state matches its CY reproduction.
The ordered actual input tensors and saved input-file hashes also match exactly.
The independent controls import no CY runtime and reproduce the same invalid loss.

These controls establish the native numerical mechanism for each of the four YOLO
cases; they do not establish full native publication success. An observation guard
stops after the invalid first validation batch. CY's complete filename ordering was
not retained, although actual first-batch tensor ordering and state are exact. The
FCOS evidence demonstrates the native convolution overflow with preceding CY
updates retained; no independent full FCOS training replay is claimed. There is
no demonstrated CY computation correction that preserves these original recipes.

The private verifier separately handles the exact native YOLO12n metadata alias
using original initialization and registry hashes plus strict native reload proof.
It retains raw metadata and rejects unrelated backend, scale, vocabulary or hash
mismatches. The existing successful YOLO12n mild task/model was accepted through
readback only, without another launch or publication. This is a private identity
verification repair; application numerical behavior is unchanged.

Host reboot interrupted Faster50's final replay before complete publication. Its
native exit remains unknown; verified boot-transition cleanup permits a fresh linked
attempt, not success or readback-only acceptance. Task-owned application files were
restored from verified persistent bytes into durable current-source checkouts. No
application runtime or native library changed during restoration. CY remains unreleased.

## Current-source closure integration, 2026-11-04

The existing task-owned diagnostics, pure result-row conversion and CPU observer
fixture are being ported unchanged onto CY 0.45.0 (8be76e4). Original dirty
checkouts and all dated evidence remain preserved. No dependency, AMP, native
optimizer, scientific recipe or public interface changes are included. The prior
CY 0.44.8/queue 0.1.7 results remain historical evidence; checks and architecture
review are reset to pending for the integrated source. Parent integration owns
the final paired versions, native replay, fresh review and release.

- [x] Port the seven task-owned runtime/test/document paths and verify focused CPU regressions.
- [x] Run parent canonical/docs/current-and-proposed pair checks on the final integrated revision.
- [ ] Reconcile the twenty-case native matrix and unexplained SIGILL gate without weakening original scientific requirements.
- [ ] Obtain fresh independent review and validate architecture acceptance before delivery.

### Ledger reconciliation, 2026-11-07

Line 137 is ticked: [test.md](test.md#current-integrated-verification--2026-11-04)
records the integrated canonical run (4,790 passed), documentation validation and
the proposed CY 0.46.0 / queue 0.1.9 pair (583 queue tests, seven physical cases
deselected). The CY 0.46.0 release hooks and the committed-version pair (584 queue
tests, in cy-queue `docs/plans/cy-046-compatibility/verification.md`) followed.
The counts come from separate runs. Lines 138 and 139 stay open for WP4.
