# Implementation Plan: Batch estimation and native distributed training

## Approved speedup amendment (2026-10-30)

Architecture and gates: [speedup record](speedup/architecture.json).
The implementation starts from released 0.44.3 in an isolated checkout; original
workspace changes remain intact. No dependency recipe or native trial is shortened.

For successful observations `(b1,m1)`, `(b2,m2)`, predict
`b2 + ((budget-m2)*(b2-b1)) // (m2-m1)` using integer arithmetic. Start at 1 then 2;
clamp growth to `[lower+1, min(4*lower, ceiling)]`. Nonpositive/missing slopes use
doubling. Observed OOM/budget bounds use existing binary refinement and confirmation.
Core owns deterministic strategy dispatch, legacy replay and schema-3 validation.

Composition builds/deduplicates all model/hardware cases, handles cache/reporting,
and admits ready work by compatible idle GPU UUID. `--jobs` caps concurrency;
the default uses available selected GPUs. Cases wait for this invocation's busy
slots, without blocking other hardware groups; foreign activity is never stopped.
One private case entrypoint calls the existing singleton application use case.
Typed requests/receipts live in application worker contracts. A generic runtime
pool owns independent subprocesses, a distinct inherited ownership marker, one
parent native-descendant scope and cleanup barriers. Pin UUID visibility before
child imports; preserve output order and atomic catalogue writes. A pending snapshot
precedes launch; receipts require matching token/key and successful process cleanup.
Keep the existing cooperating-rank supervisor's fail-fast semantics unchanged.

Independent ownership after contract freeze: search/replay agent owns core and
search/storage tests; runtime agent owns pool and process tests; parent owns request
contracts, private entrypoint, scheduling/CLI, architecture and integration.
Documentation follows fixed interfaces. Integration and canonical/docs/native checks
precede a fresh independent review and release. Bounded agents do not delegate.

Acceptance uses the canonical verifier, docs verifier, scoped mutation applicability,
legacy/forged catalogue tests, actual concurrent CPU processes and multiprocess
catalogue writers, and paired-source queue checks. Compare legacy/guided native YOLO
and FCOS searches on one idle GPU with prepared assets. Physical multi-GPU execution
is explicitly waived for this release only; no GPU scaling claim follows CPU overlap.
Update batch-estimation guidance, Russian README, generated CLI docs and canonical
corp-skills usage/evaluation guidance. Release through normal commits, annotated tag
and explicit pushes after current/proposed compatibility and review; no code assets.

Date: 2026-10-26. Specification: [spec.md](spec.md).

## Summary

Implement the supplied design through the established Spec Kit route. Preserve existing
numeric defaults, replay, approved dependency pins and the pre-existing local uv sources.

## Technical Context

Python >=3.12.13,<3.14, uv/uv_build; current locked Torch, Torchvision, Ultralytics,
RF-DETR, Lightning and approved DEIMv2 source. Linux supervised workers; CUDA native
acceptance. Tests use pytest, Ruff, strict mypy, Vulture and import-linter through the
canonical verifier. Atomic versioned local JSON stores estimates. No new service.

## Constitution Check

Typed pure policy remains in core/application; adapters own SDK, device, storage and
process effects. The explicit feature request supersedes historical unsupported batch
estimation and native single-device limitations for this feature only. No installed
workflow tooling or constitution changes are needed. One invocation owns publication.
Fresh independent review and actual native evidence are required before acceptance.

## Architecture

[architecture.json](architecture.json) records modules, ownership and executable gates.
Search policy, catalogue and compatibility use immutable validated core records. Application
orchestration receives probe/store ports. Runtime adapters supervise fresh workers and
terminate owned peers on failure. Integration adapters bridge backend selection without
moving ClearML into ranks. Storage owns atomic locked catalogue updates. Entrypoints only
compose concrete dependencies and parse options. Native backend workers receive JSON
requests and emit typed rank results; rank zero owns checkpoints and metric aggregation.
Shared Torchvision machinery accepts a family-specific model builder and label offset.
FCOS remains distinct; deployment export remains Faster R-CNN-only.

Existing import-linter and AST negative tests enforce boundaries, inert initialization,
dynamic worker targets and SDK ownership. Extend explicit classifications and exact SDK
edges for new modules, without broad exemptions.

## Phases and Ownership

1. Parent records contracts, architecture and ledger; three read-only reviews inspect
   estimator/cache, distributed execution and configuration compatibility.
2. Parallel: pure search/catalogue; shared Torchvision/FCOS; Hydra migration/export.
   Parent implements supervised worker request/results and lifecycle. Freeze interfaces
   before native integrations. Only parent changes core registry and import contracts.
3. Parallel: DEIM distributed/probes; RF-DETR distributed/probes; Torchvision distributed/
   probes. Parent integrates YOLO probes, supervision and failure classification.
