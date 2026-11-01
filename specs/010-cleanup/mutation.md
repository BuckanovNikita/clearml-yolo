# Cleanup mutation acceptance — 2026-11-01

## Scope and execution

The cleanup changes `tests/conftest.py`, which supplies fixtures to the configured
mutation tests. The dependency lock also differs from the previous evidence.
Following the scoped mutation acceptance policy, this run freshly executed every
configured mutant using explicit selection; it did not reuse the previous verdicts.
The initial execution started without a generated directory. After the integration
correction moved architecture contract construction into the lazy fixture and
restored the architecture helper boundary, this final explicit selection reran
all 433 cached mutants against the corrected copied fixture. Initial raw evidence
is preserved under `.tmp/cleanup-mutation*-revision1.*`; final raw paths below
contain the second execution. Both executions produced the same outcome totals. All 433 individual execution
durations changed in the final metadata, corroborating fresh execution.

```bash
uv run --frozen --no-sync mutmut run --max-children 2 'clearml_yolo.core.*' > .tmp/cleanup-mutation.log 2>&1
uv run --frozen --no-sync mutmut results > .tmp/cleanup-mutation-results.txt
uv run --frozen --no-sync mutmut show clearml_yolo.core.export_quality.x__pair_iou__mutmut_50
uv run --frozen --no-sync mutmut show clearml_yolo.core.export_quality.x__pair_iou__mutmut_52
uv run --frozen --no-sync mutmut show clearml_yolo.core.export_quality.x_quality_gate__mutmut_36
```

Both run and results commands exited zero. Per-mutant metadata independently confirms
**433 executed: 430 killed and three surviving equivalents**. There are zero no-test,
timeout, suspicious, skipped, type-check-only or runner-error outcomes. By source,
training-box validation contributes 57 killed mutants, evaluation policy 109 killed,
and export quality 264 killed plus the three reviewed survivors. Acceptance uses
these individual outcomes and dispositions, not the command exit status alone.

The unchanged `pyproject.toml` selection mutates only `core/datasets.py`,
`core/evaluation/policy.py` and `core/export_quality.py`. The only pytest selections
are `test_dataset_records.py`, `test_input_correctness.py`,
`test_comparison_scoring.py`, `test_export_quality.py` and `test_policy_mutation.py`.
The copied `tests/` directory provides their fixtures and helpers. No services, GPU,
native training, publication or full-suite pytest run was requested or used here.

Before launch, the installed mutmut generation, metadata, statistics and pytest
working-directory code was inspected: generated source, spans, metadata, statistics
and pytest caches stay within ignored `mutants/`. Raw logs and captured evidence
stay within ignored `.tmp/`. No configuration, runtime source or tests were edited.

## Survivor dispositions

Each actual generated diff was inspected again against the current source contract.
The selected source and tests match the [previous mutation evidence](../005-reduce-verification/evidence/mutation.md);
the changed fixture and dependency inputs are bound by the hashes below.

| Mutant (prefix `clearml_yolo.core.export_quality`) | Actual change | Current disposition |
| --- | --- | --- |
| `x__pair_iou__mutmut_50` | Replace `dtype=np.float64` with `dtype=None` | Equivalent under the supported validated-input contract. `match_detections` calls `validate_detections` on both populations before calling the private helper; that validator returns float64 arrays. The NumPy arithmetic result is already float64, so the final conversion is redundant. |
| `x__pair_iou__mutmut_52` | Omit `dtype=np.float64` | Equivalent for the same reason: inferred dtype is the already float64 arithmetic-result dtype. |
| `x_quality_gate__mutmut_36` | Replace `loss <= tolerance` with `loss < tolerance` | Equivalent: only equality differs, and the unchanged `math.isclose(loss, tolerance, rel_tol=0, abs_tol=1e-12)` accepts equality. The existing metric checks reject nonfinite inputs before this expression. |

The formerly disputed matching mutants 29 and 47 are killed in this fresh run.
There are no additional survivors or incomplete outcomes requiring assertions or
quarantine. The numerical/contract proofs above are static equivalence reviews;
no new standalone exhaustive numerical proof or extra runtime probe is claimed.

## Input provenance

