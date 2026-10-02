# Bug Fix: Optional visualization and collapsed predictions

- **Slug**: publication-collapsed-boxes (reused from assessment context)
- **Fixed**: 2026-10-02
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

Preserve finite, ordered zero-area native prediction boxes, and contain optional
visualization errors at the command boundary. Visualization failures warn and allow
computation/task completion; required computation, artifact/model uploads and flush
verification retain their failure behavior.

## Changes

| File | Change | Notes |
| --- | --- | --- |
| `src/clearml_yolo/publishing/data.py` | Modified | Allow collapsed predictions only; identify offending geometry in errors |
| `src/clearml_yolo/tasks/publication.py` | Modified | Warn on setup/publication/bookkeeping errors; disable failed setup |
| `tests/test_publication_data.py` | Added regressions | Row 225, original coordinates, indices, malformed geometry/confidence and strict GT |
| `tests/test_publishing.py` | Added regressions | Setup, database writes, missing receipts, bookkeeping and ClearML lifecycle completion |
| `tests/test_pipeline.py` | Updated regression | Pipeline continues after visualization failure and retains predictions |
| `tests/test_fiftyone_publisher.py` | Added opt-in regression | Persistence of zero width, zero height and point predictions |
| `README.md` | Updated | Russian usage and non-fatal visualization behavior |
| `docs/current-contracts.md`, `docs/project-contracts.md` | Updated | Optional visualization boundary and unchanged required publication gates |
| `specs/006-fiftyone-integration/` | Updated | Contract, spec, plan, quickstart and superseded-history notes |

## Tests Added or Updated

- Collapsed predictions retain their geometry, confidence, labels and CSV indices.
- Reversed/non-finite coordinates and invalid confidence remain rejected by the parser.
- Labelled ground truth still requires positive width and height.
- Setup failures select a no-op publisher; publication and receipt failures return no
  success result and report warnings.
- An actual invocation lifecycle with a fake ClearML SDK reaches `mark_completed`
  after visualization failure and retains the required uploaded prediction artifact.
- Pipeline visualization failure does not remove predictions or produce an adapter
  success receipt.

## Local Verification

- Test-first geometry regressions reproduced `Invalid publication box at CSV data row 225`.
- Test-first boundary regressions demonstrated eight visualization exceptions escaping.
- Affected command/publication tests: 109 passed.
- Ruff, strict mypy and all nine import contracts passed.
- A previously failing native prediction CSV now parses all 149,819 rows unchanged.
- Real persistence verification was attempted but could not establish the isolated
  database prerequisite; this initial check was not claimed as passing. The subsequent
  shared-stand retest completed all nine real persistence checks; see [test.md](test.md).
- Real FiftyOne `Detection.validate()` accepts and preserves zero width, zero height
  and point boxes with services disabled; this does not establish database persistence.
- Final regression and documentation checks are recorded in [test.md](test.md).

## Deviations from Assessment

The user subsequently supplied the actual collapsed box:
`(1482.845458984375, 1464.0, 1501.89892578125, 1464.0)` with confidence
`0.002323905471712351`, image `00031829_06_012835.jpg` and label `Пятна Эмульсии`.
This confirms the geometry category originally hypothesized.

The user explicitly clarified that visualization bugs must never fail the task.
This authorizes expanding the original geometry-only remediation to
`tasks/publication.py`, lifecycle/pipeline tests, README and contract summaries.
The previous fatal-visualization contract is superseded in current guidance while
dated evidence and completed task history are preserved.

## Documentation Update

The publisher contract, active specification, implementation plan, quickstart,
README and contract summaries now agree on optional visualization and prediction
fidelity. The existing task/checklist history is annotated rather than rewritten.
No entrypoints, configuration defaults, artifact inventory, dependencies or external
evaluation code changed. Changed Markdown, local links and example commands are
included in the final documentation validation.

## Follow-ups

The requested shared-stand setup and nine-test persistence retest are complete,
including exact row-225 readback with synthetic media; see [test.md](test.md).

## Final review correction — 2026-10-02

Independent completion review found that arbitrary backend exception text could
include MongoDB URI credentials in warnings. The publication boundary now logs
only the exception type and safe context. Three test-first regressions exercise
factory, preflight and publication failures with a credential-bearing message;
computation still continues and the credentials do not appear in warnings.
