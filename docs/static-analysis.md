# Static analysis policy and exclusion report

[pyproject.toml](../pyproject.toml) defines the policy; the
[pre-commit configuration](../.pre-commit-config.yaml) runs it. This report covers
explicit ignores, unselected rule families, preview rules, test exceptions and mypy
suppressions. The [dated audit](../specs/026-static-analysis/verification-2026-10-13.md)
and [complete rule inventory](../specs/026-static-analysis/ruff-rule-inventory.csv)
record the installed catalog and effective selection at review time.

An exclusion is not proof that a rule damages code quality. Some preserve runtime
contracts or avoid repetitive syntax; others reflect missing typing coverage,
inapplicable frameworks, unstable checks, or unresolved design debt. High violation
counts alone are not a reason to disable a useful check.

## Rules enabled by this review

- `ANN001/002/003/201/202/204/205/206`: require annotations on parameters and returns.
  These complement strict mypy and expose missing annotations earlier in linting.
- `COM818`: catches accidental singleton tuples created by a trailing comma.
- `D418/D419`: reject docstrings on overload declarations and empty docstrings without
  requiring prose on every function.
- `TC004/005/007/010`: catch runtime use of imports hidden behind `TYPE_CHECKING`, empty
  checking blocks, aliases using unavailable runtime types and string operands in unions.
- Explicit preview checks: `ASYNC119`, `B901`, `B909`, `PT029`, `PLE1141`, `PLE4703`,
  `RUF045`, `RUF054`, `RUF066`, `RUF071`, `RUF074`, `RUF052` and `PLW1514`.
  These add correctness checks, reject misleading dummy names, and require explicit
  text encodings. Comparison evidence uses ordinary names; text/JSON uses UTF-8 and
  Linux boot IDs use ASCII.

The obsolete `eta.*` mypy exception and unused test-wide Ruff `S301` exception were
removed. `S301` does not detect the existing `cloudpickle` fixture loader; removing
the exception does not establish that arbitrary fixture deserialization is safe.

## Project-wide Ruff ignores

| Rule | What enabling it enforces | Project evidence and tradeoff | Decision |
| --- | --- | --- | --- |
| `ANN401` | No explicit `Any` in function annotations | [Detector tracking adapters](../src/clearml_yolo/adapters/clearml/detectors.py) receive opaque SDK objects, and test doubles deliberately accept variable call shapes. Replacing these with `object` plus repeated casts or invented incomplete interfaces can conceal the actual dynamic boundary. Concrete project-owned models and protocols remain preferable where known. | Retain; not permission to spread `Any` through new core interfaces. |
| `PLC0415` | Imports at module scope | [Train startup](../src/clearml_yolo/entrypoints/train.py) initializes the environment before importing the workflow; [deduplication](../src/clearml_yolo/adapters/storage/dedup.py) imports Unix-only `fcntl` after the platform guard. Hoisting imports can load heavy/optional SDKs during help or fail on unsupported platforms before the guard. | Retain across entrypoints, adapters and tests. It protects import timing and portability, not merely formatting. |
| `PLR0913` | A maximum total parameter count | [compute_evaluation](../src/clearml_yolo/adapters/evaluation/scoring.py) names independent scientific settings and makes most keyword-only. [Hydra registration](../src/clearml_yolo/entrypoints/hydra/configs.py) derives configuration from workflow signatures. Arbitrary bundling can obscure units/meaning and change generated configuration. Some internal helpers still have too many responsibilities. | Retain compatibility; review helpers individually. Not all current violations are justified. |
| `PLR0917` | A maximum positional parameter count | Existing workflow and port signatures have positional callers. Blanket conversion to keyword-only breaks callers; SDK overrides may have fixed signatures. The private [_verify_model](../src/clearml_yolo/adapters/clearml/native.py) now keeps only task/model ID positional and names every expected field. | Retain for public/SDK compatibility; improve internal signatures individually. It would be false to claim keyword-only arguments inherently reduce readability. |
| `TRY003` | Exception messages defined in exception classes rather than raise sites | Validation in [config resolution](../src/clearml_yolo/entrypoints/hydra/config_resolution.py) places a specific diagnostic next to the failing condition. Stdlib exceptions and marker exceptions such as `NativeModelError` and `ReleaseError` intentionally share types across messages. Message-specific subclasses add definitions and navigation without new recovery behavior. | Retain; use dedicated exception classes when callers need distinct recovery or structured data. |

