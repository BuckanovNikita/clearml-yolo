# Quickstart Validation: FiftyOne Integration

## Use

Install the locked dependencies with `uv sync --dev`. FiftyOne is a main dependency.
Provide a supported local MongoDB server through FiftyOne's bundled service or
`FIFTYONE_DATABASE_URI`. Set `FIFTYONE_DATABASE_DIR` to the local database/lock directory.
Publishers accessing the same database on this machine must share that lock directory.

`cy`, `cy-predict`, and `cy-metrics` enable publication by default. Existing required
command inputs and ClearML configuration still apply. Use `fiftyone.enabled=false`
to select the dependency-free no-op layer, or `fiftyone.dataset_prefix=my-project`
to choose a dataset namespace. `cy-init-config CONFIG_DIRECTORY` exports these defaults.

After a successful run, inspect `fiftyone_publication.json` for the dataset name and
task-specific field names. Open the dataset manually as shown in [README.md](../../README.md#fiftyone).
Samples preserve `image_name`, `split`, and referenced image paths. Keep media available
at those paths. Unchanged effective GT CSV bytes reuse the imported samples; changing
resolved paths for the same identity fails. Image bytes are assumed immutable.

## Verify

Run the ordinary repository gates:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
```

The ordinary suite checks configuration, dependency-free no-op behavior, payload fidelity,
and command ownership. Real database tests are opt-in. Point the environment variables
below at a task-owned database and lock directory before running:

```bash
export FIFTYONE_DATABASE_DIR=/path/to/task-owned/fiftyone
export FIFTYONE_DATABASE_URI=mongodb://127.0.0.1:27017
CY_TEST_FIFTYONE=1 uv run pytest tests/test_fiftyone_publisher.py
```

These tests use unique dataset prefixes and delete only the datasets they create. They
check persistence, split/background preservation, matching annotations, reuse, path
conflicts, concurrent publication, and interrupted import/run recovery.

For actual pipeline verification, follow the `running-end-to-end-tests` skill. Exercise
the initial pipeline and paired current-test rerun, standalone prediction/metrics,
disabled publication, and an enabled publication failure. Download required ClearML
performance artifacts and verify one local owner receipt plus its run-configuration link,
frozen thresholds, retained local outputs on failure, and no FiftyOne publication by
validation/report/comparison commands. The receipt must not appear in ClearML artifacts.

See [dated implementation evidence](../../docs/evidence/2026-09-29-fiftyone.md).
