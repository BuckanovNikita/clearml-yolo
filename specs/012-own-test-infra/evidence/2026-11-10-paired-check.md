# Paired check, 2026-11-10

Command, run in this worktree as the repository documents the stage (Taskfile `paired-check`):

```bash
CY_QUEUE_DIR=/mnt/wsl/data/nkt/cy-queue uv run --locked task --exit-code paired-check
```

| Item | Value |
| --- | --- |
| clearml-yolo commit | the tree of `98a373d` (branch `feat/own-test-infra`). The run was made on `dc2760b`, a commit with the identical tree that is not in this branch's history (a since-discarded message rewrite; it survives only on the local branch `backup/own-test-infra-rewritten`). `git diff master -- src tests pyproject.toml uv.lock` empty, so the code under test is master `f1a3755` |
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

Rerun on the tree of `0af13e6` (the run was made on `266aac8`, a commit with the identical tree
outside this branch's history, as above; it changes only `specs/`), cy-queue still `d3627a0`
and clean: the same collection error, exit 2.

Rerun later on 2026-11-10 on the tree of `2bb569c` (the session-adoption wiring; the run was
made on `6e1c2cf`, a commit with the identical tree outside this branch's history, as above;
still no change outside `specs/`), same command, cy-queue `d3627a0`
with `git status --short` empty before and after: the same collection error on
`clearml_yolo.adapters.storage.batch_sizes`, exit 2. The narrower form above, run from the
cy-queue checkout with `--project <worktree>`, again failed by construction with 22 collection
errors, exit 2.

Status of the runs above: **failed for a cause outside this feature**, not passed (spec
"Dependencies").

Correction, 2026-11-10: earlier text here cited `dc2760b`, `266aac8` and `6e1c2cf` as this
branch's commits after a commit-message rewrite. That rewrite is no longer in this history:
the branch was put back in line with the merge into `012-editable-batch-sizes`, so its commits
are `98a373d`, `0af13e6` and `2bb569c`, each with the same tree as the commit the run used
(checked with `git rev-parse <commit>^{tree}`). The commit message of `47aaabe`, which
recorded those hashes, still mentions the rewrite; it is left as written.

## Run with the batch-sizes work merged, 2026-11-10 22:56-22:59 (Moscow time)

The owner directed that this feature be built on `012-editable-batch-sizes`, which was merged
into this branch (merge commit `ca754b7`), so `clearml_yolo.adapters.storage.batch_sizes` is
present. Same command, run with `nice -n19`, `PYTEST_XDIST_AUTO_NUM_WORKERS=4` and
`OMP_NUM_THREADS=4` because the user was using the machine.

| Item | Value |
| --- | --- |
| clearml-yolo commit | `d09e60b` (branch `feat/own-test-infra`), version 0.47.0 |
| cy-queue commit | `d3627a0`, version 0.1.10; `git status --short` empty before and after; HEAD unchanged |
| Result | **passed**, exit 0: `uv pip check` compatible, editable-install and version checks passed, cy-queue's suite **527 passed, 7 deselected** in 116.8 s, `cy-queue --help` ran, final version report printed |