4. Parallel: atomic storage/null lookup; queue compatibility; CLI/config regressions.
   Parent integrates registry, replay provenance and shared behavior.
5. Serialize GPU acceptance under one owner. Parallel documentation and isolated paired
   queue verification. Parent runs canonical checks, docs and applicable mutation.
6. Fresh independent reviews after integration/checks. Resolve findings, reconcile ledger
   and architecture, then complete authorized commit/tag/push only if required gates pass.

No bounded agent delegates. Shared files change sequentially. Existing services remain
untouched. The inspected machine exposes one GPU; real multi-GPU evidence is currently
unavailable and blocks distributed acceptance/release, not independent implementation.

## Documentation and Acceptance

Update README.md (Russian), docs/multi-model-backends.md, runtime-isolation.md,
project-contracts.md, current-contracts.md, queue.md, filesystem-policy.md and maintained
augmentation guidance as affected. Inspect/update the canonical corp-skills usage package.
Record actual commands in dated evidence. Run `uv run --frozen --no-sync python
scripts/verify.py`, its `--docs` mode, scoped mutation where affected, latest paired
CY/queue checks, all registered native estimation cases, FCOS round trips, distributed
failure tests and fresh independent review. No unavailable gate is a pass.

### Physical acceptance harness completion

The existing physical DDP harness covers YOLO only. T026 adds four native-family
scenarios using the existing explicit device, project and evidence options. Test-only
rank wrappers may observe the production worker entrypoint while preserving its
request, token, environment and supervisor. They must collect actual NCCL/device,
batch, training/validation membership, optimizer/model/EMA, checkpoint and publication
evidence. Missing, duplicated or divergent observations fail acceptance. Fault runs
exercise one-rank crash, actual CUDA OOM and cancellation, then a fresh successful
native run. The test harness owns its subprocess/service effects and cleans only
its tagged resources; production module boundaries and public APIs stay unchanged.
Offline contract checks cover command construction, observation validation and
opt-in behavior. Physical execution remains a separate hardware-dependent gate.

## Single-GPU estimation amendment (2026-10-27)

The supplied simplification plan supersedes the estimator's multi-GPU search matrix.
Measure once per model, resolution, training profile and GPU name/total-memory group;
identical GPUs share evidence. Probe the first idle selected representative only when
a measurement is needed. Counts select reporting allocations over the first N devices.
The search limit is per GPU (default 1024); extrapolated totals may exceed it.
Keep legacy measured records readable and prefer compatible exact-allocation evidence.
Otherwise derive typed recommendations from compatible single-GPU sources, using
N times the smallest capacity for mixed allocations. Never create synthetic trials.

Pure core policy owns compatibility and scaling. The application coordinates injected
probes/storage and deduplicates measurement profiles. Entrypoint/runtime adapters own
idle selection and enforce single-GPU execution; lookup adapters retain dataset bounds
and publish measured/extrapolated provenance separately from replayed nulls. Existing
import-linter and architecture negative cases cover these unchanged layer boundaries.
The adjacent architecture record indexes the amendment and required evidence.

Independent work: a bounded agent owns pure recommendation policy, lookup, provenance
and their tests; parent owns search orchestration, CLI, probe guard and their tests.
Documentation can proceed independently once these interfaces are fixed. Integrate
then run canonical/docs, paired queue and real single-GPU checks before fresh review.
Keep separate physical DDP correctness gates; unavailable hardware still blocks release.
Preserve all pre-existing feature changes and completed historical evidence.

## Release request (2026-10-27)

After the completed code review, ordinary verification and explicit disclosure of
failed native YOLO confirmation and unavailable physical DDP, the user requested
“make new release”. Execute the Git-only release of feature 006 under that updated
authorization, recording these native gaps as release exceptions. Do not relabel
failed/unexecuted checks or mark full architecture acceptance as passed. All other
commit, ordinary verification, documentation, paired compatibility and review gates
remain required. No runtime implementation change is planned for this release step.

Parent owns CY release documentation, exact uv-source preservation, canonical checks,
final review, contributor commit and native version/tag hook. A bounded companion
agent owns queue 0.1.2 metadata/paired verification; another owns usage-source
release preparation while preserving unrelated dirty source artifacts. Freeze queue
source before CY verification, use isolated copy-mode dependency installs, and check
the actual final versions before pushing. Publish only intended Git refs; no GitHub
Release, assets, registry package or operational installation.

## Explicit delivery authorization, 2026-10-30

After disclosure of the two failed idle preflights and the separate single-GPU
benchmark gate, the user instructed **“push”**. This authorizes the Git-only 0.44.4
delivery with that benchmark gap recorded, in addition to the earlier physical
multi-GPU exception. It does not turn T041 or full architecture acceptance into
passes. Ordinary checks, independent review, final paired-source verification and
normal release hooks remain required; no native guarantee or idle criterion changes.
