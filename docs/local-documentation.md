# Local Russian configuration reference

`cy-docs` opens a packaged Russian reference and tutorials after the ordinary Python
installation. It uses Python and vanilla JavaScript, with no Node.js build or runtime
requirement. The site assets and generated tutorial pages work offline; experiment
execution retains its normal dataset, model, device and ClearML prerequisites.

```bash
cy-docs
cy-docs --no-browser
cy-docs --port 8765 --no-browser
cy-docs --check
```

The server binds only to `127.0.0.1`, selects an available port by default (`--port 0`),
prints its URL and attempts to open a browser unless disabled. A chosen occupied port
is an error; use the automatic port or another available port. `Ctrl+C` stops the
server and cleans up documentation-owned preview workers. Opening a page neither
creates a ClearML task nor starts training. `--check` performs documentation validation
without opening a socket or browser.

## Reference and editing

Search matches public fields and utility options. Command/model filters narrow the
reference; stable links use `/#field=ground_truth` or another catalog path. Each field
identifies its meaning, accepted input shapes, constraints, applicability, examples
and owning source definition. Configuration selection supplies effective values for
the selected command, model preset and augmentation profile. Inherited expressions
remain visible separately from their selected values.

Named command dataclasses live in
[Hydra declarations](../src/clearml_yolo/entrypoints/hydra/declarations.py).
[Registration](../src/clearml_yolo/entrypoints/hydra/configs.py) projects them into the
existing permissive Hydra configuration surface. Existing keys, defaults, missing
markers, interpolation, targets and replay/export behavior remain compatibility
requirements. Existing public Pydantic model locations and runtime validators remain
authoritative. [Shared option declarations](../src/clearml_yolo/entrypoints/options.py)
supply inert utility parser factories and reference metadata.

Ultralytics defaults come from the installed dependency through the existing CY adapter;
the reference distinguishes project overrides, training/inference applicability,
inactive settings and wrapper-owned values. Nullable selectors, model references,
per-class thresholds, preprocessing and augmentation mappings retain their own field
contracts. Generated snapshots and provenance are identified separately from editable
inputs. Internal runtime records are excluded; Hydra controls have tutorial guidance.
The installed Hydra CLI flags also have individual `hydra.--…` reference entries.

The editor accepts named YAML documents and ordered overrides. It displays composed
YAML, configuration differences, unresolved values, schema errors and deferred runtime
checks. Copy/download controls produce commands and YAML to use in a terminal. The
site does not provide training, queue submission or deployment actions.

## Preview boundary

Each HTTP preview uses a fresh Python subprocess and built-in configuration groups.
Submitted documents compose without launching the application or instantiating
Python targets. Dataset selectors, checkpoints and augmentation JSON files are not
opened. Environment and custom resolver expressions remain unresolved rather than
reading the host environment or invoking user functions.

| Limit or rule | Behavior |
| --- | --- |
| Request body | At most 1 MiB |
| Named documents | At most 32 relative `.yaml` names; no traversal; Hydra's file source does not accept `.yml` |
| Sweep expansion | At most 100 jobs |
| Worker lifetime | 15-second deadline |
| Hydra runtime controls | Submitted `hydra` blocks, Hydra overrides, external search paths and plugin replacement are rejected before composition; apply runtime controls in the terminal |
| HTTP access | Loopback Host/Origin checks; no cross-origin API access |
| Worker failure | Explicit preview error; server and ordinary commands remain separate |

Preview does not verify file existence/content, ClearML credentials or storage,
dataset downloads, model loading, augmentation operator compatibility, GPU capacity,
native execution, upload success or deployment quality. A missing `???` input or an
unresolved expression must be supplied for a real run. Schema feedback is an aid to
editing; it does not replace runtime validation. No queue schemas or new extension
API are introduced. Queue lessons use the separately installed `cy-queue` interface.
Ordinary overrides retain their order. Sweep expansion follows the installed Hydra
BasicSweeper, including its repeated-key handling; avoid mixing delete/add and
replacement of the same key in a sweep. Temporary submitted files belong to the
server's worker owner and are removed after success, failure, timeout or shutdown.

