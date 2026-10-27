# Import boundaries

Runtime modules belong to `core`, `application`, a named adapter responsibility,
or `entrypoints`. Local multiruns use Hydra's standard BasicLauncher; no project
launcher plugin is shipped.
The public `clearml_yolo` package root contains no imports or startup operations.
Legacy Python paths are removed; regenerate Hydra examples after the cutover.
Import-linter's exhaustive container contracts classify every root child, adapter
responsibility and application component. A new unclassified child such as
`clearml_yolo.misc` fails `lint-imports` even when it has no imports. Adapter
responsibilities share one classification level; the peer contracts below govern
their permitted edges. The graph tests supplement these contracts with `graphlib` whole-graph cycle detection,
core/adapter dependency allowlists, explicit-effect and runtime-target checks.

`uv run lint-imports --no-cache` enforces the configured contracts in
[.importlinter](../.importlinter). `uv run pytest tests/test_architecture.py` checks
the complete module graph, responsibility classification, cycles, core dependency
allowlist, explicit effects, initializers and runtime targets. Negative tests mutate
graphs and run unique AST checks and actual configured import-linter contracts. The
canonical verifier includes both commands without a separate architecture pytest run.

## Layers and effects

| Source | Project dependencies |
|---|---|
| Entry points | Entry point helpers, adapters, application, core |
| Adapters | Approved adapter peers, application contracts/ports, core |
| Application | Application workflows/helpers, core |
| Core | Core only |

Adapters cannot import application use cases, application evaluation orchestration,
or entrypoints. Application cannot import adapters, entrypoints or protected SDKs.
Each command entrypoint remains independent of the other commands;
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
| Ultralytics | YOLO adapters and named native integration bridges |
| Torch / Torchvision / timm | Explicit native detector, export and integration modules |
| RF-DETR / Lightning / Lightning Fabric | RF-DETR backend and native probe |
| pycocotools / faster-coco-eval | Shared Torchvision evaluation, export quality / DEIM probe |
| ONNX / TensorRT | Export adapters |
| ClearML | ClearML adapters and named native integration bridges |
| digital-metrics | Evaluation and reporting adapters |
| report-generator | Reporting adapters |
| OpenPyXL | Reporting adapters |
| FiftyOne | FiftyOne adapters |
| Hydra, hydra-zen and OmegaConf | Hydra entrypoint helpers |
| HTTP requests and safetensors format validation | CY assets adapter |
| Textual / NVML | Separate `cy_queue` package only |

The exact imports listed in `ignore_imports` are the permitted ownership edges,
including imports used only for type checking. New SDK imports require a matching
owner and an explicit contract entry. Ordinary unmatched exceptions fail; optional
backend/export contracts explicitly permit absent imports and the same configured
contracts evaluate the AST-enriched graph containing literal dynamic edges. Indirect SDK use through an approved adapter is normal;
the layer rules still prevent a core or application module from reaching that adapter.

Queue admission and its disposable visibility probe belong to `cy_queue`; its
architecture contracts own their SDK edges. CY's local estimator separately owns
idle-GPU telemetry and fresh native trials; explicit training `batch=null` discovers
assigned hardware for compatible lookup. CY cannot import `cy_queue`, Textual or
NVML, and does not wait for queue capacity. The permitted dependency direction is
queue → CY shared interfaces.

## Adapter peers

| Responsibility | Ordinary peers |
|---|---|
| Storage | Observability |
| Observability | None |
| YOLO | Storage, observability |
| Evaluation | Observability |
| Reporting | Storage, observability |
| ClearML | Storage, observability |
| FiftyOne | Observability |
| Runtime | Observability |
| Assets | Storage, observability |
| Integrations | Storage, observability |
| DEIMv2, RF-DETR, Faster R-CNN, FCOS, Torchvision, export | Observability |

The following exact bridges supplement this map; they are checked independently
of SDK ownership:

- `clearml.models -> reporting.workbook_identity` reads model identity metadata
  from recovered workbooks without report generation.
- `fiftyone.publisher -> storage.publication_data` reads immutable publication
  CSV snapshots without training-dataset preparation or image validation.
- `integrations.native_runtime` and `integrations.native_ddp` use `clearml.session`
  to coordinate invocation ownership and owner-only tracking callbacks.
