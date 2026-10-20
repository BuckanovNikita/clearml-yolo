# Static analysis policy and exclusion report

[Ruff configuration](../ruff.toml) selects `ALL`, including lint preview rules, and
opts out only through commented `ignore` and path-scoped exceptions. Formatter preview
remains disabled. [Import contracts](../.importlinter) use native import-linter discovery;
[pyproject.toml](../pyproject.toml) retains mypy, Vulture, pytest, coverage and package/
release settings. The [hooks](../.pre-commit-config.yaml) use the same commands as the CLI.

Ruff is constrained to `>=0.16.1,<0.17`; the lock selects the installed version.
New stable and preview rules become active on upgrades unless explicitly excluded.
Review changed diagnostics and exclusion reasons with each upgrade. Removed rules
cannot be selected. There is no family whitelist or preview opt-in list.

The [2026-10-19 evidence](../specs/026-static-analysis/config-split/verification.md)
records configuration equivalence and effective rule changes. The
[earlier audit](../specs/026-static-analysis/verification-2026-10-13.md) and
[earlier inventory](../specs/026-static-analysis/ruff-rule-inventory.csv) remain historical.
An exclusion records a tradeoff, not proof that a rule is harmful. Violation count alone
is insufficient justification; existing architecture and complexity checks still apply.

## Ruff exclusions

The comments beside every selector in `ruff.toml` are the executable policy's rationale.
Exceptions are global unless a narrower file scope is stated below.
This table adds the relevant contracts and examples.

| Rules | Reason and boundary |
| --- | --- |
| `ANN401` | Opaque ClearML/detector SDK APIs and variable-shape test doubles need explicit `Any`. Strict mypy still checks owned interfaces; prefer concrete models and protocols where known. |
| `PLC0415` | Heavy SDKs, optional backends and platform-specific imports load behind startup/platform guards. Hoisting them changes CLI startup and failure timing. |
| `PLR0913`, `PLR0917`, `FBT` | Hydra derives configuration from workflow signatures; public ports and SDK overrides have existing positional callers. Avoid blanket argument bundling or keyword-only conversion. Prefer named arguments in new internal APIs. |
| `EM`, `TRY003` | Short validation guards keep their diagnostic at the raise site. Single-use message variables or message-specific exception subclasses add indirection without different recovery behavior. Use structured exceptions when recovery needs them. |
| `CPY001`, `FIX`, `TD` | No per-file copyright or mandatory issue/author syntax policy. Keep actionable debt notes instead of deleting them to pass marker checks. |
| `D1`, `D205`, `D209`, `D401`, `D413`, `DOC` | Require useful contract documentation, not prose on every named test/helper or a uniform summary/section layout. Remaining docstring checks, including empty/overload docstrings, stay enabled. |
| `D203`, `D213` | Choose the mutually exclusive alternatives `D211` (no blank line before class docstring) and `D212` (summary on the first line). |
| `COM812`, `COM819`, `E302`, `E303`, `E306` | Comma and preview blank-line layout are formatting choices. The accidental tuple check `COM818` and existing whitespace checks remain enabled. |
| `TC001`, `TC002`, `TC003`, `TC006`, `TC008` | Pydantic/Hydra inspect annotations at runtime. Do not relocate types into checking-only blocks or quote already available cast/alias types merely for linting. Future-annotations imports remain forbidden. |
| `S404` | Process supervision requires subprocess imports. Call-site security checks remain enabled; an import alone does not establish unsafe execution. |
| `S405` (workbook identity adapter and tests only) | Read XML members of locally generated XLSX workbooks and test fixtures. Parsing behavior remains unchanged. |
| `PLC2701` (Hydra sweeps/validation and tests only) | Hydra sweep/parser functionality uses private upstream modules. Regression tests and import architecture contracts govern these boundaries. |
| `PLC1901` | CSV/config parsing distinguishes an empty string from other falsey values; explicit lexical comparisons preserve intent. |
| `PLC2801` (native runtime adapter, core ResourceRequest and tests only) | Native settings bypass persistent SDK setters using `dict.__setitem__`; frozen ResourceRequest validation normalizes its default with `object.__setattr__`. Tests call context-manager dunders to exercise entry/failure paths. Ordinary assignment or a whole `with` block is not equivalent. |
| `PLR0914`, `PLR0916`, `PLR1702`, `PLR6301`, `PLW0717` | Native adapters/workflows have protocol methods and structured state/error handling. These extra heuristic thresholds need individual design review, not unrelated extraction to satisfy counts. Existing `C901`, `PLR0911/0912/0915` and effect boundaries remain active; this is not blanket approval of complex helpers. |
| `PLR6104` | Augmented assignment can change aliasing or array semantics. Explicit reassignment is permitted. |
| `PLR6201` | Small ordered membership literals support unhashable inputs; a set is not universally interchangeable. |
| `FURB113`, `FURB140` | Sequential list assembly and readable generators need not become bulk extension or `starmap`. The ONNX attribute generator in export/build.py illustrates the tradeoff. |
| `RUF027` (tests only) | Literal Hydra interpolation, generated-code templates and Git revision braces are not missing f-strings. |
| `RUF031` | Parentheses can clarify tuple-valued keys in scientific indexing. |
| `RUF056` | An explicit `False` fallback communicates a boolean protocol default even in a condition, as in native distributed rank parsing. |
| `RUF067` (FiftyOne plugin initializer only) | FiftyOne discovers `register()` in the plugin initializer; that executable entrypoint is required. Other initializer effects remain constrained by architecture tests. |
| `RUF069` (ClearML report adapter and tests only) | Exact integral/fixture float comparisons must not become approximate assertions. Numerical tolerance decisions belong to individual scientific contracts. |
| `RUF075` | Successful task finalization and failure cleanup have distinct owners. Context-manager exception behavior needs lifecycle review. |
| `RUF105` | Rule-specific `noqa` is allowed for documented boundaries; `RUF100` rejects unused suppressions. |
| `RUF201` | Codes remain the searchable vocabulary used in suppression comments, tooling and reviews. |

