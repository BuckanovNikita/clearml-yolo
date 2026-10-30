# Bug assessment: persistent YOLO weights directory

- Slug: yolo-weights-directory (generated from the approved plan)
- Created: 2026-10-30
- Source: user-provided implementation plan
- Verdict: valid
- Severity: high for offline estimator execution

## Symptom and reproduction

The downloader resolves a relative Ultralytics weights_dir against its working
directory but does not save that absolute location. Estimator workers change to
retained trial directories before loading named weights. The selected model and
auxiliary AMP model can consequently miss already prepared files and try network
access. SDK inspection and an isolated SDK probe confirm that updating settings
alone leaves ultralytics.utils.WEIGHTS_DIR stale.

The installed SDK is 8.4.184. Its attempt_download_asset reads live SETTINGS;
check_amp imports utils.WEIGHTS_DIR and loads yolo26n.pt. JSONDict.update writes
its entire live mapping, and its writer logs rather than propagates write errors.
The supported [settings API](https://docs.ultralytics.com/usage/settings) provides
update. Existing native runtime code temporarily overrides clearml in memory;
those unrelated live values must not leak to disk or be overwritten by setup.

## Remediation and architecture

The existing YOLO asset adapter will expose configure_weights_directory() -> Path
and WeightCacheConfigurationError. It owns explicit SDK/settings effects: read
the latest persisted mapping under an adjacent native FileLock, resolve relative
weights_dir against invocation cwd (without expanding literal tilde), persist
only the changed weights_dir through the SDK update API, and read back the entire
expected mapping. Retain absolute destinations and skip writes when already correct.
Preserve unrelated on-disk values and process-only SDK overrides. Synchronize the
live weights_dir and utils.WEIGHTS_DIR only on successful verification. Report
configuration failures with settings-file location and recovery instructions.

Catalogue preparation invokes setup before discovery or receipt reuse; preparation
failures remain explicit detached results under existing best-effort semantics.
NativeBatchProbe invokes setup for YOLO before worker launch. Keep trial cwd and
retention unchanged. Imports, help, inspection, public CLI and report schemas remain
unchanged. No numerical, interruption, dependency, or unrelated pending work is owned.

[Architecture record](architecture.json) reuses SDK ownership, inward imports,
dynamic imports and inert initialization contracts in .importlinter and existing
architecture negative tests. No new module or relaxed contract is needed.

## Task sequence and ownership

1. Parent inspects implementation, captures baseline, records architecture, validates plan.
2. Parent implements adapter and preparation/probe wiring; a bounded agent owns focused
   regression tests, with no further delegation. Tests reproduce the missing helper first.
3. Parent updates model-assets, filesystem/project contracts, README and current index;
   reconcile portable usage/evaluation guidance in corp-skills and active preparation docs.
4. Run focused tests, real cached selected/AMP checkpoint loading in existing and fresh
   processes with downloads blocked, canonical verify.py and verify.py --docs.
5. Check latest CY/cy-queue together with normal dependency resolution and matching
   metadata, queue static/import and integration checks; obtain fresh independent review.
6. Reconcile actual task delta, validate acceptance, and evaluate authorized Git release.

## Verification and compatibility

Python >=3.12.13,<3.14, existing uv environment, Ruff, strict mypy, Vulture,
import-linter and pytest remain authoritative. No dependency changes. Existing
mutation-selected pure modules/tests/dependencies are outside this task delta.
Focused checks cover relative/absolute paths, fresh workers, selected and AMP lookup,
latest unrelated persisted values, transient runtime values, idempotence, concurrent
CY setup, persistence failure and inert help/inspection. Real CPU checkpoint loading
proves lookup, not CUDA AMP numerical execution or training/publication outcomes.

## Documentation and release limits

Update cache setup and migration guidance: rerun cy-download-weights once from the
original preparation directory to reuse older relative caches. Record source and
validation for portable usage guidance. Keep artifacts here following the existing
bug-artifact convention; installed .specify tooling remains unchanged.

The starting worktree contains substantial unrelated pending source/docs, including
untracked downloader/preparation modules required by this fix. Preserve the snapshot
and stage only task-owned changes. A release must not silently include that pending
work or claim a committed standalone patch when prerequisites are absent from HEAD.
Missing required gates remain gaps; evaluate isolation or report the precise blocker.
