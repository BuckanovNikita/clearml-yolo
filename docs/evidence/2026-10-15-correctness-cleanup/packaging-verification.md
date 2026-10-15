# Installed distribution and configuration verification

Date: 2026-10-15. Result: **passed** for the runtime snapshot described below.
This verifies packaging, installed interfaces and configuration; native inference,
GPU execution and ClearML publication have separate acceptance evidence.

## Source and distribution identity

Built wheel and source archive from a frozen copy of the uncommitted integrated
runtime after base commit `813ef01aa03adc5ec5067baa73131e6ed84718d2`, bearing the
existing development version **0.31.1**. No version bump, upload or publication was
performed here. Removed the complete local `[tool.uv.sources]` section only from
the copy; the real checkout's `pyproject.toml` bytes remained unchanged.

| Evidence | SHA-256 |
| --- | --- |
| Frozen source manifest | `55c283ba988310ccd37c4a09b062b78e8994c182f819f9379778ac6765afcf18` |
| Frozen lockfile | `c1cdf415a57e31470782ccfb80e4d031c241f8702a41c48b00694fde5beb9043` |
| `clearml_yolo-0.31.1-py3-none-any.whl` | `673119f28290171abca9281e5ca5167e8b4394ac5072868734c6ae9b229a4fa6` |
| `clearml_yolo-0.31.1.tar.gz` | `a2732bf5c51e49ed041405d3b44f8dc990c5f05249ede191a70ace9e03f78fe1` |
| Installed verification harness | `1449d65ed9e3d9e1580d27a34e7af17955982e7c62ff07585b06cf05486cb690` |

Both installed packages matched all **180 shipped Python/data files**, including
FiftyOne plugin metadata. A final comparison found no runtime changes after the
freeze. Source-archive inspection confirmed local source overrides were absent.
Build metadata contained ordinary requirements and the supported Python constraint.

Approved external copies stayed editable at their unchanged clean revisions:
`digital-metrics` at `6e801be1564dce458294eb23592cc1aa0939c4d9` and
`report-generator` at `d10aa395d08f738e92e04e076cee93b3a993bf8f`.
All other runtime versions came from the frozen lock export; no dependency update
or scientific-algorithm modification was performed.

## Executed checks

Each distribution was installed into a separate fresh **Python 3.12.13** environment.
The wheel environment had core requirements without Textual; the source-archive
environment also had `queue-ui`. The harness ran in isolated Python mode from an
owned working directory outside the source package, asserted installed import paths,
and used the installed console scripts. ClearML offline mode prevented publication.

| Check | Wheel | Source archive + queue UI |
| --- | --- | --- |
| Build/install and `uv pip check` | Pass; 187 compatible packages | Pass; 195 compatible packages |
| Root import without scientific/model/tracking SDK imports | Pass | Pass |
| Installed source/data byte identity | 180 files | 180 files |
| Console entrypoints and actual `--help` calls | 12 | 12 |
| Default export and installed CLI `--cfg job` composition | 9 commands | 9 commands |
| Supported command/model export and composition | 81 combinations | 81 combinations |
| Existing-file rejection, explicit overwrite and unrelated-file preservation | Pass | Pass |
| Space-containing destination through `cy-init-config` CLI | Pass | Pass |
| Guardian, queue runner, exec child, console/mirror/FiftyOne workers, plugin, GPU probe and DDP callback targets | 9 callable targets | 9 callable targets |
| Legacy queue plugin absent | Pass | Pass |
| Canonical comparison mode | `name` accepted | `name` accepted |
| Unsupported comparison modes through installed CLI and typed contracts | `stem`, `path` rejected before workflow | `stem`, `path` rejected before workflow |
| Standalone raw prediction configuration and declared input type | `name`, `stem`, `path` accepted | `name`, `stem`, `path` accepted |
| Saved two-value queue sweep composition | 2 snapshots | 2 snapshots |

The selection matrix covers all 15 model presets for each of five model-executing
commands plus six Faster R-CNN presets for export. Defaults are checked separately.
It does not load detector models or assert inference parity.

## Commands and retained evidence

The ignored task directory `.tmp/correctness-docs-20261015/packaging/` retains
`prepare.py`, `verify_install.py`, source/lock identity manifests, artifact hashes,
`final-verification.json`, exported requirements, package inventories, build/install
logs, both verification logs and generated configuration/CLI logs. The two disposable
virtual environments were removed after successful verification; artifacts and
reproduction inputs remain.

Commands used the existing `uv` toolchain:

```text
uv export --frozen --no-dev --no-emit-project --no-hashes --no-header --no-annotate
uv export --frozen --no-dev --no-emit-project --no-hashes --no-header --no-annotate --extra queue-ui
uv build <frozen-source> --out-dir <artifacts>
uv venv --python .venv/bin/python <fresh-environment>
uv pip sync --python <fresh-environment>/bin/python <frozen-requirements>
uv pip install --python <fresh-environment>/bin/python --no-deps <wheel-or-sdist>
uv pip check --python <fresh-environment>/bin/python
<fresh-environment>/bin/python -I <packaging>/verify_install.py <packaging> <wheel-or-sdist> 2
```

The first harness attempt compared `Requires-Python` text literally and stopped
because the build backend reordered equivalent specifiers. The corrected harness
compares `SpecifierSet` values; both complete reruns exited **0**. Original failure
logs remain distinguishable from the passing runs. Existing Hydra automatic-schema
and Pydantic deprecation warnings remain visible.

Python compatibility was unchanged; this bounded run covers 3.12.13 only. Parent
integration must refresh this snapshot if runtime files change and reconcile final
review/release metadata. This evidence does not close five-GPU or multi-user/multi-host
NFS acceptance gaps.