- `integrations.training` uses `clearml.native`, `clearml.session` and `yolo.config`
  to bridge native training callbacks, tracking/model registration and requested
  versus effective native settings.
- Bootstrap bridges from storage, observability, native runtime and the FiftyOne
  worker initialize project paths; bounded publication uses storage containment.
- Native backend/export modules use exact filesystem-containment edges.
  `integrations.detectors` selects backend adapters and owner tracking;
  `integrations.export_operations` composes export operations and native model loading.
  Export ONNX/verification bridges use the Faster R-CNN model, and verification
  reads storage dataset records. `native_ddp` also uses the ClearML deadline adapter.
- `assets.execution` composes asset descriptions supplied by DEIM, RF-DETR and
  Faster R-CNN adapters. DEIM source loading uses manifest verification from
  `assets.archive`. Model asset selection/loading uses immutable core descriptions. HTTP, cache writes, locks and extraction stay outside core and
  application workflows; native detector adapters retain checkpoint transformations.
- Faster R-CNN and FCOS inject their model builders and label conventions into
  shared `torchvision` data, training, evaluation, prediction and probe modules.
  Shared execution cannot import either family or ClearML publication.
- Integration adapters compose estimate profiles, local storage, telemetry and
  supervised workers. Pure search/compatibility remains in core; application
  estimation uses `batch_ports`. `training_workers` carries typed rank records.
  Native ranks use runtime distributed setup; the invocation owner publishes results.

The authoritative exact-edge lists are `ignore_imports` in
[.importlinter](../.importlinter); there is no second Python ownership table.
This table summarizes
responsibilities rather than granting additional edges.

The composition root binds `integrations.native_runtime` training-memory release
directly to the execution resource port for downstream work and invocation cleanup.

Evaluation cannot import reporting or tracking; it returns scientific outputs that
the composition root routes to separate writers. FiftyOne publication cannot import
tracking or model execution. Additional peer edges require explicit justification
and updates to both the contracts and the negative graph tests.

## Initializers and runtime targets

Package initializers may define lazy factories, protocols and plugin registration
functions or re-export pure records. They cannot eagerly load protected SDKs or
execute startup operations. The public root is also imported in a fresh interpreter
to verify that no scientific library, framework or SDK is pulled in by that import.

CY architecture checks inventory its console scripts and literal console, native
worker and FiftyOne targets. The separate queue checks its guardian, snapshot runner
and CUDA metadata-probe targets; the retired project Hydra launcher must not remain.
They also export and compose the generated Hydra examples to inspect targets created by `hydra_zen.builds`. Target modules and named
attributes must exist in the shipped source tree; legacy aliases and missing targets
fail. These static checks complement command-help and installed-package verification
described in [development procedures](development.md).

See the [module and effect diagram](module-architecture.md) for interfaces and failure
behavior. Static checks validate visible syntax and supported re-exports; they cannot
prove arbitrary runtime attribute construction, monkeypatching or third-party effects.
Negative fixtures must demonstrate rejection of each enforced prohibition, while
positive fixtures protect legitimate pure operations and injected-port calls.

Target checks resolve every module/class segment, simple aliases and explicit project
re-exports. Function-local, nested-function, annotation-only and `TYPE_CHECKING`-only
bindings are not runtime module attributes. Initializer checks inspect definition-time
decorators, defaults, annotations, class bases/metaclass expressions and class bodies;
deferred function/lambda bodies are excluded. Effect checks resolve imported and simple
assigned aliases within function, lambda, class and comprehension scopes, including
network/process calls and environment access. Explicit application port calls such as
`deps.storage` remain permitted.

Nested class bodies do not inherit outer class namespaces. Class target aliases may
refer to prior class or module bindings. Deferred callable bodies use final enclosing
bindings; definition-time expressions retain their immediate scope. Calls made during
module initialization and arbitrary later rebinding are outside that static model.

These checks do not execute inspected modules or provide complete control-flow,
interprocedural or reflective analysis. Computed imports/attributes, generated or
inherited attributes, branch-dependent rebinding and unknown wrappers remain review
obligations. Generic filesystem method-name checks are conservative. See the
[negative-fixture evidence](https://github.com/BuckanovNikita/clearml-yolo/blob/d74945c83dc24094c599388bbcfd5e987daeb9bf/.specify/bugs/architecture-check-blindspots/test.md).
