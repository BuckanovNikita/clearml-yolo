# Validation guide

Run `cy-download-weights --help`, then `cy-download-weights` in the intended SDK
environment. A successful pass reports each native destination. Disable network
before exercising ordinary native loader names in a new process; use the same
settings/cache selectors. Preserve relative-path working-directory semantics.

Run a custom pipeline tree with architecture YAML and an explicit pretrained filename.
Verify the architecture and replay inputs remain unchanged and the file is loaded
from weights_dir. Repeated execution should skip the completed automatic pass.
Manual preparation retries after partial failure; interruption requires a new pass.

Use isolated project outputs and explicit ClearML project/tags for real pipeline
acceptance. Follow the repository end-to-end skill; unit tests alone do not prove
training or publication. Dated evidence records actual commands and outcomes.

## Superseding cache-directory correction (2026-10-30)

The original no-SDK-settings-rewrite intent above is superseded only for
Ultralytics `weights_dir`. Explicit preparation and YOLO estimator setup persist
an absolute destination before catalogue reuse or trial worker launch. Relative
values resolve against invocation cwd; existing absolute destinations, unrelated
settings and cache files are retained. CY coordinates with an adjacent lock,
verifies readback and synchronizes live SDK `weights_dir` and `WEIGHTS_DIR`.
Already-correct repeated calls do not rewrite settings. Imports, help and
configuration inspection remain inert; callback switches remain in memory.

Rerun `cy-download-weights` once from the original preparation directory to reuse
older relative caches. Errors identify the settings file and JSON/permissions/retry
recovery. Public command/report schemas and other path semantics are unchanged.
See the [current cache contract](../../docs/model-assets.md#cache-locations) for authoritative guidance.
