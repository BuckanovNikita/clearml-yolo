# Bug fix: authorized official HF DINOv3 initialization

- Slug: `dinov3-hf-native` (from assessment).
- Applied: 2026-11-04.
- Assessment: [assessment.md](assessment.md).
- Status: applied; parent integration and acceptance pending.

## Changes

Selected DEIMv2 L/X preparation reuses a valid original Meta checkpoint first,
then resolves the pinned official Facebook HF representation through the existing
Hub adapter. A dedicated DEIM adapter consumes every source tensor, restores only
architecture-defined buffers, strictly loads the native model, publishes a separate
checkpoint atomically and verifies cached tensors against the source on reuse.
Source and derived hashes remain distinct in typed derivation provenance.

| File | Ownership |
| --- | --- |
| `core/assets.py` | Optional immutable source/converter provenance on resolved records |
| `adapters/deim/assets.py` | Pinned official source identities; original Meta identities unchanged |
| `adapters/deim/hf_weights.py` | CPU conversion, native loading, derived-cache integrity and locking |
| `adapters/assets/execution.py` | Selected execution routing; canonical settings and explicit overrides preserved |
| `.importlinter` | Exact SDK and cross-adapter effect-owner edges; existing forbidden families remain enforced |
| `tests/test_dinov3_hf_weights.py` | Mapping, rejection, precedence, corruption repair, concurrency, provenance and RNG regressions |
| `docs/model-assets.md` | Selected-model HF access and conversion contract |

## Verification and review handoff

The [verification record](test.md) distinguishes executed local/CPU evidence from
the parent canonical and native acceptance gates. The architecture record remains
pending review; it must be reconciled and accepted after integration.

Self-review reproduced a Torch RNG side effect: `torch.manual_seed` also seeds
CUDA even inside a CPU-only RNG fork. The adapter now seeds the CPU generator
directly, and a regression forbids CUDA seeding while checking CPU RNG preservation.
Native construction runs explicitly on CPU and imports Torch only when needed.

## Deviations from assessment

The existing exact SDK ownership contracts required additional precise edges for
lazy safetensors conversion, HF cache-location inspection and derived-checkpoint
storage. No forbidden module family or global import rule was removed. Existing
architecture negative cases exercise the updated contracts.

Portable usage documentation was inspected and delegated to the parent team's
separate companion checkout. No dependencies, source revisions, published weight
manifest, original cached weights or release assets were changed.

## Sequential current-master integration — 2026-11-05

The approved sequence is DINOv3, scoped campaign improvements, then forced batch
admission. This isolated port starts at current master `66279a6` (CY 0.45.1).
It imports only this bug's source, regression tests, exact import exceptions and
model-assets documentation. The preserved source worktrees are read-only inputs.
Neither the campaign implementation nor the force feature is part of this stage.
The previous combined-source verification and review remain historical evidence;
all architecture results and the review gate are pending for this new integration.

The previous estimator command coupled this bug to a complete *forced* catalogue,
which requires the later force implementation. Its stated expectation concerns the
selected DEIM L/X HF route. This stage therefore verifies that same route using
ordinary DEIM L/X estimation, including raw optimizer evidence and fresh winner
confirmation, without weight/backbone overrides. This is an explicit sequencing
reconciliation, not a claim that the forced catalogue passed: its complete 64-model
native gate remains open for the subsequent force stage. Physical multi-GPU limits
remain disclosed, and neither ordinary estimation nor single-GPU training proves it.

### Current integration ledger

- [x] Validate the current architecture plan before source integration (validator exit 0).
- [x] Port the isolated runtime, tests, exact import exceptions and model guide.
- [x] Run focused regressions, canonical static/import/CPU-DDP checks and docs.
- [x] Verify current native CPU conversion/parity/offline reuse and DEIM L/X fallback.
- [ ] Verify ordinary selected DEIM L/X estimation with fresh confirmation.
- [x] Reconcile the companion portable usage source and its documentation checks.
- [x] Verify latest and proposed CY/queue source and installed metadata normally.
- [ ] Obtain fresh independent review, reconcile diff/evidence and validate acceptance.
- [ ] Complete normal hooks and authorized Git-only release before the next stage.

### User-directed admission reconciliation

After ordinary admission rejected 2% GPU utilization without a compute PID,
the user explicitly instructed: “Ignore this is idle.” The native probe has
the same idle guard as the ordinary CLI. The planned force feature provides
the explicit override while preserving measurement-time foreign-process checks.
Do not modify the ordinary policy or fabricate an ordinary-estimator success.

Continue scoped source integration in the approved DINOv3 → campaign → force
order, retaining all work on the isolated integration branch. The earlier
per-stage release milestone is superseded: **no intermediate release**; all
release/delivery is held until final integrated verification, fresh review and
the native forced catalogue gate pass. DINOv3 estimator acceptance is deferred
to fresh selected L/X forced measurements on that frozen final source, with
raw optimizer and fresh winner-confirmation receipts. The force stage retains
its full 64-model coverage requirement. No required native evidence is waived.

### Selected estimator acceptance amendment — 2026-11-06

The earlier requirement for a successful winner in every selected case is
superseded prospectively by the [dated criterion reconciliation](test.md#estimator-criterion-reconciliation--2026-11-06).
A current-profile L/X measurement must establish either a freshly confirmed usable
winner or raw-proven `no_capacity` at the existing minimum of eight per GPU, with
verified ownership cleanup. Earlier failed records are retained. Neither host
telemetry ENOMEM nor cleanup errors qualify as capacity evidence. The native
training and estimator gates remain separate; final estimator acceptance is open.
