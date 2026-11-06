# Accelerator OOM verification

Date: 2026-11-06. Result: scoped CPU checks pass; native/integrated acceptance pending.

## Reproduction and checks

All Python execution used the existing environment with frozen resolution and no
synchronization. Receipt tests ran with `CUDA_VISIBLE_DEVICES=''`,
`OMP_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`, `MKL_NUM_THREADS=2` and
`MPLBACKEND=Agg`; there was no CUDA allocation or model execution.

| Check | Actual result |
| --- | --- |
| Architecture plan validator before code changes | Exit 0 |
| Selected receipt regressions before runtime fix | Exit 1: 1 failed, 14 passed, 49 deselected |
| Full receipt and architecture suites after final fix | Exit 0: 304 passed, 19 upstream Hydra/Pydantic warnings |
| Scoped Ruff for worker and receipt tests | Exit 0: all checks passed |
| Scoped mypy for worker and receipt tests | Exit 0: no issues in 2 source files |
| Existing import-linter contracts | Exit 0: 52 kept, 0 broken |
| Documentation and whitespace | Exit 0: 241 Markdown files, 0 issues; task-owned diff whitespace clean |

The baseline failure expected `oom` for a typed AcceleratorError with opaque text
and integer code 2; the original worker instead emitted `error`. Existing negative
and legacy controls passed. The final suite includes 65 receipt tests and the
existing architecture suite, including forbidden-edge cases. The earlier 64-test
receipt-only run also passed before adding the arbitrary-RuntimeError/code-2 guard.

Commands:

```bash
uv run --frozen --no-sync python -m pytest -q tests/test_batch_probe.py tests/test_architecture.py
uv run --frozen --no-sync ruff check src/clearml_yolo/adapters/integrations/probe_worker.py tests/test_batch_probe.py
uv run --frozen --no-sync mypy src/clearml_yolo/adapters/integrations/probe_worker.py tests/test_batch_probe.py
uv run --frozen --no-sync lint-imports
```

Baseline and final logs are retained by the parent evidence inventory as
`accelerator-oom-baseline.log`, `accelerator-oom-final-focused.log`,
`accelerator-oom-mypy-final.log` and `accelerator-oom-imports.log`.

## Limits and remaining gates

The regression constructs the exception shape confirmed in the exact upstream
C++ binding and installed CUDA headers; it does not reproduce a CUDA allocation
failure. The retained native X failure still belongs to the old frozen source
profile. The parent must refresh source/candidate/profile identity, replay native
execution, prove cleanup and distinguish genuine aligned-minimum `no_capacity`
from a successful confirmation. L's separate ExceptionGroup remains unresolved;
this fix does not unwrap or reclassify it. Full canonical verification and fresh
independent review remain parent-owned. Architecture acceptance is pending those
gates; passing scoped checks is not final delivery evidence.

## Independent source review — 2026-11-06

Fresh read-only reviewer `review_oom_boundary` found no blocking code or architecture
issue in the final scoped worker/test diff. It verified the exact Torch binding's
integer error-code contract, preservation of legacy CUDA OOM handling and negative
controls for unrelated errors and mixed cleanup ExceptionGroups. This is source
review, not native or final integrated acceptance. The L telemetry failure and
refreshed native replay remain open; the canonical suite is still in progress.

## Integrated canonical verification — 2026-11-06

The parent canonical command completed with exit 0 and an unchanged-input
application receipt `application-d76129d35b89403aa15cf9216f8acfb2`: Ruff,
strict mypy, Vulture and import contracts passed; the complete ordinary suite
passed 4,856 tests, with 30 skipped and 81 deselected. Architecture negative cases
and CPU-DDP were included. Documentation validation also passed. These results
cover the integrated OOM-fixed source and replace the pending canonical gate above;
they do not establish native OOM replay or close the independent L telemetry failure.

The retained L diagnostics additionally produced helper exit 255 and a bounded
telemetry timeout; the latter snapshot showed no configured memory/task-limit
exhaustion. These distinct external failures remain errors, including their
cleanup failures. Successful idle telemetry afterward does not establish loaded
reliability. No source workaround is justified by those observations, and no
smaller workload or relaxed telemetry deadline was substituted.
