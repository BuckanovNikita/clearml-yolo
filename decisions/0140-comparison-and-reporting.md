# ADR-0140 · Compare models on a shared population and report the paired result

`cy-compare` evaluates a candidate and a baseline on the same split, using each model's frozen confidence thresholds. It records the evidence for each model, tests their differences, and writes a manifest that identifies the pair. `cy-report` uses that manifest to produce developer and business workbooks whose values can be traced back to the evaluated checkpoints.

## Model selection and an absent baseline

A local reference supplies weights and thresholds. A ClearML reference selects an explicit task or searches by project, name and tags. The default baseline is the latest eligible completed `prod` task other than the current task. An entirely default candidate is rejected. The evaluation guide says comparison ignores `evaluation.backend`, while the command preflight and comparison use case reject any value other than null. [Comparison command](../docs/commands/cy-compare.md) · [SIP-347](https://linear.app/sip-ds-team/issue/SIP-347)

For a ClearML task, model recovery first looks for a unique Output Model with `clearml_yolo_checkpoint_role=best` metadata, then a unique best-checkpoint filename. Ambiguity at either tier fails. The final fallback uses registration order and warns. The technical reference calls the first selector a `best` tag, but a tag alone does not satisfy the metadata check. An explicit threshold map takes precedence over thresholds recovered from the model or compatible historical artifacts and dashboards. [Model recovery](../src/clearml_yolo/adapters/clearml/models.py) · [SIP-352](https://linear.app/sip-ds-team/issue/SIP-352)

Only an absent automatic baseline permits a candidate-only outcome. CY scores the candidate, retains its diagnostics, thresholds and methodology, and records the comparison as skipped. This path produces no paired manifest for report generation. Failure to find an explicitly requested baseline fails the comparison. [Comparison workflow](../src/clearml_yolo/application/use_cases/compare.py)

<details>
<summary>Sources and verification</summary>

- Compare candidate and baseline on a common split — [Command preflight](../src/clearml_yolo/entrypoints/hydra/validation.py) · [Comparison workflow cases](../tests/test_comparison_reinfer.py) · [Candidate validation decision](https://linear.app/sip-ds-team/issue/SIP-211) · [Evaluation settings guide](../docs/configuration/evaluation.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#model-references)
- Recover checkpoints and frozen thresholds for comparison — [Recovery cases](../tests/test_comparison_recovery.py) · [Technical reference](../DOCS.md#comparison) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#recovering-historical-models)
- Retain candidate diagnostics when no automatic baseline exists — [Candidate workbook writer](../src/clearml_yolo/adapters/reporting/evaluation_workbook.py) · [Explicit and automatic absence cases](../tests/test_comparison_assemble.py) · [Candidate-only files](../docs/formats/workbooks.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#missing-automatic-baseline)

</details>

## Shared inference and local diagnostics

CY re-infers both checkpoints with shared requested settings on the current split. Each role can reuse predictions from the selected output directory when the checkpoint location and hash, settled inference settings, backend assertions and split image names and paths agree. CY checks available cached provenance before reuse and records requested and effective settings. A changed checkpoint timestamp alone leaves the key unchanged. The split fingerprint assumes media at each path is immutable. Disabling `reuse_existing` forces inference. [Cache identity cases](../tests/test_comparison_identity_cache.py)

A role- and split-specific local ZIP can retain native CSV, JSON, text and YAML diagnostics using relative names. The writer sanitizes structured JSON and YAML. Source-derived images stay out of the archive. [Archive writer](../src/clearml_yolo/adapters/storage/native_archive.py)

<details>
<summary>Sources and verification</summary>

- Reuse comparison predictions only for compatible inputs — [Cache key and split fingerprint](../src/clearml_yolo/application/use_cases/compare.py) · [Native inference reuse](../src/clearml_yolo/adapters/yolo/reinfer.py) · [Comparison settings](../docs/commands/cy-compare.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#re-inference-and-prediction-cache)
- Keep native comparison diagnostics in a local archive — [Archive cases](../tests/test_comparison_assemble.py) · [Containment cases](../tests/test_project_output_containment.py)

</details>

## Paired statistics and comparison manifest

Each model's dashboard retains its own measurements. CY calculates candidate-minus-baseline differences for shared eligible classes. Image-level paired bootstrap supplies the precision test and recall interval, and exact paired McNemar supplies the recall p-value. Benjamini–Hochberg correction covers precision and recall hypotheses together within a split. Shared eligible classes contribute to pooled counts, and the pooled result lies outside the class correction family. Undefined tests have unavailable verdicts. One-sided measurements and exclusion reasons stay visible. [Statistical assembly](../src/clearml_yolo/core/comparison/assemble.py)

CY writes the paired statistical workbook, exclusion and methodology CSVs, and `comparison_manifest.json`. The manifest identifies the split, roles, checkpoints and paths to the corresponding predictions, per-model dashboards and statistical workbook. It lets a report select one pair even when several runs have written results. [Workbook formats](../docs/formats/workbooks.md)

<details>
<summary>Sources and verification</summary>

- Test paired model differences over shared eligible classes — [Numerical tests](../src/clearml_yolo/adapters/evaluation/comparison.py) · [Statistical cases](../tests/test_comparison_significance.py) · [Pooled and per-class display](../tests/test_comparison_workbook.py) · [Comparison method](../docs/commands/cy-compare.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#scoring-and-statistics)
- Bind comparison outputs to named model roles — [Manifest writer](../src/clearml_yolo/application/use_cases/compare.py) · [Workbook format](../src/clearml_yolo/adapters/reporting/comparison_workbook.py) · [Manifest consumer](../src/clearml_yolo/application/use_cases/report.py) · [Manifest and missing-path cases](../tests/test_report.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/comparison.md#outputs)

</details>

## Report inputs and class populations

`cy-report` reads the manifest and both per-model dashboards. A missing input fails. The reporting adapter recovers each original dashboard layout, checks for per-model metrics and delegates table reading and workbook rendering to report-generator. A paired statistical workbook cannot substitute for a model dashboard. The manifest supplies the comparison split. Optional report YAML controls presentation and the minimum training count. [Report workflow](../src/clearml_yolo/application/use_cases/report.py)

Eligibility depends on the evaluated checkpoint's own training population. CY verifies the training task and checkpoint association before recovering the prepared ground truth and counting foreground annotations by class and original split. A per-model `Dataset counts` sheet can expose that evidence. A valid count is a nonnegative integer. Counts below `min_train_count` send a class to the excluded-class sheet. Missing or invalid counts stay unavailable and produce a warning, an `Unknown training count` sheet and a `Report issues` sheet. Each model aggregate uses its own eligible classes. Paired differences use shared classes with the required values. [Training-count recovery](../src/clearml_yolo/adapters/clearml/population.py)

<details>
<summary>Sources and verification</summary>

- Render paired developer and business reports from one comparison — [Paired rendering](../src/clearml_yolo/adapters/reporting/reports.py) · [Input and output cases](../tests/test_report.py) · [Report command](../docs/commands/cy-report.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#report-workbooks)
- Recover class counts from the evaluated checkpoint's training population — [Original annotation counting](../src/clearml_yolo/adapters/storage/population.py) · [Count provenance tests](../tests/test_training_count_provenance.py) · [Dataset counts workbook cases](../tests/test_population_count_workbooks.py) · [Workbook format](../docs/formats/workbooks.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#training-counts-and-warnings)
- Determine report eligibility separately for each model — [Training count contract](../src/clearml_yolo/core/report_counts.py) · [Partition and issue annotations](../src/clearml_yolo/adapters/reporting/count_issues.py) · [Count issue cases](../tests/test_report_count_issues.py) · [One-sided availability cases](../tests/test_report_class_availability.py)
- Keep report-generator presentation behind the reporting adapter — [OOXML integration](../src/clearml_yolo/adapters/reporting/workbook_identity.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#machine-readability)

</details>

## Developer and business workbooks

The developer workbook shows per-model metric availability and the contributing population below its tables. One-sided values remain visible. The business workbook has a fixed column order and includes listed dashboard columns when present. It retains the training-count column even when counts are unavailable. It sums example counts, respects exclusions from means, and marks differences `NA` if either operand is unavailable. It writes computed values so readers can see the results without recalculating spreadsheet formulas. The workbook includes the population note and model identity footer. [Rendering adapter](../src/clearml_yolo/adapters/reporting/reports.py) · [Business layout decision](https://linear.app/sip-ds-team/issue/SIP-242)

<details>
<summary>Sources and verification</summary>

- Present a fixed-column business comparison — [Real business workbook cases](../tests/test_report_business_layout.py) · [Workbook presentation](../docs/formats/workbooks.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#report-workbooks)
- Show metric availability in the developer report — [Real developer builder and availability cases](../tests/test_report_class_availability.py)

</details>

## Readable labels and recoverable identity

Workbook footers identify the models by name and role and can link to ClearML. CY assigns distinct readable aliases to opaque class identifiers on display copies of charts and sheets. Scientific records and CSVs retain their original class keys, and an alias notice identifies transformed workbooks.

CY owns the identity and alias schemas and uses report-generator's OOXML packaging to store the original workbook, full identities and fingerprint. When both annotations apply, the identity envelope wraps the presentation envelope. Reading an intact envelope detects later edits, and re-annotation starts from the recovered original. Third-party software that strips custom metadata can remove that evidence. [Workbook annotation](../src/clearml_yolo/adapters/reporting/workbook_identity.py)

<details>
<summary>Sources and verification</summary>

- Attach readable model identity while retaining original workbook bytes — [Identity round-trip cases](../tests/test_workbook_identity.py) · [Workbook identity in user documentation](../docs/formats/workbooks.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#identity-footer)
- Show readable class aliases without changing scientific keys — [Readable label allocation](../src/clearml_yolo/core/presentation.py) · [Dashboard and plot display](../src/clearml_yolo/adapters/reporting/evaluation.py) · [Class label round-trip cases](../tests/test_comparison_workbook.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/reports.md#readable-plots-and-charts)

</details>
