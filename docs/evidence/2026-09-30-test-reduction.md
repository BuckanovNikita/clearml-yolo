# Test redundancy reduction — 2026-09-30

## Goal and measurements

Reduce repeated test execution and setup while retaining distinct assertions. The
approved target is redundancy reduction, without a fixed test-to-code ratio quota.
Production code, dependency revisions, test selection and skip policy are unchanged.

The baseline command `uv run --locked --no-sync pytest -q --durations=10` produced
701 passed, 8 skipped and 4 upstream hydra-zen/Pydantic deprecation warnings in
131.77 seconds. Collection produced 709 cases.

| Metric | Before | After |
|---|---:|---:|
| Collected cases | 709 | 691 |
| Passed / skipped | 701 / 8 | 683 / 8 |
| Full pytest duration, seconds | 131.77 | 116.87 |
| Test Python files | 39 | 38 |
| Test Python lines | 10,169 | 10,148 |
| Production Python lines | 8,537 | 8,537 |
| Test-to-production line ratio | 1.1912:1 | 1.1887:1 |

Lines count nonblank lines that do not begin with a comment after leading whitespace;
docstrings count. Include tracked Python files under `tests/` for tests and `src/`
plus `scripts/` for production. Exclude external dependencies and ignored output
files. The reduction is 18 collected cases (2.54%) and 21 test lines (0.21%).
Durations are single observations, not a controlled speedup benchmark.

## Removed-case assertion mapping

| Original checks | Retained checks | Fewer cases |
|---|---|---:|
| `test_configs.test_command_composes`, all eight commands | [Configuration round trips](../../tests/test_config_tree.py): `test_examples_round_trip_through_hydra` still composes all eight builtins and exports, now asserting that ClearML exists and has no `enabled` option before comparing configurations | 8 |
| `test_ultralytics_params.test_explicit_native_defaults_survive_projection` | [Native configuration](../../tests/test_native_config.py): `test_classification_covers_template_once_and_preserves_detection_losses` now asserts projected training `epochs` equals the native default | 1 |
| `test_ultralytics_params.test_native_invalid_parameter_is_rejected` | `test_native_config.test_unknown_and_raw_cfg_fail` already calls the same project validator with an unknown key and requires `ValueError` matching `Unknown`; the literal unknown key changes, but the behavior does not | 1 |
| `test_inference.test_missing_resolution_never_uses_checkpoint` | [Inference](../../tests/test_inference.py): `test_inference_requires_configured_resolution` has identical setup, invocation and expected exception | 1 |
| `test_inference.test_inference_settings_reach_ultralytics`, `test_precision_is_left_to_native_defaults`, both cases of `test_naming_the_precision_hands_the_decision_over`, `test_compilation_comes_from_explicit_configuration`, `test_the_letterbox_shape_is_named_rather_than_inherited` and `test_compilation_can_be_forced_back_off` (seven cases) | One `test_default_prediction_settings_reach_ultralytics` case retains `quantize is None`, `compile is True`, `rect is True` and streaming; two `test_explicit_prediction_settings_reach_ultralytics` cases retain numeric/string precision and explicit confidence, IoU, size, device, `compile=False`, `rect=False` and streaming assertions | 4 |
| Four cases of `test_run_identity.test_a_generated_run_id_carries_the_task_the_host_the_stamp_and_the_pid` | [Run identity](../../tests/test_run_identity.py): one generated ID is checked for task, host, timestamp and PID, with the missing component in the assertion message | 3 |

Distinct failure paths, native-parser compatibility, fresh-process CLI checks,
tracking ownership, uploads, interruption, secret handling, dataset integrity and
comparison checks remain separate. Consolidation reduces failure isolation for
forwarding assertions: an earlier failing assertion prevents later assertions in
that scenario from running. Numeric and string precision still have separate cases.

## Verification

- Affected tests: `uv run --locked --no-sync pytest -q tests/test_inference.py
  tests/test_configs.py tests/test_config_tree.py tests/test_native_config.py
  tests/test_native_yaml_compatibility.py tests/test_run_identity.py` — 127 passed,
  4 upstream warnings in 34.34 seconds.
- `uv run --locked --no-sync ruff check .` — passed.
- `uv run --locked --no-sync lint-imports` — all nine contracts kept.
- `uv run --locked --no-sync mypy src tests scripts` — passed, 92 source files.
- Initial `uv run --locked --no-sync mypy .` — blocked by 17 errors in the pre-existing,
  ignored `outputs/documentation-compression-2026-09-30/audit/verify_docs.py`.
  That unrelated file was preserved.
- `uv run --locked --no-sync pytest --collect-only -qq` — 691 cases, summing
  the per-module counts.
- Initial `uv run --locked --no-sync pre-commit run --all-files` — every hook passed
  except repository-wide mypy, blocked by the same unrelated ignored audit script.
  The full pytest hook, changelog generation, Ruff and import checks passed;
  changelog generation left no tracked changes outside this task.
- Independent static review — no lost behavioral assertions or other findings.
- Markdown structure, whitespace and all five local links — passed.
- Final `uv run --locked --no-sync pytest -q --durations=10` — 683 passed,
  8 skipped and the same 4 upstream warnings in 116.87 seconds.

### Authorized cleanup before commit

The user subsequently authorized removal of unused scripts, a passing repository-wide
mypy check, commit and push. The ignored audit helper above depended on a deleted
temporary manifest and had no workflow references. Removed only that obsolete script;
retained the audit manifest, logs and verification records. Its deletion is local cleanup
and is not part of the tracked patch. Repository-wide checks are rerun before
committing; the initial blocked results above remain historical evidence.

- After cleanup, `uv run --locked --no-sync mypy .` — passed, 92 source files.
- After cleanup, the all-files pre-commit run passed Ruff, mypy and import checks;
  pytest produced 683 passed, 8 skipped and 4 warnings in 120.49 seconds. The
  pre-commit wrapper rejected that run because this evidence document was staged
  during the pytest hook, changing the working-tree diff it monitors. Inspection
  found no unstaged changes or test-generated tracked changes. The staged tree is
  subsequently verified by the installed commit hooks without concurrent edits.

Coverage tools are not installed. Assertion mapping and passing test results are
the evidence here; no measured line/branch coverage preservation, GPU execution,
native training or live ClearML uploads are claimed. The eight optional FiftyOne
database tests retain their existing skip policy.

## Documentation scope

Reviewed the [current contract index](../current-contracts.md), affected native
configuration and CLI contracts, README, active specs, migrations and integration
guidance. No user-facing behavior, configuration, entrypoint or execution guidance
changed, so those documents need no amendments. This dated evidence records the
test maintenance outcome without changing historical results or evergreen contracts.
