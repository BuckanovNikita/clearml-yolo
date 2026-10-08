# Import boundaries

Runtime modules belong to `core`, `application`, a named adapter responsibility,
or `entrypoints`. The shipped `hydra_plugins.cy_queue` launcher is an outer entrypoint.
The public `clearml_yolo` package root contains no imports or startup operations.
Legacy Python paths are removed; regenerate Hydra examples after the cutover.
Import-linter's exhaustive container contracts classify every root child, adapter
responsibility and application component. A new unclassified child such as
`clearml_yolo.misc` fails `lint-imports` even when it has no imports. Adapter
responsibilities share one classification level; the peer contracts below govern
their permitted edges. The graph tests supplement these contracts with complete
helper-cycle detection, core allowlists, explicit-effect and runtime-target checks.

`uv run lint-imports --no-cache` enforces the configured contracts in
[pyproject.toml](../pyproject.toml). `uv run pytest tests/test_architecture.py` checks
the complete module graph, responsibility classification, cycles, core dependency
allowlist, explicit effects, initializers and runtime targets. Negative tests mutate
graphs and run both project checks and actual configured import-linter contracts.

## Layers and effects

| Source | Project dependencies |
|---|---|
| Entry points and Hydra launcher | Entry point helpers, adapters, application, core |
| Adapters | Approved adapter peers, application contracts/ports, core |
| Application | Application workflows/helpers, core |
| Core | Core only |

Adapters cannot import application use cases, application evaluation orchestration,
or entrypoints. Application cannot import adapters, entrypoints or protected SDKs.
Each of the ten command entrypoints remains independent of the other commands;
shared composition and Hydra helpers provide their common infrastructure.
All project helper and core imports form an acyclic graph.

Core permits the standard library, Pydantic, Pandera, pandas, NumPy and SciPy.
It performs no filesystem, network, process or environment access and imports no
SDK, rendering library or Loguru. Paths in data records describe values; adapters
resolve, inspect and open them. Application effects go through typed ports such as
`deps.storage`; direct `Path` reads, pandas file readers and workbook writes are
rejected by the architecture checks.
Application logging likewise uses `deps.resources.log` through the
`ExecutionResources` port. Direct Loguru, rendering, HTTP client and file-lock
dependencies are forbidden in both application and core.

## SDK owners

| Dependency | Owner |
|---|---|
| Ultralytics and Torch | YOLO adapters and named native integration bridges |
| ClearML | ClearML adapters and named native integration bridges |
| digital-metrics | Evaluation and reporting adapters |
| report-generator | Reporting adapters |
| OpenPyXL | Reporting adapters |
| FiftyOne | FiftyOne adapters |
| Hydra, hydra-zen and OmegaConf | Hydra entrypoint helpers; launcher for Hydra/OmegaConf |

The exact imports listed in `ignore_imports` are the permitted ownership edges,
including imports used only for type checking. New SDK imports require a matching
owner and an explicit contract entry. Unmatched entries fail so retired exceptions
cannot silently accumulate. Indirect SDK use through an approved adapter is normal;
the layer rules still prevent a core or application module from reaching that adapter.

`adapters.runtime.gpu_probe -> torch` is the one metadata-probe exception: the
scheduler launches this disposable process to map inherited GPU visibility before
admission. It performs no model inference or training.

## Adapter peers

| Responsibility | Ordinary peers |
|---|---|
| Storage | Observability |
| Observability | None |
| YOLO | Storage, observability |
| Evaluation | None |
| Reporting | Storage, observability |
| ClearML | Storage, observability |
| FiftyOne | None |
| Runtime | Observability |
| Integrations | Storage, observability |

The following exact bridges supplement this map; they are checked independently
of SDK ownership:

- `clearml.models -> reporting.workbook_identity` reads model identity metadata
  from recovered workbooks without report generation.
- `fiftyone.publisher -> storage.publication_data` reads immutable publication
  CSV snapshots without training-dataset preparation or image validation.
- `runtime.gpu_runtime -> clearml.session` records effective devices;
  `runtime.gpu_runtime -> integrations.native_runtime` releases native training
  memory before handing the retained GPU to downstream work.
- `integrations.native_runtime` and `integrations.native_ddp` use `clearml.session`
  to coordinate invocation ownership and owner-only tracking callbacks.
- `integrations.training` uses `clearml.native`, `clearml.session` and `yolo.config`
  to bridge native training callbacks, tracking/model registration and requested
  versus effective native settings.

Evaluation cannot import reporting or tracking; it returns scientific outputs that
the composition root routes to separate writers. FiftyOne publication cannot import
tracking or model execution. Additional peer edges require explicit justification
and updates to both the contracts and the negative graph tests.

## Initializers and runtime targets

Package initializers may define lazy factories, protocols and plugin registration
functions or re-export pure records. They cannot eagerly load protected SDKs or
execute startup operations. The public root is also imported in a fresh interpreter
to verify that no scientific library, framework or SDK is pulled in by that import.

Architecture checks inventory console scripts and literal subprocess worker, CUDA
probe and Hydra launcher targets. They also export and compose the generated Hydra
examples to inspect targets created by `hydra_zen.builds`. Target modules and named
attributes must exist in the shipped source tree; legacy aliases and missing targets
fail. These static checks complement command-help and installed-package verification
described in [development procedures](development.md).
