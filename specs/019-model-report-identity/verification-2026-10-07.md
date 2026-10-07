# Verification: 2026-10-07

## Scope and workflow

Implemented the approved model identity plan through Spec Kit specification, design,
task mapping, consistency analysis, implementation and documentation. No material
requirements needed clarification. Source publication, workbook adaptation and
evaluation captions were delegated with separate ownership; the parent integrated
tasks/configuration and verified the combined changes. Installed Spec Kit tooling and
pinned dependency sources/revisions remain unchanged.

The shared identity retains finalized model name, full source training task ID, model
ID and checkpoint hash. New outputs carry it through checkpoint/prediction sidecars,
evaluation contexts, comparison manifests, plots and every workbook worksheet.
Unknown standalone inputs require a fallback label and explicitly unavailable
training provenance. Existing artifact names and output paths are preserved.

## Regression and repository checks

- Full suite before final review corrections: 1,261 passed, 30 skipped. These results
  establish the earlier integrated state; final release hooks verify the corrections.
- Final workbook/source/cache/flow selection: 119 passed. It includes real generated
  multi-sheet dependency dashboards and developer/business workbooks, literal long
  Unicode/formula-like labels, unchanged metric cells/styles/class populations,
  translated formulas, charts, tables, filters, validation, freeze panes, print titles,
  print areas and explicit row breaks, plus exact legacy-layout threshold reading.
- Comparison cache regressions reproduced reuse of stale identity/prediction bytes
  before correction. Reuse now validates prediction/checkpoint hashes and source
  identity before writing provenance; explicit regeneration remains available.
- Two metadata-integrity regressions failed before the correction and pass afterward:
  changing either a valid stored identity or embedded original workbook is rejected.
  The package fingerprint covers metadata and original content, excluding only itself.
- Final rendering/reporter/comparison-assembly selection: 77 passed.
- The empty comparison-table regression failed before the correction: no rows meant
  no displayed identity values. A persistent escaped caption now retains both source
  identities without fabricating metric rows or changing plot title/series keys.
- Ruff, strict mypy (146 source files), all ten import contracts and whitespace checks
  passed after the integrity correction. Final hook evidence is recorded below.

## Documentation and compatibility

Updated Russian README usage, current contracts, model metadata, task recovery,
evaluation publication, end-to-end prerequisites and feature artifacts together.
Hydra configuration snapshots expose all eight label keys across six entrypoints;
the quoted Unicode label example composes and roundtrips successfully. Markdown
parsing, 110 local links/anchors and nine fences passed across 17 changed documents.

Historical unannotated dashboards remain readable. Annotated workbooks preserve an
embedded original for the pinned readers and reject subsequent package edits; users
regenerate reports from their inputs instead of editing annotated metric cells.
Existing source provenance wins over a fallback label. Historical ClearML artifacts
are not rewritten.

## Limits

Print repetition and coordinate preservation are verified through OOXML/openpyxl,
not an Excel/LibreOffice PDF render. Horizontal print width is normalized to one page;
explicit row breaks and existing print titles are preserved, while automatic page
counts can change to accommodate repeated banners. Long labels, Unicode text and
formula-like strings roundtrip literally. The available raster font lacks some CJK
glyphs; those PNG glyphs are not claimed rendered, although full Unicode identity is
retained in PNG metadata, interactive captions and workbooks.

Physical multi-GPU execution and enabled FiftyOne persistence are outside this change's
native acceptance. Focused regression and the full suite exercise relevant publication
failure paths; mocked tests do not establish GPU execution or remote uploads.

## Native execution and publication

The final isolated stand run completed nine stages: CPU pipeline without a baseline,
single-GPU pipeline with a promoted baseline, standalone validation through training
task ID, model ID and local sidecar, standalone comparison/reporting, and prediction
and metrics from unknown local inputs with custom Unicode labels.

Repeated training resolved `train` to the distinct candidate `train-sunny-lynx`.
Fresh model downloads matched recorded SHA-256 and source task metadata. Validation
thresholds remained frozen for train/test. All reporting/validation tasks retained
the original training identities; they did not substitute their own task IDs.
Custom labels remained `local-custom-Ω` and `csv-custom-Ω` with unavailable training
provenance. Canonical CSVs retained all eight ground-truth source rows and source
identity columns in prediction/evaluation contexts.

Force-downloaded all 70 published artifacts. The 46 downloaded workbooks contained
60 worksheets: each showed its complete identity and repeated print titles with
one-page horizontal width. All 82 locally generated workbooks carried metadata.
All 100 published evaluation plots retained source identity in SDK readback.
Separate readback of comparison, methodology and the empty degraded table confirmed
both source names/full task IDs, no reporting-task substitution, and no fabricated
rows in the empty table. Real developer/business workbooks retained nine sheets.

Two attempts across the exploratory/final runs encountered transient failures in
existing ClearML SDK model/project queries before the changed behavior. Repeated
read-only queries succeeded; unchanged resumed commands completed. The underlying
server cause remains unclassified. One exploratory Unicode CLI attempt was rejected
by Hydra before execution; quoting the value resolved it and is documented.

Machine logs, commands, downloaded artifacts, model/task records and failed attempts
are archived with the global environment skill. Both task-owned stand projects and
run directories were cleaned; listings confirmed no owned tasks/projects remained.
Pre-existing shared services and data were left intact.

## Independent review and release preparation

Fresh independent reviews found and verified the three corrected edge cases above.
The final review returned `ship`, independently passing 35 focused tests and the
whitespace check with no remaining feature finding. An uncached pretrained-alias
late-download issue was confirmed to exist before this change and was not expanded
into this feature's scope.

Wheel and source distributions were built and installed in separate fresh environments;
all ten command helps passed in each. Final-version builds follow release metadata.
The ordinary feature/release hooks run against the installed frozen environment with
`UV_NO_SYNC=1` while the exact local source overrides are temporarily absent. No hooks
are bypassed. The existing offline root-version lock refresh uses a disposable source
configuration and verifies every dependency record remains identical.

The first feature-hook attempt stopped with 1,235 passed, 30 skipped and 35 release
fixture setup errors: the temporary offline-lock adapter intercepted fixture
repositories as well as the real project. The adapter is now restricted to this
repository's exact working directory; other commands use the real tool unchanged.
No feature/release commit was created by that failed attempt, and local overrides
were restored. The release fixtures and complete hooks are rerun before acceptance.
