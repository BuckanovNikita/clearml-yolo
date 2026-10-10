# TRACE verification — 2026-10-10

## Implementation and parent checks

The supplied plan was implemented in dependency-aware waves: three read-only inventories,
then independent ClearML, FiftyOne and runtime/DDP work; storage, computation/rendering
and documentation followed. The parent owned shared tracing/ports/composition, workflow
instrumentation, architecture allowances, integration and verification. Agents did not
delegate. Global and project standing collaboration instructions were updated; the
relative CLAUDE.md symlink and exact local dependency overrides were preserved.

- Full `uv run --locked --no-sync pytest -q`: **1423 passed, 30 skipped**, 52 warnings,
  469.37 seconds. Includes actual two/four-rank native CPU DDP success and failure paths.
  Default skips cover opt-in database integration and unsupported reflink behavior;
  these are not claimed as passes. Native database acceptance below ran separately.
- Final focused integration selection: **135 passed**, four upstream warnings. This
  covers new tracing/domain/subprocess tests, architecture, ports, composition and
  comparison observability. Subsequent foundation refinements passed **13 tests**.
- Ruff: passed. Strict mypy: passed, 193 files. Import-linter: **27 contracts kept**.
  Core/application isolation remains; evaluation/FiftyOne may import observability.
- Parent inspected combined implementation diffs, including generator lifetimes, cache
  lock semantics, full inference-stream consumption, finalization and native cleanup.
- New failure injection reproduced and fixed a watchdog-start failure state leak.
  Successful SystemExit(0) now records DONE while preserving the exit exception.
  Snapshot suppression has a deterministic changed/unchanged-sequence test; live stacks
  may legitimately change when a blocked operation wakes.
- Independent review reproduced two further defects: a caller sink raising SystemExit
  could replace the application's exception, and overlapping threads could mix task IDs.
  Terminal emission while unwinding now isolates sink BaseExceptions; task identity uses scoped context with a PID
  guard, retaining explicit DDP thread context copying and resetting ownership after fork.
  Parent verification of these corrections passed **51 tests**, including success/failure/
  interruption preservation, concurrent task binding, actual DDP callback threads and fork
  recovery. Ruff, mypy and all 27 import contracts passed again.
- A second independent review caught real SIGINT/SIGTERM being swallowed by unconditional
  sink isolation. Six subprocess regressions reproduced it at START, DONE and command.return.
  Normal emission now propagates termination exceptions without replacing signal handlers;
  only an already-pending application exception has precedence over terminal sink failures.
  Parent verification passed **58 tests**, including those six real-signal cases; Ruff,
  strict mypy and Markdown/link/example validation passed on this corrected state.
- The runtime worker's final affected selection passed **147 tests**. Running one existing
  native-runtime restoration test alone before filesystem initialization exposes its prior
  environment-order assumption; the established full-suite order passes. No unrelated
  native-runtime behavior was changed to address that test-order limitation.
- Resource-boundary review then reproduced lock/task/DDP ownership gaps when a sink
  interrupted acquisition completion, plus original-error replacement in nested failure
  finalization. ExitStack now owns the FiftyOne lock and ClearML task before acquisition
  completion is emitted; DDP startup rolls back its thread and callbacks. Mandatory
  cleanup spans defer diagnostic-emission interruptions to the outer cleanup boundary,
  and active application exceptions retain precedence in nested finalizers. PID guards
  prevent inherited cleanup/task contexts from changing child-process behavior.
  Domain checks passed **87 ClearML tests** and **160 runtime/DDP tests**; the parent's
  final combined selection passed **267 tests**, with four upstream warnings, in
  45.23 seconds. Ruff, mypy (193 files), all 27 import contracts, and documentation
  validation passed again. The final source is frozen for native rerun and fresh review.

## Subprocess and diagnostic acceptance

Controlled tests accelerate only diagnostic intervals; production defaults remain
30/60 seconds. Tests establish heartbeat/stack output during blocked Loguru sinks,
intercepted stderr and stalled SDK closure, fork recovery, inert import after dependency
initialization, sequential thread/descriptor cleanup, exception identity, original results,
safe scalar contexts, grouping, active-thread priority, truncation and suppression.
All ten command helps expose a TRACE lifecycle without importing native SDKs.

## Real native acceptance

A task-owned synthetic dataset used eight disjoint train/val/test images, including
empty images, one native training epoch, 64-pixel images and 20 bootstrap iterations.
The CPU baseline and single-GPU candidate completed in 48.40 and 70.66 seconds. Fresh
ClearML server reads reported both tasks completed; every published artifact was forced
down from the server and hashed (11 CPU, 17 GPU). Exactly one best Output Model per task
was downloaded. Only the completed owned baseline was promoted to prod.

The GPU candidate performed paired current-test reinference with matching image membership
and conf/iou/imgsz/batch/device settings, comparison and both developer/business reports.
FiftyOne published eight samples with train/val/test native evaluations; all were loaded
again in a fresh interpreter. The parent independently checked 377 CPU and 437 GPU START
records against matching DONE records, with no dangling operation, and verified that
command.return followed actual native temporary-directory cleanup.

