# Single-GPU estimator amendment — 2026-10-27

This evidence covers T027–T032 in the [ledger](../tasks.md). It supersedes the
estimator count matrix, while preserving the separate physical DDP training gate.
The implementation began from the existing unfinished feature working tree; its
unrelated FCOS, distributed-training, configuration and dependency changes remain
intact. No installed Spec Kit tooling or dependency revisions were changed.

## Architecture and scope

Pure core policy introduces `ResolvedRecommendation` and `select_recommendation`.
Compatible exact-allocation measurements take priority. Otherwise every distinct
name/total-memory group needs compatible single-GPU evidence, and global batch is
allocation size times the smallest measured capacity. Source keys, boundary/ceiling
statuses and actual evidence remain separate from the target allocation. No trial
or catalogue schema change fabricates distributed measurements.

The application rejects multi-GPU search profiles before effects, deduplicates
hardware keys even during refresh, and calls injected idle preparation only for
uncached cases. Preparation failure also invalidates a refreshed success and is
saved as a failed case. The entrypoint selects the first idle matching selected GPU,
reports requested first-N allocations and permits totals above the per-GPU ceiling.
The native probe adapter independently rejects multi-GPU trials before discovery.
Lookup preserves dataset/profile checks, explicit batches, replayed null and the
worker's actual assigned allocation. Normal training failure handling is unchanged.

Existing import-linter contracts and negative architecture tests cover the same
core/application/adapter/entrypoint boundaries. Plan-phase architecture validation
exited 0 before implementation. Spec Kit prerequisites resolve feature 006, its
requirements checklist has five checked items and no unchecked items, and installed
extension hooks are empty. The amended spec, plan, tasks, interfaces and data model
agree on single-GPU evidence and explicit extrapolation. Completed history remains.

## Verification

Focused recommendation/lookup/provenance checks: 115 passed. Focused orchestration,
CLI, probes and profile checks: 103 passed before the final refresh-preparation
regression was added. The canonical run covers the integrated final tests.

The first canonical attempt passed Ruff and found one CLI-test typing error (access
to an imported module attribute without an explicit re-export). The test now uses
its own typed hardware fixture; the subsequent canonical run uses empty CUDA
visibility so it cannot interfere with physical probes.

Current and proposed paired-source verification passed; see
[single-gpu-queue.md](single-gpu-queue.md). No selected mutation source, selected
mutation test/fixture or dependency changed, so scoped mutation requires no rerun.

Final canonical, native, documentation and independent-review outcomes are recorded
below after execution. Skips, deselections and unavailable hardware are not passes.

## Documentation and portable usage

Updated Russian README; batch estimation, queue, project/current contract and runtime
isolation guides; active specification, interfaces, data model, plan and quickstart.
Canonical corp-skills source remains at commit
`44426a6b6fce058ec9ab37588483eb4bc860ca0a`, package version 0.3.0, with preserved
pre-existing working-tree changes. This amendment updates only
`skills/clearml-yolo/SKILL.md`, `references/usage.md` and `references/evaluation.md`.

CY Markdown/link checks passed. Corp-skills Markdown (53 files), metadata/name and
packaged-link checks, quick validation and skills@1.7.1 discovery passed. Source
module `--help` verifies report-only counts and the per-GPU ceiling. The current
CY environment lacks the console script; paired source installations verify it
separately. No operational installation or skill export was performed.

An initial fresh native-agent skill evaluation gave correct recommendations but
omitted explanation details under a concise-answer instruction. It was recorded
as incomplete, not passing. The entrypoint now explicitly asks estimation explanations
to include default output counts, fresh confirmation, ceiling limits, provenance
and the separate DDP gate; a fresh evaluation checks that revision. No OpenCode or
DeepSeek runtime behavior is claimed.

The fresh `usage_recheck` evaluation included the omitted explanation details and
passed the workload and mixed-hardware cases. Its initially frozen first answer
still deferred FCOS schema inspection; that strict incomplete verdict is retained.
An evidence-only read-only follow-up validated current editable source identity,
FCOS ResNet-50 `imgsz=960`, `device=[0,1]`, `batch=None`, and Hydra model registration.
The combined three-case review then passed. Source-module support and isolated
installed-command support remain distinct from native/DDP execution.

## Native single-GPU observations

The real invocation selected one GPU, nominal resolution 128, default 150 classes,
300 objects/image, 90% memory budget, five warm-up and ten measured optimizer updates,
and a per-GPU ceiling of two. Every saved request contains exactly one GPU.

