# Bug Assessment: Input and evaluation identity correctness

- **Slug**: input-evaluation-correctness (explicit delegated slug)
- **Created**: 2026-10-15
- **Source**: user implementation plan, section 1
- **Verdict**: valid
- **Severity**: high

## Report

Four reproduced defects: byte-identical CSVs can reuse another dataset's images;
relative prediction/comparison media paths use the working directory; detection CSV
labels such as `NA` become missing; noncanonical prediction names silently lose
membership during evaluation. The approved correction keeps `stem/path` raw exports
and restricts comparison/evaluation to canonical `name` identities.

## Reproduction

A 2026-10-15 offline `uv run --frozen --no-sync python` probe prepared two CSVs with
identical bytes and distinct red/blue images under `.tmp`. Both produced the same
cache entry (`different datasets reused: True`). Reading those rows with workflow
CSV settings yielded `literal NA became missing: True`; `images_to_score` returned
relative `train.png`/`val.png`; `InferenceConfig(..., image_name="stem")` succeeded.
The first probe correctly rejected output outside CY_HOME; the rerun used task-owned
project temporary space and cleaned it on exit. No native inference occurred.

## Suspected Code Paths

- `src/clearml_yolo/adapters/storage/dataset_cache.py`: byte-only key.
- `src/clearml_yolo/adapters/storage/file_io.py`: generic pandas NA inference.
- `src/clearml_yolo/application/use_cases/predict.py`: unresolved paths.
- `src/clearml_yolo/application/use_cases/compare.py`: unresolved fingerprints/inference.
- `src/clearml_yolo/adapters/yolo/reinfer.py`: prediction-cache CSV parsing.
- `src/clearml_yolo/adapters/clearml/results.py`: CSV publication and provenance.
- `src/clearml_yolo/adapters/evaluation/scoring.py`: membership before scoring.

## Root Cause

High confidence: parsing/resolution policy is duplicated across storage consumers;
cache identity omits resolved media references; evaluation assumes canonical membership
without checking incoming predictions.

## Proposed Remediation and Architecture

Storage owns lexical detection parsing, path resolution and cache identity; application
consumes a typed source/execution frame pair through `RunStorage`; pure core evaluation
policy rejects noncanonical mode and unknown image membership before scoring. Preserve
row order, identity text and round-trip float precision. Only explicit empty cells
represent missing/background values. Generic CSV reading remains independent.

Increment preparation version, include resolved references beside CSV digest/format,
and preserve old cache entries. Image contents at unchanged paths remain an explicit
invalidation responsibility. Newly written hash-bound provenance records prediction
naming mode. Historical files without mode remain valid when canonical membership holds.
Raw publication associates media by explicit mode without rewriting names or evaluation
status. No dependency/scientific algorithm changes are authorized.

See [architecture.json](architecture.json). Existing layered import contracts cover
all affected modules. Scope includes contracts/ports/composition, the listed adapters,
core evaluation policy, metrics workflow and corresponding regression tests. Parent
owns current/historical documentation, portable skill, native E2E, integration review
and release. This subtask makes no commits.

## Tasks and Acceptance

1. Validate architecture plan before implementation.
2. Add reproducing regressions; implement all shared input fixes together.
3. Verify targeted cache, prediction, comparison, metrics, publication and validation tests.
4. Run Ruff, mypy and import contracts; record actual results and remaining gaps.
5. Supply exact contract amendments to parent for documentation and native acceptance.
6. Parent obtains fresh review and records final architecture acceptance after integration.

## Risks and Considerations

Typed port additions require composition/test doubles to match. Historical stem/path
files intentionally fail evaluation; raw exports remain supported. No image hashing or
mtime validation is introduced. Empty backgrounds must stay missing for existing metric
algorithms while literal NA-like labels retain text identity.

## Open Questions

None; user choices are explicit. Native GPU/publication evidence remains parent-owned.
