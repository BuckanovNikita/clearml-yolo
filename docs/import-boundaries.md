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
their permitted edges.

`uv run --locked task --exit-code architecture` runs the declarative contracts in
[.importlinter](../.importlinter). The development `check` and `verify` tasks include
this stage and the product import restrictions in [Ruff configuration](../src/ruff.toml).
Product tests exercise imports, generated configuration and supported runtime targets.

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
Import and execution tests catch circular imports that break supported behavior;
there is no separate whole-graph or sibling-cycle prohibition. Layer and dependency-
direction contracts still apply.

Core uses explicit dependency restrictions rather than a blanket dependency allowlist.
Scientific dependencies such as Pydantic, Pandera, pandas, NumPy and SciPy remain
supported; newly introduced dependencies require review.
It performs no filesystem, network, process or environment access and imports no
SDK, rendering library or Loguru. Paths in data records describe values; adapters
resolve, inspect and open them. Application effects go through typed ports such as
`deps.storage`; direct `Path` reads, pandas file readers and workbook writes violate
the design contract and require review. Custom static effect enforcement has been
removed: passing architecture checks does not prove these operations are absent.
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
owner and an explicit contract entry. Import-linter checks ordinary imports, including
function-local imports. Fixed-name imports use that form at the point of use so
lazy loading remains visible to the dependency checker. Ruff restricts dynamic import
facilities in product source; computed DEIM namespace loading retains documented
call-site exceptions. The installed rule detects `import_module` aliases and
`builtins.__import__`, but not bare `__import__`; review must catch that unsupported
spelling rather than relying on the lint result.
Those computed targets are runtime behavior and are not statically resolved.
Indirect SDK use through an approved adapter is normal; the layer rules still prevent
a core or application module from reaching that adapter.

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
and updates to the contracts.

## Initializers and runtime targets

Package initialization remains inert: imports must not eagerly load protected SDKs
or perform prohibited startup effects. Fresh-process product tests exercise this
behavior, including the public root's stronger requirement to avoid scientific
libraries, frameworks and SDKs. Calls and decorators are not forbidden merely by
syntax; their observed import behavior and effect ownership matter.

Product tests cover console entrypoints from metadata, exported and composed Hydra
configuration, destinations emitted by worker launch paths, plugin registration,
configuration field references and resource consumers. Supported modules and named
attributes must resolve; retired Python aliases and unsupported queue launch behavior
remain rejected. The separate queue owns tests for its guardian, snapshot runner and
GPU probe. Command-help and installed-package verification follow
[development procedures](development.md#python-integration-and-architecture).

Tests execute product paths rather than inventory every dotted source string or
reimplement Python name resolution. They establish behavior for exercised paths,
import orders and environments, not all unexecuted branches or reflective constructs.
Review effect ownership explicitly; neither import-linter nor runtime tests establish
that arbitrary effects are absent from every allowed module.

## Tooling boundaries and enforcement limits

Product code remains independent of test packages and dependencies. The weight packager
uses approved product-module boundaries and explicit dependency restrictions; individual
imported members and every possible external dependency are not allowlisted. Pure
ClearML projection helpers remain SDK-free and use explicit dependency restrictions
and inert behavior tests rather than blanket dependency allowlists.

The custom architecture scanners are retired. Their whole-graph cycle prohibition,
initializer syntax restrictions, core/pure-helper dependency allowlists, packager
member/external-library allowlists and all-dotted-string inventory are not replacement
test requirements. New dependencies and unexercised behavior require review. The
[module and effect diagram](module-architecture.md) describes preserved responsibilities.
Historical static-effect probes describe former coverage, not current guarantees.

Standalone pytest module names are listed explicitly in `.importlinter` because pytest
prepends the test directory. Extend that contract when adding standalone test modules
or helpers; it does not discover new filenames automatically. The weight packager may
not import `importlib`; reflective imports via bare builtins remain a review limitation.
