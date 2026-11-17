# Installation

CY is installed into a uv-managed Python environment on Linux, either from a Git URL or
from a source checkout. One installation provides every runtime capability: all detector
families, ONNX export, ClearML tracking and optional FiftyOne publication. Two evaluation
dependencies, `digital-metrics` and `report-generator`, come from the installer's own
package index or, in a source checkout, from approved local source copies.
GPU drivers, TensorRT, ClearML access and the separate `cy-queue` scheduler are
prerequisites or add-ons that the user installs and configures; CY never installs
packages while it runs.

## Behavior

### Supported environment

- Python `>=3.12.13,<3.14` (package metadata `requires-python`); both 3.12 and 3.13 are
  supported.
- Linux. On Linux, before native work, a direct experiment command checks that the
  interpreter exposes `os.pidfd_open`, `os.waitid`, `os.P_PIDFD`, `os.pipe2`,
  `os.register_at_fork` and `signal.pidfd_send_signal`, that the kernel accepts a pidfd
  signal probe and `waitid(P_PIDFD)`, that the process can become a child subreaper, and
  that it can read its own `/proc` identity ([process-ownership](process-ownership.md)).
  A Python version constraint cannot guarantee these build and kernel capabilities.
- ClearML server access with remote artifact storage, configured through the ClearML
  SDK's normal configuration ([clearml-publication](clearml-publication.md)). Every
  experiment command requires it.
- NVIDIA drivers and CUDA for GPU execution; TensorRT and its matching CUDA runtime only
  for engine build and verification ([export](export.md)).

### Installing CY

The package is not published on PyPI. `pyproject.toml` declares `digital-metrics` and
`report-generator` by version only, without a source location, so there are two routes.

Installing from a Git URL of the repository ignores the committed `uv.lock` and the local
wheelhouse: the installer's own package index must provide `digital-metrics` and
`report-generator` at versions satisfying the declared lower bounds.

The source-checkout route, which the repository's own setup and the README quick start
use, builds both packages locally. Copy the approved source trees of
`digital-metrics` and `report-generator` (revisions are listed in
[development](../development.md)) to `external/digital-metrics` and
`external/report-generator`, then from the repository root:

```bash
uvx --from go-task-bin task local-deps   # builds external/wheelhouse, creates uv.toml
uv sync --locked --dev
uv run --locked cy --help
```

`local-deps` builds source distributions of both copies into the ignored
`external/wheelhouse` and creates an ignored `uv.toml` that points uv at it; it never
overwrites an existing `uv.toml`. The committed `uv.lock` records both packages from that
wheelhouse and selects every other version. Development tools live in the separate `dev`
dependency group, which `--dev` installs as well; they are not needed to run CY.

### What is installed

The default installation has no extras and includes:

- the detector stack: Ultralytics, RF-DETR training, Torch, Torchvision, timm, PyTorch
  Lightning, pycocotools and faster-coco-eval;
- ONNX and ONNX Runtime for deployment export;
- ClearML, FiftyOne, Hydra, Albumentations, pandas and Pandera, and the evaluation and
  reporting libraries.

`pyproject.toml` declares the direct lower bounds, exact pins and upper bounds; `uv.lock`
records the selected versions. A resolver result alone does not establish runtime
compatibility.

### Separate queue package

`cy-queue` is a separate source package that owns scheduling, its Textual interface and
NVML access. Install it from its own checkout after CY, into the same environment
([queue](queue.md)). CY and all its commands work without it, and CY never imports it.

### Execution-time resolution

DEIMv2 source code and non-YOLO pretrained weights are resolved at execution time into
project caches, and explicit local checkouts and files take precedence
([model-assets](model-assets.md)). This downloads model assets only; Python packages are
never installed by a command, by a ClearML Agent replay or by model execution.

## Configuration

Installation has no CY settings. uv reads `uv.toml` for the local wheelhouse; ClearML
credentials and endpoints come from the ClearML SDK configuration; `CY_HOME` selects the
workspace at run time ([filesystem](filesystem.md)).

## Failure behavior

- `local-deps` stops with `local-deps: missing approved checkouts: ...` when a source copy
  under `external/` is absent; `uv sync --locked` needs the wheelhouse and `uv.toml` it
  creates to resolve the two local packages.
- An existing `uv.toml` without `find-links = ["external/wheelhouse"]` stops `local-deps`
  with `local-deps: uv.toml exists without find-links = ["external/wheelhouse"]; add that
  entry by hand.`
- A Git URL installation fails to resolve when the installer's package index does not
  provide `digital-metrics` or `report-generator`.
- On Linux, a missing interpreter capability fails before native work with `Process
  supervision unavailable in <interpreter>: missing <names>. Use a Linux Python build
  exposing pidfd APIs before starting native work`; a failed kernel, subreaper or `/proc`
  probe fails with a `Process supervision unavailable` or `cannot read /proc identity`
  message naming the interpreter. A failed check never falls back to PID-only signalling.
- No setting runs an experiment command without ClearML: `clearml.enabled` does not
  exist and fails composition.

## Limits

- Only Linux is supported for experiment execution.
- `uv.lock` does not store the source of the two local dependencies and does not enforce
  their Git revisions; using the approved revisions is the user's responsibility.
- Installation does not provide GPU drivers, CUDA or TensorRT.
- The package defines no extras.

## Code and tests

- [pyproject.toml](../../pyproject.toml) — supported Python, dependencies, entry points
- [Taskfile.ops.yml](../../Taskfile.ops.yml) — `local-deps`
- [adapters/runtime/process_tree.py](../../src/clearml_yolo/adapters/runtime/process_tree.py)
  — `require_process_supervision`
- Tests: [test_process_capabilities.py](../../tests/test_process_capabilities.py)
- Installation on each supported Python minor and on a clean machine is not covered by
  the routine suite; the procedure for checking interpreter and dependency-floor changes
  is in [development](../development.md).