For example, keeping `raise ValueError("Expected a mapping")` beside the guard makes
the condition and explanation visible together. Moving it to a new exception class
solely for lint compliance adds indirection. By contrast, changing a long private call
to named arguments can improve readability: the argument-budget exceptions are a
compatibility compromise, not a claim that every large signature is good design.

## Unselected stable Ruff rules

The inventory lists every code and rule name. This table explains all wholly or
partially omitted families; selected families otherwise include their stable rules,
apart from the explicit ignores above. Family names are distinct selectors: `A` does
not imply `ANN`, and `F` does not imply `FBT`.

| Family or codes | What the rules ask for | Why excluded, and what remains useful |
| --- | --- | --- |
| `AIR`, `FAST`, `DJ` | Airflow, FastAPI and Django conventions/API migrations | No corresponding application interfaces. No negative readability claim: these checks become useful if those frameworks are introduced. |
| `FBT001/002/003` | Avoid positional Boolean parameters/defaults and literal Boolean call arguments | Blanket keyword-only conversion affects existing Hydra/port contracts. `FBT003` also flags legitimate external calls such as `pd.Series(False, ...)`. Prefer named Boolean arguments in new internal APIs; the rule's intent is useful. |
| `COM812`, `COM819` | Require or prohibit trailing commas | These encode opposing styles and overlap with the Ruff formatter. Enforcing comma layout independently can create formatting churn. `COM818`, which catches an accidental tuple, is enabled. |
| `CPY001` | A copyright notice in every file | The repository has no per-file header requirement. This is an ownership policy decision, not a correctness rule; repetitive headers add reading overhead. |
| `EM101/102/103` | Assign literal, f-string and formatted exception messages to variables before raising | Adding a single-use `msg` separates a short guard from its diagnostic. This differs from TRY003's exception-class rule. The benefit is less duplicated message text in tracebacks; use a variable when a message is complex or reused. |
| `FIX001–004` | Ban FIXME, TODO, XXX and HACK markers | Removing honest debt notes to satisfy a marker ban can hide known limitations. Resolve the issue or keep actionable context; marker presence alone is not a defect. |
| `TD001–007` | TODO tag, author, issue link, colon, description and punctuation conventions | No mandatory issue-linked TODO policy. Mechanical attribution/punctuation can add clutter or encourage deleting useful notes. Descriptive, actionable comments remain expected. |
| `TC001/002/003` | Move annotation-only imports under `TYPE_CHECKING` | Runtime annotation consumers include Pydantic and Hydra. Blind relocation can break schema/configuration introspection or require quoted types and extra checking blocks. Runtime annotations are a project contract; evaluate import savings at specific boundaries. |
| `TC006` | Quote the type argument to `typing.cast` | A resolved expression such as `cast(list[dict[str, str]], value)` remains readable and navigable. Quoting already available types adds no typing guarantee. Quote when a type is unavailable at runtime; no future-annotations import is permitted. |
| `D100–107` | Require docstrings on public modules, classes, methods/functions and magic methods | Tests already name their scenario; requiring a second sentence on every obvious helper encourages paraphrases that drift. Document contracts, constraints and surprising behavior. |
| Remaining stable `D2xx`, `D3xx`, `D4xx` except enabled `D418/419` | Docstring whitespace, quoting, summary grammar and section layout | There is no single structured docstring style across these concise modules. Blanket adoption mixes useful consistency checks with forced rewrites; `D203/D211` and `D212/D213` are mutually incompatible alternatives. Formatting checks could be selected later without making all docstrings mandatory. |

## Preview and removed rules