- FCOS ResNet-50 completed batches 1, 2 and an independent fresh confirmation at 2.
  It is `ceiling_limited`, not a measured maximum. Native validation completed in
  every successful trial.
- A second invocation reused that FCOS record and reported `cached`; a subsequent
  `--refresh` completed 1, 2, 2 with disjoint fresh trial IDs and the same estimate
  key. Both commands exited 0. Typed record replay and these assertions passed.
- Pure lookup against this real source and a hypothetical pair of identical GPUs
  returned global 4/per-GPU 2, origin `extrapolated`, preserving the source key and
  `ceiling_limited` status. This checks derivation only, not physical two-GPU execution.
- YOLO11n completed batch-one trials across both automatic optimizer paths with
  actual updates/validation, but larger-batch and fresh-confirmation attempts were
  rejected for active GPU compute without attributable PID telemetry. A separate
  attempt hit a pretrained-checkpoint download timeout. Its already-downloaded
  checkpoint copies had identical hashes; a task-local SDK configuration/cache
  removed that download dependency, but fresh confirmation still failed telemetry.
  Those cases remain failed with no usable recommendation. The monitor was not
  relaxed and no unrelated workload was stopped.

No unconstrained capacity maximum, successful YOLO recommendation, physical mixed
allocation, or multi-GPU execution is claimed. Physical DDP requires at least two
GPUs; only one is available. The failed YOLO confirmation and existing DDP gate
remain native acceptance gaps. Failed catalogues, raw requests, rank logs/receipts
and successful FCOS before/after snapshots are retained as private verification
evidence; no derived trial was added to the catalogue.

## Canonical freshness investigation

Run `8069ab54dd5d4119875c0e7185f404bc` passed Ruff, strict mypy, Vulture, all import
checks and 3,967 tests (30 skipped, 81 opt-in deselected), but exited 1 because the
verifier detected changed input identities. It correctly wrote no success receipt.
A read-only inventory found 753 installed dependency files with changed ctimes and
no mtime newer than verification start. The affected packages include Ultralytics,
LibCST and mutmut; sampled installed files have multiple hardlinks. Their common
ctime window coincides with isolated paired-environment cleanup. Shared uv-cache
hardlink removal is the supported cause of this identity-only change; no source
correction or verifier weakening was made. A fresh canonical run started after
that cleanup, with no concurrent dependency installation/removal.

The final canonical run `65b9fa3b35bc49908586774232130620` exited 0 and wrote a
valid unchanged-input application receipt. Ruff, strict mypy (404 source files),
Vulture and all 50 import contracts passed. Its ordinary suite passed 3,967 tests,
with 30 skips, 81 opt-in deselections and 163 warnings. The skipped/excluded native
service and physical GPU cases are not covered by that result. CPU-DDP and negative
architecture cases are included. No application source changed after this run.

## Independent review and acceptance outcome

Fresh read-only reviewer `final_review` inspected the amendment after parent
integration and verification, comparing the saved initial working-tree snapshot
with all 28 changed files (six runtime modules, seven tests, maintained docs and
feature/evidence artifacts). It found no code changes required and accepted the
module responsibilities, pure scaling/compatibility, injected application effects
and adapter ownership. It independently validated the architecture plan and all
five canonical log hashes/exit codes. The verdict is ship for amendment code only;
release remains blocked. Earlier broader feature changes were excluded from this
amendment and preserved.

Final CY documentation checks exited 0 (run
`20ff2b841cb74efa8805aab4b10ccb33`), including local links and new evidence. Corp-skills
Markdown and quick validation also passed after the explanation-routing refinement.
Both repository whitespace checks passed; no staged changes were introduced.

Architecture acceptance is deliberately not successful: the native check contains
failed YOLO confirmation evidence, and the separate DDP check remains not run.
The record retains those gaps while recording passed canonical, docs, paired checks
and accepted code review. T031/T022 therefore still block feature acceptance and
T025 release. No commit, version bump, tag, push, operational installation or package
publication was performed in either source repository.

Raw task logs, catalogue snapshots, rank requests/receipts and the amendment diff
are retained in Git-private verification storage under
`.git/verification/single-gpu-20261027-26gdpl56/`. Task-owned probe processes have
finished; disposable native data, checkpoint copies, isolated SDK configuration and
the initial working-tree backup are removed after retaining that evidence. Shared
services and pre-existing workloads were preserved.
