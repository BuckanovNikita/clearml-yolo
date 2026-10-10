# Implementation Plan: Native ClearML tracking

**Branch**: `010-native-clearml-integration` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Stream native DDP epoch events during training and retain existing v0.10 configuration-only replay, performance publication and verified native best-model contracts. Preserve native callback authority and final publication barriers.

## Technical Context

- **Language/Version**: existing Python compatibility from pyproject.toml, Python 3.12 development environment.
- **Primary Dependencies**: pinned Ultralytics, ClearML, existing Hydra/OmegaConf/ruamel.yaml; no dependency updates.
- **Storage**: task-owned local JSONL event journal, existing ClearML Configuration Objects, native Output Model and result artifacts.
- **Testing**: pytest behavior tests, Ruff, strict mypy, import-linter and real integration evidence.
- **Target Platform / Project Type**: existing native CLI applications on supported CPU/GPU installations.
- **Performance Goals**: owner consumer polls every 250 milliseconds; backend delivery uses existing SDK flush/reporting behavior.
- **Constraints**: one task, owner-only SDK access, local diagnostics retained, final publication after complete journal validation.
- **Scale/Scope**: single training invocation and existing nested pipeline stages; no persistent service.

## Constitution Check

**Before research: PASS. After design: PASS.** No amendment required.

Preserve strict types, module boundaries and deferred model imports. Thread context preserves invocation ownership. Workers retain no SDK publication. Failure propagation, model-upload barriers, sanitized configuration-only replay, frozen thresholds and existing dependency pins remain mandatory. Mocked tests do not claim GPU or backend outcomes. Documentation stays portable and existing workspace work is preserved.

## Research and Design

See [research.md](research.md), [data-model.md](data-model.md), [tracking-publication.md](contracts/tracking-publication.md) and [quickstart.md](quickstart.md).

## Implementation

### Live native DDP relay

Preserve native_ddp_relay context-manager and replay(trainer) call interfaces. Start an owner-only consumer in the relay context, using contextvars.copy_context so active_task identity reaches the thread. Poll appended journal bytes every .25 seconds, retaining incomplete trailing bytes. Validate record shape and callback set before dispatch. Maintain original order and a consumed cursor; each completed non-final event dispatches once through installed native callbacks using the existing replay views and recorded model information.

Defer on_train_end until replay(trainer) stops/joins the consumer, drains pending bytes and validates full journal ordering/counts/arguments/best checkpoint. Only then dispatch the deferred native final callback, apply final worker args/checkpoint/save_dir to the parent trainer and proceed to existing best-model verification. Do not replay prior events. Repeated or misplaced terminal events fail validation. Non-DDP execution does not consume local owner events as DDP events.

Store consumer failures and propagate them at replay/exit boundaries. Stop and join before removing callbacks or temporary journal resources, including exceptions and interruption. No worker tasks/uploads and no surviving task-owned consumer. Earlier telemetry on failed runs is allowed, final successful completion is not.

### Native tracking and publication contracts

Add behavior coverage for native registration, task reuse, requested plots behavior, upstream scalar names/indices and restored settings. Keep automatic native capture choices as installed callbacks define them; do not add competing scalar implementations.

Protect existing exactly-one native best-model barrier and byte verification with existing/new regressions. Audit command publication inventories and configuration-return paths, including repeated consumed files, numbered temporary names, train_data_overrides.json, report inputs and local manifests/receipts. Keep named configurations/General as replay authority. Root makes production changes only where tests/evidence demonstrate a remaining violation; do not rewrite feature 009 or broad-filter filenames/extensions.

Source-model provenance uses task/model links from the model's source task. Preserve existing
comparison inference ownership, canonical exact validation CSV readers and historical weight/
threshold fallback. Resolve source weights and thresholds without automatically fetching source
General parameters or Configuration Objects; missing required model inputs fail actionably.

### Parallel ownership

- Relay agent: src/clearml_yolo/native_ddp.py and tests/test_native_ddp.py.
- Tracking agent: tests/test_native_tracking_contract.py.
- Publication agent: tests/test_publication_commands.py and tests/test_config_upload_commands.py.
- Root: shared wiring/production corrections, README.md, native best-model review, real verification and integration.
- Artifact agent: assessment and this feature's Spec Kit artifacts; root owns .specify/feature.json.

Agree lifecycle interfaces before edits. Disjoint behavior tests can run in parallel; root integrates combined changes and updates task status only from evidence.

## Project Structure

Retain src/clearml_yolo and tests layout. This feature adds specs/010-native-clearml-integration and .specify/assessments/native-clearml-integration; no new runtime service or public schema.

## Delivery and Gates