Lint preview is enabled with `explicit-preview-rules = true`; only the exact preview
codes listed above are selected. Formatter preview remains disabled. Ruff is constrained
to `>=0.16.1,<0.17` and the lock determines the reviewed version. Preview also affects
existing rule behavior, so explicit selection is not a promise of stable diagnostics.
Review rule promotions, changed diagnostics and this inventory on upgrades.

Excluding other previews is a stability/scope decision, not evidence that they are bad.
Promotion to stable brings rules from selected families into scope on a tool upgrade.
The inventory includes every preview code even in otherwise selected families.

The remaining previews fall into these reviewed categories:

- **Formatting and documentation:** E/W spacing overlaps with formatting. `DOC` and
  `D420/421` demand structured documentation or additional consistency; concise helper
  summaries need not restate every return and exception. They become more useful for
  a documented external API with an adopted section style.
- **Import bans:** preview `S4xx` rules reject imports such as `subprocess` or XML
  libraries regardless of their safe use. This project owns process supervision;
  existing call-site security checks provide more specific signals.
- **Framework/API migrations:** preview `AIR` is inapplicable; `TC008`, `TID254/255`
  and `UP051` require a separate compatibility review before import/annotation changes.
- **Heuristic refactoring:** preview `B`, `PL`, `FURB` and `RUF` rules mix useful
  suggestions with subjective transformations. For example `FURB140` suggests replacing
  the clear ONNX attribute generator in [build.py](../src/clearml_yolo/adapters/export/build.py)
  with `starmap`. A shorter expression is not necessarily easier to understand.
- **Concrete semantic conflicts:** `PLC2801` flags explicit `dict.__setitem__` calls in
  [native runtime settings](../src/clearml_yolo/adapters/integrations/native_runtime.py)
  that intentionally bypass persistent SDK setters. `RUF027` mistakes literal Hydra
  interpolation and Git revision braces for missing f-strings. `RUF069` would replace
  exact integral/fixture float assertions with approximate comparisons. `RUF075` needs
  lifecycle review where successful finalization and failure cleanup have different owners.
- **Policy preferences:** `RUF031` removes optional tuple-key parentheses;
  `RUF067/105/106/201` concern export/suppression policy. They require an intentional
  policy change, not mass edits solely to make a preview scan green.

Removed catalog entries cannot be enabled and are not policy gaps.

## Test-only Ruff exceptions

| Exception | Reason and boundary |
| --- | --- |
| `ARG` | Pytest fixture injection and mocks intentionally accept unused parameters. Prefer `pytest.mark.usefixtures` for setup-only fixtures and underscore-prefixed callback parameters where practical. |
| `INP001` | Pytest discovers this test directory without making it an installed package. |
| `PLR2004` | Literal expected values keep small test scenarios self-contained; naming every expected count adds navigation. |
| `S101` | Assertions are pytest's assertion/reporting interface. This does not allow production assertions for input validation. |
| `S108` | Tests use known fake temporary path strings. Real writable test outputs still use isolated fixtures. |
| `SLF001` | Focused tests exercise internal failure paths and state without adding public test-only APIs. |

Inline `noqa` remains rule-specific and subject to `RUF100` unused-suppression checks.
Per-file exceptions apply only to tests; they do not disable production checks.

## Mypy review

Strict mode, `warn_unreachable`, `disallow_any_unimported` and the explicitly enabled
optional error codes remain active. There is no global `ignore_errors` or global
`ignore_missing_imports`. Strict mode includes unused-ignore checking; `ignore-without-code`
requires named error codes. Deleting an ignore that then produces an error is evidence
that it is active, not proof that the underlying typing is ideal.

| Package exception | Why retained | Cost and route to removal |
| --- | --- | --- |
| `digital_metrics.*` | Installed protected source lacks recognized typing at the integration boundary. | Imported APIs are opaque. Project adapters validate/copy results into typed records. Do not change the approved dependency revision as a lint repair. |
| `report_generator.*` | Installed reporting integration lacks recognized type coverage. | Preserve typed project inputs; accurate upstream/local stubs would improve checking. |
| `fiftyone.*` | Dynamic SDK base classes, plugins and evaluation objects lack installed coverage. | Narrow project subclasses still need code-specific boundary ignores. A maintained stub/interface effort is preferable to invented broad signatures. |

