# Feature Specification: Estimated-batch native acceptance

**Feature Branch**: `master`
**Created**: 2026-11-15
**Status**: Approved scope
**Input**: Campaign ticket 03: adopt fresh estimated batches and two-epoch native acceptance.

## User Scenarios & Testing

### User Story 1 - Measure the selected training recipe (Priority: P1)

A verifier needs a capacity measurement for the exact chosen model, precision,
resolution and augmentation before starting native acceptance training.

**Why this priority**: A measurement of a different recipe cannot justify the batch.
**Independent Test**: Change precision or augmentation and observe a distinct profile
and worker recipe; exercise actual augmentation during a bounded measurement.

**Acceptance Scenarios**:
1. Given an explicit native or JSON/Mosaic recipe, when measured, then workers execute
   that recipe and report its synthetic workload bounds and resource state.
2. Given failed estimation, when acceptance starts, then it fails without substituting
   batch one or a stale standard-table recommendation.

### User Story 2 - Train the frozen acceptance corpus (Priority: P1)

A verifier trains the selected preset for two epochs using a freshly measured batch,
then verifies the scientific result and its publication.

**Why this priority**: Acceptance must exercise optimizer updates and native outputs.
**Independent Test**: Complete one GPU scenario through prediction, validation,
checkpoint reload and independent remote readback.

**Acceptance Scenarios**:
1. Given positive usable capacity, when training begins, then the selected batch is
   the largest backend-valid batch no greater than that capacity and 160 images.
2. Given the frozen 160/40/40 corpus, when any of 21 selections and three augmentation
   variants runs, then it uses seed zero, FP32 and the preset resolution for two epochs.
3. Given training OOM, when the scenario ends, then evidence records failure without retry.

### User Story 3 - Respect a reserved-memory execution window (Priority: P1)

A verifier can require free VRAM to remain available to other workloads.

**Why this priority**: A scenario must not consume the user's reserved GPU memory.
**Independent Test**: Resource telemetry below an optional reserve prevents launch or
terminates only owned workers and leaves incomplete evidence.

**Acceptance Scenarios**:
1. Given a reserve, when memory changes materially after estimation, then admission is
   rechecked and stale measurements cannot authorize training.
2. Given a reserve breach, when a worker is running, then it stops and cannot produce
   accepted capacity or training evidence.

### Edge Cases

Missing/unresolved augmentation, changed pipeline content, invalid capacity, empty
training population, foreign compute, changed GPU identity, telemetry failure,
nonfinite loss, failed independent confirmation, and interrupted cleanup fail explicitly.

## Requirements

### Functional Requirements

- **FR-001**: Measurements MUST identify and execute the exact selected model configuration,
  precision, resolution, augmentation content and current memory state.
- **FR-002**: Custom augmentation MUST execute during measurement; conservative synthetic
  bounds MUST preserve the selected native finalization, target amplification and shape policy.
- **FR-003**: Acceptance MUST freshly estimate each case and select the largest backend-valid
  batch no greater than its usable raw capacity and 160 training images, recording both values.
- **FR-004**: All maintained 21-by-three scenarios MUST train for two epochs with the frozen
  160/40/40 split, seed zero, preset resolution and FP32; separately contracted precision checks remain.
- **FR-005**: Estimation errors, OOM, invalid measurements and resource interruptions MUST fail
  the case with diagnostic evidence; no silent fallback or unapproved extra training is allowed.
- **FR-006**: An optional free-memory reserve MUST be checked before and during owned execution;
  material memory changes invalidate admission. Ordinary estimator defaults remain unchanged.
- **FR-007**: A representative end-to-end scenario MUST prove real optimizer updates,
  checkpoint reload, predictions, validation and independent publication/readback.
- **FR-008**: Existing bounded scenario/trial timeouts, process ownership, upstream pins,
  and immutable fixture handoffs MUST remain preserved; superseding configurations are distinct.

### Key Entities

- Training recipe: model settings, augmentation snapshot, precision and resolution.
- Capacity evidence: recipe identity, resource snapshot, trial outcomes and raw capacity.
- Acceptance selection: capacity identity, chosen batch, corpus identity and two-epoch inputs.
- Memory reserve: optional free-byte requirement with observed admission/monitoring state.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every accepted scenario retains matching measurement and training identities.
- **SC-002**: Every selected batch is positive, backend-valid and bounded by capacity and corpus size.
- **SC-003**: A representative scenario produces the complete scientific result and independently
  verified publications after two epochs; failed or incomplete checks are never accepted.
- **SC-004**: No accepted run breaches its selected free-memory reserve or loses owned-process cleanup evidence.

## Assumptions

Campaign fixtures and renewable services are separately accepted prerequisites. The
campaign video-mode reserve is 8 GiB; host resource restrictions still govern admission.
Single-GPU capacity is a constrained synthetic-workload measurement, not a guarantee
for arbitrary datasets or an unconstrained physical-device maximum. No longer training,
external deployment, release or upstream dependency change is authorized here.