Assessment intake/research/define/shape/decide → specify → clarify → plan → checklist → tasks → analyze → implement → repository/real verification → independent review → converge. The approved conversation supplies review decisions; extension hooks are empty. Run pytest, Ruff, mypy and import-linter. Real acceptance follows running-end-to-end-tests and environment skill contracts; report physical DDP separately if unavailable. No commit/push/release.

## Complexity Tracking

No constitution deviations. A scoped journal consumer thread is necessary for progress during blocking native DDP training; completion-only replay does not satisfy the requirement.

## CPU distributed verification amendment — 2026-10-10

This additive plan implements FR-012–FR-017 and SC-006–SC-008 from the amended
[specification](spec.md#cpu-distributed-verification-amendment--2026-10-10).
Existing checked tasks and real-service evidence retain their original scope.
The approved scope is tests and developer guidance only: no new public APIs,
dependencies or production adaptations.

### Native execution and isolation

Generate an isolated synthetic detection dataset with eight training images, eight
validation images, 64-pixel image size and one class. Use the installed local
YOLOv8n architecture YAML with random initialization, two epochs and global batch
size eight. Set dataloader workers to zero; disable AMP, compilation, plots and
augmentation. Use real Torch distributed CPU/Gloo processes at world sizes two
and four and the installed native DetectionTrainer loops.

Test-only trainer adaptations cover CPU device setup, CPU DDP wrapping and final
evaluation. Preserve native optimizer, sampler, validation, callback and checkpoint
behavior; do not patch dependency source or add a production CPU-DDP launcher.
Worker diagnostics prove actual PID/rank identity, CPU tensors, Gloo, DDP wrapping,
optimizer parameter changes, matching final rank parameters and epoch sampler
partitions. Native final-best validation may reuse an epoch number; verify event
identity/order without incorrectly treating that epoch index as a duplicate.

The owner runs the production relay with a local recording task and observes native
telemetry while workers remain live. Local recordings prove callback ownership and
one best-model association; loading that actual checkpoint proves inference
compatibility. They do not prove ClearML SDK uploads, backend delivery or download
barriers. Worker processes cannot create tasks or publish.

### Failures and resource lifetime

Inject failures after epoch zero in rank zero and a nonzero rank, and inject an
owner publication callback failure. Verify a failed outcome, no successful terminal
best-model record and complete owned-process/thread cleanup. Use a 30-second Gloo
process-group timeout, a 180-second per-scenario deadline and a five-second graceful
shutdown window followed by termination of only the scenario-owned process tree.
Retain unit cases for malformed journals, missing checkpoints and duplicate owner
events; real distributed tests complement those controlled failure cases.

Prerequisite checks may skip only unsupported Linux/WSL platforms or unavailable
Torch distributed/Gloo support. Native runtime, worker and callback failures are
test failures. Register `ddp_cpu` without a default exclusion: both `uv run pytest`
and the existing pytest commit hook execute the suite. Focused selection uses
`uv run pytest -m ddp_cpu`.

### Ownership, dependencies and verification

- Worker agent owns `tests/ddp_cpu_worker.py` and `tests/ddp_cpu_trainer.py`.
- Parent owns `tests/test_native_ddp_cpu.py`, `tests/ddp_cpu_harness.py`,
  `tests/ddp_cpu_launcher.py`, `tests/ddp_cpu_recording.py`, marker registration and
  integrated verification.
- Documentation agent owns additive changes to this feature's `spec.md`, `plan.md`,
  `tasks.md`, `quickstart.md` and `docs/development.md`.
- Parent owns dated evidence, final task status and a fresh independent read-only
  review after integrating disjoint results. Bounded agents do not delegate further.

Run focused CPU acceptance, existing relay/publication regressions, default pytest,
Ruff, strict mypy and import-linter, followed by applicable commit checks without
bypassing hooks. Record outcomes and limitations in
`docs/evidence/2026-10-10-cpu-ddp.md`; do not record observed timings/counts in
evergreen guidance. Accelerator launcher behavior, NCCL, AMP and real ClearML
uploads remain outside this amendment's acceptance evidence.

### Documentation stage and constitution check

Update `docs/development.md` and this feature's `quickstart.md` for prerequisites,
default/focused collection, failure behavior and evidence limits. Validate changed
Markdown, local links and documented selection commands after test integration.
Review README, current contract index, native publication contracts and integration
skills against the actual diff. No changes are planned there because public command,
configuration, native publication and real-service acceptance contracts remain
unchanged; this amendment documents a developer regression harness. Record that
review outcome in the task ledger and dated evidence.

Constitution check: test-only CPU adaptations preserve production delegation to
Ultralytics and installed dependency pins. Isolated paths, explicit owned-resource
cleanup, native execution evidence and truthful local-recording limits satisfy the
verification and collaboration principles. Existing workflow artifacts are reused;
no installed Spec Kit tooling or completed history is rewritten.
