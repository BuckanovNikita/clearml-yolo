# Validation guide

Run `uv run cy-init-config /tmp/cy-config-example` in a fresh destination. Inspect native
sections, then compose `uv run cy --config-dir /tmp/cy-config-example --config-name cy --cfg job`.
Override `ultralytics.device=cpu`; prediction stays [-1]. Override prediction explicitly
with `ultralytics_predict.device=cpu` for a CPU run.

Run `uv run pytest`, `uv run ruff check .`, `uv run mypy .`, and `uv run lint-imports`.
Use the running-end-to-end-tests and applicable environment skills for live execution.
Use three disjoint splits with labelled and empty images and explicit project/tags.
Inspect/download one consolidated evaluation workbook per selected split and the single exact
validation-threshold CSV; inspect the local FiftyOne receipt and its run-configuration link.
Compare frozen maps, payload matching and dataset reuse across roots. Run cy-val publication-free.
See [the contract](contracts/configuration-and-artifacts.md) for expected behavior.
