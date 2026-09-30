# Validation Guide: Native ClearML tracking

## Prerequisites

Initialize existing submodules and the repository's uv environment if needed. Do not advance external dependency revisions. Read AGENTS.md and the running-end-to-end-tests skill; load the applicable environment guidance for actual native acceptance. Use explicit ClearML project/tags and task-owned output directories.

## Repository checks

```bash
uv run pytest tests/test_native_ddp.py tests/test_native_tracking_contract.py tests/test_publication_commands.py tests/test_config_upload_commands.py
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
```

Expect early DDP epoch dispatch, exact-once final drain, deferred native terminal publication, context identity, partial-record buffering, failure propagation and cleanup coverage. Mocked tests do not establish native training or backend uploads.

## Real acceptance

Follow the E2E skill's portable command/configuration examples and read actual maintained environment values there. Run a small multi-epoch CPU or single-GPU native training case plus a pipeline case with explicit project/tags and dataset inputs. Inspect backend loss scalars before training finishes; after completion inspect native plots/debug samples, single native Output Model, downloaded checkpoint hash/loadability and exact artifact inventory from the publication contract.

Replay using the current task's configuration with original consumed files unavailable. Compare
source task/model links, source checkpoint/threshold resolution and paired selected-split
evaluation under the current comparison settings (test for the pipeline). Confirm temporary numbered YAML and
train_data_overrides.json never appear as artifacts. Exercise physical DDP only if sufficient
owned resources are available; otherwise record it as unverified, separate from simulated relay coverage.

## Evidence and cleanup

Record commands, task IDs, observations, failures and limitations in dated verification evidence under this feature. Stop/join task-owned consumers and clean only resources created by the acceptance run. Leave pre-existing services/data intact. No commit, push or release is part of this guide.
