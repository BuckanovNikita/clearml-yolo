# 2026-09-20 packaging verification

## Scope and environment

- Repository artifact version: `clearml-yolo 0.3.0`.
- Toolchain: `uv 0.11.32`, CPython `3.12.13`.
- No ClearML task, GPU workload, training, prediction, or dataset operation was run.
- Each distribution was installed into its own freshly created virtual environment
  below `/tmp`; neither environment used `--system-site-packages`.  uv's ordinary
  download/build cache was reused where available.
- This final pass supersedes the prior 93-package artifact snapshot after the
  native Albumentations dependency was restored.

## Initial dependency metadata finding and correction

The first wheel build contained bare `Requires-Dist: digital-metrics` and
`Requires-Dist: report-generator` metadata.  A clean

```bash
uv pip install --python <fresh-venv>/bin/python \
  dist/clearml_yolo-0.3.0-py3-none-any.whl
```

failed because neither dependency exists on the package index.  The repository
manifest was then updated to use the two pinned PEP 508 Git URLs, and `uv lock`
was run by the implementation owner.  This verification rebuilt both artifacts
from that corrected manifest.  Their wheel metadata now contains:

```text
Requires-Dist: digital-metrics @ git+https://github.com/Wasilkas/digital-metrics@ecce79cdcade2bb463c4bcc9eac77512d1033117
Requires-Dist: report-generator @ git+https://github.com/Wasilkas/report-generator@2172d3945723233b087b1375c2c821d020462f00
```

The final wheel metadata also contains `Requires-Dist: albumentations>=2.0,<3`.

## Artifact and isolated-install results

`uv build --wheel --sdist` completed successfully and produced:

```text
dist/clearml_yolo-0.3.0-py3-none-any.whl
dist/clearml_yolo-0.3.0.tar.gz
```

The final artifacts tested in the two fresh environments are identified by
these SHA-256 digests:

```text
a5ffa55ba780e894e0c950da4137c9c65f7b78d25377a86ff7d1b86337fa417e  clearml_yolo-0.3.0-py3-none-any.whl
20d25834d77edd8b77c04f8f5ad4d257ff55bc6846f50a13492be062db5404e8  clearml_yolo-0.3.0.tar.gz
```

The wheel was installed with `uv pip install --python
/tmp/clearml-yolo-packaging-albu-wheel.cQCz6Z/venv/bin/python
dist/clearml_yolo-0.3.0-py3-none-any.whl`.  The sdist was installed with the
same command shape in separate
`/tmp/clearml-yolo-packaging-albu-sdist.lPYAxH/venv`, targeting
`dist/clearml_yolo-0.3.0.tar.gz`.  Both resolves installed 98 runtime packages,
including the pinned Git dependencies, and imported `clearml_yolo` from the
respective venv's `site-packages` directory.

For each clean install, every retained console command returned exit code zero
for `--help`:

```text
cy
cy-train
cy-predict
cy-val
cy-metrics
cy-report
cy-compare
cy-ground-truth
```

The installed `bin` directory contained exactly those eight `cy*` console
scripts.  `cy-queue` and `cy-init-config` were absent in both environments.

In both isolated environments, the following native Ultralytics check passed:

```python
from ultralytics.data.augment import Albumentations
assert Albumentations().transform is not None
```

The constructor reported its native detection transforms, including `Blur`,
`MedianBlur`, `ToGray`, and `CLAHE`; it did not require a dataset, ClearML task,
or GPU.

The final source and archive checks also found no retired Python or YAML source
for `conf`, `queue`, `config_tree`, `gpu`, `augment`, or
`ultralytics_params`.  The checkout retains an ignored stale
`src/clearml_yolo/conf/__pycache__/` directory from an earlier import, but it
contains no source and is absent from both artifacts.

## Documentation composition check

The native-override example was parsed without executing a task.  Before the
README correction made during this verification, its second command omitted
the leading `+` before the absent `train.ultralytics.epochs` key and exited 1.
The refreshed README now contains:

```bash
uv run cy +train.ultralytics.epochs=10 +train.ultralytics.compile=true
```

This composition succeeds with `--help` (and does not initialize ClearML):

```bash
uv run --no-sync cy +train.ultralytics.epochs=10 \
  +train.ultralytics.compile=true --help
```

## Limits

This proves package buildability, dependency resolution, installed entrypoints,
and help-time configuration loading.  It does not prove a ClearML connection,
artifact upload, native Ultralytics execution, a GPU run, or end-to-end command
semantics.  Temporary virtual environments created for these checks were removed
after verification; the ignored `dist/` artifacts were retained for release
inspection.
