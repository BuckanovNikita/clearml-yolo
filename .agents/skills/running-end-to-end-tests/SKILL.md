---
name: running-end-to-end-tests
description: Use when verifying native CPU/GPU execution, cy-queue, ClearML publication, FiftyOne, detector/export changes or release evidence.
---

# Verify native outcomes

Paths start at the repository root. Read `docs/development.md` (Acceptance tiers)
for automated scope and
`.agents/skills/running-end-to-end-tests/references/pipeline-prerequisites.md`
before preparing inputs. Use `clearml-yolo-environment` before live runs.
Verification respects host mode and grants no publishing or deployment authority.

## Select evidence

Use affected contracts as the assertion inventory. These are starting points;
mocked checks establish simulated behavior only.

| Claim | Contract in `docs/` | Concrete evidence |
| --- | --- | --- |
| Native execution | `runtime-isolation.md`; `development.md` (Native CPU distributed regression tests) | `acceptance` CPU smoke, `release-acceptance` single-GPU Severstal, real CPU-DDP tests; current checkpoints and downloaded outputs |
| Queue | `queue.md` | `paired-check` queue suite; compare direct and queued single-GPU runs with identical settings, allocation and terminal cleanup |
| Inputs and replay | `input-provenance.md`, `filesystem-policy.md`, `experiment-records.md` (Configuration resolution and replay) | Repeated live CSV run, exact downloaded bytes/source identity, retained workspace, generated command/model YAML and saved-configuration replay |
| Evaluation and publication | `experiment-records.md` (Evaluation, comparison and historical model recovery; Required publication and task lifecycle) | Baseline-free and baseline/candidate evaluation; standalone `cy-val`, `cy-compare`, `cy-report` with nondefault options; independent artifact and best Output Model downloads |
| Charts | `experiment-records.md` (Reports and readable visualization) | Standalone HTML rendering and independent ClearML API payload readback |
| Telemetry and failures | `diagnostics.md`, `runtime-isolation.md` | Active console/scalar readback, observed failures and local outcome diagnostics |
| FiftyOne | `runtime-isolation.md` (FiftyOne evaluation publication) | `release-acceptance` database/panel tests, fresh-process reload, optional failure/cancellation and worker containment |
| Package compatibility | `development.md` (Paired CY and queue release check) | `paired-check` with final source versions, installed metadata, normal resolution and queue suite |

## Observe and record

1. Use disjoint validation/test inputs including empty images. Pass explicit projects,
   tags, workspace and devices; preserve source data and SDK settings. Match
   direct/queued settings; scheduling alone does not establish a compiler fix.
2. Observe owned cancellation/failure paths, logs and cleanup. Retain simulated
   multi-device allocation, lost-acknowledgement, guardian-failure and fencing checks.
   Physical multi-GPU, external multi-user and two-host NFS are outside the mandatory
   gate; simulations establish none of those deployments.
3. Read publication independently through the API. Force-download required artifacts
   and the best Output Model, load it, and compare checkpoint hashes, metadata and
   thresholds. Apply the publication contract's trained-checkpoint warning versus
   standalone/skip-training failure semantics. Missing uploads remain unverified.
   Inspect checkpoint-owned counts, unknown/zero handling, baseline skip reasons and
   exact validation thresholds in downloaded reports.
4. Render confusion-matrix and PR HTML in a browser. Exercise every matrix normalization
   and class legend, empty/unknown cases, hover, captions and slot identity. API readback
   and standalone rendering establish separate layers; the environment has no ClearML
   web UI, and embedded UI presentation is neither required nor inferred.
5. For FiftyOne App claims, explicitly install its plugin in the backend environment
   and inspect native evaluation/report views, alongside database/panel and containment
   checks. Use `verification-workflow` for unavailable supported resources.
6. Record versions, commands, selectors, task/model IDs, observations and limitations
   in dated evidence. Preserve diagnosis evidence and prove owned processes and
   environments are gone after cleanup.

Native CPU and single-GPU runs remain release requirements. Build package archives
only for a concrete packaging investigation. For detector/export changes, also read
`.agents/skills/running-end-to-end-tests/references/multi-model-acceptance.md`.