## Tutorials and scenario coverage

Authored Russian Markdown, generated HTML and the scenario inventory are packaged in
[tutorial assets](../src/clearml_yolo/adapters/documentation/assets/tutorials).
Every tutorial includes prerequisites, editable examples, expected outputs, field
links, common failures and verification instructions. The inventory maps commands
and configuration groups to tutorial scenarios and composition cases.

The following maintenance matrix connects each public surface to its declaration,
lesson and executable checks. The packaged JSON inventory supplies named scenarios
and the exact preview inputs; the compatibility fixture identifies every composed
command/model/profile case. These checks validate configuration and documentation,
not the runtime outcomes described by a lesson.

| Commands or configuration group | Reference | Tutorial | Verification case |
| --- | --- | --- | --- |
| `cy`, `metrics`, `compare`, `report` pipeline settings | [Command declarations](../src/clearml_yolo/entrypoints/hydra/declarations.py) | [Complete experiments](../src/clearml_yolo/adapters/documentation/assets/tutorials/pipeline.md) | `test_all_compositions_preserve_unresolved_and_resolved_defaults`; inventory `pipeline` |
| `cy-train`, `model`, `ultralytics` | [Models](../src/clearml_yolo/core/models.py), [native declarations](../src/clearml_yolo/entrypoints/documentation/native.py) | [Training](../src/clearml_yolo/adapters/documentation/assets/tutorials/training.md) | `test_all_compositions_preserve_unresolved_and_resolved_defaults`; inventory `training` covers every model preset |
| `cy-predict`, `cy-val`, `cy-metrics`, `cy-compare`, `cy-report`, `ultralytics_predict`, `evaluation`, `fiftyone` | [Commands](../src/clearml_yolo/entrypoints/hydra/declarations.py), [evaluation](../src/clearml_yolo/core/evaluation/models.py), [publication](../src/clearml_yolo/core/publication.py) | [Evaluation](../src/clearml_yolo/adapters/documentation/assets/tutorials/evaluation.md) | `test_all_compositions_preserve_unresolved_and_resolved_defaults`; inventory `evaluation` |
| `cy-ground-truth`, `clearml`, dataset/model selectors | [Commands](../src/clearml_yolo/entrypoints/hydra/declarations.py), [selectors](../src/clearml_yolo/application/contracts.py) | [Quick start](../src/clearml_yolo/adapters/documentation/assets/tutorials/quickstart.md) | `test_legacy_override_shapes_remain_permissive`; inventory `quickstart` |
| `cy-init-config`, Hydra CLI controls | [Options](../src/clearml_yolo/entrypoints/options.py), [Hydra controls](../src/clearml_yolo/entrypoints/documentation/controls.py) | [Composition](../src/clearml_yolo/adapters/documentation/assets/tutorials/configuration.md) | `test_inert_parsers_preserve_exact_existing_help`, `test_command_specific_required_values_and_hydra_cli_reference`; inventory `configuration` |
| `transforms`, `transform_overrides` | [Transform fields](../src/clearml_yolo/core/transforms.py), [profile overlays](../src/clearml_yolo/entrypoints/hydra/transforms.py) | [Customization](../src/clearml_yolo/adapters/documentation/assets/tutorials/customization.md) | `test_all_compositions_preserve_unresolved_and_resolved_defaults`, `test_preview_never_loads_an_augmentation_file`; inventory `customization` |
| `cy-batch-estimate` | [Options](../src/clearml_yolo/entrypoints/options.py) | [Training](../src/clearml_yolo/adapters/documentation/assets/tutorials/training.md) | `test_inert_parsers_preserve_exact_existing_help`, `test_option_declarations_preserve_parsing_types_and_defaults` |
| `cy-download-weights`, `cy-dedup` | [Options](../src/clearml_yolo/entrypoints/options.py) | [Operations](../src/clearml_yolo/adapters/documentation/assets/tutorials/operations.md) | `test_inert_parsers_preserve_exact_existing_help`, `test_option_declarations_preserve_parsing_types_and_defaults` |
| `cy-export`, `export` | [Export fields](../src/clearml_yolo/core/export_requests.py) | [Deployment](../src/clearml_yolo/adapters/documentation/assets/tutorials/deployment.md) | `test_all_compositions_preserve_unresolved_and_resolved_defaults`; inventory `deployment` |
| `cy-docs` | [Options](../src/clearml_yolo/entrypoints/options.py) | [Quick start](../src/clearml_yolo/adapters/documentation/assets/tutorials/quickstart.md), [composition](../src/clearml_yolo/adapters/documentation/assets/tutorials/configuration.md) | `test_installed_catalog_and_tutorial_examples`; [browser cases](../browser_tests) |

