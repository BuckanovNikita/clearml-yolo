# Campaign repair verification

- Date: 2026-11-02.
- Assessment: [assessment.md](assessment.md).
- Fix: [fix.md](fix.md).
- Result: partial; all-failure/native acceptance and release remain blocked.

## Current status, 2026-11-03

- Tested latest sources: CY 84166d53 (0.44.8), queue 0139152c (0.1.7); final
  fetches confirmed both still match their default branches. Normal dependency
  resolution, source/installed versions/paths and final pip compatibility passed.
- Current canonical CPU verification passed: 4,709 passed, 30 skipped, 81
  deselected, with static/import checks and a stable-input success receipt.
- Sequential current queue verification passed: 582 passed, 7 deselected. Its
  static/import/help checks passed. Earlier cleanup failure and isolated replay
  are retained below; their cause is unconfirmed.
- Current exact 50,000-row/relationship parity and the observer fixture's
  CPU-only red/green negative control passed. Documentation checks passed.
- Fresh independent review accepted this partial source stage and current paired
  CPU evidence. Helper source v0.13.0 and verified skill rollout v0.13.1 are
  released; all three registered exports match the reviewed Git snapshot.
- Native matrix remains incomplete: 3 recovered, 5 numerical failures and one
  deadline unresolved, 11 not replayed. No GPU work occurred in this continuation.
  Original ledger/logs match retained snapshots; timers and Windows task remain
  disabled. No application commit or release was made. Prospective release-version
  pair checks remain for the eventual application delivery stage.

Earlier blocks below preserve dated intermediate observations. Their current-tense
pending/conflict statements are superseded by this summary and later checkpoints.
The earlier SIGILL did not recur in two complete resumed runs; its cause remains
unconfirmed, and no native-library repair is claimed.

## Earlier integration evidence (retained)

The initial paired integration used CY `73bb044` (0.44.7) and queue
`32bea01` (0.1.7). Its observations are retained in this section. Normal editable dependency resolution succeeded,
installed/source versions and module paths match, and pip check reported compatible
installed packages. No dependency source or locked revision was changed.

- Earlier queue integration suite: 582 passed, 7 deselected. Queue Ruff, format check,
  strict mypy and import contracts passed.
- Private campaign suite: 73 passed, including all 15 blocked-arm eligibility cases
  and forbidden-import negative cases. A real configured child probe confirmed the
  explicit 64 MiB SDK request limit and available GPU tooling.
- Numerical/result-export regressions: 11 passed independently. The final pure-API
  correction plus core/application effect checks: 13 passed.
- Exact old/current DataFrame parity passed on 50,000 retained prediction rows and
  full match/exclusion/background/threshold edge cases. Final latest-source profile:
  5.39 to 1.32 seconds on that sample, approximately 4.1x faster. This is scoped CPU
  evidence, not an end-to-end latency promise.
- Latest CY Ruff, mypy, Vulture and import checks passed. Its complete canonical CPU
  suite aborted with SIGILL at the existing concurrent asset-download test, matching
  an earlier initial-copy failure. No canonical success receipt exists. The unpatched
  latest-source CPU prefix through the asset module passed 3,406 tests, with 30
  skipped. This does not establish a cause for the patched process crash. Bounded controls did
  not reproduce SIGILL: row-only passed 3,406 tests; diagnostics-only passed
  3,409 with one failure in the native torchrun cancellation test because cleanup
  encountered unverifiable /proc access. Its finally block removed both owned
  ranks; their PIDs were absent afterward. The full-process crash remains
  unexplained; neither baseline status nor patch causality is established.
- Final documentation and local-link checks passed; final evidence changes are
  checked again before handover.
- [Independent review](review.md) accepted only the partial source changes.

## Native case outcomes

Three original technical cases have verified full-pipeline recovery attempts:
CoatingDet YOLOv10n, YOLOv10x and DEIMv2-s. They used original scientific settings,
including AMP, full validation/test populations and frozen source copies. Native
exit was zero, cgroup exit was verified, required artifacts/models were forced-
downloaded, and downloaded checkpoints reloaded with matching embedded identity/
vocabulary and local/remote CSV hashes. Model quality is not inferred from this:
the one-epoch YOLO runs retain zero AP50; DEIM scores remain exploratory.

