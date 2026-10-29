# Preliminary CY and queue verification

Date: 2026-10-29. Feature: [local Russian reference](../spec.md).

This verifies the current working source pair before the feature release version
is selected. It is **not final proposed-version release acceptance**. Refresh and
recheck the pair after any source/version change required by integration or hooks.

## Source identity

Both SSH remotes were fetched successfully without changing branches or worktrees.
The fetched default branches match the respective local HEADs:

| Package | Local and fetched default-branch HEAD | Working source / installed version |
| --- | --- | --- |
| clearml-yolo | `0037059dcf8a8ed16582f256b98036480cabd842` (`master`) | `0.41.0` |
| cy-queue | `ae252ed8e633e7548180577739673ff0506e1c0c` (`main`) | `0.1.3` |

The latest fetched CY version tag is `v0.41.0`; the queue checkout has no version
tags. CY includes the uncommitted feature `007` and `008` changes. The queue already
contains unrelated `pyproject.toml` changes from `0.1.2` to `0.1.3` and a CY bound
from `<0.42` to `<0.43`, plus its compatibility assessment and submission regression
test. Those changes were inspected and preserved, not authored by this task.

The approved external dependency checkouts remain clean and unchanged:

- digital-metrics: `6e801be1564dce458294eb23592cc1aa0939c4d9`.
- report-generator: `d10aa395d08f738e92e04e076cee93b3a993bf8f`.

## Normal resolution and metadata

Ran from CY with the approved local sources available:

```bash
uv pip install --python .venv/bin/python -e . -e ../cy-queue
uv pip check --python .venv/bin/python
```

Normal dependency resolution succeeded without `--no-deps`: 243 packages resolved;
only the two local editable packages were reinstalled. The compatibility check
reported all installed packages compatible. No lockfile or dependency revision was
changed by these commands.

Read both source `pyproject.toml` files and installed distribution metadata. Versions
and normalized requirement sets match exactly. The installed queue requirement is
`clearml-yolo>=0.38,<0.43`, which contains the tested `0.41.0`. This does not replace
testing a later intended release version.

## Queue verification

Commands ran from the queue repository using CY's prepared environment, so queue
configuration remained authoritative:

```bash
uv run --frozen --no-sync --project ../clearml-yolo pytest -q
uv run --frozen --no-sync --project ../clearml-yolo ruff check .
uv run --frozen --no-sync --project ../clearml-yolo ruff format --check .
uv run --frozen --no-sync --project ../clearml-yolo mypy .
uv run --frozen --no-sync --project ../clearml-yolo lint-imports
uv run --frozen --no-sync --project ../clearml-yolo cy-queue --help
```

All commands passed. Pytest reported **518 passed, 7 deselected**, with 19 existing
hydra-zen/Pydantic deprecation warnings. Ruff accepted the source and formatting;
strict mypy reported no issues in 69 source files; import-linter kept both queue
contracts. Help exposed the expected configuration, submission, worker, monitoring,
recovery, archive and GPU operations.

The deselected opt-in physical tests are not claimed as passed. These checks do
not establish real GPU/NCCL, multiuser/NFS or ClearML publication outcomes. The
separate CY canonical/native verification remains owned by feature acceptance.
No worker, shared queue, GPU reservation, remote task or release was created or
modified by this verification task.
