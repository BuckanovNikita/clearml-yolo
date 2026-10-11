# Feature Specification: Controlled execution and library isolation

**Created**: 2026-10-11. **Status**: Approved for implementation by the user.

## User scenarios and testing

### US1 — Generate one command configuration (P1)

An operator generates the pipeline defaults, or selects one execution command.
Acceptance: omission produces only `cy.yaml` and required native groups; each of
the eight command selections composes; unrelated files remain untouched.

### US2 — Coordinate GPU jobs with explicit controls (P1)

Concurrent experiments use the restored full FIFO scheduler. Operators may disable
automatic device selection and scheduling independently.
Acceptance: three simultaneous single-GPU commands admit one runner and two waiters;
manual selection preserves device identity; disabling both adds no GPU probes/waits.

### US3 — Continue safely after FiftyOne failure (P1)

Visualization failure warns and preserves successful computation. A blocked library
operation cannot indefinitely hold the command or a queue reservation.
Acceptance: subprocess faults during import, database access, locking, writes and
shutdown complete within the configured deadline plus bounded cleanup; successful
publication retains the established receipt and evaluation persistence contracts.

### US4 — Own runtime configuration and temporary files (P1)

Runtime libraries use project configuration and clean invocation-owned scratch.
Acceptance: conflicting home/system configuration has no influence; completed,
failed and cancelled invocations remove their scratch while retaining durable data
and concurrent jobs' files. `HOME` remains unchanged.

## Functional requirements

- FR-001: `cy-init-config DIRECTORY [--command NAME] [--force]` accepts the eight
  public execution command names; default `cy`; generate exactly one wrapper YAML
  plus its schema-required groups. Selected outputs alone participate in preflight.
- FR-002: `queue.enabled` and `autogpu.enabled` default true on model commands and
  are validated execution controls, never workflow arguments.
- FR-003: Both enabled restores FIFO, atomic whole-GPU UUID reservations, fresh
  supervised children, liveness-based recovery, contraction and concurrent sweeps.
- FR-004: Queue off/auto on retains direct availability waiting. Both off preserves
  native settings and bypasses project GPU discovery/waiting/device replacement.
- FR-005: Queue on/auto off requires exact GPU selectors, reserves the union of
  enabled phases, preserves training order and retains the inference device after
  training. CPU/MPS bypass scheduling. Replay cannot change launch policy or exceed
  admitted identities/capacity. Mixed queue modes in one sweep fail before admission.
- FR-006: Preserve the compatible user-wide registry and ownership protocol across
  projects; corrupt/incompatible state fails closed, with no deletion or migration.
- FR-007: FiftyOne remains optional and warn-and-continue. Defaults are preflight
  60s, publication 900s and lock 30s; finite positive overrides only. Operation
  deadlines include import and exit. Cancellation retains cancellation semantics.
- FR-008: Only successful worker exit plus a matching complete receipt counts as
  publication success. Preserve partial persistent state for retry. Workers inherit
  no GPU visibility or application queue/ClearML ownership.
- FR-009: All exercised runtime libraries use project-owned configuration, cache
  and scratch paths. Credentials are explicit environment values or ignored local
  project configuration. No ambient home/system library configuration is read.
- FR-010: Preserve `HOME`, package defaults and OS runtime assets; reject library
  configuration outside the physical project root. Explicit data/output paths stay
  valid. Ordinary package imports remain inert.
- FR-011: Scratch ownership spans native children, publication, task finalization
  and upload completion. Clean success/failure/cancellation, including library leaks;
  recover abandoned scratch only with liveness/ownership evidence. Never delete
  shared data or advertise released capacity while owned GPU work may remain.
- FR-012: Preserve current TRACE/DDP/reporting behavior, dependency pins, original
  local modifications, installed workflow tooling and historical evidence.

## Success criteria

All command selections compose. Queue acceptance proves one runner/two waiters.
All injected publication failures warn and finish within deadline plus ten seconds
of cleanup. Config-access tracing shows no forbidden lookup. Owned scratch is absent
after normal/failure/interruption completion, with explicit diagnostics for cleanup
failures. Required project checks, native acceptance and independent review pass.

## Assumptions and boundaries

The original remote hang remains unconfirmed; fault injection proves containment,
not reproduction of that incident. Shared queue state is coordination, not project
configuration. Persistent caches, datasets, checkpoints and partial publication data
are not disposable scratch. No dependency source changes, deployment or asset upload.

The user's accepted controls/isolation supersede former queue-bypass and ambient
library-configuration restrictions. Preserve the dated constitution and installed
`.specify` files; record current authority in this feature and maintained contracts.
