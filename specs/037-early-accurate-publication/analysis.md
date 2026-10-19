# Specification consistency and coverage — 2026-10-19

The implementation follows the supplied plan as one Spec Kit change. Existing
configuration/publication contracts remain authoritative; feature 036 supplies
cache compatibility and is a release prerequisite. No workflow-tooling migration,
dependency revision change or historical-task rewrite is included.

| Requirement | Implementation boundary | Executable coverage |
| --- | --- | --- |
| FR-001 resolved active run | Hydra common composition; tracking session immutable executable roots | model replay, configuration publication, queue configuration publication |
| FR-002 nested selected-preset differences | Hydra built-in defaults; detached tracking mapping diff | configuration publication including explicit empty values, typed false/zero and ordered nested lists |
| FR-003 informational sanitized differences | tracking sanitization and recognized-script cache projection | configuration publication and cache tests, including conservative fallback |
| FR-004 early training General | direct entrypoint before workflow; programmatic train fallback; owner adapter | startup backend/skip/remote matrix, training, detector workflows, live reads before preparation |
| FR-005 early complete artifacts | result bundle, evaluation/report workflow, export producer callback | early publication/export, comparison assemble, metrics/report and live downloads |
| FR-006 declared contributor barrier | typed tracking port plus pipeline/standalone workflows | eight stage combinations, validation composition, cancellation and duplicate completion |
| FR-007 final verification/model lifecycle | existing owner finalizers, required uploads and model barriers | session/publication tests and real downloaded native/detector/DDP best models |
| FR-008 preservation/architecture/delivery | isolated snapshot delta; inward ports; sequential release | import contracts, injected forbidden imports, independent review and final reconciliation |

`run_overrides` excludes output/storage/task routing and result provenance. Effective
device selectors remain executable input differences, including queue-bound local
ordinals. Explicit CPU/GPU selection is meaningful; the full run always records it.
This interpretation avoids suppressing user device choices while preserving the
plan's exclusion of generated output locations and task identity.

No uncovered implementation requirement remains in this matrix. Pending full/native
checks, independent review, prerequisite integration and delivery are acceptance work,
not evidence of completed release. Physical multi-GPU/backend/export target limitations
must remain explicit in the verification record.
