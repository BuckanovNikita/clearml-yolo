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
