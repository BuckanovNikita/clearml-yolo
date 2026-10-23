# Dependency floor acceptance, 2026-10-23

This check covers the new direct runtime dependency `requests>=2.32.0` and
development dependency `types-requests>=2.32.0`, with the queue-only direct
dependencies removed from CY. It follows the isolated lowest-direct requirement
in [development guidance](../../../docs/development.md#runtime-dependency-compatibility).
No production code, dependency pins, normal lockfile, shared Python environment or
external dependency checkout was changed by this acceptance subtask.

## Isolated resolutions

The current `pyproject.toml` was copied into a disposable source directory. Its
existing local-source overrides were retained, resolving against source archives
of the clean approved dependency revisions:

- `digital-metrics`: `6e801be1564dce458294eb23592cc1aa0939c4d9`, version `0.7.0`.
- `report-generator`: `d10aa395d08f738e92e04e076cee93b3a993bf8f`, version `0.1.2`.

No dependency source was patched. The runtime requirements and development group
were resolved together with these commands from that disposable source directory:

```bash
uv pip compile pyproject.toml --group dev --resolution lowest-direct \
  --python 3.12.13 --no-python-downloads --output-file ../lowest-3.12.13.txt
uv pip compile pyproject.toml --group dev --resolution lowest-direct \
  --python 3.13.14 --no-python-downloads --output-file ../lowest-3.13.14.txt
```

Both exited zero: 269 packages on Python 3.12.13 and 268 on Python 3.13.14.
The direct versions were identical on both interpreters and are recorded below;
complete transitive resolutions and logs are retained in
`.tmp/portable-dependency-floor/lowest-*.txt` and `resolution-*.log`.
The resolver warned that the pre-existing `pandas-stubs` and `types-PyYAML`
requirements have no lower bounds. Their resolved versions were recorded without
changing those unrelated declarations.

| Group | Direct dependency | Resolved version on both interpreters |
| --- | --- | --- |
| runtime | `ultralytics` | `8.4.165` |
| runtime | `aiohttp` | `3.10.5` |
| runtime | `albumentations` | `2.0.0` |
| runtime | `hydra-core` | `1.3.0` |
| runtime | `hydra-zen` | `0.16.0` |
| runtime | `omegaconf` | `2.3.0` |
| runtime | `clearml` | `2.1.6` |
| runtime | `fiftyone` | `1.22.0` |
| runtime | `graphql-core` | `3.2.0` |
| runtime | `filelock` | `3.32.0` |
| runtime | `requests` | `2.32.2` |
| runtime | `pydantic` | `2.10.0` |
| runtime | `pyyaml` | `6.0.2` |
| runtime | `loguru` | `0.7.0` |
| runtime | `pandas` | `3.0.0` |
| runtime | `numpy` | `2.1.0` |
| runtime | `pandera` | `0.34.1` |
| runtime | `pillow` | `12.2.0` |
| runtime | `scipy` | `1.14.1` |
| runtime | `openpyxl` | `3.1.5` |
| runtime | `tqdm` | `4.66.0` |
| runtime | `digital-metrics` | `0.7.0` |
| runtime | `report-generator` | `0.1.2` |
| runtime | `ruamel-yaml` | `0.18.0` |
| runtime | `calflops` | `0.3.2` |
| runtime | `faster-coco-eval` | `1.8.0` |
| runtime | `pycocotools` | `2.0.11` |
| runtime | `pytorch-lightning` | `2.6.6` |
| runtime | `rfdetr` | `1.11.2` |
| runtime | `tensorboard` | `2.20.0` |
| runtime | `timm` | `1.0.24` |
| runtime | `torch` | `2.13.0` |
| runtime | `torchvision` | `0.28.0` |
| runtime | `onnx` | `1.23.2` |
| runtime | `onnxruntime` | `1.31.0` |
| dev | `import-linter` | `2.13` |
| dev | `markdown-it-py` | `4.2.0` |
| dev | `mypy` | `1.11.0` |
| dev | `packaging` | `26.0` |
| dev | `pandas-stubs` | `1.0.4.2` |
| dev | `types-PyYAML` | `0.1.0` |
| dev | `types-requests` | `2.32.0.20240521` |
| dev | `pre-commit` | `4.6.1` |
| dev | `pytest` | `8.0.0` |
| dev | `ruff` | `0.16.1` |
| dev | `scipy-stubs` | `1.18.0.1` |
| dev | `types-tqdm` | `4.70.0.20260906` |
| dev | `vulture` | `2.16` |
| dev | `python-semantic-release` | `10.5.0` |
| dev | `hypothesis` | `6.169.1` |
| dev | `pytest-cov` | `7.1.0` |

## Bounded runtime and type checks

The resolver selected Requests `2.32.2`, rather than the declared numeric lower
bound `2.32.0`, and types-requests `2.32.0.20240521`. Two disposable environments
used those Requests bytes. The Python 3.12 environment loaded the existing
prepared CY dependencies through a task-owned `.pth` after its own site-packages;
its own Requests and type stubs therefore took precedence. The Python 3.13
environment installed only Requests and its small dependency closure for the
transport probe. Neither environment installed the full lowest-direct detector
stack.

The final transport checks explicitly used the resolved Requests dependency
closure: urllib3 `2.8.0`, certifi `2026.10.23`, charset-normalizer `3.5.2` and idna
`3.7`. Import-origin/version records prove the isolated Requests and stub packages
were selected.

- Python 3.12.13: all 11 existing tests in `tests/test_model_assets.py` passed with
  Requests `2.32.2`. These include concurrent consumers, atomic cache replacement,
  manual offline placement, proxy construction/fallback/redaction, redirects,
  authentication, read timeouts, interrupted bodies and aggregated missing-asset
  instructions.
- Python 3.12.13 and 3.13.14: a real loopback HTTP fixture passed eight checks per
  interpreter for streamed bytes, redirect handling, Basic authentication, HTTP
  rejection, read timeout, interrupted body, download size bound and credential
  redaction. The fixture used ephemeral ports and shut down its server/thread.
- Strict mypy passed for `adapters/assets/http.py` and `adapters/assets/resolver.py`
  using the isolated minimum types-requests package. The mypy executable and other
  dependencies came from the prepared CY environment, not their lowest-direct
  versions.

Executed commands, from the CY checkout:

```bash
.tmp/portable-dependency-floor/python312/bin/python -m pytest \
  tests/test_model_assets.py -q \
  --basetemp=.tmp/portable-dependency-floor/pytest312-closure
.tmp/portable-dependency-floor/python312/bin/python -m mypy \
  --no-incremental --cache-dir=.tmp/portable-dependency-floor/mypy-cache \
  src/clearml_yolo/adapters/assets/http.py \
  src/clearml_yolo/adapters/assets/resolver.py
.tmp/portable-dependency-floor/python312/bin/python \
  .tmp/portable-dependency-floor/http_smoke.py
PYTHONPATH=src .tmp/portable-dependency-floor/python313/bin/python \
  .tmp/portable-dependency-floor/http_smoke.py
```

The fixture and logs remain under `.tmp/portable-dependency-floor/`. The final
runtime outputs are `pytest312-closure.log`, `http312-closure.json` and
`http313-closure.json`; `mypy.log` records the type check.

## Preservation and limits

Before/after SHA-256 checks confirmed that the normal `pyproject.toml` and
`uv.lock` were unchanged during this subtask. Both original external checkouts
remained clean at the approved revisions. `state-before.json` and `summary.json`
retain those checks in the ignored evidence directory.

These results establish resolution on both supported Python minors and bounded
compatibility of the new Requests APIs/stubs at the minimum versions selected by
that resolution. They do not establish runtime compatibility of all resolved
lower-bound detector, scientific, tracking or developer dependencies. The full
lowest-direct environments were not installed, and the literal Requests `2.32.0`
release was not separately forced. Native detector and Agent runs used their
separately documented prepared environments; those outcomes must not be described
as full dependency-floor execution. Live Artifactory connectivity remains
unverified.
