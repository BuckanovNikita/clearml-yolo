# Independent review — 2026-10-20

## First integrated review

A fresh-context native reviewer inspected the complete task-owned application
diff against `41a4036`, the architecture record, executed checks and the companion
skill diff against `351fde3`. The reviewer had no write ownership and performed
no shared-service calls or further delegation. Requested model settings inherited
the parent; exact runtime model/effort metadata was not observable.

Verdict: **fix-first**. One P2 finding: checking only the presence of root
`dataset.csv` permits additional files or external links. A no-network probe of
the installed ClearML SDK demonstrated that an empty filtered link mapping falls
back to all external links, despite `files=["dataset.csv"]`. The reviewer required
an exact CSV-only logical inventory check before materialization, negative tests,
and matching application/skill documentation.

No other actionable defects were found. The reviewer accepted the separation
between selectors and resolved provenance, inward injected dependencies, exact
deferred SDK ownership, nested workflow propagation, replay behavior, pure export
validation, default runtime dependencies and preserved protected sources.

The reviewer inspected the 332-test integrated focused result, 28-test replay
result, static/import checks, documentation and initial native/packaging evidence.
Pending full/minimum/native completion was explicitly not treated as passing.

## Resolution

Two new extra-inventory cases failed before the fix because they reached the
download stub. The adapter now requires `set(dataset.list_files()) ==
{"dataset.csv"}` after checking finalization and the required root path.
Extra files and links fail before `get_local_copy`. Documentation distinguishes
the logical/materialized input from SDK archive-level transfer/cache behavior.
Final verification and fresh independent re-review are recorded below.

## Scope adjudication

Physical multi-GPU/compiled execution, every detector/export target, FiftyOne
publication, live remote queue replay, unrelated cache policy changes and strict
exclusion of historically deleted bytes from SDK archive transport were considered
and set aside. The parent accepts these scope limits: this feature supports
CSV-only logical datasets, existing media references and the existing workflow
capabilities; it does not replace the SDK's transport or expand backend coverage.

## Fresh final review

A second reviewer started with a fresh context after the correction, parent
verification and documentation reconciliation. Verdict: **ship** for the final
code and documentation, with no remaining actionable findings. The reviewer
confirmed SDK file/link inventory coverage, the pre-materialization guard,
selector/replay/provenance semantics, pure export validation and inward effect
ownership. Independent TOML comparison confirmed unchanged development
dependencies, protected dependency requirement and every non-root lock record.

The reviewer performed read-only source/diff/test inspection, architecture plan
validation, companion no-impact acceptance, whitespace/dependency comparisons
and wheel-content inspection. It explicitly identified the older retained wheel
as preceding the guard; final-source rebuild and installed-wheel probes remain
a delivery gate. Full-suite completion and final evidence reconciliation are
parent acceptance responsibilities. The reviewer neither reran full suites nor
contacted shared services. No new behavior was set aside beyond the adjudicated
scope above.

## Constructor compatibility follow-up

A third fresh-context reviewer inspected the final constructor correction after
parent verification. Verdict: **ship**, with no actionable findings. The original
parameter order/defaults are preserved; the optional repository follows exporter.
Local and resolved inputs return before accessing it; remote selectors without
it raise the documented error. The reviewer verified that the regression had
failed through positional misbinding before the fix and that the training assertion
continues checking the existing path contract. Explicit Hydra registration removes
collection-order dependence. No SDK/filesystem effect leaked inward.

The reviewer independently compared baseline/current signatures and ran a passing
probe for 11- and 12-argument positional construction, old keyword construction,
exporter identity, local resolution and missing remote capability. Whitespace and
architecture planning checks passed. It inspected the 134-test focused and
285-test architecture/tooling results, static/docs logs and the complete suite's
nine original failures. It performed no edits, further delegation or shared-service
calls. Minimum-matrix completion, final wheel and architecture acceptance remain
separate evidence gates.

## Final dependency and verification reconciliation

After the scoped review, exact report failures established pandas 3.0.0 and
openpyxl 3.1.5 as the final common floors. This changed only root dependency
requirements/lock metadata. The parent independently compared every non-root lock
record against the integrated baseline; all are unchanged. Final report checks
(46 per interpreter), full minima (3,370 passed per interpreter), all four
installed-wheel probes and normal full commit hooks passed. The packaged Python
sources match the reviewed final source. No new runtime implementation, architectural
exception or weakened test fixture was introduced by this floor adjustment.

## Concurrent baseline integration: review pending

The verdicts above apply to the source preceding upstream `0340e9c`, not the
current merge. Preserve the original fix-first finding and all closure evidence.
Fresh review must assess the retained cleanup, dedicated Ruff/import contracts,
relocated frozen fixtures, migrated `001` feature records and combined source
after renewed checks. The unpublished `aaa35d9` / `v0.36.0` candidate provides
historical verification only; it is superseded for release. T022 remains pending.

### Fresh concurrent-baseline integration review

Fresh-context native reviewer `/root/baseline_review` requested gpt-6.1-sol at high
effort with read-only ownership; runtime model metadata was not observable.
Verdict: **ship** for integrated source/docs, no actionable regressions. The reviewer
independently passed 61 source/replay tests, architecture plan validation and
working/staged whitespace checks, and inspected parent static/import checks,
395 normal tests, both 535-test minimum selections and the current-source build.

Review confirmed feature runtime is unchanged from `de726d9` except an AST-identical
ports comment, upstream baseline/Ruff/cleanup/fixtures are preserved, and the
dedicated import configuration has exactly the two intended feature changes.
Non-root lock records match both predecessors, and runtime/dev requirements match
the accepted feature. Selector validation, complete logical inventory rejection,
lazy effects, nested resolution, local warnings and replay/provenance separation
satisfy the contract. A stale pending T021 sentence in dependency evidence was
reconciled with the executed checks. Architecture record acceptance and required
full commit/release hooks, final versioned probes and delivery are parent gates.
No tracked edits or remote effects were performed by this reviewer.
