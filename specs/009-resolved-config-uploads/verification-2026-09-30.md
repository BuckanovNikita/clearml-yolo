# Verification evidence: Resolved configuration uploads

**Date**: 2026-09-30

## Initial implementation checks

Root reported the first combined `uv run pytest` run: **643 passed, 8 skipped, 4 existing warnings**, in **115.82 seconds**. Skips concern optional FiftyOne behavior; existing warnings are Pydantic deprecations. This initial suite predates the independent-review corrections below and is not final release acceptance.

## Independent review and convergence

Review identified three P1 gaps: artificial markers could corrupt custom-resolver arguments; sensitive context/environment aliases lost credential provenance; tuple outputs could bypass strict validation. These are captured in appended T019–T021. Relative-path preservation and task-owned execution-copy cleanup are captured in T022. Specification/design clarification established that effective context is current composed command values after replay/app output derivation, preserving explicit nulls; it does not include native model/task normalization.

Initial corrections passed 127 affected tests. Final independent review then reproduced a credential leak through computed node targets; T026 records confidential rejection of that unsupported expression form. Two regression tests failed before the guard and passed afterward. Final scoped review found no remaining blocker and confirmed ordinary/nested resolver arguments and mixed literals still work. The final combined affected suite passed **129 tests**, with four existing warnings; Ruff, strict mypy (92 source files) and all nine import contracts passed. Final repository/pre-commit and release acceptance are recorded below as completed.

## Real-run evidence inspected

The maintained global environment evidence document named `resolved-config-uploads-2026-09-30/verification.md` was read directly. Machine-specific run identity, service details, capacity readings and operational paths remain in that global source.

- Real ground-truth publication resolved environment, file-local and owning-command references in dataset YAML. Active uploaded values retained types; source bytes and interpolation-example comments were preserved.
- CPU baseline and single-GPU candidate pipelines trained native YOLO11n for one epoch over four training, two validation and two test images, including empty images and mixed extension casing. Successful training took 52.1 and 58.3 seconds respectively.
- Automatic baseline comparison skipped when no production baseline existed; after baseline promotion, the GPU candidate compared both models on identical current test images and generated reports from interpolated YAML.
- Validation/test thresholds were exactly frozen; full-precision validation CSV values matched payloads. Workbook display intentionally rounds thresholds to four decimal places. Paired comparison inference settings and image lists matched.
- Dataset cache image/NDJSON hashes and modification times remained unchanged; source extension casing was preserved.
- Every published artifact was force-downloaded: CPU **8**, GPU **10**, standalone validation **5**, comparison **3**, reporting **2**. Both training tasks had one native best Output Model, downloaded and loaded with matching labels/architecture. Native General parameters, Scalars, Plots and validation previews were present; checkpoints were not duplicated as artifacts.
- Standalone validation used nondefault IoU 0.45; standalone comparison reused retained checkpoints/exact thresholds; standalone reporting published interpolated JSON as concrete floats/strings while preserving input bytes.
- A real missing-reference dataset attachment failed its command and task without publishing dataset configuration or artifacts.
- Final task-owned cleanup reported zero matching projects/tasks, with unrelated workloads and shared infrastructure preserved.

## Limitations and harness corrections

The native smoke above predates the final credential-provenance corrections; the subsequent real attachment checks and final gates below cover those corrections. Two verification-harness assertions interrupted checks after successful product commands: a HOCON-only parser was incorrectly applied to YAML model metadata, and exact float equality was incorrectly required for rounded workbook display. Corrected checks reused owned successful evidence and retained outputs.

Physical multi-GPU operation and live upload-rejection, flush-failure, callback-registration-failure and interruption fault injection were not established by this smoke. Mocked checks remain distinct evidence. Final build/install, semantic-release and remote publication evidence is recorded below.

## Intermediate combined checks

After the first review corrections, root reported **659 passed, 8 skipped, 4 existing warnings** in **109.65 seconds**. Ruff, strict mypy over **92 source files**, and all **9 import contracts** passed. These results precede supplemental fixes T023–T025 and remain pre-final evidence.

Supplemental review found unsupported set/object resolver outputs, mixed escaped literal/active interpolation and embedded aliases, and embedded sensitive custom-resolver provenance reevaluation. A noncached resolver could execute twice and inventory a different sensitive value from the one actually published. These observations are captured as appended convergence work, including credential protection first.

## Follow-up real attachment boundary evidence

