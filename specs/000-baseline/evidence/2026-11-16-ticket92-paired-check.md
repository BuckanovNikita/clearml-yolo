# Ticket92: CPU-only CY/cy-queue compatibility preparation

The native `paired-check` passed for the accepted CY source and the current clean
queue checkout. This completes the compatibility prerequisite only; ticket92's
actual direct-versus-queued GPU, cancellation/recovery, reservation and independent
publication observations remain pending coordinator scheduling.

## Immutable pair

| Package | Source version | Git revision | Source checkout |
| --- | --- | --- | --- |
| clearml-yolo | 0.48.2 | `60b5c63aebd70fbe6329f6e0534bd1cccfc6832b` | `/mnt/wsl/data/nkt/.codex/worktrees/6140/clearml-yolo` |
| cy-queue | 0.1.10 | `d3627a0da85968429ddeaff4920c05825e6e05e2` | `/mnt/wsl/data/nkt/cy-queue` |

CY began and ended clean at detached HEAD, equal to local `master`. Queue began and
ended clean on local `main`, equal to that branch. The native check fetched queue
origin's default HEAD and tags; fetched HEAD equaled the tested queue revision.
CY remote references were not fetched during this bounded compatibility step;
the coordinator explicitly selected the accepted CY revision. This is neither a
release nor a claim that an unfetched CY remote has the same tip.

The native metadata checker verified both source versions against their installed
distribution metadata and required editable paths pointing to these exact
checkouts. Python was 3.12.13. No repository dependency, lockfile or upstream source
was changed, and the shared operational queue environment was not upgraded.

Input SHA-256 values:

| Input | SHA-256 |
| --- | --- |
| CY `pyproject.toml` | `c862794ac2164d82dbf8ff4dfa53b274cbd40d429261978b66bf4f3232904ba8` |
| CY `uv.lock` | `93d8365190c796529bff2b1ebe7951cef2f77ff290d19bb6645f3123ec115635` |
| CY `Taskfile.ops.yml` | `2782b6a99d763533074c6badf719ab9f135b680f3459646868ff4a52eebf4726` |
| CY `scripts/paired_metadata.py` | `690b8b1b0c6709d51dd8e30dd11366264163c95ea1c73dd4aca4a8529bb1f0c5` |
| Queue `pyproject.toml` | `8b675fe6455d531bb786f67b9a0b387b8861dd0a5a85e093670357884ad208bf` |

## Executed native procedure

Executed from the CY checkout above:

```bash
taskset -c 0,1 nice -n 19 env -u UV_PROJECT_ENVIRONMENT -u CY_QUEUE_CONFIG \
  CUDA_VISIBLE_DEVICES= CY_QUEUE_DIR=/mnt/wsl/data/nkt/cy-queue \
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  uv run --locked task --exit-code paired-check
```

The [retained native log](2026-11-16-ticket92-paired-check.txt) includes command
expansion, dependency resolution, check outputs and final source/version reports.
The command exited **0**.

- **Passed:** locked CY development-environment synchronization into a task-owned
  temporary environment, followed by normal editable queue dependency resolution.
- **Passed:** `uv pip check`, 284 installed packages compatible.
- **Passed:** editable source/version identity checks for both packages.
- **Passed:** queue Ruff check and format check; 78 files already formatted.
- **Passed:** queue mypy; no issues in 70 source files.
- **Passed:** queue import contracts; two kept, zero broken.
- **Passed:** routine queue suite; 527 passed, seven opt-in GPU cases deselected,
  19 warnings, 136.20 seconds. Warnings concern Hydra Zen's deprecated Pydantic
  `__fields__` use and did not fail checks.
- **Passed:** installed `cy-queue --help`.
- **Passed:** final native source-immutability checks for both repositories.
- **Not executed:** physical queued/direct GPU jobs, native training, queue daemon
  operation against the shared coordination root, live cancellation/recovery,
  multi-GPU or multiuser evidence, ClearML Agent scheduling and remote publication.
  Routine tests use controlled telemetry and owned temporary subprocess/storage
  fixtures; they do not establish those live outcomes.

## Cleanup and handoff

The native task created
`/mnt/wsl/data/nkt/.codex/worktrees/6140/clearml-yolo/.tmp/paired-check.AW8ImJ`
and removed it through its exit trap. A subsequent filesystem check confirmed it
absent. Process inspection found no remaining pairing task or process using that
environment. Source checkouts remained clean at the recorded revisions. The CY
worktree's prepared `.venv` remains available; shared caches and unrelated queue
state were preserved. No deployment, push, release or distribution deliverable was
created. Temporary editable-install build steps are part of source compatibility
installation, not release artifacts.

The coordinator was notified that the immutable worktree could be unfrozen after
the final checks and cleanup. Reuse this result only for the same relevant source,
version and dependency inputs; later changes require an applicability assessment.
