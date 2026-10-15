# Bug Fix: Input and evaluation identity correctness

- **Slug**: input-evaluation-correctness
- **Fixed**: 2026-10-15
- **Assessment**: [assessment.md](assessment.md)
- **Status**: applied

## Summary

The four input defects are corrected without changing scientific algorithms or approved
dependencies. Source rows retain their lexical identifiers and order; execution resolves
media from the source CSV; evaluation requires canonical membership.

## Changes

| Ownership | Paths | Change |
| --- | --- | --- |
| Storage | `adapters/storage/file_io.py`, `dataset.py`, `dataset_records.py`, `dataset_cache.py`, `publication_data.py` | Shared exact detection reader; typed source/execution pair; CSV-relative media resolution; preparation version 2 keys include resolved references; consistent UTF-8 BOM support. |
| Workflow interfaces | `application/contracts.py`, `application/ports.py`, `entrypoints/composition.py` | `GroundTruthRead`, detection/ground-truth reads, naming-mode provenance capability; canonical comparison request types. |
| Workflows | `application/use_cases/predict.py`, `compare.py`, `metrics.py` | Resolved inference/fingerprints, lexical source lineage, canonical-only evaluation before filtering/scoring, mode-bound prediction provenance. |
| Policy and adapters | `core/evaluation/policy.py`, `adapters/evaluation/scoring.py`, `adapters/yolo/reinfer.py`, `adapters/clearml/results.py`, `entrypoints/hydra/validation.py` | Pure mode/membership checks, exact cache reads, raw export split association preserving names and unevaluated status, early configuration rejection. |
| Regressions | `tests/test_input_correctness.py`, `test_dataset_cache.py`, `test_predict.py`, `test_metrics.py`, `test_comparison_identity_cache.py`, `test_comparison_reinfer.py`, `test_comparison_assemble.py`, `test_clearml_results.py`, `test_quality_properties.py` | Reproductions and compatible fixture/property updates. |

Paths in this table are relative to `src/clearml_yolo` except the test group.

## Tests Added or Updated

The dedicated input suite proves distinct relative-reference caches and shared absolute
reference reuse; changed contents/mtime at unchanged paths retain existing cache entries;
BOM and reordered columns preserve reference identity on misses/hits; source/execution
rows remain aligned; literal `NA`, `NULL`, `nan`, `None`, numeric-looking and Unicode labels
retain perfect AP and exact threshold-edge floats. Unknown prediction identities fail.

Workflow tests exercise prediction and `skip_train` from a different directory with a
conflicting same-named image, comparison resolved inference/fingerprints with lexical
source lineage, raw name/stem/path publication and strict explicit provenance modes.
Historical sidecars lacking the naming field remain usable with canonical membership.
The existing Hypothesis cache round-trip property now uses canonical comparison mode
and includes explicit NA-like identities.

## Local Verification

See [test.md](test.md) for executed commands and dated results. Architecture planning
was validated before code changes; existing import contracts pass unchanged.

## Deviations from Assessment

The initial assessment grouped metrics with resolved ground-truth reads. Inspection
showed metrics can validly evaluate a CSV without media paths, so it consumes the shared
lexical detection reader; only inference and media association use `GroundTruthRead`.
This preserves evaluation-only input compatibility.

Parent review identified UTF-8 BOM inconsistency. Specialized training and FiftyOne
lexical readers already preserve label text but decoded plain UTF-8; they now accept
UTF-8 BOM consistently and share media resolution. They retain strict original row/header
validation rather than adopting pandas inference. The BOM regression includes first-column
`image_path`, two source directories, cache hits and FiftyOne snapshot inspection.

## Documentation and Follow-ups

Parent owns current contract/spec amendments, portable usage guidance, full routine
verification, native CPU/GPU and ClearML acceptance, packaging, independent final review
and release. Exact contract amendments were sent to parent. These gates remain distinct
from the focused checks here. No commits, dependency edits, shared-service intervention
or deployment were performed by this subtask.

## Integration follow-up: geometry fixtures (2026-10-15)

The first complete routine suite exposed three obsolete assertions in
`tests/test_prediction_geometry.py`. A focused reproduction yielded 3 failures and
45 passes: the geometry fixture supplied six prediction image names absent from truth,
and the missing-`image_name` case expected the former generic diagnostic. Current
identity admission correctly rejected these inputs before geometry filtering.

The fixture now includes those six images as explicit canonical background rows,
retaining every original geometry, preprocessing and warning assertion and checking
that background membership survives preparation. Missing-column checks require the
specific missing field. Five added cases verify that zero-area, reversed, missing,
nonnumeric and nonfinite geometry cannot hide an unknown image identifier. Runtime
source and identity policy are unchanged; native and packaging source snapshots remain
valid. The architecture scope adds only this test file and preserves the parent's
reconciled module/contracts/check fields.
