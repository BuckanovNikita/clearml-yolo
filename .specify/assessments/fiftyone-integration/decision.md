# Decision: FiftyOne Integration

- **Slug**: fiftyone-integration
- **Decided**: 2026-09-29
- **Verdict**: go
- **Artifacts reviewed**: intake.md, research.md, problem.md, concept.md

## Scorecard

| Criterion | Rating | Justification |
|-----------|--------|---------------|
| Problem validity | strong | Existing metrics output has no persistent sample-level review surface. |
| Evidence strength | adequate | Repository evidence establishes current scoring and ownership; real adapter behavior remains a release check. |
| Value vs. inaction | adequate | The feature connects existing result evidence to per-image review. |
| Feasibility / appetite | adequate | A bounded adapter and explicit recovery design fit a medium appetite. |
| Strategic fit | strong | The boundary and verification plan honor the constitution. |
| Risk posture | adequate | Identity, locking, disabled mode, and fidelity are explicit requirements. |

## Verdict & Rationale

Go. The problem and constraints are concrete, and the selected publisher boundary keeps FiftyOne observational rather than authoritative. The remaining API uncertainty is covered by an explicit real smoke gate.

## If go — Handoff to `$speckit-specify`

- **Problem**: make exact evaluated results visually inspectable without changing scoring or ownership.
- **Chosen approach**: typed neutral publisher with a single FiftyOne adapter.
- **In scope / out of scope**: default eligible commands, persistent local reuse and failure safety; no UI/media copy/scoring changes/val or compare publishing.
- **Success metrics**: dependency-free disabled path, single receipt, reuse-safe records, matching fidelity.
- **Carried-forward open questions**: validate real adapter behavior in smoke evidence.
