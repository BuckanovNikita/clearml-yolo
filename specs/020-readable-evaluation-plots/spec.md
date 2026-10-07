# Feature Specification: Readable evaluation plots

**Created**: 2026-10-07
**Status**: Approved for implementation
**Input**: Clean unreadable plot IDs, combine related graphics, show PR only on test,
and exclude previous-model content including comparison tables from ClearML Plots.

## User Scenarios & Testing

### US1 — Read grouped current-model results (P1)
Reviewers identify the evaluated model and split without decoding identifiers, toggle
class curves on one test PR chart, and select normalization on one confusion chart.
**Independent test**: inspect published labels, traces and normalization choices.
1. A multi-class test evaluation produces one PR chart with class legend entries.
2. Each current-model split produces one confusion chart with four selectable views.
3. Repeated evaluation of the same checkpoint/split reuses its display slot.

### US2 — Keep previous models out of Plots (P1)
Reviewers see only the current model in Plots while comparison reports remain available.
**Independent test**: run comparison with a baseline and inspect every plot event.
1. Baseline evaluations publish durable results and reports, but no charts.
2. Comparison, degraded-class and methodology tables do not appear in Plots.
3. Native training callbacks do not upload validation PR charts.

### Edge Cases
Empty predictions preserve AP50 zero; no GT has unavailable recall/AP without invented
points. Numeric, Unicode and markup-sensitive labels retain their identity. Missing
model display identity uses a readable fallback. Colliding display names must not
silently overwrite unrelated model contexts. Workers publish nothing.

## Requirements
- **FR-001**: Visible evaluation chart labels use model names/splits, never encoded IDs,
  checkpoint hashes or training task IDs. Full identity remains in provenance.
- **FR-002**: Combine class curves into one current-model test PR chart, preserving
  observations, AP50, integration method, confidence and cumulative TP/FP.
- **FR-003**: Combine confusion views using Counts, Row %, Column %, Overall %, default
  Counts; preserve class order/background, orientation, exact counts and finite percentages.
- **FR-004**: Exclude baseline charts and comparison tables from Plots while preserving
  downloadable comparisons and headline values outside that tab.
- **FR-005**: Reuse chart slots for repeated checkpoint/split publication; distinguish
  unrelated contexts with readable stage labels and numeric suffixes when necessary.
- **FR-006**: Native callbacks cannot publish non-test PR. Preserve native non-PR output,
  scalar reporting, model uploads, callback state and owner-only publication.
- **FR-007**: Update affected contracts and validate documentation; preserve historical tasks.

### Key Entities
Evaluation context retains durable model/context/split provenance. Display slot is an
invocation-local readable chart identity, independent of stored provenance IDs.

## Success Criteria
- **SC-001**: One PR chart per current-model test evaluation, with every class inspectable.
- **SC-002**: One confusion chart per current-model split with all four views available.
- **SC-003**: Zero baseline charts, comparison tables or non-test PR in new Plots output.
- **SC-004**: Display changes preserve every numerical observation and report artifact.

## Assumptions
Current model is comparison candidate or standalone evaluated model. Historical tasks
are unchanged. Comparison headline values outside Plots and downloadable reports remain.
