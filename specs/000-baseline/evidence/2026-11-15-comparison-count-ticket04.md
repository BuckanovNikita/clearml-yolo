# Ticket 04: eligible-class comparison count

Date: 2026-11-15. Comparison base: `bce7df823f85f4c52ad7785ca2800dce691e20c1`.
Scope: routine defect correction against the existing
[scientific-result contract](../spec.md#data-and-scientific-results) and
[shared comparison policy](../../../docs/shared-evaluation-reporting.md#scientific-computation).
No specification or public result schema change is required.

## Change and agreed test seam

The public `compare()` workflow returned the number of displayed class rows,
including excluded classes. It now returns the existing methodology's count of
statistically eligible classes, which already owns workbook reporting.

The approved ticket selects the product comparison workflow as the test seam.
Regression cases exercise real CSV ingestion, reinference adaptation, evaluation,
comparison assembly, and workbook/sidecar generation. Detector inference, checkpoint
resolution metadata, and task initialization are replaced at external boundaries.
These offline tests establish the returned result and local artifact semantics;
they establish no live model execution, remote service outcome, or publication.

## Verification ledger

- **Passed: defect reproduction.** A shared `cat` vocabulary with one ground-truth
  box and no predictions failed the new `compare()` assertion on the original
  implementation: `classes_compared` was 1, expected 0. The minimal correction
  then passed that same regression.
- **Passed: five workflow cases.** No predictions; missing model vocabulary;
  absent ground truth; mixed eligible/excluded classes; and an all-eligible
  control. Expected compared/excluded counts are literal scenario expectations.
  The generated methodology CSV agrees with those values.
- **Passed: focused type checking.**
  `uv run --locked mypy src/clearml_yolo/application/use_cases/compare.py tests/test_workflow_quality.py`.
- **Passed: focused Ruff lint and formatting.** Same two paths checked with
  `ruff check` and `ruff format --check`.
- **Passed: focused comparison/workbook suite.**
  `uv run --locked pytest --testmon-noselect tests/test_workflow_quality.py tests/test_comparison_assemble.py tests/test_comparison_workbook.py tests/test_shared_comparison.py -q --disable-warnings --basetemp=.tmp/ticket04-pytest`:
  106 passed in 110.36 seconds. This refreshes dependency evidence for the new regression.
- **Passed: native mutation report production and review.**
  `uv run --locked task --exit-code mutation -- --max-children 1`, against an
  isolated index containing this source/test change, exited 0. Selection covered
  the changed `compare` function and 35 test selectors across 16 modules, including
  the new workflow regression. The native 300-second budget was unchanged.
  Clean baseline and forced-failure checks passed. Of 488 mutants in the changed
  function, 34 were killed, 1 survived, 0 were unreached, and 453 were not run
  within the budget. This is bounded mutation evidence, not full mutant coverage.
  The one survivor, `x_compare__mutmut_4`, changes the unchanged default
  `bootstrap_iterations=10000` to `10001`. It exposes an existing default-value
  observation gap outside the eligible-class return-field correction; it is not
  claimed globally equivalent and no statistical default was changed. The direct
  red/green reproduction separately establishes that the new regression rejects
  the original incorrect count expression.
  [Compact native report output](2026-11-15-ticket04-mutation.txt) retains the
  result counts and complete surviving diff.
  The first run's pre-existing testmon selection
  omitted the newly added test within an already represented module. It was
  interrupted and discarded (exit 130); the fresh report used refreshed
  dependency evidence as recorded above.
- **Passed: fresh independent review.** Read-only source/test/evidence review found no critical, important, or minor issues; both assembly paths supply the methodology integer and the public schema/workbook behavior are preserved.
- **Passed: final automatic verification and commit.** Commit `31e2733dd79f82f1b7d5a9166dbe3b90a8c73b47` passed the canonical `prek run --all-files` with overrides cleared in a clean, separately prepared managed checkout. The native route ran static checks and established a fresh full unit baseline. A fresh immutable-commit review passed afterward, and the exact commit fast-forwarded onto local `master`. No global coverage floor or release is claimed.
- An earlier automatic attempt in the shared working checkout stopped at Ruff on in-progress ticket03 profile complexity. It ran no product tests and supplies no count-fix acceptance evidence; the clean-checkout pass above isolates this ticket.

Selection is focused because only an existing result field's source changes;
there is no shared runtime, configuration, dependency, or queue interface change.
The campaign's final full suite is not duplicated here. No global coverage floor,
GPU execution, publication, or paired queue compatibility is claimed by these
checks. No check was waived.

Verified implementation SHA-256:
`49e89df08c81a5e70c25729c8b0d3d773b04e2980b854eb386268f9b21d1626c`.
Regression module SHA-256:
`ae5b178e513e7694e0ff03ce5430759adf2145575e7c1cb9abdfd2a125e43362`.

## Preservation and cleanup

No dependency source, pin, lockfile, public field, workbook behavior, or unrelated
working-tree change was modified. Mutation execution uses a disposable alternate
Git index, preserving shared staging. Its native driver owns and removes mutation
workspaces and descendants. Completed focused-suite outputs at
`.tmp/ticket04-pytest` and the three isolated initial-regression pytest directories
were removed after recording results and confirming their ownership. No GPU work
or live environment was created for this ticket. Both mutation runs and all
descendants have exited; disposable indexes/workspaces and the temporary raw log
were removed, retaining the compact native report above.
