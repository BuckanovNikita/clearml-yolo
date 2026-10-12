# Shared extraction acceptance evidence — 2026-10-12

## Source and baseline

Application baseline: 4aef37f6. Dependencies were verified byte-for-byte against the
approved source revisions recorded in [plan.md](plan.md). Independent Git repositories
now track the ignored dependency copies. See [baseline evidence](baseline-2026-10-12.md)
for immutable pre-extraction observations; expected values were not regenerated after
implementation. One detected regression (skipped kappa -1 versus 0) was fixed at the
new evaluator, preserving the baseline.

## Executed checks

The manual application checks below used `uv run --frozen --no-sync` in the existing
environment. The final isolated commit also ran the repository's normal hooks, with
dependency synchronization disabled and imports explicitly resolving its source tree.

| Check | Result |
|---|---|
| `pytest -q` | Exit 0: 2171 passed, 30 skipped, 56 warnings; 452.27 seconds |
| `pytest tests/test_shared_extraction_compatibility.py tests/test_shared_comparison.py tests/test_architecture.py -q` | Exit 0: 133 passed, 7 warnings; includes the newly added comparison tests collected after the full run began |
| `pytest tests/test_comparison_significance.py tests/test_comparison_assemble.py tests/test_comparison_observability.py -q` | Exit 0: 93 passed |
| `pytest tests/test_shared_extraction_compatibility.py tests/test_evaluation_separation.py tests/test_scoring_evidence.py tests/test_report.py tests/test_identity_flows.py -q` | Exit 0: 45 passed |
| `mypy .` | Exit 0: no issues in 280 source files |
| `ruff check .` | Exit 0 after task-owned formatting correction |
| `vulture` | Exit 0 |
| `lint-imports` | Exit 0: all 40 contracts kept |

The architecture suite exercises positive rules and injected forbidden imports/effects.
Exact SDK ownership edges now include the new comparison adapter and reporting v2
wrappers. Obsolete openpyxl ownership edges were removed because application wrappers
no longer import it. Core/application still cannot import either extracted library.

Library owners ran their unchanged suites and new interface/boundary tests. Their
dated records live beside their architecture plans. Metrics additionally uses its own
locked environment to distinguish optional SDK typing differences from library errors.

## Coverage and limits

Frozen checks cover all matching/AP combinations, confidence ties, empty predictions,
unavailable metrics, signatures/defaults, CLI/configuration, exact labels, one-sided
availability, custom layouts and original-workbook recovery. New comparison tests
compare exact rows and callback ordering over six populations and three seeds.
Workbook checks compare cells/formulas/resolved styles/charts/printing semantically;
original embedded content recovery is byte-exact. The library's new-render test counts
one save per plot and checks caption metadata and figure closure.

Existing match image ordering originates from a set, so baseline comparison canonicalizes
incidental match ordinals/order while retaining all numerical values and source-row
relationships. Skips are not passes. These offline checks establish neither representative
model accuracy nor native GPU execution or remote uploads. Those systems were not changed.

## Documentation and ownership

Updated shared capability guidance, dependency documentation and current contract index.
README usage/configuration, persisted publication contracts and machine setup remain
unchanged, so no corresponding example changes are needed. Preserved unrelated static
analysis configuration, runtime/gpu_queue.py, test and lockfile edits listed in plan.md.

Independent integrated review, final architecture acceptance and delivery are recorded
below after their execution.

## Independent integrated review — 2026-10-12

Fresh native agent `integrated_review`, requested gpt-6.1-sol/high with no inherited
conversation and read-only ownership, returned **ship** with no material compatibility
or architecture findings. Runtime model/effort were not independently observable.
The reviewer inspected all three task-owned runtime diffs and independently checked
frozen science, paired tables, public signatures/config/CLI, dependency constructors,
metadata v1 recovery/validation/tamper cases and both libraries' negative import tests.
AST comparisons found nine copied statistical models/kernels and fifteen OOXML helpers
unchanged; AP arithmetic remained unchanged apart from observation collection.

The parent reconciled the application record's test/documentation scope and replaced
its placeholder documentation-check path with the actual executed standard-library
Markdown/link command. Eight application Markdown files passed fence/link checks.
All application source/testing changes, dependency boundary configuration, untracked
additions and removed duplicated implementations were inspected; unrelated static
analysis/runtime/test/configuration edits are excluded from task ownership.
The library records cover their complete runtime modules, tests, fixtures and guides.
Residual limits remain the representative fixture populations and offline execution
scope documented above. All three architecture acceptance validators passed separately
after this review was recorded.

## Versioned delivery

Digital-metrics release hooks passed and published main and annotated tag `v0.7.0`
at `6e801be1564dce458294eb23592cc1aa0939c4d9`. Report-generator has no established
release workflow; its task-scoped commit `d10aa395d08f738e92e04e076cee93b3a993bf8f`
was published to main after the user's continuation of the pending push request.
Both approved dependency revisions are available upstream.

Application implementation commit `55dcabd87f002502f59fe55b8910f161be01da62` was
created in an isolated checkout containing only task-owned changes. Normal commit
hooks passed: whitespace/configuration checks, changelog generation, Ruff, mypy,
import-linter, the full pytest suite including the new comparison tests, and the
semantic release hook. The refactor does not trigger a version bump under the
existing policy; the application remains at 0.25.0. The commit was fast-forwarded
into the original workspace and published to master.

All 21 captured preservation fingerprints matched after integration, including the
shared configuration, lockfile and development guide containing unrelated changes.
The committed pyproject has no local source section; the original working copy
retains that section unstaged. No GitHub Release object or package artifact was
created. The task-owned lockfile change is only digital-metrics 0.6.1 to 0.7.0;
other dependency/source metadata is retained. Generated changelog changes follow
the repository's existing hook and carry no module impact.
