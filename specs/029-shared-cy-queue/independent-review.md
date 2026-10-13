# Independent review — 2026-10-13

## First integrated checkpoint

Two fresh-context read-only reviewers assessed the complete task-owned working tree
against revision `95f07e17f413c369dad6af7b801a540ac12fa756`, the feature requirements,
architecture record and parent check evidence. The queue reviewer owned queue policy,
persistence, ownership, recovery and CLI/TUI review. The execution reviewer owned
direct execution, containment, observability, native adapters and dependency contracts.
Both requested GPT-6.1 Sol with high effort; realized runtime settings are not observable.
Neither reviewer edited source or delegated further. GPU/ClearML workloads and process
fault tests were excluded while the native baseline was active.

Both verdicts were **fix-first**. No architectural rethink was requested.

| Finding | Independent evidence | Corrective work |
| --- | --- | --- |
| Fork-only direct children escaped cleanup | Real fork child absent from marker-only tree because Linux `/proc/environ` retains the initial exec environment | Replace marker-only scope with ancestry, preserved subreaper, positive Python fork birth provenance and protected existing helper branches; ambiguous unmarked adoption fails closed |
| Generated sibling paths could escape project | Provenance symlink overwrote an outside file; deterministic `.pending` symlink redirected CSV bytes and became canonical output | Validate generated leaves/result-publication routes; exclusive unique sibling temporary CSV; native YAML/manifests/training outputs checked |
| DDP consumer dispatched after shutdown timeout | Real blocking callback and two records: consumer remained alive and dispatched both after join deadline | Remove SDK effects from background consumer; retain live rank-zero scalar journal and bounded synchronous owner callback replay |
| Partial sweep validation | Invalid later IoU/q members, weights with training, and unsupported report keys composed successfully | Shared effect-free stage-key validation plus nested request/cross-field preflight before any manifest submission |
| Restrictive first-user umask excluded peers | Namespace created as 0600 under umask 077 despite shared sticky directory | Apply descriptor mode 0644 before publishing namespace metadata |

Parent regression evidence reproduced eight invalid-sweep failures, four generated-path
failures and one restrictive-umask failure before the corresponding fixes. Runtime
implementer reproduced three fork-only failures. Raw red and green logs remain in the
ignored verification directories. Corrections require renewed full verification,
installed-distribution checks and a fresh independent review; this first review is not
acceptance of the corrected source.

The reviewers separately retained the physical five-GPU, real two-user/two-host NFS,
original cuBLAS and intermittent CPU-DDP SIGILL acceptance gaps. Simulated UID and CPU
process tests do not close them. No release approval was given.

## Second integrated checkpoint

Fresh-context `queue_review_final` and `execution_review_final` again requested
GPT-6.1 Sol at high effort with bounded read-only ownership and no further delegation.
Both returned **fix-first** after independent reproductions:

- Native fraction/type checks were absent from sweep preflight: a later `conf=2.0`
  member composed despite rejection by the installed native parser.
- Real Hydra overwrote an external sentinel through a pre-existing generated
  `config.yaml` symlink and appended to an external log through an actual run-directory
  interpolation. The preflight used a placeholder runtime directory.
- A CPU Faster R-CNN checkpoint save overwrote an external sentinel through `best.pth`.
  Validating the native output directory alone did not validate generated leaves.

The reviewed checkpoint's full suite passed 2,212 tests with 30 skipped; corrected
whole-tree mypy passed 301 files, Ruff/Vulture passed, and all 43 import contracts were
kept. Fresh wheel and source-archive installed checks also passed at that checkpoint.
Those passes did not invalidate the independently reproduced failures.

After recording their verdicts, the two reviewers received exclusive implementation
handoffs. Their subsequent implementation results are not independent acceptance.
The queue correction adds shared effect-free native type/range checks and actionable
`auto_gpu` rejection; 26 red regressions preceded a focused 166-test green run. The
parent reproduced seven Hydra generated-file escapes and added per-job actual-route,
relative-log/chdir and sweep-manifest validation. The execution correction reproduced
12 native-output failures before adding a shared read-only output-tree check and
explicit generated checkpoint/metrics checks. Exact backend-to-filesystem import edges
retain negative tests for other storage dependencies.

The corrected source requires renewed parent verification and a different fresh
independent reviewer. Native target gaps and the original unresolved failures remain
open; neither review approved release.

## Third integrated checkpoint

