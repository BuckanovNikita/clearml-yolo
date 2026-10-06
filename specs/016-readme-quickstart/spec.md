# Feature Specification: README quickstart

**Created**: 2026-10-06
**Status**: Approved for implementation in conversation
**Input**: Rewrite the Russian README around the primary cy command and migration
from a manual Ultralytics, digital-metrics and report-generator workflow. The user
selected a comparison table without a second executable manual scenario.

## User Scenarios & Testing

### User Story 1 — Run the pipeline (Priority: P1)

An existing Ultralytics user needs a short path from a YOLO dataset to pipeline results.
This is the primary purpose of the README.

**Independent Test**: Follow installation, tracking setup, data conversion and the
main command; inspect configuration without running training.

**Acceptance Scenarios**:

1. Given a YOLO dataset, the reader can identify prerequisites, prepare input and
   configure one pipeline invocation without consulting internal contracts.
2. Given a completed invocation, the reader knows where weights and evaluation
   outputs are stored and why paired reports may be absent.

### User Story 2 — Map an existing workflow (Priority: P2)

A user running the underlying libraries manually needs to see which steps cy connects.

**Independent Test**: Read the comparison and parameter tables, then locate each
standalone command and the relevant detailed documentation.

**Acceptance Scenarios**:

1. Each pipeline step identifies its manual library and wrapper behavior.
2. The reader can distinguish training and prediction settings and find limitations.

### Edge Cases

Missing test split, missing automatic baseline, CPU-only execution, existing local
dependency overrides, unavailable ClearML storage, and differing native defaults.

## Requirements

- **FR-001**: Lead with a Russian quickstart for cy, including installation, required
  tracking, data preparation, explicit model/device/project/tags and result locations.
- **FR-002**: Explain all manual pipeline steps through one comparison table using
  the actual underlying libraries, without a second manual executable scenario.
- **FR-003**: Provide a parameter mapping, one pipeline diagram, brief descriptions
  of other commands and links to detailed guidance.
- **FR-004**: Explain migration differences and conditional comparison/report outputs;
  do not imply identical results under differing data or settings.
- **FR-005**: Use short direct sentences, one action per step and stable terminology;
  interpret 80% ASD-STE100 as a style preference, not formal conformance.
- **FR-006**: Preserve application behavior, pinned dependencies, unrelated work and
  useful documentation destinations; validate examples and documentation.

## Success Criteria

- **SC-001**: One main pipeline example covers the complete primary journey.
- **SC-002**: All nine entrypoints are discoverable; every local link resolves.
- **SC-003**: Examples resolve against the current configuration; review finds no
  unsupported claims about automatic reports, data equivalence or installation.

## Assumptions

Readers know YOLO detection datasets and have access to a ClearML server and storage.
README remains Russian; workflow evidence remains English. No application changes,
dependency updates or real training are required for this documentation change.

## Follow-up clarification — 2026-10-06

The user corrected the onboarding path: assume an existing ground-truth CSV, passed
directly through `ground_truth`. Remove YOLO YAML conversion from the quickstart and
diagram; retain the converter only as an optional auxiliary command. This supersedes
the conversion-first language above without changing runtime input contracts.

Make the Russian prose natural and friendly while preserving technical accuracy.
Replace general GPU/hardware and manual device selection guidance with DDP and queue
instructions. All wrapper device examples must use `-1`; show repeated `-1` entries
for DDP. This is documentation guidance, not a new runtime validation restriction.

Acceptance: the quickstart starts with CSV, has no conversion prerequisite, and uses
automatic device requests. DDP and queue behavior matches current implementation.
The user also requested removal of the local source configuration block from README.
Installation and execution must use the committed lock without requiring that edit.

Further clarification: explicitly explain that each comparison reruns the old model
on the current ground-truth test split and recomputes its metrics, rather than using
historical predictions or scores. Preserve the distinction from retraining or threshold
recalibration: saved weights and frozen thresholds remain in use.
Add a concise FiftyOne integration note describing visual inspection and shared
evaluation results; omit enabled/disabled controls from README.
Remove the clone/submodule checkout and `cd` block from README installation, as
explicitly requested. The remaining instructions assume an available project checkout.
Remove the ClearML initialization step as well; keep ClearML access as a prerequisite.
Final steering supersedes these partial removals: assume all setup is complete.
README must focus on cy use, with no installation, environment prerequisites,
ClearML initialization, general setup troubleshooting or contributor navigation.
Show the installed cy commands directly; retain cy inputs/configuration/results,
migration comparison, DDP/queue and the requested FiftyOne integration note.
Show a concrete cy-config workflow: generate with cy-init-config, put native training
and prediction parameters in their respective group files, fill cy inputs/tracking,
then run `cy --config-dir cy-config --config-name cy`.
Make that generated-YAML workflow the primary quickstart, replacing the long inline
argument example. Keep CLI overrides secondary. The user explicitly requests committing
the documentation and publishing the next minor Git release (0.17.0 from 0.16.0).
