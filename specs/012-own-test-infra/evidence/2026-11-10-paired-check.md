# Paired check, 2026-11-10

Command, run in this worktree as the repository documents the stage (Taskfile `paired-check`):

```bash
CY_QUEUE_DIR=/mnt/wsl/data/nkt/cy-queue uv run --locked task --exit-code paired-check
```

| Item | Value |
| --- | --- |
| clearml-yolo commit | `dc2760b` (recorded as `98a373d` before a message-only rewrite, same tree; branch `feat/own-test-infra`; `git diff master -- src tests pyproject.toml uv.lock` empty, so the code under test is master `f1a3755`) |
| cy-queue commit | `d3627a0` on `main`, `git status --short` empty before and after |
| Result | **failed**, exit 2 from pytest during collection. Before pytest, `uv pip check` and the editable-install and version-match check passed; after the failure the stage did not run `cy-queue --help` or its final version report |

Failure (verbatim, abridged to the error):

```text
ERROR collecting tests/test_batch_estimate_submission.py
tests/test_batch_estimate_submission.py:12: in <module>
    from clearml_yolo.adapters.storage.batch_sizes import BatchSizeStore
E   ModuleNotFoundError: No module named 'clearml_yolo.adapters.storage.batch_sizes'
Interrupted: 1 error during collection
```

Cause: cy-queue `d3627a0` imports `clearml_yolo.adapters.storage.batch_sizes`, which master does
not contain (`git ls-files src/clearml_yolo/adapters/storage | grep -c batch_sizes` gives 0).
The module exists only on the clearml-yolo branch `012-editable-batch-sizes` (`1268846`), which
is not merged into master. The failure is independent of this feature: this branch changes no
file under `src/`, and the failing step is an import of product code, not the test
environment.

An independent verifier's run of the narrower form `cd /mnt/wsl/data/nkt/cy-queue && uv run --frozen
--no-sync --project <worktree> pytest -q` failed by construction ("22 errors during
collection"): the worktree's development environment does not have cy-queue installed. That
form is not the paired check and is no longer specified (tasks T031, research R-11).

Rerun on the final tip of this fix (`266aac8`, recorded as `0af13e6` before a message-only
rewrite, same tree; it changes only `specs/`), cy-queue still `d3627a0` and clean: the same
collection error, exit 2.

Rerun later on 2026-11-10 on `6e1c2cf` (branch tip after the commit-message rewrite and the
session-adoption wiring; still no change outside `specs/`), same command, cy-queue `d3627a0`
with `git status --short` empty before and after: the same collection error on
`clearml_yolo.adapters.storage.batch_sizes`, exit 2. The narrower form above, run from the
cy-queue checkout with `--project <worktree>`, again failed by construction with 22 collection
errors, exit 2.

Status: the paired check is reported as **failed for a cause outside this feature**, not as
passed, until master gains `batch_sizes` or the owner decides otherwise (spec "Dependencies").