Framework checks such as Airflow, FastAPI and Django remain enabled even though this
application currently has no such interfaces. Unexcluded previews run by default.

`TrackingSession` has a class-specific `PLR0904` exception: its published methods
describe one invocation's tracking lifecycle, including contributor completion.
Keep that cohesive port and its consumer contracts intact; the method-count rule
remains enabled for other production classes.

## Test-only Ruff exceptions

| Exception | Reason and boundary |
| --- | --- |
| `ARG` | Pytest fixture injection and mocks accept unused parameters. Prefer setup-only `usefixtures` and underscore callback parameters where practical. |
| `B903` | Simple test doubles need not acquire dataclass-generated equality, representation or constructor semantics. |
| `FURB118` | Local lambdas keep callback expectations readable without importing operator helpers. |
| `PLC2701` | Focused tests import private helpers without exposing a public test API. |
| `PLC2801` | Direct context-manager entry/failure probes and SDK setter bypasses need explicit dunder calls. |
| `RUF027` | Literal templates and Git revisions must not interpolate in the test process. |
| `PLR0904` | SDK test doubles mirror interfaces with many methods. |
| `RUF069` | Integral and exact float fixture comparisons do not need tolerances. |
| `S405` | Workbook fixtures parse XML generated by the test. |
| `INP001` | Pytest discovers tests without an installed test package. |
| `PLR2004` | Literal expectations keep small scenarios self-contained. |
| `S101` | Assertions are pytest's reporting interface; production input validation still uses exceptions. |
| `S108` | Known fake temp path strings are fixtures; actual writable outputs use isolated temporary directories. |
| `SLF001` | Tests probe internal failure paths without adding public test-only APIs. |

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