YOLOv10n took 535.69 native seconds under its measured 780-second budget; YOLOv10x
used 525.60 seconds under a bounded 1,200-second pilot. Server readback confirmed
plots of about 26.5/25.7 MB, above the previous 15 MiB client limit. DEIMv2-s took
1,152.74 native seconds under a 1,200-second pilot, demonstrating that the previous
510-second budget was insufficient. Its native positive-infinity anchor-buffer
sentinel was verified against the exact invalid-anchor mask from the pinned source;
all other floating state was finite. No checkpoint values were substituted.

All four original YOLO numerical recipes reproduced NaN val/box_loss with AMP
unchanged. YOLO11x live model and EMA tensors remained finite before validation;
a GPU diagnostic located BatchNorm FP16 activation overflow beyond +/-65504
(correct FP32 diagnostic range about [-93596.54, 73430.04]). Diagnostic FP32 is not
an alternative accepted recipe. The other three YOLO causes are not independently
established by that observation. FCOS ResNet101-FPN reproduced nonfinite component
losses at batch 809, image ID 3902; its underlying cause remains unconfirmed.

Faster R-CNN ResNet50-FPN reached validation scoring but hit its 1,200-second native
pilot deadline, then exited under bounded cleanup. That is a censored timing failure,
not a recovered case or a complete sample for the measured-budget helper.

Current original-case matrix: 3 recovered, 5 numerical failures unresolved, 1 timeout
still unresolved, 11 not replayed. Blocked arms were tested for eligibility only;
operator interruption and eight pending original trials were excluded as agreed.

## Earlier verification failures retained

The initial working-tree view's release fixture inherited local tool.uv.sources
settings; the documented temporary-removal view made that fixture pass. The original
section was restored byte-exactly after checking; no dependency resolution was used
to alter its lock. One broad run aborted with SIGILL in the existing concurrent
asset-download test; the same test passed alone and its cause is unconfirmed.
Checking the remainder separately produced 1,287 passes and one CPU observer fixture
failure: lazy CUDA capability probing encountered a fake property object lacking
major. The isolated observer reproduces that failure. Neither split check is a
canonical suite pass.

A later initial-copy run completed with 4,500 passed, 30 skipped, 81 deselected and
two failures: the generic rename effect finding (corrected using set_axis and
verified by the existing effect checks), and an untouched direct-descendant cleanup
failure. These results are preserved, not hidden or labeled successful. Final
canonical verification now uses the latest clean source pair on CPU; real GPU
replays above remain separate evidence.

## Remaining acceptance and preservation

The requested 20-case native success matrix is incomplete and all five numerical
failures remain unresolved under strict original AMP. No release version is prepared;
the checked development pair is not prospective release-version acceptance. Missing
native outcomes are not inferred from unit tests or deadline increases.

Original ledger equality against its stopped snapshot and byte equality of every
original failed log against its retained copy were independently checked. Three
original timers and the Windows task remained disabled; all task-owned GPU units
were inactive after the replays. Existing services, unrelated workloads, weights
and history remain intact. No original outcome was rewritten.

Shared recovery skill source and restoration links were updated. Both hosts were
reviewed through registered mappings: WSL Claude intentionally shares the agents
skill directory; all three registered installed copies have unresolved drift. The
read-only maintenance synchronization check returned conflict for each, while source
frontmatter validation passed. No conflicting installed copy, host override or
host-managed file was replaced. Source release/export and fresh-host discovery
remain open gates, not claimed parity.

Scoped mutation configuration was inspected: changed row-export/diagnostic logic
and tests lie outside the selected mutation files/test selection, so no mutation
rerun was required. Portable usage guidance was inspected; unchanged public CLI,
configuration and artifact contracts need no companion skill edit.

The new numerical tests followed immediately by the complete asset-test module
passed 15 focused tests. This does not explain or repair the full-process SIGILL.
Final synchronization review found 12 task-scope differing files in each registered
export; all three maintenance states are conflicts. Source skill frontmatter is
valid. No export/apply transaction, source release, or host-managed configuration
change was performed. WSL Claude's shared agents-directory alias is intentional;
registered copy-content drift remains unresolved.