After the 2,282-pass full suite, both new read-only reviewers returned **fix-first**.
`execution_acceptance_review` reproduced an external sweep-manifest overwrite when
Hydra mode came from `hydra.mode=MULTIRUN` or saved YAML instead of `-m`.
`queue_acceptance_review` reproduced ignored saved `hydra.sweeper.params`: an intended
two-job 1/2-epoch sweep became one 100-epoch snapshot. It also demonstrated unvalidated
top-level pipeline types (`skip_train=garbage`, integer input paths and split elements).
Neither reviewer found another concrete ownership, process, publication or import defect.

The parent reproduced thirteen failures, then consolidated mode resolution and native
BasicSweeper expansion into the shared effect-free `entrypoints.hydra.sweeps` module.
Direct preflight and queue snapshots now use the same effective mode, saved-parameter
expansion and CLI precedence. Strict top-level validation derives from the existing
`run_pipeline` signature; nested requests retain their separate target-aware validation.
A further four red cases cover saved legacy defaults, now rejected with migration guidance
before Hydra loads a removed group/plugin. Unsupported concurrent launcher/sweeper targets
are rejected explicitly rather than being validated under incorrect sequential semantics.

The first combined mode/type correction passed 132 focused tests and scoped mypy. New
independent acceptance remains required after parent integration. A real ClearML shutdown
timeout from the same checkpoint is investigated separately in native evidence; the SDK
reporter was observed alive through the timeout, so premature termination is unproven.

## Fourth integrated checkpoint

After parent verification passed 2,306 tests with 30 skips, fresh-context reviewers
`queue_final_review_4` and `execution_final_review_4` independently inspected the
corrected source. Both requested GPT-6.1 Sol/high, owned no writes and did not delegate.
Actual runtime model/effort remains unobservable. They avoided native SDK/GPU and
process-opacity probes during the physical acceptance run.

The queue verdict was **ship, software scope only**, with no blocking finding. It
independently passed 19 pure policy/composition tests (seven deselected), verified all
172 source hashes, and checked that a fresh direct pipeline import loads no queue,
Textual, NVML, Torch, Ultralytics or ClearML modules. Review-owned scratch was removed.
That verdict explicitly does not approve release or unavailable infrastructure gates.

The execution verdict was **fix-first** after a safe inert reproduction: generated
`native_outputs_candidate_test.zip` bypasses the output guard in
`adapters/storage/native_archive.py`. An existing contained symlink caused `ZipFile`
to truncate an external sentinel into an empty ZIP. This storage adapter is reached
by actual comparison execution. No other blocking finding was reported in its
execution, containment, observability, DDP and process-supervision scope.

The parent reproduced both the generated-leaf and direct-external-destination paths
with two failing regressions (`archive-containment-red.log`). T024 owns the scoped
containment correction and renewed execution review. The physical matrix preserves
its earlier source identity; production edits wait for a controlled boundary before
remaining native processes switch to the retained immutable source copy.

The same execution reviewer subsequently confirmed a separate failure-isolation
issue from the installed SDK and Hydra sources. Skipping unsafe `Task.close()` after
unacknowledged console delivery leaves ClearML's main-task singleton alive;
BasicLauncher continues later sweep members in the same process. A later matching
`Task.init()` returns that failed task despite `reuse_last_task_id=False`, allowing
configuration and artifacts to cross invocation boundaries. T025 owns an adapter
guard for incomplete owner shutdown. It must preserve the first error and refuse
later owner creation before SDK/workflow effects, without resetting private SDK
state or invoking an unsafe close. This investigation is not fresh acceptance.

## Fifth integrated checkpoint

After the parent full suite passed 2,348 tests with 30 skips and the frozen source
passed static, architecture, installed-distribution and documentation checks,
fresh read-only `queue_final_review_5` returned **ship, queue software scope only**.
It independently passed twelve pure policy/device-binding tests, checked all 172
source hashes and confirmed a fresh direct import loads no queue, Textual, NVML,
Torch, Ultralytics or ClearML. It found no blocking queue issue, including the new
owner-first guardian cancellation. External acceptance and live replay remained
explicitly outside release approval.

`execution_final_review_5` returned **fix-first** after a pure-fake reproduction
using a real Loguru sink with `catch=False`. A secondary publication/finalization
diagnostic raised through the owner cleanup path and replaced the original
computation error. The first error diagnostic already protected its caller; the
same protection must cover barrier, cleanup and final-console diagnostics. T032
owns this correction and renewed execution review. No further concrete defect
was found in its inspected direct/containment/capture/lifecycle scope.