Read the global evidence document `final-attachments/verification.md` within the maintained dated environment evidence. A fresh public ground-truth invocation published dataset YAML with resolved environment/file-local/command references, typed integer/boolean/null values and preserved interpolation-example comment. Source SHA-256 stayed unchanged; its artifact was force-downloaded.

A separate real invocation using the default provenance-aware callback published YAML and JSON with redacted sensitive context aliases, direct environment references and dynamically nested environment references, retaining concrete benign paths and collection/scalar types. Execution copies stayed unredacted and separate; original source hashes remained unchanged. Fixtures used dummy values and credentials were not printed.

An initial harness ordering error let SDK process-master state reach a subsequently launched child and produce a StubObject. Its log was retained, cleanup ran, and the successful retry launched the public command first without product changes. Final cleanup reported zero matching projects/tasks and removal of owned scratch resources. Remote clone replacement remains covered by fake repository tests, not this real run. No native training was repeated for the attachment checks.

These attachment observations precede the newest supplemental corrections; the subsequent final edge checks below cover them.

## Final review corrections and edge checks

The resolver now rejects unsupported sets/objects and validates tuple outputs recursively. Escaped literals and embedded aliases preserve native arguments; syntax-only provenance does not execute registered code. Sensitive embedded references protect the rendered value without reevaluating noncached resolvers, and unused context resolvers remain uncalled. Private metadata is excluded from the result representation. Generic error categories intentionally do not expose private field/reference details.

The first final full suite passed **666 tests, 8 skipped, 4 existing warnings in 110.26 seconds**, before the last two dynamic-node regression tests were added. This is pre-final acceptance for that last guard; the configured full pre-commit gate below supplies final coverage.

Actual ClearML YAML/JSON edge checks confirmed one custom private-resolver call per file, no consumed dummy credential in uploaded text, private execution inputs, unchanged source hashes, preserved mixed literal/interpolated strings, and unsupported set rejection before publication. A subsequent real run with the final dynamic-node guard repeated those checks and verified both direct and embedded computed targets failed their tasks without publishing a configuration. Owned execution files and tagged projects/tasks were cleaned up; zero matching projects/tasks remained.

## Final delivery acceptance

Final `uv run pre-commit run --all-files --verbose` passed every configured gate. Its repository pytest run passed **668 tests, 8 skipped, 4 existing warnings in 115.87 seconds**. Ruff passed, strict mypy found no issues in 92 source files, and import-linter kept all nine contracts. Eleven changed Markdown files passed local-link (14 links), whitespace and fenced-block checks; staged diff whitespace validation passed.

Spec Kit convergence checked 11 functional requirements, five success criteria, seven acceptance scenarios, six implementation design decisions and the five governing constitution principles against the implemented scope and regression/live evidence. No remaining implementation finding was identified; no empty convergence phase was appended. All implementation and delivery tasks have observed acceptance evidence. Independent scoped review has no remaining blocker.

The authorized feature commit is `6aefaa354e2f20ef05e3d62b7901399548045133` (`feat(config): resolve configuration files before ClearML upload`). Normal commit hooks passed; the local release hook checked and created `4431d8f543ff3f55e9926c4db82af5ac1a5c1bf3` (`chore(release): 0.10.0`) with annotated tag `v0.10.0`. The release commit changes only the root project versions in pyproject.toml and uv.lock. All external locked package metadata, versions and sources, and both submodule revisions, remain unchanged.

`uv build` produced the 0.10.0 wheel and source distribution. Fresh separate wheel/sdist installations each passed version/import checks, all **nine** command help pages, all **eight** exported command-config compositions, overwrite protection, device/default/publication compatibility and the new provenance-aware resolver check. All 52 packaged Python modules matched the checked tag source. Owned package environments and fixtures were removed; logs and release artifacts were retained.

The commits and exact annotated tag were pushed through the existing SSH remote. The published [GitHub release v0.10.0](https://github.com/BuckanovNikita/clearml-yolo/releases/tag/v0.10.0) is neither draft nor prerelease and includes the wheel, source distribution and SHA256SUMS. GitHub reported all three assets uploaded with matching sizes and SHA256 digests. Downloaded wheel/sdist bytes and SHA256SUMS also matched the tested local assets. The first public asset-host download timed out; a retry completed and passed integrity checks. Remote master/tag references matched the checked release commit before final evidence bookkeeping.

All T001–T026 tasks are complete. Full SDD workflow, independent scoped review and final convergence have no remaining implementation finding. Extension configuration registers no before/after implement or converge hooks. Physical multi-GPU and live fault injection limitations remain as stated above.
