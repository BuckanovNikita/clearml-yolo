# Command and startup contract

`cy-download-weights` prepares the full eligible catalogue, prints destinations and
individual failures, returns zero only on full success, and always retries unresolved
preparation. `--help` performs no downloads and requires no tracking service.

Actual `cy` execution invokes the same preparation with automatic policy. A completed
catalogue/location fingerprint suppresses further automatic attempts even after
partial failure. Changed eligible selections, asset identities or destinations
trigger another attempt; valid files are reused. Interrupted attempts are unfinished.
State remains under CY_HOME, with native locks and atomic publication.

Normal loaders discover native files without rewriting Hydra model/pretrained/resume
values, native settings or environment selectors. Explicit non-null ultralytics.cfg
remains rejected. Only SDK-owned asset destinations may be outside CY_HOME.

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
See the [current cache contract](../../../docs/model-assets.md#cache-locations) for authoritative guidance.