Final architecture acceptance validation returned exit 1 in both repositories:
CY requires canonical/full-native success; private source requires synchronization
without conflicts. These are expected gate rejections, not accepted delivery.
The final matrix is 3 recovered, 6 reproduced-unresolved and 11 not replayed.
No task code commit, tag, push, installed skill replacement or original campaign
restart was performed. Task-only patches and individual receipts remain in the
private evidence root.

## CPU-only continuation, 2026-11-02 evening

User permits no heavy load until 2026-11-03 01:00 Europe/Moscow. No test suite,
Torch/model diagnostic or native workload was started during this continuation.
The CPU observer fixture now explicitly reports no accelerator to prevent AdamW's
health probe from initializing CUDA against synthetic readiness properties. The
retained original failure trace establishes the failing path. Ruff and format
checks passed; the corrected runtime regression has not run. Fresh static review
found no actionable defect and explicitly retained that verification gap.

The earlier prefix controls did not preserve full collection: canonical pytest
imports later test modules before prefix execution. Collection-time interactions
therefore remain an open SIGILL hypothesis, not an established cause. A bounded
manual minimal-pair/full-collection probe is prepared outside the repository. It
forces CUDA invisible, limits native CPU thread pools, retains selected/collected
node IDs and enforces a finite deadline. Its time guard was exercised and refused
execution before the user deadline (exit 2); no pytest or Torch import occurred.
It has no timer or automatic trigger. Runtime probe behavior remains unverified.

The private source repository independently advanced to 0cbcdc3 / v0.12.1. Its
retained rollout receipt records all three registered exports at reviewed immutable
390c91a, with WSL Claude sharing the agents-directory alias. This supersedes the
earlier current-drift claim, while preserving the earlier failed observations.
Those exports deliberately exclude this task's uncommitted recovery changes. New
source release, exact-snapshot export and verification remain pending; an old-pin
check cannot establish rollout of the new code. No export or release was performed
by this continuation.

## Resumed CPU verification

The user explicitly permitted heavy CPU work before the former 01:00 boundary.
No GPU permission was inferred. The corrected CPU observer test passed in 5.72 s
with CUDA hidden. A full-default-collection minimal pair passed 2 tests, 4,816
deselected, in 7.35 s. Collection imports alone therefore did not reproduce SIGILL.
The native crash cause remains unconfirmed; canonical verification is running.
Fresh latest-source integration uses CY 84166d53 (0.44.8) and queue 0139152c
(0.1.7); final pair checks are retained externally. Development prerequisites
include pi-heif 1.4.0 provisioned before verification, following the existing
development guidance. No locked dependency or approved upstream source changed.

## Helper release and current-source parity

The private recovery helpers passed their complete offline gate and fresh
independent source review, were released as v0.13.0 (8cc95f0), and exported only
from that exact immutable Git snapshot. All three registered copies match the
reviewed fifty-three-file package. Scoped synchronization, host configuration
audit, owned-source validation and private architecture acceptance passed.
Transaction backups and the rollout receipt are retained privately; evidence
registry changes are committed in ab21887 / v0.13.1. Unrelated dirty automation
source and original campaign runtime/schedules were preserved. Fresh native host
sessions were not exercised; configuration/content checks remain static.

On current CY 0.44.8, exact original/current parity passed again for all fifty
thousand retained result rows and the full relationship/exclusion edge case.
The scoped profile measured 1.64 s under current concurrent load; the earlier
original baseline measured 5.39 s. This is scoped CPU evidence with different load,
not an end-to-end speed or accuracy claim.

Current queue 0.1.7 normal resolution, source/installed metadata, static/import/help
checks passed. Its first full run had 581 passed, 1 guardian-cleanup timeout and
7 deselected; that case passed in isolation. A sequential full rerun is pending;
the cause is unconfirmed, and isolated success is not full paired acceptance.

## Successful earlier-source canonical run and fixture negative control

The resumed canonical CPU run on CY 73bb044 / 0.44.7 completed with 4,707
passed, 30 skipped and 81 deselected in 1,128.21 s. Static/import checks and the
final input-stability check passed; an application success receipt exists. SIGILL
did not recur, but no causal runtime repair or root-cause claim follows.

