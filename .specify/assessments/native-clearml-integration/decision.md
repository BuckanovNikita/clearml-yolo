# Decision: Native ClearML tracking

- **Slug**: native-clearml-integration
- **Decided**: 2026-09-30
- **Verdict**: go
- **Artifacts reviewed**: intake.md, research.md, problem.md, concept.md

## Scorecard

| Criterion | Rating | Justification |
|---|---|---|
| Problem validity | strong | User request and final-only DDP replay agree. |
| Evidence strength | adequate | Local source proves delay; real runtime remains to verify. |
| Value vs. inaction | strong | Mid-run progress enables inspection while training proceeds. |
| Feasibility / appetite | adequate | Existing native relay bounds the change. |
| Strategic fit | strong | Constitution already requires native ownership and clean replay. |
| Risk posture | adequate | Lifecycle, duplicate dispatch and failed publication are explicit acceptance gates. |

## Verdict & Rationale

Proceed with Option B. Static evidence identifies a concrete reporting gap and existing contracts protect the other requested behavior. No constitution amendment or dependency change is needed.

## Handoff to speckit-specify

- **Problem**: distributed progress is delayed; performance evidence needs clean, replayable publication.
- **Chosen approach**: complete native reporting and preserve publication contracts.
- **In scope / out of scope**: new-task telemetry, model verification and publication/replay regressions; no historical deletion or release.
- **Success metrics**: live epochs, one verified best model, zero configuration artifacts, successful configuration-backed recovery.
- **Carried-forward open questions**: none blocking specification; real device evidence remains a delivery gate.
