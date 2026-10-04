# GPU Scheduling Requirements Quality Checklist

**Purpose**: Reviewer checklist for concurrency, lifecycle, and integration requirement quality
**Created**: 2026-10-02

`[x]` means a reviewer approved the requirements quality. `$speckit-implement` reads but does
not modify this reviewer-owned checklist.

## Requirement Completeness

- [ ] CHK001 Are queue participants and explicitly immediate commands exhaustively identified? [Completeness, Spec §FR-001]
- [ ] CHK002 Are demand rules complete for every accepted native device value and command role? [Completeness, Spec §FR-008]
- [ ] CHK003 Are supervisor, child, queue-entry, and reservation lifecycles all defined? [Completeness, Spec §FR-006, §FR-009, §FR-014]
- [ ] CHK004 Are the pre-admission and post-admission ClearML ownership boundaries explicit? [Completeness, Spec §FR-010]

## Requirement Clarity and Consistency

- [ ] CHK005 Is strict FIFO defined consistently as head-of-line admission with no fit-based bypass? [Clarity, Spec §FR-002, §FR-015]
- [ ] CHK006 Is atomic reservation consistently defined as all N whole devices or none? [Consistency, Spec §FR-003]
- [ ] CHK007 Are stable UUID identity and child-local native indices clearly separated? [Clarity, Spec §FR-007, §FR-009]
- [ ] CHK008 Are requested and effective device settings consistently separated from queue demand? [Consistency, Spec §FR-008, §FR-009]
- [ ] CHK009 Is the retain-first pipeline rule consistent across transition, inference, and final release? [Consistency, Spec §FR-011]

## Acceptance Criteria Quality

- [ ] CHK010 Can FIFO and non-overlap outcomes be measured without relying on timing luck? [Measurability, Spec §SC-001]
- [ ] CHK011 Can liveness recovery distinguish held from acquirable supervisor/child native locks without TTL or PID authority? [Measurability, Spec §SC-002]
- [ ] CHK012 Is the exact multi-GPU transition outcome objectively measurable? [Measurability, Spec §SC-004]
- [ ] CHK013 Are ordered Hydra success and failure results objectively observable? [Measurability, Spec §SC-005]

## Scenario and Edge-Case Coverage

- [ ] CHK014 Are external compute users and unknown telemetry both covered with fail-closed outcomes? [Coverage, Spec §FR-004]
- [ ] CHK015 Are inherited visibility values, including indices and UUIDs, covered before native context creation? [Coverage, Spec §FR-007]
- [ ] CHK016 Are crash, interruption, stale registry, and lock-release risks covered by ownership requirements? [Coverage, Spec §FR-006, §FR-014]
- [ ] CHK017 Are oversized requests explicitly rejected before enqueue? [Edge Case, Spec §FR-003]
- [ ] CHK018 Are unsupported MIG, cross-host, daemon, priority, and bypass behaviors explicitly excluded? [Coverage, Spec §FR-015]
- [ ] CHK019 Is the race with outside processes after the final telemetry check documented as a residual limitation? [Assumption, Spec §Assumptions]

## Dependencies and Evidence

- [ ] CHK020 Is the NVML dependency and its fail-closed role documented? [Dependency, Spec §FR-004, §FR-007]
- [ ] CHK021 Is BasicSweeper the only promised sweep integration, with callback, environment, directory, and ordering semantics stated? [Dependency, Spec §FR-013]
- [ ] CHK022 Are native multi-GPU and DDP claims gated on dated evidence rather than mocked tests? [Evidence, Spec §FR-016, §SC-006]

## Notes

- Reviewers leave items unchecked until they evaluate the written requirements.
