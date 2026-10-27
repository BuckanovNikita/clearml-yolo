# Scoped mutation applicability — 2026-10-26

## Decision

**No affected configured mutation target requires a fresh run for feature 006.**
This is an inspected no-impact decision, not a newly executed mutation pass.
Existing mutation output/history was preserved. No mutation command, source/test
edit, policy/configuration change, GPU work or broader audit was performed.

The [development rule](../../../docs/development.md#scoped-mutation-acceptance)
requires a fresh explicit selection when selected target logic, tests, fixtures or
dependencies change. The configured selection and its relevant execution paths
remain unchanged by this feature, as detailed below. Canonical application tests
and the feature's new batch/worker/model tests remain separate acceptance gates.

## Configured scope and comparison baseline

`pyproject.toml` selects exactly these files:

- `src/clearml_yolo/core/datasets.py`
- `src/clearml_yolo/core/evaluation/policy.py`
- `src/clearml_yolo/core/export_quality.py`

Its five selected tests are `test_dataset_records.py`, `test_input_correctness.py`,
`test_comparison_scoring.py`, `test_export_quality.py` and `test_policy_mutation.py`.
It copies `tests/` and `pyproject.toml` for imports and fixtures; copying the whole
test tree does not select every test for mutation execution.

The baseline is the accepted feature 005
[mutation evidence](../../005-reduce-verification/evidence/mutation.md) and its
[input hashes and outcomes](../../005-reduce-verification/evidence/mutation-results.json),
committed at `35dd11c8105b8b3ba97d51a6bb2edabeb8e5996b`.

Read-only SHA-256 comparison found all three selected source files and all five
selected test files byte-identical to that recorded baseline. At initial inspection,
`tests/conftest.py` was also identical. Final integration changed only its
`--severstal-backbone` help text to include FCOS; fixture implementations,
collection/opt-in behavior and selected mutation execution are unchanged.
The complete parsed `[tool.mutmut]` table is also identical. No selected fixture
file changed; these tests construct their CSV/image/array fixtures in temporary
directories or inline.

The current lockfile hash differs from the old recorded hash. Parsed lockfile
comparison against the matching baseline revision showed exactly one changed
package field: root `clearml-yolo.version`, from `0.39.0` to `0.40.0`. Every external
package entry, version, dependency and source is identical. Feature 006 has no
`uv.lock` diff and no dependency declaration changes. Its `pyproject.toml` diff adds
the estimator entrypoint and retains the pre-existing local `[tool.uv.sources]`
section. The approved external dependency checkouts have no working-tree changes.

## Transitive execution-path inspection

The inspection included actual feature changes to imported modules, rather than
assuming unchanged target filenames alone established applicability.

| Imported area | Observed feature change | Selected-test impact |
| --- | --- | --- |
| `adapters/clearml/session.py` | Preserve null during `replay_training_parameters` | The autouse fixture only resets `_INCOMPLETE_OWNER` using `_IncompleteOwner`; that class is unchanged. The selection does not replay training parameters. |
| `entrypoints/hydra/validation.py` | Local precedence return value in `validate_launch_arguments` | Input correctness calls unchanged `validate_wrapper_keys` directly with an inference-only config; it does not launch or compose application YAML. |
| `entrypoints/hydra/transforms.py` | Add the FCOS native overlay | `prepare_transforms` is unchanged; the selected comparison rejection has no transforms or model selection. |
| `adapters/yolo/config.py` | Permit an explicit null training batch | The selected wrapper check has no Ultralytics group and never enters native training-value validation. |
| `core/models.py` | FCOS registry and nullable training batch | Selected inference/preprocessing and checkpoint records remain unchanged; the tests do not construct the new FCOS training recipe or null training batches. |
| `adapters/runtime/process_tree.py` | Add live-owner discovery and recorded adopted-zombie reaping | Selected fixtures do not start supervised training or call these methods. Bootstrap/owner-environment functions used by the selection are unchanged. |
| Native detector/probe adapters and batch policy | New or changed training, model, worker and estimator code | None is selected for mutation or invoked by the five policy test files. Deployment quality policy remains within its existing scope. |

AST comparison against the baseline confirmed unchanged definitions for
`_IncompleteOwner`, `validate_wrapper_keys`, `materialize_model_config`,
`prepare_transforms`, `stage_settings`, `Preprocessing`, `CheckpointMetadata`,
`InferenceConfig` and `validate_owner_environment`.

Whole-file comparisons also confirmed unchanged selected-test support in
`tests/ddp_gpu_harness.py`, `adapters/runtime/bootstrap.py`, and these adapter files:
`storage/dataset_records.py`, `storage/dataset_cache.py`, `storage/dataset.py`,
`storage/dataset_export.py`, `storage/file_io.py`, `storage/publication_data.py`,
`evaluation/scoring.py`, `export/quality.py` and `clearml/results.py`.
The retained scientific dependency versions and selected fixture generators are
unchanged. The parent's later YOLO probe patch lies outside these paths as well;
any later edit to the listed target/test/support paths requires reassessment.

## Evidence status and preservation

The historical accepted run recorded 433 mutants: 430 killed and three reviewed
equivalences, with no incomplete outcomes. Those are historical results linked above,
not results generated by this task. The equivalences concern redundant float64
conversion and a tolerance equality already accepted by an unchanged `isclose`
branch; their target code and relevant assertions remain byte-identical.

`mutants/mutmut-stats.json` and all three target `.meta` files retained their original
2026-10-24 modification timestamps before and after inspection. No prior results
were deleted, invalidated or overwritten. Only this evidence document was written.

This bounded documentation-only subtask introduces no module/interface/effect change;
the parent [architecture record](../architecture.json) and final independent review
own acceptance of the overall feature. Documentation validation for this new evidence
uses `uv run --frozen --no-sync python scripts/check_docs.py` with this file explicitly
selected. No successful mutation execution is claimed for feature 006.