To verify the observer fix without GPU access, an external diagnostic fixture
advertised an accelerator and rejected both stream access and CUDA lazy init.
The unchanged control test failed at AdamW's stream probe in 4.15 s; the corrected
current-source test passed in 2.12 s with the same diagnostic fixture. CUDA was
hidden for both. This confirms the original accelerator-probe failure path is
avoided while real CPU optimizer/EMA/hash checks execute. No project test selector
or contract was weakened.

Canonical verification on current CY 84166d53 / 0.44.8 is still in progress. Its
Ruff, strict mypy, Vulture and import checks passed. These current-source results
will replace the earlier-source receipt only after the full suite and stable
input snapshot pass. The earlier SIGILL evidence remains retained.

## Current-source canonical success, 2026-11-03

Current CY 84166d53 / 0.44.8 canonical CPU verification completed successfully:
4,709 passed, 30 skipped, 81 deselected, 178 warnings in 1,026.00 s. Ruff, strict
mypy, Vulture and all fifty-two import contracts passed. The final input-stability
check passed and the verifier wrote an application success receipt. No selection
flag reduced ordinary canonical acceptance; opt-in physical tests remained
deselected by the documented default. CUDA was hidden throughout.

Both complete resumed runs passed the former SIGILL location. The root cause of
the earlier aborts remains unconfirmed; no causally justified native-library change
was made. An isolated, locally extracted debugger was smoke-tested on /bin/true
for a future genuine recurrence; no global package installation or dependency
change was performed. A sequential current-pair queue rerun is now in progress.

## Final CPU and preservation reconciliation

Sequential current queue verification passed 582 tests with 7 deselected in
123.27 s. Final pip check found all 286 installed packages compatible. Fresh
review inspected the final log and accepted the paired CPU gate; the source-stage
verdict remains accepted with no actionable finding. Native twenty-case acceptance
and application release remain blocked, without a waiver from CPU success.

Final preservation checks matched the stopped ledger and all twenty-one copied
failed logs, confirmed the three original timers and Windows campaign task remain
disabled, and found no active task-owned GPU unit. Unrelated source and workloads
were preserved. Registered helper exports remain current at the reviewed release.

Final architecture acceptance validation passed for private helper source/rollout
and rejected application completion solely on the aggregate native-matrix check
(exit 1). All recorded CPU/source/docs/development-pair checks pass. No application
commit or release was made; its task-only patch and dated evidence are retained.

## Service-resilient continuation checks, 2026-11-03

The latest canonical run on unchanged current CY 84166d53 / 0.44.8 runtime
completed with 4,709 passed, 30 skipped and 81 deselected (178 warnings) in
1,123.79 s. Ruff, strict mypy, Vulture, all fifty-two import contracts and
input-stability verification passed. Separate documentation verification passed.
Current queue 0139152c / 0.1.7 passed its full suite: 582 passed, 7 deselected
(19 warnings) in 137.34 s. Fresh queue Ruff, formatting, mypy, import contracts
and CLI help checks all exited zero. These are development-pair checks, not
prospective release-version acceptance.

The requested three identical full-collection prefixes collected 4,820 tests and
selected 3,440 each. Two passed (3,410 passed, 30 skipped, 1,380 deselected); the
third genuinely recurred with SIGILL (exit 132) during concurrent model-asset
downloads and Python garbage collection. Python stacks are retained. Three
debugger attempts stopped on expected signals and did not capture a SIGILL
native instruction address. Another correctly configured, bounded debugger
replay is pending. Later canonical success does not establish a causal fix. No
native library or test selection was changed.

Guardian-death cleanup passed five sequential repetitions and five repetitions
with two bounded task-owned CPU workers. All thirty recorded child/guardian/rank
identities were absent afterward; both owned CPU workers exited during cleanup.
No shared process or service was stopped.

The original campaign ledger and all twenty-one retained failure logs still match
the stopped snapshots; all original campaign schedules remain disabled. Native
recovery and diagnostics use fresh attempts and preserve service waiting separately
from computation and readback. Private helper source v0.14.0 and its v0.14.1
rollout metadata are released; their 179-test source gate and exact registered
exports passed independent review. Application release remains gated on all twenty
original cases, architecture acceptance and unresolved runtime evidence.

