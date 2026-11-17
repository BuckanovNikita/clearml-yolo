# Architecture and engineering rules

These rules govern code structure. Commands that check them are in
[development procedures](development.md#architecture-checks).

## Layers

```
entrypoints  ->  adapters  ->  application (ports, contracts)  ->  core
```

- Every runtime module belongs to `core`, `application`, a named adapter responsibility or
  `entrypoints`; the import contracts are exhaustive, so an unclassified new package fails.
- Imports point inward only. Adapters may use application ports and contracts but never
  `application.use_cases`, `application.evaluation`, `application.ground_truth` or
  entrypoints. Application never imports adapters, entrypoints or SDKs.
- Command entrypoints are independent of each other; shared composition and Hydra helpers
  hold their common infrastructure. Use cases compose inward (`pipeline` above `val` and
  `report`, above `metrics`, above the single-stage commands, above `publication`).
- Adapter responsibilities are peers. By default `augmentation` and `observability`
  import no other adapter, storage consumers (`assets`, `clearml`, `integrations`,
  `reporting`, `yolo`) may import `storage` and `observability`, and the rest import only
  `observability`. Every other cross-adapter edge (detector families on shared
  `torchvision`, `integrations` composing backends and ClearML, bootstrap bridges into
  `runtime`) is an exact entry in `ignore_imports` of [.importlinter](../.importlinter),
  the only edge table. Evaluation never imports
  reporting or tracking; FiftyOne publication never imports tracking or model execution.
- Each SDK is imported only by its owner modules, again listed exactly in `ignore_imports`;
  a new SDK import needs an owner and a contract entry. Hydra, hydra-zen and OmegaConf
  belong to `entrypoints.hydra`.
- Direct commands stay independent of the queue and optional UI: CY never imports
  `cy_queue`, Textual or NVML, and never waits for queue capacity. The dependency points
  from cy-queue to CY's process, lifecycle and configuration interfaces. Local multiruns
  use Hydra's sequential BasicLauncher.
- Product code never imports tests, test dependencies or `scripts`. The weight packager
  imports only approved asset modules and no runtime SDK or `importlib`.

## Effect ownership

- Core owns no filesystem, network, process or environment access and no SDK object,
  rendering library or Loguru. It may use the standard library, NumPy, pandas, SciPy,
  Pydantic and Pandera; any other core dependency needs review. Paths in core records are
  values; adapters resolve and open them.
- Application performs effects only through typed ports supplied in
  `WorkflowDependencies` (for example `deps.storage`, `deps.resources.log`). Direct
  `Path` reads, pandas file readers or workbook writes in application code violate the
  design. Core and application never import Loguru, Matplotlib, Pillow, OpenPyXL,
  requests or filelock.
- `entrypoints.composition` builds one dependency bundle per invocation and injects the
  concrete adapters. Use cases never construct adapters or find them through a cache,
  locator or global setter; tests inject their own ports.
- Package initialization has no runtime effect: importing a package never loads a
  protected SDK, initializes storage, builds services or changes logging. The public
  `clearml_yolo` root imports nothing. Runtime initialization is explicit at invocation.
- Defer heavyweight SDK imports to their point of use where startup or help speed needs it,
  written as ordinary function-local imports so the import contracts still see them.
  Computed imports are reserved for DEIM namespace loading.
- The pinned `digital-metrics` algorithms (matching, AP integration, confidence ordering)
  run only in evaluation adapters; exact results are copied into core evaluation records.
  Only reporting writes workbooks and plots.

## Engineering rules

- Keep the declared Python compatibility, uv toolchain, `uv_build` backend and dependency
  constraints. Declare every directly imported dependency. Never weaken Ruff or strict
  mypy to silence a failure; executable values belong in maintained configuration.
- Use runtime annotations, absolute imports, typed parameters and returns, and
  `typing.Self` where it fits; quote forward references runtime evaluation cannot handle.
  Product code never uses `from __future__ import annotations`, because Pydantic and Hydra
  read annotations at runtime.
- Use Pydantic for configuration and validated records, Pandera for dataframe validation,
  and factories for mutable defaults. Keep project interfaces explicitly typed; confine
  `Any`, casts and dynamic access to external boundaries with stated assumptions.
- Every suppression names its rule or error code and has a visible reason.
- Recover or report an exception at a boundary that can act on it, with specific types;
  never discard an unexpected failure silently.
- Log with Loguru through the observability adapter and injected ports; preserve CLI
  output contracts, including Rich rendering. Comments and log messages are English.
- Name and split code by responsibility within the configured complexity limits; use
  `pathlib`.
- Keep Hydra configuration centralized in `entrypoints.hydra`. The pipeline owns tracking
  and output routing; runs have isolated identities; uploads complete and flush before
  success; native backends own native execution; validation and test data stay separate.
- Tests exercise observable product behavior with isolated temporary paths and controlled
  substitutes for external dependencies. `tests/test_native_config.py` is the deliberate
  exception: it reads the installed Ultralytics configuration. Other tests may stub
  ClearML, Ultralytics or Torch.
- A bug fix reproduces the original failing observation where feasible and verifies that
  path again; otherwise the report separates hypotheses, static evidence and executed
  checks.
- Keep credentials out of tracked files and uploads; machine-specific values belong in
  local configuration.
- Public CLI and Python APIs, serialized formats and scientific values are compatibility
  boundaries. Integrate `digital-metrics` and `report-generator` through additive
  interfaces that keep existing reader and annotation signatures and failure behavior.

## Enforcement and its limits

- import-linter ([.importlinter](../.importlinter)) checks the rules under
  [Layers](#layers), including function-local and type-only imports. Standalone pytest
  module names are listed by hand; add new ones there.
- Ruff ([src/ruff.toml](../src/ruff.toml)) bans `importlib.import_module` and
  `builtins.__import__` in product code; bare `__import__` is not detected, so review must
  catch it.
- Product tests import packages in fresh interpreters to prove inert initialization and
  resolve generated Hydra targets, console entrypoints, worker destinations and plugin
  registration.
- Passing these checks does not prove that an allowed module is free of arbitrary
  filesystem, environment, process or SDK effects, nor cover unexecuted branches or
  reflective imports. Review effect ownership explicitly; circular imports are caught only
  where they break exercised behavior.

## Static analysis

The comments in [ruff.toml](../ruff.toml), [src/ruff.toml](../src/ruff.toml) and
[pyproject.toml](../pyproject.toml) are the rationale for each exclusion. Beyond them:

- Ruff selects `ALL` with lint preview; there is no family whitelist. Upgrades activate new
  rules: review changed diagnostics and exclusion reasons with each Ruff upgrade. An
  exclusion records a tradeoff; a violation count alone does not justify one.
- mypy package-level `ignore_missing_imports` also hides missing submodules in those
  packages, a real coverage limit. Project adapters validate opaque results into typed
  records. Strengthen known interfaces instead of replacing an ignore with an equally
  opaque cast; a passing ignore is not proof the typing is ideal.
- Keep lint and stub packages in the development group, reviewed with their runtime
  versions.
- Pydantic validators, serialized fields, FiftyOne
  callbacks and SDK-consumed attributes are used indirectly: never delete them on a
  static unused-name report alone. Use `pytest.mark.usefixtures` for setup-only fixtures
  and `_name` or `del` for required unused arguments; never rename an injected fixture
  parameter. A clean Vulture run does not prove all code reachable.
