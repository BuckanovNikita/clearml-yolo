---
name: mutation-testing
description: Runs and triages clearml-yolo's changed-function mutation report (scripts/mutation.py, [tool.mutmut] in pyproject.toml). Use for surviving mutants from the mutation Task stage, hardening tests of a changed function, deciding whether a survivor is equivalent, a run that produces no mutants, a mutation tool error, or edits to the mutmut settings.
---

# Changed-function mutation testing

`scripts/mutation.py` maps changed lines to the top-level functions and methods they
touch, exports the index into a fresh temporary workspace with `git checkout-index`, and
runs mutmut there on those functions only. The child environment drops `CLEARML_*`,
`INFRA_*`, `CY_RUN_*` and `GIT_*` variables, so no mutant reaches a live service or this
repository. Default budget: 8 changed functions and 120 s of mutmut; mutants left
unjudged count as "not run" and mutants no unit test reaches as "not reached by tests",
never as survivors. Read the script's docstring for the mechanics.

```bash
uv run --frozen --no-sync task --exit-code mutation                          # staged vs HEAD
uv run --frozen --no-sync task --exit-code mutation -- --base master         # whole branch
uv run --frozen --no-sync task --exit-code mutation -- --strict              # survivors fail
```

Exit 0: report produced (survivors are advisory). Exit 1: survivors under `--strict`.
Exit 2: tool error, including a failing clean test run in the workspace. Nothing is
cached between runs; the staged comparison and the `--base` branch comparison are
different reports. Before acceptance of a code change, run the branch comparison.

## Triage a survivor

Triage only behavioural survivors; leave mutants of default arguments, message wording
and other presentation details alone.

1. Read the diff. If the mutation changes an outcome, boundary, side effect or contract
   a caller can observe, strengthen or add a behavioural unit test, stage it, rerun.
2. If it cannot change observable behaviour (equivalent) or only changes presentation,
   leave it and say so in the report. There is no allowlist.
3. Keep correct production code as it is; reshaping it only to stop a mutant is not a fix.

## Why a change produces no mutants

mutmut mutates code inside undecorated top-level functions and methods, never module
constants, f-strings or docstrings. "No mutants" is a pass. "No unit test exercises the
changed functions" (code only `tests/integration` reaches) also passes, but prompts a
unit test.

## Settings invariants

- `source_paths = ["src/clearml_yolo"]`; `only_mutate` is derived per run by the script,
  never checked in.
- `pytest_add_cli_args` keeps `-n 0` (mutmut forks per mutant; xdist would start a
  pool each time) and ignores `tests/integration` (live services) and the architecture
  tests (import structure, not behaviour).
- Generated `mutants/` stays ignored by Git, Ruff, mypy and Vulture.

## Completion

Report the functions mutated (and any skipped by the budget), the
killed/survived/not-reached/not-run counts, each survivor's classification (test added,
equivalent, presentation) and the rerun result. Tool errors remain unresolved; keep
dispositions in dated feature evidence.