Named test functions above live in [compatibility tests](../tests/test_docs_compatibility.py),
[catalog tests](../tests/test_docs_catalog.py) and [preview tests](../tests/test_docs_preview.py).
The external `cy-queue` scenarios in the operations tutorial retain the separate queue
package's tests and [paired verification](development.md#paired-cy-and-queue-release-check).

- First installation, ClearML setup, executable tiny dataset generation, CSV,
  background images, disjoint splits and local/ClearML dataset selectors.
- All registered model families, architecture/weights selection, fine-tuning,
  devices, image sizes, batch estimation, memory failures and offline assets.
- Prediction, validation, saved-prediction metrics, val calibration/test thresholds,
  baseline/candidate comparison, reports, FiftyOne and artifact provenance.
- Complete pipeline, separate stages, skipped work, output reuse, failure recovery
  and published configuration inspection.
- Generated trees, defaults, CLI precedence, interpolation, nested/list/null
  overrides, sweeps, backend settings and DDP.
- Albumentations/Mosaic, processing between stages and typed dependency replacement
  using `dataclasses.replace` with explicit lifecycle ownership.
- Agent replay, queue submission/recovery, cache maintenance, weight preparation,
  supported ONNX/TensorRT operations and their verification limits.

## Maintenance and verification

Catalog assembly and Hydra composition belong to documentation entrypoints. Serving
adapters receive typed records/callbacks and own sockets, packaged-file access and
worker processes. Core/application modules cannot import serving or rendering code.
Documentation assets are loaded only by explicit documentation operations, so missing
assets, malformed tutorials and preview-worker failures cannot become ordinary
library-import or application-command dependencies.

After changing tutorial Markdown, regenerate the shipped pages using the existing
development Markdown dependency:

```bash
uv run --frozen --no-sync python scripts/render_docs.py
uv run --frozen --no-sync cy-docs --check
uv run --frozen --no-sync python scripts/verify.py --docs
```

`cy-docs --check` rejects missing/stale assets, unknown field links, uncovered commands
or groups and invalid tutorial preview cases. Catalog completeness is checked against
registered commands, composed configurations, Pydantic fields and supported native
keys. New public fields require documentation/classification; fallback prose must
not silently hide a missing declaration. Runtime/schema changes also require the
canonical repository verification and configuration compatibility checks.

Browser acceptance lives separately in [browser_tests](../browser_tests). Python
Playwright and a compatible Chromium browser are development tools, not runtime
dependencies:

```bash
uv run --frozen --no-sync pytest browser_tests -q
```

Provision the browser through the development environment first. The optional
`CY_DOCS_BROWSER_CHANNEL` selects an installed Playwright-compatible channel; omitting
it uses Playwright's default Chromium. This suite exercises search, editing, preview,
downloads, keyboard access, offline assets, error handling and shutdown. Its results
are distinct from real training/GPU/ClearML artifact evidence, which follows the
repository's native end-to-end workflow. Record observed outcomes in feature evidence,
not as permanent claims in this contract.