Mutation scope was inspected: the task changes neither the configured mutation
targets (datasets, evaluation policy, export quality), their selected tests nor
mutation configuration. No additional mutation run is applicable to this diff.
The portable clearml-yolo usage skill was inspected again: public CLI, configuration,
artifacts and scientific settings are unchanged, and its preserved-settings/failure
classification guidance remains valid, so no portable skill edit is needed.

## Fault-only debugger followup, 2026-11-03

One additional bounded debugger replay used a signal configuration smoke-tested
to pass expected cancellation/pipe signals while stopping SIGILL, SIGSEGV and
SIGABRT. The unchanged full-collection prefix passed: 3,410 passed, 30 skipped,
1,380 deselected in 851.57 s. The inferior exited normally without a native fault
or core. GDB returned 1 because post-exit register/mapping queries require a live
inferior; this is not a pytest failure. All 375 sampled owned process identities
exited, and their inherited 128 MiB core limit was verified.

The genuine third-prefix SIGILL is still unexplained. The followup supplies
non-reproduction and ownership evidence, not a native instruction address or a
causal repair. No further debugger launch, library change or test-selection
weakening followed.

## Final CPU reconciliation after reboot, 2026-11-03

The restored source bases remain CY 84166d53 / 0.44.8 and queue 0139152c / 0.1.7.
Full source comparison covers all 343 CY and 33 queue runtime/metadata files, including
non-Python assets; all frozen current attempt manifests match. The post-restoration
source audit reports 14 strict accepted cases, five without ordinary final execution
and one ordinary attempted but unaccepted. Fifteen distinct cases have successful
recovery evidence overall. The original failed ledger has one additional interrupted
row outside the requested twenty; it remains excluded.

After restoration, all 52 import contracts passed, 12 focused numerical/result-row/CPU
observer regressions passed (4.34 s), and the exact released private campaign suite
passed 200 tests (16.67 s). Normal editable source/installed metadata match and pip
check reports 286 compatible packages. Lost temporary-path console shebangs initially
caused executable-not-found errors; regenerating scripts with the exact same tool
versions fixed invocation. No native training dependency changed. The earlier full
canonical 4,709-test and paired queue 582-test passes apply to byte-identical runtime
sources; they were not rerun merely to move the checkout.

Corrected independent YOLO controls completed for all four original numerical
cases, reproducing the exact prevalidation model/EMA/optimizer/scaler/RNG/input bytes
and invalid native losses. Each control's owned descendants exited. FCOS's native
convolution reference independently reproduces its 163-element overflow mask. These
are causal failure observations, not successful recoveries. Five ordinary final
numerical replays and the linked Faster50 replacement remain prepared, unlaunched.

Faster50's final attempt was interrupted by host reboot. Boot identity, absent old
unit/cgroup and vanished old queue pool establish prior descendant/lock cleanup.
No zero exit or complete native duration is inferred. The fresh linked attempt
retains the original 1,800-second pilot and scientific recipe. It will require fresh
service, source, dataset, ownership and budget admission in the next GPU window.

The private YOLO12n alias fix passed 200 campaign tests, 72 architecture checks,
30 environment tests, 33 maintenance tests, five shell checks and source/docs gates.
Source v0.14.2 plus metadata v0.14.3 and all three registered exports are verified.
CPU readback-only acceptance retained the original task/model/checkpoint identities
and native duration. There was no duplicate publication or native rerun.

All fifteen blocked dependencies were rechecked after reboot without executing arms.
Twelve have strict final-source baseline proof; the three Faster50 arms remain API
eligible against the older successful baseline but lack the stronger final proof.
Original ledger/image-manifest hashes and fresh CSV/initialization hashes were checked;
this final audit does not claim another complete image rehash, remote download or
checkpoint reload beyond each retained attempt's verified evidence.

The executable source gate checks report freshness and complete source equality.
The native gate requires twenty accepted original identities and must fail at 14/20.
Architecture acceptance must also fail on native-matrix and recurrent SIGILL checks.
A later passing debugger prefix does not resolve the SIGILL recurrence. No application
commit/tag/push or proposed-release-version acceptance is claimed.

Final executable source gate passed with zero problems; native gate exited 1 at
14/20 (15 ordinary cases attempted). Separate post-restoration docs verification
passed. Timing analysis includes fifteen complete successful current runs, excludes
failed/interrupted/diagnostic samples, preserves earlier measurements, and reports
service wait separately. Traced category intervals overlap and are not additive;
training envelopes are not pure GPU kernel durations.

