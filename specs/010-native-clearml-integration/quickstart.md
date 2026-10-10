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
source task/model links, role-marked Output Model/validation-CSV resolution and paired selected-split
evaluation under the current comparison settings (test for the pipeline). Confirm temporary numbered YAML and
train_data_overrides.json never appear as artifacts. Exercise physical DDP only if sufficient
owned resources are available; otherwise record it as unverified, separate from simulated relay coverage.

## Evidence and cleanup

Record commands, task IDs, observations, failures and limitations in dated verification evidence under this feature. Stop/join task-owned consumers and clean only resources created by the acceptance run. Leave pre-existing services/data intact. No commit, push or release is part of this guide.

## CPU distributed regression acceptance — 2026-10-10 amendment

The additive [specification](spec.md#cpu-distributed-verification-amendment--2026-10-10)
and [plan](plan.md#cpu-distributed-verification-amendment--2026-10-10) add a local
CPU/Gloo suite to the default repository and commit checks. Historical real-service
acceptance above remains a separate verification scope. Follow current
[development dependency setup](../../docs/development.md#external-dependencies)
for the existing environment; no new dependency or shared-service setup is needed
for this suite.

Prerequisites are Linux or WSL, the installed repository runtime and Torch
distributed with Gloo support. Unsupported platform/Gloo prerequisites may skip;
worker crashes, callback failures and native execution errors fail the tests.
The tests generate isolated local data and use random weights from the installed
YOLOv8n architecture YAML. No GPU, ClearML service, external dataset, network access
or pretrained-weight download is required.

```bash
uv run pytest -m ddp_cpu
uv run pytest tests/test_native_ddp_cpu.py
uv run pytest
```

The first two commands focus on the same CPU scenarios included by the last
command and the existing pytest commit hook. A success run uses real two-rank or
four-rank native training and validation. It verifies CPU/Gloo/DDP identity,
optimizer parameter changes, cross-rank equality and training-sampler partitions;
owner telemetry arrives once in order while training remains active. The owner
records one native best checkpoint locally and loads it for inference.

Rank-zero/nonzero-rank failures after epoch zero and owner callback failure must
fail without a successful final model record or surviving owned workers/descendants
or relay consumer. Each scenario has a 180-second deadline, a 30-second Gloo group
timeout and five seconds for graceful shutdown before owned-tree termination.
Existing relay unit cases still cover malformed journals, missing checkpoints and
duplicate owner events.

Local recording proves callback ownership and association with a real native
checkpoint. Accelerator launcher behavior, NCCL, AMP and ClearML upload/download
barriers require separate acceptance evidence. Record actual outcomes, skips,
failures and cleanup in `docs/evidence/2026-10-10-cpu-ddp.md`; preserve those limits.
The historical no-release scope above does not override the current task's explicit
completion authorization; follow the current development commit/release procedures.
