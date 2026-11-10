---
name: mutation-testing
description: Runs and triages clearml-yolo's changed-function mutation report (scripts/mutation.py, [tool.mutmut] in pyproject.toml). Use for surviving mutants from the mutation Task stage, hardening tests of a changed function, deciding whether a survivor is equivalent, a run that produces no mutants, functions no test reaches, a mutation tool or configuration error, or edits to the mutmut settings.
---

# Changed-function mutation testing

`scripts/mutation.py` maps changed lines to the top-level functions and methods they
touch, exports the index into a fresh temporary workspace with `git checkout-index`, and
runs mutmut there on those functions only. The child environment drops `CLEARML_*`,
`INFRA_*`, `CY_RUN_*` and `GIT_*` variables, so mutants inherit neither test-environment or stale shell credentials
nor this repository's version-control state. Read the script's docstring for the
mechanics; [development procedures](../../../docs/development.md#mutation-report) own the
policy.

- **Test selection per change**: the union of the test node ids that this worktree's
  `.testmondata` records for the changed files and that still exist in the staged tree,
  and, for a changed module without such validated testmon nodes, the test modules
  (`test_*.py`) that import it. A missing or unreadable `.testmondata` leaves the import
  scan alone. When nothing is selected, mutmut does not run and the report ends early
  with the functions "Not reached by tests".
- **Excluded tests**: `tests/integration` is never selected; every run deselects
  `-m "not ddp_cpu and not process_capabilities and not gpu_controls"` (`gpu_controls`
  is reserved for GPU-holding tests), and the tooling suites ignored by `pytest_add_cli_args`
  in `[tool.mutmut]` never run.
- **Budget**: 8 changed functions and 300 seconds by default. Functions beyond the
  budget are skipped; mutants left unjudged count as "not run" and functions no selected
  test reaches as "not reached by tests", never as survivors.

```bash
uv run --locked task --exit-code mutation                          # staged vs HEAD
uv run --locked task --exit-code mutation -- --base master         # whole branch
uv run --locked task --exit-code mutation -- --strict              # survivors fail
```

| Exit | Meaning |
| --- | --- |
| 0 | Report produced; survivors and unreached functions are advisory. |
| 1 | Under `--strict`: surviving mutants, or changed functions no selected test reaches. |
| 2 | Tool or configuration error, or the clean test run failed in the workspace. |

Nothing is cached between runs; the staged comparison and the `--base` branch comparison
are different reports. Before acceptance of a code change, run the branch comparison.

## Triage a survivor

Triage only behavioural survivors; leave mutants of default arguments, message wording
and other presentation details alone.

1. Read the diff. If the mutation changes an outcome, boundary, side effect or contract
   a caller can observe, strengthen or add a behavioural unit test, stage it, rerun.
2. If it cannot change observable behaviour (equivalent) or only changes presentation,
   leave it and say so in the report. There is no allowlist.
3. Keep correct production code as it is; reshaping it only to stop a mutant is not a fix.

## No mutants, or functions not reached

mutmut mutates code inside undecorated top-level functions and methods, never module
constants, f-strings or docstrings. "No mutants" is a pass. A changed function that no
selected unit test reaches (for example code only `tests/integration` or an excluded
marker exercises) is advisory by default but fails under `--strict`; add a behavioural
unit test that reaches it, or report why only live or hardware tests can.

## Settings invariants

- `source_paths = ["src/clearml_yolo"]`; `only_mutate` and the selected tests are derived
  per run by the script, never checked in.
- Tests run without xdist (`-n 0`): mutmut forks per mutant, and xdist would start a pool
  each time.
- The excluded tests above never run against mutants.
- Generated `mutants/` stays ignored by Git, Ruff, mypy and Vulture.

## Completion

Report the functions mutated (and any skipped by the budget), the selected tests and
whether testmon or the import fallback chose them, the killed/survived/not-reached/not-run
counts, each survivor's classification (test added, equivalent, presentation) and the
rerun result. Tool and configuration errors remain unresolved; keep dispositions in dated
feature evidence.
