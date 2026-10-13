# Integration verification — 2026-10-13

## Status and source

Implementation, final-source software checks and available native checks are complete.
Fresh independent software reviews passed; required five-GPU and actual
multi-user/multi-host NFS acceptance is unavailable. This is not full native acceptance. The subsequent user-directed release
continuation and its explicit limitations are recorded in
[release-2026-10-13.md](release-2026-10-13.md). Sections below retain successive checkpoints;
[final software verification](#final-unwind-source-software-verification) records
the latest source and results.

The starting revision is `95f07e17f413c369dad6af7b801a540ac12fa756`. Existing
Ctrl+C implementation and untracked bug evidence were inspected and integrated,
not reset. Historical feature 026/v0.26.1 remains completed. The earlier runtime
baseline and unresolved native failures are preserved in
[baseline-2026-10-13.md](baseline-2026-10-13.md).

The parent inspected tracked differences and untracked additions. Task scope includes
the direct/queue split, generic descendant ownership, capture/publication/progress,
project write containment, CLI/TUI, packaging, configuration and executable contracts,
tests, maintained documentation and feature/bug evidence. Eight old scheduling/plugin
modules and their obsolete four-mode tests are removed; process cleanup, inventory,
force-device validation, cancellation and new queue failure tests retain relevant
coverage. Exact local dependency source overrides remain in the working tree; neither
external dependency source/revision was changed.

Raw checks remain under ignored `.tmp/cy029-checks`; installed artifacts and independent
environments remain under `.tmp/cy029-installed`. Native evidence stays under retained
project `runs` directories. These are local evidence, not release assets.

## Parent checks

Commands use the prepared locked environment with `uv run --frozen --no-sync` so
optional native packages are preserved.

| Check | Observed result | Local evidence |
| --- | --- | --- |
| Ruff `ruff check .` | Exit 0 | `ruff-final.log` |
| Strict mypy `mypy .` | Exit 0; 299 files | `mypy-final.log` |
| Vulture `vulture` | Exit 0 | `vulture-final.log` |
| Import-linter `lint-imports --no-cache` | Exit 0; 43 kept, zero broken | `imports-final.log` |
| Architecture and queue CLI composition | Exit 0; 114 tests | `parent-contracts.log` |
| Dedup and queue CLI follow-up | Exit 0; 35 passed, one skipped | `parent-final-scoped.log` |
| Test-fixture typing follow-up | Exit 0; 13 tests | `typing-fixtures.log` |
| Full stable-source suite | Exit 1; 2,177 passed, 30 skipped, one stale CLI expectation | `pytest-final.log` |
| Corrected dedup CLI contract | Exit 0; eight tests, scoped Ruff exit 0 | `dedup-cli-final.log`, `dedup-cli-ruff.log` |
| Markdown structure and local links | Exit 0; 26 changed files, 245 links at that checkpoint | `docs.log` |
| Working-tree whitespace `git diff --check` | Exit 0 at that checkpoint | Parent tool output |

The initial integration suite (`pytest-full.log`) had stale removed-control fixtures,
external-output assumptions, fake publication adapters and an in-flight module import;
its 57 failures and ten errors are retained, not counted as passing. Those fixtures
were reconciled with the approved contracts. The subsequent full suite's sole failure
expected an explicit dedup directory to bypass `CY_HOME`. Production correctly rejected
that write. The revised CLI tests verify an explicit contained directory and rejection
of an external directory without modifying the input bytes/inode or creating the
missing workspace. A fresh complete suite will follow native execution; process-opacity
fault tests are kept separate from physical cleanup checks to avoid cross-test interference.

Queue implementer verification: 40 tests passed in a unique retained basetemp, with
real process cancellation, repeated signals, detached children, concurrent guardians,
worker/guardian SIGKILL and uncertain cleanup. Scoped Ruff and mypy (17 files) passed.
These tests simulate inventories/identities and do not establish physical GPU or real
multi-user/NFS acceptance. Observability implementer verification: 290 tests passed,
including real file-descriptor child capture, partial output, publisher failures,
shutdown deadlines, original-exception preservation and quiet prediction. Fake SDK
publication proves protocol behavior, not remote visibility.

## Installed distribution and examples

Both distributions were built from a frozen source copy with the local
`tool.uv.sources` section removed only from that copy. All 171 application Python files
matched the working source by SHA-256. The repository's own `uv_build` backend produced
a wheel and source archive bearing the existing development version, 0.26.1; no version
bump or publication was performed.

Separate fresh environments installed the locked runtime dependencies and then the
wheel or source archive. The wheel environment has no Textual. The source-archive
environment includes the optional `queue-ui` extra. `verify_install.py` checked actual
package import locations inside those environments, all 12 console-command help paths,
all nine generated command configurations, all 15 model presets, overwrite protection,
removed legacy controls, explicit prediction verbosity and complete two-job sweep
snapshot composition. Guardian, snapshot runner, console publisher, mirror and GPU
probe modules are present; the retired Hydra queue plugin is absent. Both runs exited 0.

Logs: `build.log`, `wheel-environment.log`, `sdist-environment.log`, `install-wheel.log`,
`install-sdist.log`, `installed-wheel.log` and `installed-sdist.log` beneath
`.tmp/cy029-checks`. Source hashes and the executable installed-check harness are under
`.tmp/cy029-installed`. Hydra's existing automatic-schema matching deprecation warnings
were visible; no warning was converted into proof of future compatibility.

## Native acceptance and review

A separate investigator is performing actual single-GPU direct/queued eager/compiled
pipelines, independent remote reads during training, artifact downloads, prediction
comparison, forced termination and syscall write audit. Results will be reconciled
when complete. Source changes during those checks require a fresh source identity and
compatible new snapshots, rather than silently reusing old jobs.

Fresh read-only reviews were dispatched after parent integration and checks to
`queue_review` (queue/persistence/ownership/recovery/CLI) and `execution_review`
(direct execution, observability, containment, native adapters and contracts), each
requesting GPT-6.1 Sol at high effort and no further delegation. Runtime model settings
are not independently observable. Both initial verdicts were fix-first; reproduced findings and corrections are recorded in
[independent-review.md](independent-review.md). Renewed verification/review is required.

Required five-GPU hardware, two real Unix users on a shared NFS queue and two owning
hosts sharing that NFS are unavailable in the inspected environment. Their acceptance
is open. The original five-GPU cuBLAS failure has not been reproduced or diagnosed;
the CPU-DDP SIGILL is also unresolved despite successful isolated baseline checks.
Neither a passing retry nor queue refactoring is a root-cause fix. Release remains
blocked until the required acceptance gaps are closed.

## Review-driven corrections

The first review exposed missing validation at generated leaf paths, fork-only process
ownership, late DDP callback effects, nested sweep requests and namespace permissions.
The parent added failing regressions before fixing its owned paths. Expanded submission
validation uses the same pipeline stage-key contract, validates typed evaluation/model/
tracking/publication requests without invoking their SDKs, and rejects known cross-field
conflicts before committing a batch. Containment now includes prediction provenance,
result publication shards/manifests, native YAML and image manifests; atomic CSV writes
use private exclusive unique siblings. Namespace metadata receives explicit public-read
permissions before publication, independent of umask.

Parent follow-up: `review-parent-green.log` records 31 passing queue/containment tests;
`review-parent-regressions.log` records 157 passing storage, pipeline, model/replay,
configuration and ClearML result tests. Scoped Ruff and mypy passed. These results do
not replace the pending full suite and refreshed installed distributions.

Further submission regressions reproduced three accepted invalid native image-size,
prediction-batch and mode variants. Submission now runs the existing effect-free native
execution-settings validator as well. The refreshed queue-command scope passed 24 tests
(`review-queue-final.log`). Parent direct-descendant and architecture verification passed
112 tests (`review-direct-contracts.log`). Fork restoration fault injection also preserves
the original error when subreaper restoration or descriptor closure fails.

## Reviewed checkpoint and further corrections

`pytest-reviewed.log` completed with **2,212 passed, 30 skipped**, exit 0. Whole-tree
Ruff and Vulture passed; `imports-reviewed.log` recorded 43 kept contracts. The initial
`mypy-reviewed.log` found five typing errors in two new test files; the corrected
`mypy-reviewed-corrected.log` passed all 301 files. The fixes concern optional SDK
exports, serializer typing and typed subprocess fakes, with behavior retained.

Refreshed wheel/source-archive builds and separate fresh core/UI environments passed
`installed-wheel-reviewed.log` and `installed-sdist-reviewed.log`. Their frozen source
was superseded by the second review's native validation and Hydra/native containment
findings, recorded in [independent-review.md](independent-review.md). These checkpoint
passes therefore remain evidence, not final-source acceptance. Further build and full
regression checks will use another immutable snapshot.

## Corrected integrated source

All 171 application Python files were frozen again under the ignored installed-build
evidence directory and verified by SHA-256 against the working tree. Both fresh runtime
environments passed the installed harness on the rebuilt wheel/source archive:
`installed-wheel-integrated.log` and `installed-sdist-integrated.log`. The wheel excludes
Textual, while the source-archive environment includes the optional UI dependency.

Parent integrated regressions passed 231 tests (`review-final-integration.log`). The
separate architecture suite passed 104 tests, including negative cases that keep backend
storage exceptions limited to the containment helper (`architecture-integrated.log`).
Whole-tree Ruff, mypy (303 files) and Vulture passed their `*-integrated.log` checks;
`imports-review-corrected.log` recorded all 43 kept contracts. Documentation validation
reported 29 changed Markdown files and 249 local links with zero errors at this checkpoint.
The complete integrated suite is still running; native acceptance and new independent
review remain outstanding.

The complete corrected-source suite subsequently finished with **2,282 passed, 30 skipped,
56 warnings**, exit 0 in 532.09 seconds (`pytest-integrated.log`). All 171 production hashes
still matched the frozen build afterward. Real CPU/Gloo distributed cases were included;
this pass does not establish the cause of the previously observed intermittent SIGILL.
The native package identity for the next physical acceptance phase is
`7b899490fdc02b8c79445e11b2dfacbe7bccb795eff7258b09cef448b1cd1bf4`.

After this parent verification, two new fresh-context read-only reviewers were dispatched:
`queue_acceptance_review` and `execution_acceptance_review`, requesting GPT-6.1 Sol at high
effort, no edits and no further delegation. GPU, ClearML and process-fault probes remain
exclusive to the native investigator; their software review results are pending.

## Effective Hydra composition and shutdown budget amendment

The third review findings were reproduced before correction: thirteen failing mode/type
cases (`hydra-effective-red.log`) and four saved legacy-default cases
(`saved-legacy-red.log`). The shared Hydra composer now honors saved MULTIRUN mode,
BasicSweeper parameters and CLI precedence before either execution or submission.
The combined configuration/direct/queue/architecture follow-up passed 186 tests
(`hydra-composition-final.log`); the final mode/plugin-specific suite passed 16
(`hydra-mode-final.log`). These checks include real inert Hydra launch attempts against
external symlink sentinels.

Fresh wheel/source-archive environments then passed installed command/configuration
checks, all 172 application-file hashes and saved two-job sweep expansion
(`installed-wheel-composed.log`, `installed-sdist-composed.log`). The wheel omitted
Textual; the source-archive environment included the optional UI extra.

Actual native execution subsequently exposed an insufficient application finalization
budget. The real-SDK diagnostic on retained immutable source failed under the original
15-second budget after approximately 9.4 seconds before close, leaving only 5.6 seconds
for the SDK's second drain. Its separately labelled 60-second diagnostic completed:
approximately 9.4 seconds before close and 9.9 seconds in close. Verified process
evidence showed the legitimate SDK reporter remained excluded from native cleanup;
no native-tree child was signaled. Stacks identified the SDK reporter event wait, and
the installed SDK's `Task.close` explicitly calls another upload-waiting flush. Full
timings, process identities, tasks and traces belong to
[native-verification-2026-10-13.md](native-verification-2026-10-13.md).

The owner finalization budget is now 60 seconds to cover both drains, the required
publication barrier, model/readback and status work. This changes neither SDK settings
nor lifecycle ordering; the shorter publisher receipt waits remain. Deadline and
original-error regressions passed 99 tests (`sdk-budget-regression.log`). Whole-tree
Ruff, mypy (305 files), Vulture and all 43 import contracts passed the `*-sdk-budget.log`
checks. Markdown/local-link validation reported 29 changed files, 249 links and zero
errors at that checkpoint. The production change still requires native re-execution
without diagnostic overrides; a passing longer diagnostic is not full acceptance.

The resulting 172-file source is frozen as `candidate-source` with a SHA-256 manifest
under the retained installed-build evidence directory. The candidate full suite and
rebuilt distribution checks are in progress.

The candidate installed runs completed with exit 0 (`installed-wheel-candidate.log`,
`installed-sdist-candidate.log`). Both verify the complete 172-file manifest from the
installed package, twelve command helps, generated configurations/presets and saved
MULTIRUN parameters. The environments were freshly created for this composition
checkpoint, then the candidate artifacts replaced its earlier package; no repository
source is imported by the installed harness. The separate candidate architecture suite
passed 104 tests with five existing deprecation warnings (`architecture-candidate.log`).

The candidate full suite exited one: **2,304 passed, 30 skipped, one failed**, with
56 warnings in 552.27 seconds (`pytest-candidate.log`). The sole failure was actual
`torchrun` rank cancellation in `test_native_torchrun_ranks_do_not_escape_cancellation`.
The denied `/proc` PID, 508247, matches its retained rank-zero PID file. The old
`supervision._release_process_tree` stopped on the first inaccessible scan during
rank termination, unlike the guardian's bounded fresh-verification loop. This
observation does not justify ignoring permission errors or releasing uncertain claims.

T023 assigns only `supervision.py` and its cancellation regressions to the existing
runtime investigator, preserving the generic runtime/SDK separation and current
deadline. It requires deterministic transient and persistent denial evidence before
correction, then actual `torchrun` cancellation verification. GPU/SDK acceptance stays
paused while process-opacity tests run. The complete suite is not counted as passing.

T023 correction: supervision now retries a denied ownership scan until its existing
release deadline, signaling only positively owned processes. Its registrations remain
unmodified until a complete fresh scan proves cleanup. The runtime implementer reported
a deterministic failing regression before this change, then nine passing cancellation
checks including real detached `torchrun` ranks, repeated signals, PID reuse and an
unrelated nondumpable process. The permanent-denial test additionally verifies that
both ownership registrations remain and the unrelated process survives. Parent inspected
the implementation and tests; the complete suite is rerunning on this corrected source.
Only the existing generic supervision module and its regression file changed.

The runtime implementer did not persist separate command logs for T023. Its returned
tool transcript records the red command `uv run --frozen --no-sync pytest -q
tests/test_gpu_cancellation.py -k release_retries --basetemp
/tmp/cy029-supervision-red`: one failed, eight deselected in 0.10 seconds, with
`UnverifiableProcessTreeError` on PID 516124 during the first release scan. The green
command selected the complete same test file with `/tmp/cy029-supervision-green`: nine
passed in 17.21 seconds. Scoped Ruff/format and one-file mypy passed. These are reported
agent observations; the parent's retained full-suite log supplies independent regression
evidence after integration.

## Verified supervision candidate

The parent full suite on the corrected frozen source passed **2,306 tests, 30 skips,
56 warnings**, exit zero in 552.56 seconds (`pytest-supervision-candidate.log`). This
includes the previously failing real `torchrun` cancellation path, the new transient
denial regression, permanent opaque-process quarantine and native CPU/Gloo tests.
All 172 production hashes still match `supervision-source-manifest.json` afterward.
Its native package identity is
`2d3b90a79f774ce44a8320c2a71e3078ff661f5fd07509be34c66ce69693b624`.

Whole-tree Ruff, mypy (305 files), Vulture and 43 import contracts passed the
`*-supervision.log` checks. Rebuilt wheel and source archive passed the installed
172-file hashes, twelve command helps, nine command configurations, fifteen presets,
overwrite protection and CLI/saved two-job sweep examples in
`installed-wheel-supervision.log` and `installed-sdist-supervision.log`. Their core/UI
environments respectively exclude/include Textual. Markdown/local links passed with
29 changed files, 250 links and no errors at this checkpoint (`docs-supervision.log`).

Only after these parent checks, fresh-context read-only `queue_final_review_4` and
`execution_final_review_4` were dispatched with GPT-6.1 Sol/high requested, no write
ownership and no further delegation. Runtime settings remain unobservable. They cover
queue/core/storage/guardian/CLI and direct/containment/observability/native ownership
respectively. Process-opacity, native SDK and GPU probes are excluded during the
parallel physical acceptance run. Their verdicts and the new native results remain
pending; these software passes alone do not authorize release.

## Generated archive containment amendment

The fourth execution review's ZIP finding was independently reproduced by the parent:
`archive-containment-red.log` records two failures, covering an explicit external
destination and a generated archive symlink. Both external sentinels were opened by
the unguarded implementation. The corrected storage adapter validates its destination
and generated ZIP leaf with the existing project containment helper before opening.
Archive selection, sanitization and serialization are unchanged.

The combined containment, comparison assembly, trace-storage and architecture checks
passed **182 tests**, five existing warnings (`archive-containment-green.log`).
Whole-tree Ruff, mypy (305 files), Vulture and all 43 import contracts passed the
`*-archive.log` checks. The 172-file source is retained as `archive-source` with a
manifest under the installed-build evidence directory; only `native_archive.py` differs
from the preceding verified supervision source. Final full-suite and independent
execution review remain pending.

The physical matrix's direct and queued eager runs completed successfully before this
production edit. At a verified idle boundary the investigator reaped its worker and
orchestrator, then switched remaining native/control/guardian imports to the retained
source copy with the exact prior package identity. Those runs therefore establish
that recorded source, not execution of this later archive guard. The guard is verified
with actual filesystem/ZIP operations in the scoped regression suite; the matrix
comparison settings and archive payload code remain unchanged. Native evidence records
the exact source boundary.

Both archive-source distribution checks subsequently exited zero
(`installed-wheel-archive.log`, `installed-sdist-archive.log`), including every
installed production-file hash and saved sweep example. Documentation validation
passed with 29 changed files, 250 local links and zero errors (`docs-archive.log`).
T021 is closed by the corrected composition checks and fourth review's accepted queue
software scope; its separate archive finding belongs to T024. T023 is closed by the
parent full-suite verification of the native Torch cancellation failure path; broader
physical cancellation/forced-death acceptance remains under T015.

## Final failure-isolation amendments

Follow-up source review confirmed that an incomplete ClearML owner shutdown leaves
the SDK's main-task singleton available to a later sequential Hydra member. T025
owns an adapter-local guard before subsequent task creation, with successful close
as its release condition and no private SDK reset. The first failure must remain
primary; a subsequent member must not mutate its configuration or artifacts.

Actual normal queued cancellation on the retained native source released verified
process identities and capacity, but the guardian's immediate whole-tree TERM/KILL
also interrupted the publisher/reporter and DataLoader children. T026 adds bounded
owner-first cancellation before the existing complete descendant barrier. Physical
replay and complete remote-console readback remain necessary before accepting it.
The four passing direct/queued eager/compiled pipelines retain their exact earlier
source identity; later containment and failure-path changes are separately verified.

The user confirmed that no additional acceptance environment is available. Five
physical GPUs and actual two-user/two-host NFS checks therefore remain unavailable,
not passed. No release tag will be published while those required gates remain open.

The guardian red regression demonstrated a publisher already dead when owner
shutdown began (`guardian-grace-red.log`, one failure). Its corrected owner-first
path passed six focused process tests and three additional lifecycle selections;
parent verification combined the new tests with architecture checks and passed
107 tests, five warnings (`guardian-grace-parent.log`). These checks use ordinary
owned subprocesses, not opaque-process fault injection during physical acceptance.

The first actual publisher SIGSTOP and combined SIGKILL/computation-error cases
failed acceptance: required errors were retained locally, but remote tasks ended
`stopped` after ClearML's development monitor interpreted application-owned failure
as an external status change and killed its process tree. Source inspection of the
installed SDK's `DevWorker._daemon` and `Task._dev_mode_stop_task` corroborated the
observed diagnostic and transition. T027 records bounded owner-monitor shutdown
before failure publication, without SDK singleton reset. Passing ordinary runs do
not erase these retained failures; corrected actual fault replays remain required.

T025/T027 implementation retains a process-local incomplete-owner record across
failed initialization, unconfirmed close and forks. Only the exact owner PID/task
can release it after `Task.close()` returns and the SDK's inert public
`is_main_task()` confirms release. An interrupted or silently incomplete close is
never retried: installed SDK shutdown sets its exit flag before draining, so a
second `close()` can return without actually releasing the main task. Later Hydra
members fail before another task is initialized; successful closure still permits
ordinary sequential execution.

Failure cleanup unregisters only the current owner's development status monitor
before changing remote status. It detaches that task's exit callback and its
already-created reporter's separate unbounded drain callback when closure is
uncertain, without invoking lazy reporter construction or resetting SDK state.
The original credential-safe error diagnostic is emitted before the publisher
barrier, because Hydra prints its outer traceback after owner finalization. Local
original exceptions remain primary even if a diagnostic or cleanup operation fails.

The bounded implementation agent requested GPT-6.1 Sol/high, owned four exclusive
session/deadline/test-fixture files and did not delegate; runtime settings remain
unobservable. Red evidence includes nine retained-owner failures, three close-retry
failures, eight monitor/detachment failures, an exact reporter callback subprocess
timeout and one diagnostic-order failure. Its final checks passed 34 focused cases,
123 inert session tests (one offline SDK case intentionally deselected during native
work), 104 architecture tests and all 43 import contracts. Scoped Ruff, formatting
and mypy also passed. These are integration evidence, not independent acceptance.

The parent froze all 172 production files as `acceptance-source`. Exactly four
files differ from the native matrix's earlier supervision source: the archive
containment guard, queue guardian grace, ClearML session and deadline adapters.
Whole-tree Ruff, mypy (306 files), Vulture and 43 import contracts pass the
`*-acceptance.log` checks. The renewed full suite, installed distribution checks,
corrected actual fault replays and fresh final review remain in progress.

Available native evidence closes T013/T014: independent active-training reads
verified console and epoch scalars; a real two-rank CPU/Gloo owner observed four
epoch-zero metrics within 1.647 seconds while workers remained gated and alive.
This establishes live distributed relay/publication, not physical GPU DDP. Quiet
native prediction processed all 16 images with 80 nonempty detections matching
verbose native inference within `1e-6`, using the normal `conf=0.001` without a
fallback. Broader physical hardware acceptance remains under T015.

A bounded read-only SDK inspection found an additional independent exit path in
supported reporter thread mode (including SDK fallback after reporter subprocess
loss). Python logging shutdown closes the task's `TaskHandler`, whose separate
log sender joins its thread without a timeout while network retries may continue.
Detaching the reporter's callback does not stop this sender. The SDK handler clears
its own cached task/background references before that join, so closing exactly the
owner's existing handler under the application deadline makes subsequent logging
shutdown inert. T027 includes this final bounded-close correction; global logging
handlers, other task owners and SDK configuration remain untouched. The preceding
acceptance-source checks are retained as a checkpoint and require a renewed final
source check after this correction.

The pre-final full attempt (`pytest-acceptance.log`) ended with 2,343 passing tests,
30 skips, 56 warnings and two failures in 555.86 seconds. One test incorrectly
required exactly one idempotent callback-unregister call; the other watchdog stub
returned an unconstrained truthy Mock from the newly required `is_main_task()`
closure check. The first retained its deadline and original exception correctly;
the second simulated an unclosed owner. Parent corrections keep the assertions
about exact callback ownership and actual watchdog closure while supplying the
stub's explicit closed state. The entire deadline file then passed nine tests,
and the original watchdog test passed (`deadline-integration-green.log`,
`watchdog-integration-green.log`). That attempt is not final-source acceptance.

The exact-owner log-handler join correction was separately reproduced by two
failing tests, including a subprocess unable to exit through `logging.shutdown`.
After correction, the implementation agent passed 37 focused regressions and
126 inert session tests, with the offline SDK case deferred to the full suite.
Only the incomplete owner's cached handler is closed, after status handling and
before publisher EOF, under a separate deadline. A swallowed SDK join alarm is
not reused for another network call, and returning does not claim daemon cleanup.
The owner guard remains set until a fresh process is used.

The parent froze the corrected 172-file source as `closure-source`; all production
hashes still match. Whole-tree Ruff, mypy (306 files), Vulture and 43 import contracts
passed. Both rebuilt distribution checks passed installed source hashes, all twelve
command helps, nine command configurations, fifteen model presets, overwrite
protection and two-job CLI/saved-sweep composition. Core/UI environments respectively
exclude/include Textual. Evidence is in `*-closure.log`.

Spec Kit convergence reviewed the 18 functional requirements, three scenario groups,
the aggregate success criteria, six planned module boundaries and five constitution
principles, respecting the explicit approved changes to historical scheduler policy.
It appended T028-T031 for unavailable infrastructure, corrected live failure replays,
remaining final gates and a document-only state-label discrepancy. The data model
now matches implemented `completed`; Markdown/local links passed with 29 changed
files, 250 local links and zero errors. No installed workflow file was changed.

## Final software checkpoint

`pytest-closure.log` records **2,348 passed, 30 skipped, 56 warnings**, exit zero
in 558.98 seconds. This full run includes the offline SDK test deferred by the
bounded implementation agent, native CPU/DDP, transient process visibility,
guardian grace, all owner/exit regressions and the corrected watchdog fixture.
All 172 production hashes still match `closure-source-manifest.json` afterward.
Whole-tree Ruff, mypy (306 files), Vulture, 43 import contracts, both installed
distribution/example checks and documentation validation also passed on this
source. Required unavailable target checks are not included in those passes.

Only after these parent checks, fresh-context `queue_final_review_5` and
`execution_final_review_5` received bounded read-only review tasks with GPT-6.1
Sol/high requested, no write ownership and no further delegation. Actual runtime
settings remain unobservable. Their scopes cover the complete queue/guardian/
composition integration and direct/containment/publication/SDK ownership respectively.
They avoid native SDK/GPU and process-opacity tests during corrected live replays.
Their final verdicts and live replay evidence remain pending.

## Secondary diagnostic failure correction (T032)

The fifth execution review found that secondary diagnostic emission could replace
the original error. Four parent regressions using a real Loguru sink with
`catch=False` reproduced this at the console barrier, SDK failure finalization,
console finish and failed-status update (`secondary-diagnostic-red.log`). The
session now shares a protected diagnostic helper across these branches, original
failure reporting and incomplete-handler cleanup. It retains credential-safe
formatting and emits a fixed local fallback if a sink raises; neither diagnostic
failure can replace the exception already being handled.

After correction, 130 inert session tests passed with one offline SDK case reserved
for the full suite (`secondary-diagnostic-green-final.log`). Tests verify the
original exception object's identity, failed status where possible, publisher
finish, signal/environment restoration and owner-context release. No additional
module or dependency edge was introduced. The final production source is frozen
as `diagnostic-source` (172 files); only this diagnostic guard differs from the
immutable `closure-source` used by the corrected native failure replays. Native
results retain their exact source identity and do not cover the injected broken
Loguru sink, which is covered by these regressions. Final gates are being renewed.

Whole-tree Ruff, mypy (306 files), Vulture and all 43 import contracts passed
against the diagnostic source. Rebuilt wheel and source distributions each passed
all 172 source hashes, twelve command helps, nine generated configurations, fifteen
model presets, overwrite protection and two-job CLI/saved-sweep expansion. The core
installation has no Textual; the UI installation has the extra. Changed Markdown
and local links pass (29 files, 250 links). Evidence is in `*-diagnostic.log`.
The full suite starts only after all native fault replay processes are reaped.

Available native verification and cleanup have finished; see the detailed
[native record](native-verification-2026-10-13.md). Four matched one-GPU
direct/queued eager/compiled pipelines completed and produced numerically equal
prediction tables. The separate corrected cancellation published its original
signal diagnostic before releasing capacity. Corrected stopped/killed publisher
cases reached failed status with bounded owner exit and retained local originals;
a stopped channel cannot deliver its final remote console messages. Two genuine
SDK owners closed sequentially with distinct task IDs.

The corrected stopped-publisher run also reproduced the earlier SDK model-ID error
on eager execution. A distinct publisher-only replay completed pipeline work and
failed only at its required console barrier. Both are retained, so successful
replays do not erase the independent model-publication failure. Exact source
identities distinguish the main matrix, these corrected native replays and the
last diagnostic-only change.

Parent inspection of `final-process-cleanup-proof.json` and
`final-queue-cleanup-proof.json` confirms the investigator checked 307 recorded
PID/birth identities and six SDK child birth identities, found all eight queue
jobs terminal and no owned GPU claim remaining. Exact-tag remote cleanup listed
zero projects and tasks afterward; local evidence, downloaded artifacts and SDK
caches were retained. No shared service or pre-existing workload was changed.
T022/T025-T027/T029 are reconciled against this available evidence; unavailable
five-GPU and actual two-user/two-host NFS gates remain open.

## Final diagnostic-source software verification

The final full command, `uv run --frozen --no-sync pytest -ra --basetemp
.tmp/cy029-checks/pytest-diagnostic`, exited zero: **2,352 passed, 30 skipped,
56 warnings in 567.19 seconds** (`pytest-diagnostic.log`). It includes actual
CPU/DDP, process-failure, offline SDK, architecture and all four real broken-sink
regressions. Skipped optional/isolated integration cases are not counted as passing.
All 172 production hashes still match the installed diagnostic source; only
`adapters/clearml/session.py` differs from the corrected native replay source.
The final manifest SHA-256 is
`3f04013c947d990da82bc0cb696ce461ac8bb7366b9c8e6a635b568cd60765f8`.
Markdown and local links pass with 29 changed files and 252 links after native and
Ctrl+C evidence reconciliation. Fresh execution review follows these parent checks;
the fifth queue review remains applicable because its production scope is unchanged.

## Direct cleanup diagnostic correction (T033)

The sixth review reproduced two related direct-memory cleanup defects. The parent
retained a first interrupted red run, then captured all cases with explicit
`BaseException` assertion handling: five failures and four passes in
`direct-unwind-red-complete.log`. A cleanup `KeyboardInterrupt`/`SystemExit` or a
broken Loguru sink could replace an already-unwinding computation error. With no
primary error, the original cleanup failure already propagated correctly.

The direct cleanup boundary now catches secondary `BaseException` values only to
preserve an existing primary; otherwise it re-raises them unchanged. Session and
direct cleanup share protected diagnostic emission in the existing observability
adapter. Ordinary diagnostic emission retains its existing interruption behavior.
The session snapshots its task ID before yielding to computation, avoiding opaque
SDK identifier access while assembling later failure diagnostics. Two additional
regressions preserve the original even when both the sink and FD fallback fail.

The first integrated focused run passed 222 tests and failed five monitor tests
whose mock targeted the old session-local diagnostic binding; actual original
errors and cleanup were preserved. Their assertions remain intact and now observe
the shared diagnostic adapter. The renewed final source is frozen as `unwind-source`
(172 files); this correction does not change native computation settings or queue
allocation behavior. The native source scopes and unavailable acceptance gates
remain as previously recorded.

After the mock-binding correction, the focused direct/session/diagnostic/TRACE
suite passed **229 tests** (`direct-unwind-green-final.log`). Full final-source
verification has started; all 172 production hashes still match the built source.

Whole-tree Ruff, mypy (306 files), Vulture and all 43 import contracts passed for
`unwind-source`. Rebuilt wheel/source distributions passed 172 installed source
hashes, twelve command helps, nine configurations, fifteen model presets and both
CLI/saved-sweep expansion checks, with Textual absent/present as intended. Updated
diagnostics guidance and all changed Markdown/local links pass. Logs use the
`*-unwind.log` suffix (`mypy-unwind-final.log` and `ruff-unwind-final.log` include
the corrected test-only monkeypatch typing). No SDK or GPU run was repeated for
this diagnostic-only boundary correction.

## Final unwind-source software verification

The full `uv run --frozen --no-sync pytest -ra --basetemp
.tmp/cy029-checks/pytest-unwind` command exited zero: **2,363 passed, 30 skipped,
56 warnings in 573.11 seconds** (`pytest-unwind.log`). The eleven new cleanup
regressions are included, together with offline SDK, native CPU/DDP, process
failure, architecture and preceding publication tests. Optional FiftyOne and
unsupported reflink cases remain skipped, not passed. All 172 production hashes
match the frozen and installed `unwind-source`; the manifest SHA-256 is
`77a1ecd56f9970982f74bfced8d6bb52c44497addd4ce769692feea53fbc95e9`.
Only session, observability diagnostics and direct Hydra cleanup changed since
the preceding final software checkpoint. No queue implementation changed.

## Final acceptance and release decision

The seventh fresh execution review returned **ship, software scope**, independently
passing 18 cleanup regressions and 104 architecture tests and verifying final source
hashes and direct import isolation. The fifth queue review remains valid for the
unchanged queue implementation. Their detailed findings, corrections and limits are
retained in [independent review](independent-review.md).

All available implementation, verification, native readback, cleanup and documentation
work is complete. Required five-GPU and real two-user/two-host NFS acceptance is
unavailable, confirmed by the user. The original cuBLAS and intermittent CPU-DDP
SIGILL causes remain unresolved; the independent ClearML missing-model-ID failure
reproduced during corrected native testing and remains unresolved too. These limits
block full acceptance and release. No commit, tag, push, package publication or
GitHub Release was performed. Retained local evidence is intentional; task-owned
active processes, queue reservations and tagged remote resources were cleaned up.

The architecture record passes planning validation. Final acceptance validation
exits **1** solely at `checks[4].result.status: acceptance requires passed`: this
is the declared unavailable native matrix, not an import/review failure. The raw
result is retained in `architecture-acceptance-unwind.log`; it is not reported as
a passing gate. The ledger keeps T019's full acceptance and T020 release open.