Environment: mutmut 3.8.0, pytest 9.1.1, NumPy 2.5.1 and SciPy 1.18.0, using the
existing project environment with frozen/no-sync execution and no installation.
All three selected source hashes and all five selected test hashes are identical
to the [005 per-mutant evidence](../005-reduce-verification/evidence/mutation-results.json).
`tests/conftest.py` and `uv.lock` differ from 005. Their current hashes were captured
before execution and rechecked afterward; all captured inputs remained unchanged.
The additional copied helper/configuration hashes identify this run's exact context.
The current `conftest.py`, architecture helper, all selected tests and copied
`pyproject.toml` were also checked byte-for-byte against the generated copies.
Mutmut warned about changes to non-Python planning artifacts and the `external`
entry; these do not change the configured policy/test selection. Explicit
selection reran all selected verdicts despite the general cache warning.

| Input | SHA-256 |
| --- | --- |
| `src/clearml_yolo/core/datasets.py` | `1f557162e86ae00f765df0e2a85355d440a2124f15a246960a66e6d4ebc67195` |
| `src/clearml_yolo/core/evaluation/policy.py` | `88e18d0615a29875ee5fb3c184251ae5f86c16bd5b2ef81044aad3c362dc8ab5` |
| `src/clearml_yolo/core/export_quality.py` | `3a157e752034348213244d7dfa3d057f254d094ddc4d00efc863d45539e0f91a` |
| `tests/conftest.py` | `bc3eae9567dbbf95ba69c7b014c1f66ab4634d9b92933fa7d4c4e633b4872a71` |
| `tests/test_comparison_scoring.py` | `1856cda840bb474c2e42dda28f96b9dfb5d4590db04ec8dde30cb0aa5a2cfba5` |
| `tests/test_dataset_records.py` | `a71b5ef10e2b7cf4740c240949db6e0d0507e5e492108fe7b4c4bbb7f62af23b` |
| `tests/test_export_quality.py` | `e355c3b75141617c98886c9cf9933bd3acb9708c43fbc30dcd059771ad0d9e30` |
| `tests/test_input_correctness.py` | `58cc698c4cb63723dc5e89383dd47581dbf74464c9d0c1f00cb888784547467f` |
| `tests/test_policy_mutation.py` | `c5e878cbf9a764272c74a3af028ec40eb7cdcd8e211c8a173f64fd2b313d7e05` |
| `uv.lock` | `f148265da8e5dc4430bae66f24635b6478142575e9bb5c973d2a3e70ba0efc6c` |
| `pyproject.toml` | `66989b4b9765ee2ed2b75b32bb065c8d5d53fe5ab01b25b835c0e905c406ee35` |
| `tests/architecture_helpers.py` | `5d2dd989c2cc09ab89c0d535e64a0d19986508747ab0c74ed41f81b104952a9d` |
| `tests/ddp_gpu_harness.py` | `73d84c298d836888ecc392757aa8cfd22fff3d64c37374d775f99089587dc63d` |

Private raw evidence is retained at `.tmp/cleanup-mutation.log`,
`.tmp/cleanup-mutation-results.txt`, `.tmp/cleanup-mutation-meta.json`,
`.tmp/cleanup-mutation-inputs.json` and `.tmp/cleanup-mutation-provenance.json`.
Actual survivor diffs are retained at `.tmp/cleanup-mutation-survivor-50.txt`,
`.tmp/cleanup-mutation-survivor-52.txt` and `.tmp/cleanup-mutation-survivor-36.txt`.
Generated execution metadata remains under `mutants/src/clearml_yolo/core/`.

This establishes scoped mutation acceptance for these inputs. It does not replace
canonical verification, architecture acceptance, independent integration review or
paired release checks. Changes to selected code, tests, fixtures or dependencies
require renewed affected mutation evidence under the development policy.

## Native-process fix applicability reassessment

After the later native-process fix, parent checked every captured hash again: all
remain unchanged. The process-tree adapter is neither a configured mutation target
nor an imported dependency of the selected core policies/tests or their runtime
bootstrap fixture. Its new topology tests are outside mutation selection. The
existing 433 fresh outcomes remain applicable; native safety is instead covered by
the 64-case scoped suite, original stress reproduction and canonical verification.