`scipy.*` and `tqdm.*` were removed after installing compatible development-only
`scipy-stubs` and `types-tqdm`. Strict checking passes without source workarounds;
invalid statistical options and progress totals fail type checking. The exact pins
are maintained in `pyproject.toml` and should be reviewed with their runtime versions.
`eta.*` was removed because the project does not import it. Package-scoped import
exceptions still mask missing submodules within those packages; they are a real typing
coverage limit. Local external copies and generated output/build directories are excluded
from recursive discovery because they are not first-party source, not because their
errors are harmless.

The inline suppression audit found these categories, kept at their call sites:

- `attr-defined`/`mutable-override`: platform-gated Windows ctypes/process fields and
  declarative ctypes `_fields_`, plus intentionally dynamic test doubles.
- `import-untyped`, `misc`, `no-any-unimported`: SDK/plugin imports and inheritance;
  marker comments do not make the external classes type-safe.
- `no-untyped-call`/`no-any-return`: installed native training, tensor or panel calls
  without usable annotations. Keep typed results/validation at the project boundary.
- `redundant-expr`: defensive validation of queue input that may violate its nominal
  annotation at runtime. Removing that validation would weaken the boundary.
- Test-only `arg-type`, `call-arg`, `union-attr`: deliberate invalid-input scenarios or
  dynamic fixtures. These codes remain enabled elsewhere.

Not every optional mypy restriction is enabled. In particular, globally forbidding all
`Any` expressions/decorated values would flood dynamic SDK seams and encourage unchecked
casts; `strict` already rejects untyped definitions/calls where usable signatures exist.
This review does not certify every cast or `Any` as necessary. Strengthen known project
interfaces incrementally instead of replacing suppression comments with equally opaque casts.

## Vulture gate

```bash
uv run --frozen --no-sync vulture
uv run --frozen --no-sync pre-commit run vulture --all-files
```

The hook uses the locked development environment and scans `src`, `scripts` and
`tests` together through `[tool.vulture]`; staged filenames are not passed to it.
Its 80% threshold includes unused arguments/unreachable code (100%) and imports (90%).
It deliberately does not gate most attributes, functions and variables (60%).

Run `uv run --frozen --no-sync vulture --min-confidence 60` for the advisory inventory.
Pydantic validators, serialized fields, FiftyOne callbacks and SDK-consumed attributes
are invoked indirectly. Do not delete them based only on a static unused-name report.
The scan also reports genuine review candidates; the threshold does not prove they are
live. No wildcard ignore-name list or generated blanket allowlist is used.

Use `pytest.mark.usefixtures` for setup-only fixtures, and `_parameter` or an explicit
`del` for required unused protocol arguments. Never rename an injected pytest fixture
parameter without preserving its fixture identity. The new gate complements Ruff/mypy;
it does not establish that all remaining code is reachable.

## Tool references

The [SciPy stubs](https://pypi.org/project/scipy-stubs/1.18.0.1/) and
[tqdm stubs](https://pypi.org/project/types-tqdm/4.70.0.20260906/) are separate
development dependencies; they do not change runtime implementations.

Rule meanings and lifecycle status come from the installed catalog and
[Ruff rule reference](https://docs.astral.sh/ruff/rules/). Selection and conflicting
rules are described in the [Ruff linter guide](https://docs.astral.sh/ruff/linter/)
and [preview policy](https://docs.astral.sh/ruff/preview/). Missing-import behavior is
documented by [mypy](https://mypy.readthedocs.io/en/stable/running_mypy.html).
[Vulture's documentation](https://github.com/jendrikseipp/vulture) defines confidence
classes and describes its limitations with dynamic calls. Project-specific tradeoffs
above are conclusions from inspecting this repository, not claims made by those tools.