Final preservation checks again matched the stopped ledger and all twenty-one
failure logs, confirmed all original schedules disabled, and found no task-owned
recovery unit/process active. All six pending native receipts remain prepared
without launch evidence. Six source-audit CPU tests passed after matrix reconciliation.
Fresh independent checkpoint review reproduced source gate success, native gate
failure at 14/20, and architecture rejection only on native and SIGILL gates.

## Current-source closure checkpoint, 2026-11-04

The seven task-owned application/test/document paths were ported byte-for-byte
from the preserved campaign repair checkout onto CY 0.45.0 (`8be76e4`). No
dependency, scientific settings, native library, installed environment or original
campaign record was modified. All historical verification above remains historical.
The resumed architecture record clears prior check/review outcomes so they cannot
stand in for current integrated acceptance.

The architecture planning validator passed. Focused tests selected the isolated
source explicitly with `PYTHONPATH="$PWD/src:$PWD/tests"`,
`PYTHONDONTWRITEBYTECODE=1`, `CUDA_VISIBLE_DEVICES=''` and `MPLBACKEND=Agg`, using
the existing prepared recovery interpreter without reinstalling packages:

```bash
"$CY_TEST_PYTHON" -m pytest -q \
  tests/test_architecture.py::test_actual_inner_layers_have_no_direct_effects \
  tests/test_result_export.py tests/test_campaign_numerics.py \
  tests/test_native_backend_ddp_harness.py::test_cpu_observer_tracks_real_updates_hashes_and_original_samples \
  --basetemp .tmp/campaign-focused -o cache_dir=.tmp/pytest-cache
```

The first invocation failed during all fourteen fixture setups because the owned
`.tmp` parent directory did not exist. Creating that directory corrected the
invocation; the unchanged selection then passed **14 tests in 7.05 seconds**.
This includes actual CPU optimizer/EMA/hash checks and inner-layer effect checks;
it does not establish native GPU outcomes or source/installed package pairing.

Ruff and strict mypy passed for the six changed Python files;
`git diff --check` passed. Mypy used the same explicit source selection and
prepared interpreter with an owned `.tmp/mypy` cache. The
document checker passed all five changed Markdown files with zero issues.
No current canonical suite, proposed-release pair, fresh independent final review,
GPU replay, full source audit or SIGILL repair is claimed by this bounded port.
The parent owns those acceptance gates on the final integrated revision.

## Current integrated verification — 2026-11-04

Preserved work was reconciled onto CY `8be76e4` (0.45.0); original dirty trees,
their index states and local overrides remain preserved. The integrated source
passed the canonical verifier with **4,790 passed, 30 skipped, 81 deselected**,
including architecture negative cases and CPU-DDP. Ruff, strict mypy, Vulture and
import contracts passed with unchanged-input success receipt
`application-106ddd8c9333425a8182c6d398a2d77b`. Documentation validation passed.

The proposed **CY 0.46.0 / cy-queue 0.1.9** pair resolved normally and passed
**583 tests, seven physical cases deselected**, metadata/dependency checks,
Ruff, strict mypy, import contracts and command help. Before/after source
inventories remained identical. These proposed versions supersede earlier candidate
identities in this dated continuation; no historical measurements are relabeled.

Fresh independent reviewer `integrated_source_review` inspected all 45 task-owned
changed/untracked files against the frozen pre-review inventory and returned SHIP
for source/architecture scope. Separate force, campaign and HF changes retain
individual records and native acceptance gates.

Portable skill source was reconciled against collection 0.7.3; static, link,
discovery, routing/example evaluation and fresh independent review passed. Its
force/HF guidance is explicitly unreleased. Publication remains separate.

Twenty attempts are prepared against the frozen proposed source using the reviewed,
pinned retained-baseline recovery path. Their original scientific recipes and
archived evidence remain unchanged. Preparation is not native success. The original
AMP numerical failures, twenty-case replay, current-source audit, CPU crash
investigation and final acceptance remain separate outstanding gates.


## Current CPU stability and prepared-source audit, 2026-11-05

