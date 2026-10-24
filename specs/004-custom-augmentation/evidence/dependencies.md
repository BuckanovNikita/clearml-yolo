# Dependency floor acceptance, 2026-10-23

The changed requirements `ultralytics>=8.4.184`, `albumentations>=2.0.8,<3` and
`cloudpickle>=3.1.1` passed isolated resolution and bounded runtime checks under
the [dependency compatibility gate](../../../docs/development.md#runtime-dependency-compatibility).
This acceptance subtask changed no production module, dependency declaration,
normal lockfile, installed project environment or external dependency source.
Its architecture impact is limited to this evidence document and disposable probes;
the feature's existing architecture record owns the runtime integration changes.

## Isolated resolutions

The parent copied `pyproject.toml` to a disposable source directory, preserving its
local-source overrides through links to the existing approved dependency checkouts:

- `digital-metrics`: `6e801be1564dce458294eb23592cc1aa0939c4d9`.
- `report-generator`: `d10aa395d08f738e92e04e076cee93b3a993bf8f`.

Runtime requirements and the development group were resolved together:

```bash
uv pip compile pyproject.toml --group dev --resolution lowest-direct \
  --python 3.12.13 --no-python-downloads --output-file ../lowest-3.12.13.txt
uv pip compile pyproject.toml --group dev --resolution lowest-direct \
  --python 3.13.14 --no-python-downloads --output-file ../lowest-3.13.14.txt
```

Both commands exited zero: 269 packages for Python 3.12.13 and 268 for Python
3.13.14. Each selected exactly Ultralytics 8.4.184, Albumentations 2.0.8 and
cloudpickle 3.1.1. Existing unbounded `pandas-stubs` and `types-PyYAML` declarations
produced resolver warnings; this work did not change those unrelated requirements.
Complete resolutions and logs remain in the task-owned temporary directory
`cy004-dependency-floor`, as `lowest-*.txt` and `resolution-*.log`.

## Installed probe environments

Separate Python 3.12.13 and 3.13.14 environments installed only these exact packages,
selected from the corresponding complete resolutions, using binary distributions:

| Package | Version in both environments |
| --- | --- |
| `ultralytics` | `8.4.184` |
| `albumentations` | `2.0.8` |
| `cloudpickle` | `3.1.1` |
| `albucore` | `0.0.24` |
| `numpy` | `2.1.0` |
| `scipy` | `1.14.1` |
| `opencv-python-headless` | `4.10.0.84` |
| `pydantic` | `2.10.0` |
| `pydantic-core` | `2.27.0` |
| `annotated-types` | `0.8.0` |
| `typing-extensions` | `4.16.0` |
| `PyYAML` | `6.0.2` |
| `simsimd` | `6.5.16` |
| `stringzilla` | `5.3.1` |

The Python 3.12 environment appended the prepared project's site-packages through
a task-owned `.pth` file. Its isolated packages therefore took precedence, while
Torch 2.14.1, pytest, Hydra, tracking libraries and other supporting dependencies
were reused at their prepared versions. The Python 3.13 environment had no such
fallback and did not install Torch. `imports312.json` and `imports313.json` record
actual module origins and isolated distribution versions. Ultralytics imported
from the isolated Python 3.12 environment; Torch imported from the prepared one.

Every probe used six approved CPU cores, priority 15, one OpenMP/MKL/OpenBLAS
thread and an empty `CUDA_VISIBLE_DEVICES`. The runtime receipts record affinity,
priority and CUDA visibility. No model weights, GPU packages or native training
workloads were downloaded or started by this subtask.

## Executed runtime checks

Both interpreters passed six checks in `runtime_probe.py`:

1. Standard `A.save` JSON executes through CY's actual `TrainingPipeline`, with
   correct flipped boxes and preserved 64-bit instance identifiers.
2. Real Albumentations Mosaic with a 2x3 grid requests five distinct raw donors,
   produces the requested geometry and preserves aligned classes, crowd flags
   and unique instance identifiers.
3. A crop removing every box retains an empty sample and aligned empty vectors.
4. Normalize and dtype conversion are rejected as preprocessing conflicts.
5. cloudpickle serializes a dynamic class containing the frozen transform snapshot;
   a fresh interpreter replays it successfully after deletion of the original JSON.
6. Static inspection of the installed Ultralytics 8.4.184 source confirms the
   augmentation default keys and the dataset methods overridden by the integration.

Python 3.12 also passed all **69 tests** in these existing files:

With `FLOOR_ROOT` identifying the retained temporary directory, the probe and test
commands from the CY checkout were the following, wrapped by the resource limits
described above:

```bash
PYTHONPATH=src "$FLOOR_ROOT/python312/bin/python" \
  "$FLOOR_ROOT/runtime_probe.py" "$FLOOR_ROOT/probe312"
PYTHONPATH=src "$FLOOR_ROOT/python313/bin/python" \
  "$FLOOR_ROOT/runtime_probe.py" "$FLOOR_ROOT/probe313"
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  "$FLOOR_ROOT/python312/bin/python" -m pytest \
  tests/test_augmentation.py tests/test_yolo_augmentation.py \
  tests/test_hydra_transforms.py -q --tb=short \
  --basetemp="$FLOOR_ROOT/pytest312" -o cache_dir="$FLOOR_ROOT/pytest-cache"
```

This includes actual Ultralytics dataset loading/final formatting, preserved raw
source geometry, empty targets after custom crop, native mosaic-close behavior,
cloudpickle round-trip of the owned native trainer class without its source JSON,
all registered preset profiles, conflict handling and frozen configuration replay.
Nine existing Hydra/Pydantic deprecation warnings were emitted; no tests failed.
The command used the project source via `PYTHONPATH`, disabled pytest plugin
autoload and wrote its temporary files and cache beneath the task-owned directory.

Retained records include `probe-*.txt`, `install*.log`, `runtime_probe.py`,
`runtime312.log`, `runtime313.log`, `probe312/result.json`, `probe313/result.json`,
`imports312.json`, `imports313.json` and `pytest312.log`.

## Preservation and limits

Before/after SHA-256 checks found `pyproject.toml` and `uv.lock` unchanged during
this subtask. Prepared package versions and locations also remained unchanged;
`state-before.json` and `state-after.json` retain those observations.

These checks establish the changed minimum versions on both supported Python
minors, including actual shared augmentation and fresh-process serialization.
They do **not** establish runtime compatibility of the entire lowest-direct stack.
Only the listed numerical dependency closure was installed at resolved minimum
versions. Python 3.13 did not import or execute Ultralytics because Torch was not
installed there; its Ultralytics check was static. Python 3.12 reused Torch and
other supporting packages above their lowest-direct versions. Neither environment
ran native model training, GPU execution, ClearML publication or the full routine
suite. Those feature acceptance outcomes remain separate gates.