Both agents were requested as GPT-6.1 Sol/high with bounded read-only ownership and
no delegation; runtime settings remain unobservable. They performed no SDK/GPU or
process-ownership fault probes while the immutable native replays were active.

## Sixth integrated checkpoint

After the final diagnostic-source suite passed 2,352 tests with 30 skips, fresh
read-only `execution_final_review_6` returned **fix-first**. It independently passed
the four T032 regressions, verified all 172 hashes and direct import isolation, and
found no further defect in the reviewed containment/capture/owner/SDK lifecycle
scope. It did reproduce a separate direct GPU-memory cleanup failure: a Loguru
`catch=False` sink replaced the original computation error, and a secondary
`KeyboardInterrupt` escaped the cleanup boundary's `except Exception`. T033 owns
this correction, including propagation when there is no original error.

The reviewer inspected the remaining task-owned secondary diagnostic sites and
TRACE's existing protection, without SDK/GPU/process fault probes, writes or
further delegation. GPT-6.1 Sol/high was requested; runtime settings are not
observable. Its finding does not invalidate the recorded preceding test passes
or establish unavailable native acceptance. A corrected source needs fresh review.

## Seventh integrated checkpoint and software acceptance

After the final full suite passed 2,363 tests with 30 skips, fresh read-only
`execution_final_review_7` returned **ship, execution/observability software scope**
with no blocking finding. It independently passed 18 cleanup/diagnostic regressions
and 104 architecture tests, verified all 172 final production hashes and the exact
three-file delta, and confirmed that a fresh direct import loads no queue, Textual,
NVML, Torch, Ultralytics or ClearML modules. It reviewed the full parent static,
distribution, documentation and native evidence without claiming to rerun them.

The shared observability helper owns diagnostic effects, session owns task lifecycle,
and direct cleanup preserves the primary error across ordinary failures, interrupts
and broken sinks/fallbacks. Without an earlier error, cleanup failures propagate.
The fifth queue review remains accepted because its implementation has not changed.
Together these verdicts accept the implemented software scope; they do not approve
release, unavailable native targets or the unresolved cuBLAS/SIGILL/model-ID causes.

GPT-6.1 Sol/high was requested with no write ownership and no further delegation;
runtime settings are unobservable. The reviewer performed no SDK initialization,
network/GPU/process fault probes, edits or commits.

## Release history reconciliation review

After the user requested release, fresh read-only `release_audit` inspected
`origin/master` and the local candidate. It returned **fix-first**: later v0.26.2
PID-reuse and stable-empty-scan safeguards were absent from the refactor's older
process-tree copy. The shipped regressions were also missing. T035 restores them
and requires new verification and independent review before publication. Earlier
reviews accurately describe their local snapshots but did not establish preservation
of those subsequently published upstream changes.

The reviewer accepted the task-branch/merge/master/release procedure and explicit
user-directed release with disclosed native gaps. It checked all 172 preceding
source hashes and performed no native/network/fault tests or repository edits.
Sol/high was requested; runtime settings remain unobservable.

## Reconciled release source review

Fresh read-only `release_reconciliation_review` returned **ship for reconciled
software scope**, with no blocking finding. It independently verified all 172
source hashes in manifest `845dfc7a03fd5ae9cbe859fcc8cff6bbf927af104ee89ad1f3db1212ccccc30d`,
the sole production-file delta, AST preservation of the upstream regressions and
exact/append-only preservation of the published bug records. It confirmed shared
stable-discovery and liveness handling preserves direct fork provenance, helper
exclusions, zombie reaping and bounded cleanup, with release only after proof.

It inspected the parent's focused, architecture and actual one-GPU cancellation
evidence. Planning validation passed; full architecture acceptance still fails only
on the recorded missing native matrix. No suites, native/network/process probes,
edits or delegation were performed by the reviewer. Sol/high was requested; actual
runtime settings are unobservable. Publication remains subject to normal hooks,
merge/source preservation and exact versioned-distribution checks.

The same reviewer confirmed the resolved merge index: all source/test bytes and
172 hashes matched, upstream records were preserved and only the root version
changed in dependency metadata. Parent version inspection subsequently found the
existing generator misgrouped the feature under v0.26.2 on that merge graph. The
unpublished attempt was stopped; the [release record](release-2026-10-13.md) records
a linear-history continuation with identical verified software bytes.