The current CY 0.46.0 / queue 0.1.9 guardian-death check passed ten repetitions:
five sequential and five with two bounded owned CPU workers. Every repetition
passed and its observed owned descendants exited. No original assertion or
production source was changed.

Two complete current collection-prefix runs passed **3,491 tests with 30 skipped
and 1,380 deselected each**. Both used the same 4,901-item collection and 3,521-item
selected prefix; their collection identity is
`5c2f2af282ebbd9748ba89eac44e008b6e466306f531c6d557f3b36563eaabd3`.
The plain run took 797.53 seconds; the resumed fault-only debugger run took
782.57 seconds. The latter inferior exited normally without SIGILL, SIGSEGV or
SIGABRT. Its debugger wrapper returned one because post-exit diagnostic commands
had no live inferior; this is retained separately from the passing pytest outcome.

Two other attempts are explicitly excluded from acceptance: the first harness
used an overlong temporary path and hit the Unix socket path limit; it was stopped
and the task-owned path shortened. A later debugger attempt was interrupted at the
user's request to free resources until 02:00, after 1,358 test passes. The single
resumed debugger attempt began after that time. All 936 observed PID/birth identities
were verified dead; source and recorded interpreter/native dependency bytes remained
unchanged. The private CPU evidence report and its 105-file manifest preserve this
complete accounting, not only successful attempts.

The historical SIGILL remains **unresolved**. Its retained November 3 trace proves
an illegal-instruction exit (132) in a Python GC/ABC/Requests/asset-resolver path,
but contains no fault address, opcode or native fault stack. Earlier debugger
stops were expected signals, and subsequent non-reproduction cannot identify a
cause. Incident-time Linux and Windows event inspection found no relevant logged
hardware/trap/storage fault; absence of logs does not exclude those causes. No
causal source or dependency fix is claimed. The SIGILL acceptance gate remains open.

A fresh prelaunch audit passed all twenty prepared current-source attempts: full
frozen manifests, current runtime and installed versions, original baseline pins,
scientific recipes, data/initialization provenance and original OpenCV identity
match. The auditor correctly reports zero accepted native cases before execution.
The final audit must be repeated after native recovery. The separately reviewed
private helper source was released as v0.17.0; this does not establish application
native success or change its original AMP recipes.

## Current campaign continuation, 2026-11-05

The unchanged twenty-case source audit now reports **seven accepted cases**:
CoatingDet YOLOv10n, YOLOv10x, YOLO11x, DEIMv2-S, DEIMv2-X, RF-DETR Nano and
RF-DETR Large. Source and installed metadata remain CY 0.46.0 / cy-queue 0.1.9;
no runtime components, pinned inputs or receipts changed during that audit.
The full native gate remains incomplete. Four original AMP recipes failed
numerically; their failures and scientific settings are preserved.

Both DEIM attempts initially completed native execution and remote verification
but failed CPU checkpoint acceptance. The supplied source argument selected an
older campaign's manifest-managed archive outside the current managed source root;
validation therefore treated it as a Git checkout. A bounded CPU reproduction
failed at `git rev-parse`, while the same checkpoint loaded strictly and passed
finite-state checks with the byte-identical source under the current managed root.
Both source trees matched all 161 manifest-pinned files. No source, checkpoint,
dependency or scientific setting was changed.

Before recovery, original bookkeeping was preserved and every mapped retained
artifact replica was rechecked. The existing readback-only path then passed full
acceptance for S and X with only the source argument corrected. The helper reused
its previously successful remote verification and retained downloads; this retry
does not claim a new remote download. Both helper processes exited zero, and
their native exit and fence-release evidence remained verified.

The machine rebooted during Faster R-CNN ResNet50-FPN's later execution. Its
incomplete receipt has no verified native return code and remains unaccepted.
Different recorded/current boot identities establish that its old processes cannot
survive; they do not establish successful execution or a cause for the reboot.
The original receipt, driver journal and logs were preserved before continuation.
No interrupted result was rewritten as success.

Private dated evidence is retained under `resume-20261105-postboot`, including
the preservation recheck, separate DEIM command/result records, post-reboot
ownership observations and the complete twenty-case audit. This documentation
checkpoint changes no module interfaces, dependencies or effect ownership; the
existing architecture record's native and SIGILL acceptance gaps remain open.
