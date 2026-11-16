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

## Local queued-execution preparation

The ignored handoff directory
`.tmp/verification-gap-closure/ticket92-plan-20261116/` contains `plan.md`,
`observer-handoff.md`, exact CLI argument arrays, source/input/environment hashes,
four private scenario requests, and the explicit `queue.toml`. No queue submission,
list operation, worker, GPU operation or service write was performed. Those live
operations remain deferred to the coordinator's serial GPU slot and review.

Native settings validation passed without creating state. The explicit config
selects campaign-owned metadata and durable user-state coordination at
`/mnt/wsl/data/nkt/.local/state/clearml-yolo/queue-coordination`. No existing host
binding was found. The first stateful queue command will establish one; preserve
that authoritative coordination resource after per-job cleanup. The config
initially retained the default 2 GiB startup occupancy ceiling. The coordinator
then explicitly approved 8.0 GiB for local startup admission, independently of
the campaign's 8 GiB free-memory requirement.

Prepared task-owned child instrumentation follows the queue's maintained native
acceptance hook pattern. It gates on the actual pipeline invocation, applies CY's
allocator reserve before model imports, retains fixed batch72/two epochs and
records optimizer observations. The separate external monitor records conservative
whole-device telemetry and calls native cancel/recover on timeout, interruption or
reserve failure. It neither submits jobs nor starts workers; the controller owns
those processes and must cancel if the monitor dies unexpectedly.

CPU-only preparation checks passed: Ruff/format, source compilation, monitor help,
all four private request validations, and an inherited-hook inertness check that
imported neither torch nor cy-queue. A deliberately invalid batch1 request against
the real pipeline startup exited86 before case creation or GPU/application
execution. Its temporary input was removed. These checks do not prove the new
observer's actual GPU runtime or any live queue lifecycle outcome.

| Prepared input | SHA-256 |
| --- | --- |
| `queue.toml` after approved occupancy adjustment | `005978ee9867764e2f1b704f678640a68ca3791cabd002bce8531bac74d51c3e` |
| `monitor_queue_case.py` | `6da91b3ff70eee3141168ba51c1e0f08b202404d885197b75a103ea71d778f4f` |
| `instrumentation/sitecustomize.py` | `71042f1757805b4261c2d5b182cabe0137afe875f9206345b6132ee29db03592` |
| `instrumentation/ticket92_child.py` | `7d47f3ef7fbc964d41f9d518bb03cd8597b29f5335f7fd97b3ac581dd09afd70` |
| `run_completed_case.py` | `da79ec617444ade7448c327e8086d90bf533560e4193e2cc14dc8a99c50c5d5e` |
| `admit_batch72.py` | `c05014e159f042c53fd9ab5e5f7dbfc450f3e65849f1ee6b0a324abcf3ce9033` |

The accepted ticket05 direct baseline has the same product/dependency content as
the paired CY revision. Reuse remains conditional on exact scientific-input,
fixture, initial-weight and allocation comparisons; historical capacity alone
does not admit a new batch72 run. Independent publication readback and lifecycle
fault/cleanup evidence remain required. No product or queue source changed for
this preparation, no task process remains running, and no distribution release
or persistent global user configuration was created.

The task-owned paired venv was subsequently prepared against managed CY
`c026a75148378240070c9a588f93eb19964719b7`, a documentation-only successor with
unchanged product/dependency inputs, and the same queue revision. Native editable
metadata checks and 284-package compatibility passed. The local
`environment-identity.json` retains installed package and source-file hashes;
native package identity is
`dc64b31bce77b4949514befb3b1e2dfcc1178b3272ffe2f216204b72175379d9`.
Documentation-only commits may continue while those relevant inputs stay fixed.

The completed-case controller's CPU-only `--prepare` passed native queue
composition and scientific-config comparison against the accepted direct
baseline, plus retained baseline and initial-weight digest checks. Its separate
session launch is gated by an explicit coordinator GPU-slot flag and has not run.
It will first require a fresh native ceiling-72 search and independent winner
confirmation, then own submission, monitor/worker handles, timeout, cancellation,
recovery and PID/start-time cleanup observations. Lower capacity or uncertain
admission prevents submission; no batch fallback or training retry is implemented.
Successful native execution remains pending independent publication/scientific
readback rather than being labelled accepted. Controller/admission help, source
compilation and all five script Ruff checks passed; live runtime remains deferred.

A subsequent controller review added lifecycle deadline admission before probing
and immediately before submission: require 4200/2400 seconds respectively, clamp
to the recorded creation plus48 hours, and reserve600 seconds for cleanup. A
SIGTERM/interrupted admission exits the owned pool before recording cleanup;
execution remains failed even when cleanup succeeds. Spawned process handles are
registered before fallible receipt writes, so cleanup retains ownership on errors.
Five-script Ruff/format, compilation/hashes and CPU-only composition passed again
on docs-only managed tip137079d, with unchanged native package identity. Final
read-only readiness at15:55:50Z found no completed case, launch receipt, queue
metadata, coordination directory or host binding. The exact proposed launch array
uses nice19/ionice class3 and two-thread OMP/MKL/OpenBLAS environments.