Real watchdog output identified plot saving and ClearML task closure. The GPU run emitted
a location-only stack snapshot with ten observed groups, eight emitted groups, twelve-frame
bounds and an explicit two-group truncation notice. This validates the diagnostic path;
it does not establish that the originally suspected remote hang is fixed.

The native worker cleaned its exact tagged ClearML project/tasks and verified zero remaining
objects, removed its single prefixed FiftyOne dataset and checked none remained, and removed
its owned local run directory. Pre-existing workloads and shared services were untouched.
Machine-specific commands, logs, IDs and artifact hashes are archived in the global
clearml-yolo environment skill's dated native evidence, outside this repository.

After the final lifecycle corrections, native acceptance was repeated against unchanged
hashes of all 103 source modules. CPU/GPU runs completed in **57.23/63.49 seconds**;
fresh terminal status, all **11/17 artifacts** and one best model per task were verified
again. Paired membership/settings, both reports and fresh-process FiftyOne persistence
passed. The parent independently verified **379 CPU / 440 GPU** balanced operations,
zero failed/interrupted or dangling operations, and native cleanup before command.return.
The final GPU watchdog captured task closure with parent_stage=clearml.task.terminal and
bounded stack output (ten observed groups, eight emitted, twelve frames, two omitted).
Both owned native/capture processes exited zero; exact tagged ClearML objects, the one
owned FiftyOne dataset and the owned local run were removed and checked. This final
rerun has a separate dated global evidence archive; no dependency/source changes occurred.

## Packaging and documentation

Wheel and sdist built successfully before release versioning. Each was installed non-editably
in a separate fresh venv, with import provenance proving the installed artifact was used.
Both passed all ten command helps and configuration generation, protected overwrite rejection,
and forced regeneration. Dependencies were explicitly reused from the approved existing
environment; this does not prove fresh-machine dependency resolution. No assets were uploaded.

Russian README and maintained English guides/contracts were updated. Focused Markdown
structure/local-link checks passed for five guides (127 links/anchors, 14 fenced blocks),
and Bash syntax/behavior preserved command statuses 0, 7 and 130, including simultaneous
command/tee failure. Feature documents and standing instruction links are checked separately
before commit: **12 Markdown files, 137 local links/anchors and 14 fenced blocks** passed.
No installed Spec Kit tooling, `.specify/` files or dependency revisions changed.

## Independent acceptance and release

The fresh final read-only reviewer returned **ship** after independently running **96 tests**
and an additional **13-case interruption matrix**, inspecting ownership, rollback, nested
cleanup deferral and context restoration. No blocking findings remained. Earlier findings
were reproduced, corrected and re-reviewed; the parent independently checked final native
source hashes, balanced events and cleanup ordering. Exact publication lockfiles for both
native campaigns were also confirmed absent within their removed task-owned run directories.

The feature commit passed every normal hook, including the full pytest gate. During
release preparation, remote master advanced to v0.21.1 with a separately validated
report-layout fix. The task-owned pending release attempt was stopped and archived,
then both histories were merged without replacing remote work. The sole source conflict
retained the incoming class-count formatting and existing TRACE scopes, adding an
aggregate class-count formatting span. Parent integration checks passed **77 tests**,
Ruff, mypy (194 files), and all 27 import contracts. This report-only integration follows
the native campaign above; native training/publication/lifecycle source was unchanged.
Six actual workbook-layout tests also passed with TRACE enabled; merged documentation
checks passed for 19 Markdown files and 158 links/anchors. A fresh merge reviewer compared
both parents, confirmed all incoming implementation and prior TRACE source was preserved,
independently passed the 77-test selection and returned **ship**.

The merged source commit `11e2d9d` passed all normal commit gates, including full pytest.
Automatic release preparation encountered the existing offline dependency-cache limitation
for digital-metrics. Documented recovery updated only the root package version in uv.lock;
the parent compared the complete parsed lock against the original baseline and confirmed
every dependency/source record was unchanged. No release tooling or hooks were bypassed.

Release commit `a1b225b1984f9ed4a6735b5b9128553fa17be27e` passed the normal release
commit checks and the separate all-files recovery validation, including full pytest,
Ruff, mypy, import-linter and the applicable formatting/configuration checks. The hook
created annotated tag **v0.22.0**. Both master and that tag were pushed atomically over
SSH on 2026-10-10; no package assets or registry publication were performed.

Wheel and sdist were built from an archive of that immutable release commit and installed
non-editably into separate fresh virtual environments. Both passed all ten command helps,
configuration generation, protected overwrite rejection and forced regeneration. Installed
version and tracing source hashes matched the archived release; the parent subsequently
verified that the annotated tag resolves to the tested commit and produces the identical
archive. Approved existing dependencies were reused, so fresh-machine dependency resolution
remains unverified. Task-owned packaging virtual environments were removed after checking
that no processes used them; distribution artifacts and verification evidence were retained.

The exact original local uv sources table was restored unstaged, the release contains no
local source overrides, and CLAUDE.md remains a relative symlink to AGENTS.md. The release
lock and recovery record were removed by the successful workflow. Physical multi-GPU
execution and the full historical product UI campaign were not performed for this
diagnostic feature; native CPU DDP and single-GPU execution are the applicable evidence.
