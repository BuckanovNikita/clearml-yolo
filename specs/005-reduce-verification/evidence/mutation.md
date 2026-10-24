# Scoped mutation evidence — 2026-10-24

The installed locked mutmut 3.8.0 runs only `core/datasets.py` (training-box function),
`core/evaluation/policy.py` and `core/export_quality.py`. Selection/configuration lives in
`pyproject.toml`; existing offline dataset/input/comparison/export tests plus focused
policy/export boundary cases supply assertions. Source and test helpers are copied into
ignored `mutants/`; no GPU/native training/publication/release tests are selected.

Initial command: `uv run --frozen --no-sync mutmut run --max-children 4`.
Initial result: **433 generated; 302 killed, 84 survived, 47 no tests**. No timeout,
suspicious, skipped or type-check-only outcome. Exit zero did not establish acceptance.
Private log: `.tmp/cy005-mutation-initial.log`; result listing:
`.tmp/cy005-mutation-initial-results.txt`.

Expanded tests add direct missing/empty membership and split-leakage cases, lexical
class vocabulary, exact invalid-row diagnostics, confidence/IoU endpoints, dtype/shape
validation, empty populations, rectangular geometry, matching cardinality and quality-loss
boundaries. They preserve observable contracts and exercise actual functions.

Expanded command: same bounded mutmut run. Result: **433 generated; 428 killed, 5
survived; zero no-tests, timeouts, suspicious, skipped or runner errors**. Private log:
`.tmp/cy005-mutation-expanded.log`. After consolidation into the existing export test file, the same command reran all
433 mutants: **428 killed and the same five survivors**, with zero incomplete outcomes.
Fresh execution log: `.tmp/cy005-mutation-consolidated.log`; retained selection, source/test/lock
hashes and individual mutant exit codes: [mutation-results.json](mutation-results.json).

After removing the local dependency-override section, an incremental run confirmed the
same complete results (`.tmp/cy005-mutation-final.log`); selected source/test/fixture/lock
hashes were rechecked and unchanged. This reused mutant results, not a second fresh run.

## Equivalent survivor dispositions

The three remaining equivalences are listed below. Two preliminary equivalence
arguments were disproved and those mutants are now killed, as documented below.

| Mutant (prefix `clearml_yolo.core.export_quality`) | Change | Equivalence within the supported contract |
| --- | --- | --- |
| `x__pair_iou__mutmut_50` | `np.asarray(..., dtype=None)` | Both arrays have already passed `validate_detections` and are float64. The arithmetic result is float64, so explicit dtype conversion is redundant. |
| `x__pair_iou__mutmut_52` | Omit the dtype argument | Same float64 input/result proof; this private helper receives validated arrays from the matcher. |
| `x_quality_gate__mutmut_36` | `loss <= tolerance` becomes `<` | The only differing case is equality, which the unchanged `math.isclose(loss, tolerance, rel_tol=0, abs_tol=1e-12)` accepts. All nonfinite inputs are rejected before this expression. |

No application policy changes were needed. Ordinary pytest success remains separate
from mutation results. Future affected source/test/fixture/dependency changes require
fresh affected mutation selection and renewed disposition review.

## Independent-review correction and fresh execution

The preliminary equivalence argument for `x_match_detections__mutmut_47` considered
real arithmetic but missed floating-point cancellation in SciPy assignment. Supported
float64 inputs change `max_score_error` from `6.5937460680049415e-06` to
`6.627767370277572e-06`. The added nearest-compatible-score case fails against the
actual mutant and passes against unchanged production policy. See [review](review.md).

An unqualified incremental run retained cached verdicts after the assertion changed.
Acceptance therefore used explicit selection to force fresh execution:

```bash
uv run --frozen --no-sync mutmut run --max-children 4 'clearml_yolo.core.*'
```

Result at that stage: **433 generated, 429 killed, four surviving candidates; zero untested, timeouts,
suspicious, skipped or runner-error results**. Mutant 47 is killed. The current per-mutant
outcomes and input hashes are in [mutation-results.json](mutation-results.json); full
execution log: `.tmp/cy005-mutation-fresh-final.log`. Future acceptance uses an explicit
affected module/function selection to rerun cached verdicts.

## Final empty-side correction

The parent disproved survivor 29's explanation using a finite `1e200`-sized box, an
empty opposite population and strict NumPy overflow handling. The original returns
unmatched counts; the `or` mutant evaluates unnecessary area arithmetic and raises
`FloatingPointError`. The existing three empty-population cases now cover this boundary
and pass unchanged production code. Scoped Ruff, strict mypy and all **109 export tests
passed in 1.13 seconds**. The interrupted fourth canonical attempt reached 1,792 passed,
one skipped and 47 deselected in 332.27 seconds; it recorded no receipt.

The same explicit all-selected-mutant command then reran all **433 mutants: 430 killed,
three equivalent candidates, zero untested/timeouts/suspicious/skipped/runner errors**.
Both disputed matching mutants are killed. Final log: `.tmp/cy005-mutation-final-three.log`.
The remaining two dtype mutants cannot change an already float64 arithmetic result;
the comparison mutant's equality case remains accepted by unchanged `math.isclose`.
The second fresh independent runtime review confirmed all three dispositions against
the actual generated functions, validated input contract and recorded exit codes;
see [review](review.md). The subsequent receipt-inventory correction changes none of
the selected mutation inputs or dependencies, so these results remain applicable.
