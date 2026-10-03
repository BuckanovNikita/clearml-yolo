# GPU queue implementation verification — 2026-10-02

## Scope and outcome

The five model commands share atomic whole-GPU FIFO admission and fresh-process execution.
Deterministic tests cover concurrent fitting reservations, strict head blocking, liveness recovery,
external occupancy, telemetry errors, provenance, cancellation and Hydra context. Native
single-GPU training and a two-job BasicSweeper pipeline completed successfully. Physical multi-GPU
DDP/contraction and native Windows execution remain unverified; this is not release certification.
Machine-specific task records and logs are retained with the global environment skill.

## Repository checks

| Check | Observed result |
|---|---|
| `uv run --no-sync pytest -q` | 868 passed, 9 skipped, 4 existing hydra-zen/Pydantic warnings |
| Focused resource/queue/execution/supervision/launcher/pipeline suite after hardening | 148 passed, same 4 warnings |
| Later resource/supervision/launcher regression check | 101 passed, same 4 warnings |
| `uv run --no-sync ruff check .` | Passed |
| `uv run --no-sync mypy .` | Passed, 109 source files |
| `uv run --no-sync lint-imports` | 9 contracts kept, 0 broken |
| `uv build --wheel` | Passed |
| Import both packages from the extracted final wheel | Passed; imports resolved inside the artifact |
| Nine command configuration/help checks | Passed without creating tasks |
| `git diff --check` | Passed |

Two POSIX descendant-cancellation cases were added after full-suite collection and passed in the
focused checks. An additional fresh-worker test for `${hydra:runtime.output_dir}` passed separately. Subsequent production changes were checked in their affected suites. Nine skips
belong to opt-in database integration tests. No commit/release hooks ran; no commit or push was
requested. Local dependency-source overrides were preserved; external dependency revisions did not
change.

## Failures reproduced and repaired

- Concurrent registry writers failed immediately under the inherited zero timeout. A contention
  regression now verifies waiting for a short transaction lock.
- A fresh sweep worker rejected composed `hydra.env`; structured restoration now accepts the
  legitimate extension.
- A transported config resolved absolute Hydra interpolations from its payload envelope. The
  worker now detaches it into a separate root.
- The real launcher attempted to freeze readonly sweep settings. The narrow write context now
  preserves Hydra's readonly configuration contract afterward.
- Sweep results used the supervisor directory. A validated worker receipt now supplies actual
  status and working directory; missing/invalid receipts fail.
- Requested native device YAML drifted to execution ordinals. Invocation-scoped intent now
  preserves requested YAML alongside effective YAML and distinct ClearML scheduler fields.
- Cleanup could skip later jobs or leave descendants after their root exited. Cleanup aggregation,
  owned POSIX groups, Windows Job Objects and a private startup gate protect the boundary.
- Unsupported process telemetry appeared permanently busy. It now raises an actionable error;
  the disposable visibility probe also has a 30-second timeout.

## Native checks

Every invocation used explicit project name and tags, a task-owned workspace and the shared stand
through the environment skill. Synthetic CSV data contained four training, two validation and two
test images, with disjoint paths. Each image was annotated. Compilation and AMP were disabled,
image size was 64, batch was 2, workers were 0 and training lasted one epoch.

1. `cy-train` requested scalar `ultralytics.device=7`. Admission reserved one UUID and native training
   ran on child-local `0`. One ClearML task completed, native best-model upload/download validation
   succeeded and `ultralytics_requested.yaml` retained `device: 7`. Registry requests were empty
   after worker exit.
2. `cy --multirun ultralytics.seed=1,2` requested training device `7` and prediction device `8`.
   Metrics, reports, comparison and optional publication were disabled to isolate scheduling.
   The second ticket waited while the first ran training then prediction. It started after the
   first worker exited. Both jobs completed, each with one reused ClearML task, a verified best
   model and prediction table. Canonical run objects retained requested selectors `7`/`8`, effective
   selectors `[0]`/`[0]`, one reserved UUID and final phase `inference`. Registry requests were empty.

The first multirun attempt exposed the readonly sweep bug before creating a task; it was repaired
and the original command passed on rerun. A transient ClearML task reload error during the successful
run recovered without changing the stand. Tagged projects/tasks and local run directories were
removed after every attempt, with an empty tag-scoped listing confirmed.

Unavailable native gates: simultaneous physical multi-GPU jobs, multi-rank DDP teardown, real
N-to-one surplus release, native Windows Job Object execution and CPU-training/GPU-inference
handoff. Simulated inventory/subprocess tests cover their applicable logic but do not establish
those hardware outcomes. Full evaluation/baseline/report release acceptance was outside this
scheduler smoke scope.

## Documentation and review

Reviewed and updated the README, contract index/summary, filesystem guidance, native configuration
contracts, portable end-to-end prerequisites, feature artifacts and the approved narrow constitution
amendment. The implemented JSON schema and supported pipeline retention rule are documented.
Markdown fence/terminal-newline/whitespace checks and 92 local links/heading anchors passed across
20 changed Markdown files. All nine command configuration/help checks passed; device examples
were exercised by normalization tests and the native runs. A fresh independent read-only reviewer returned **ship**, with no blocking findings and approval
of scheduling requirement-quality items CHK001–CHK022. Physical multi-GPU and Windows limitations
remain open hardware gates. The final four-test Hydra launcher suite also passed.
