# Research: static analysis

- Use installed Ruff catalog/effective settings for audit completeness; stable,
  preview and removed rules differ. Do not use ALL blindly: some rules conflict.
- Keep mypy strict and inspect import exceptions independently of inline suppressions.
- Vulture assigns 100% to unused arguments/unreachable code, 90% to imports and 60%
  to most symbol guesses. Start the gate at 80% to include the two stronger classes;
  inspect 60% candidates separately because frameworks call validators/callbacks and
  consume serialized fields dynamically. A threshold is a coverage limit, not proof
  that everything below it is live.
- Use the existing local uv hook pattern, with pass_filenames=false and configured
  paths. A changed-file scan loses cross-file uses.

Sources: [Ruff rules](https://docs.astral.sh/ruff/rules/),
[Ruff preview](https://docs.astral.sh/ruff/preview/),
[Vulture](https://github.com/jendrikseipp/vulture),
[mypy imports](https://mypy.readthedocs.io/en/stable/running_mypy.html).

## Follow-up findings — 2026-10-13

The exact preview opt-ins were checked against the installed Ruff catalog:

| Code | Installed rule name |
| --- | --- |
| `ASYNC119` | `yield-in-context-manager-in-async-generator` |
| `B901` | `return-in-generator` |
| `B909` | `loop-iterator-mutation` |
| `PT029` | `pytest-warns-without-warning` |
| `PLE1141` | `dict-iter-missing-items` |
| `PLE4703` | `modified-iterating-set` |
| `RUF045` | `implicit-class-var-in-dataclass` |
| `RUF054` | `indented-form-feed` |
| `RUF066` | `property-without-return` |
| `RUF071` | `os-path-commonprefix` |
| `RUF074` | `incorrect-decorator-order` |
| `RUF052` | `used-dummy-variable` |
| `PLW1514` | `unspecified-encoding` |

Nineteen encoding findings and two consumed dummy names required local fixes.
The private model verifier has two callers, native and detector tracking; both must
name their expectations after the keyword-only change. The initial integration check
exposed the detector caller and its failure was reproduced before correction.

Compatible SciPy/tqdm stubs required no source casts, ignores or type changes.
The refreshed [60% Vulture inventory](vulture-advisory-2026-10-13.txt) is advisory: it
includes framework attributes and callbacks as well as review candidates. No broad
allowlist or automatic dead-symbol deletion was added.
