# Forced selection and readable admission — 2026-10-12

## Scope and reproduced behavior

FR-011–015 implement strict force policy, protected concrete device choices, sequential
forced sweeps and readable admission decisions. The reported eight-card memory sample
(1215, 3, 409, 3, 3, 3, 3, 3 MiB) admits five through the inventory and empty queue.
Live reservation/FIFO fixtures explain waits and admit after release. The user's
actual waiting run was not inspected, so its cause remains unconfirmed.

Initial force tests failed for the absent policy and selector helpers; initial
admission tests failed for the absent diagnostics/visibility API. Inventory regressions
failed before hidden-card scoping was implemented. Integration caught and fixed an
unconditional force-selector check affecting ordinary automatic mode, and updated
fake inventory interfaces/default-policy expectations.

## Executed checks

Commands use `uv run --frozen --no-sync` to preserve the prepared environment.

- GPU/launcher/controls/force/decision/memory-wiring/direct suite: 283 passed before
  final presentation placement and added blocked-queue regressions.
- Post-integration direct/force/decision/wait/execution/wiring checks: 100 passed.
- Final decision suite, including real inventory on the supplied five-of-eight sample:
  8 passed. Required-device failures, hidden memory/MIG, threshold equality, reordered
  indexes, simultaneous reservation/memory reasons, FIFO, detached sample and refresh
  behavior have deterministic coverage.
- `ruff check .`: passed. `mypy .`: no issues in 283 source files. `vulture`: passed.
- `lint-imports`: 40 kept, zero broken. `pytest tests/test_architecture.py`: 94 passed.
  Negative cases include injected forbidden dependencies, mutated actual import
  graphs, core effects, dynamic targets, helper cycles and unclassified modules.
- `cy-init-config` plus `--cfg job`: all six model/export commands export force=false
  and compose concrete force overrides. The documented five-GPU example composes.
- MarkdownIt parsed 10 changed Markdown files and checked 188 local links/anchors.
  Final evidence/task edits receive a final documentation/whitespace check.

The full suite passed 2255 tests with 30 skips and 56 warnings before the final
selector-normalization correction. After that correction, the complete affected
GPU/launcher/force/decision/wiring/direct/model-scheduling selection passed 345
tests; Ruff, mypy (283 files), Vulture, all 40 import contracts and all 94
architecture tests passed again.

## Architecture and ownership

Core validates strict force and concrete selectors; adapters own NVML, isolated CUDA
metadata, telemetry scoping and locked registry effects. Immutable diagnostics are
created from the admission sample and registry transaction; Hydra formats/logs after
lock release. Direct waiting accepts a callback; it does not import entrypoints.
The existing launcher consumes effective controls and retains its implementation.

Planning record validation passed before implementation. The task-owned diff preserves
pre-existing static-analysis changes in `.pre-commit-config.yaml`, `pyproject.toml`,
`uv.lock`, `docs/development.md`, `docs/static-analysis.md`, feature 026 and existing
test cleanups. Only the new force-default expectations in `test_gpu_memory_wiring.py`
and admission changes in `gpu_queue.py` belong to this task; their initial edits
remain separately owned. No dependency reference or upstream source changed.

## Deferred follow-ups

Forced-kill orphan recovery and permission-denied process inspection require separate
reproduction/lifecycle work. Physical multi-GPU/DDP and MPS execution are not established
by synthetic inventory tests or single-device native execution.

## Native execution and publication limitation

Using the repository end-to-end skill and tag-scoped environment workflow, controlled
random-checkpoint prediction on two small synthetic images completed on CPU and one
CUDA GPU. A two-job forced GPU confidence sweep completed sequentially in one process
with separate invocation-owned tasks. Each successful invocation logged required
`gt_csv` and `predicts_csv` uploads, kept inherited CUDA visibility unchanged, and
left its dedicated queue directory absent. These are execution observations, not
accuracy or physical multi-GPU/DDP evidence.

Fresh server status/configuration/artifact-download readback remains unverified.
The first acceptance reader used an incorrect project lookup; required cleanup
removed the successful test resources. Follow-up attempts, including a bounded
single-GPU retry with direct task-ID readback, failed before inference in the
pre-existing documented ClearML naming query: `Task.query_tasks` attempted to extend
a list with `res.response.tasks=None`. No application or dependency workaround was
applied. Effective policy/replay are covered by deterministic tests, not claimed as
fresh server readback. This is an outstanding publication/release acceptance gap.

Every successful and failed attempt's tag-scoped resources and invocation arenas
were cleaned; the final scoped listings were empty. External test scripts and logs
are retained with the environment evidence, outside the repository.

## Independent review and correction

The first fresh read-only review reproduced a case/whitespace forwarding gap:
force validation accepted padded/uppercase selectors, but native detector device
converters received the raw strings. New owner/provenance regressions failed for
` CUDA: 2 ` and ` MPS:0 ` before the fix. Hydra now normalizes effective string
selectors without changing requested provenance, identity, order or visibility.
Regression cases call the native DEIMv2, RF-DETR and Faster R-CNN device converters
with normalized CPU and CUDA inputs. No backend or external dependency was patched.

A second independent read-only review (`final_review`, fresh context) returned
`ship` for implementation with no blocking correctness or architecture findings.
It reviewed the integrated source/test/documentation diff and the final check logs,
and independently passed planning-record validation and `git diff --check`.
The reviewer accepted validation/effect ownership, immutable admission evidence,
Hydra presentation, selector normalization and reuse of launcher contracts.

Final Markdown validation parsed 11 files and checked 189 local links/anchors;
whitespace checks passed. Architecture acceptance validation passed after evidence
and review reconciliation. This validates the architecture record and its executed
code/documentation checks, not the outstanding live publication/release gate.
T027 and T030 remain open; no commit, release tag or push was attempted while the
required fresh server readback remained unverified.

## Source delivery authorization — 2026-10-13

After the implementation report, the user explicitly requested “commit and push
work”. This authorizes source delivery while the T027 live ClearML readback and
T030 release acceptance remain open. No version tag is included in this delivery.

A fresh read-only scope review (`commit_scope_review`) returned `ship` for the
scoped source commit and push. The source is prepared on an isolated feature
branch using the committed development and hook configuration. Existing
static-analysis edits and fixture/WorkerClaim cleanups are excluded. The isolated
`pyproject.toml` contains no local source overrides; the original workspace keeps
its exact local overrides and unrelated edits. Normal commit hooks are required,
with the prepared environment reused without dependency resolution. The verified
source commit can then fast-forward `master`; this does not close the documented
publication/release acceptance gap.

The first source-commit attempt passed Ruff, mypy and all import contracts, but
its full pytest hook terminated with SIGILL (exit 132) while the existing native
DDP relay tests were running. The trace showed garbage collection in the relay
thread and `fsync` in the main thread; it did not establish a cause. An unchanged
focused rerun of `tests/test_native_ddp.py` passed all 22 tests. The source remains
unchanged; delivery still requires the complete normal commit hooks to pass on
retry, with no skipped tests or disabled hooks.

### Delivery result

The unchanged-source retry passed every applicable commit hook, including the
full pytest suite, Ruff, mypy and import contracts. Source commit
`be587ec69e112df25302c03694be8a0ec842a5d1`
(`feat(gpu): force explicit devices and explain admission decisions`) was
fast-forwarded to `master` and pushed to `origin/master`. All unrelated workspace
files and the exact local source overrides were verified byte-for-byte against
the pre-delivery snapshot; the index was clean after integration. The committed
`pyproject.toml` and lockfile are unchanged from the prior source revision.

Markdown validation parsed 11 files and checked 190 local links/anchors after
the authorization amendment; architecture acceptance validation and whitespace
checks passed. The final delivery-only additions receive the normal documentation
commit checks. The first SIGILL remains an unexplained, non-reproduced observation;
it was not waived or fixed by changing the test suite.

The named feature branch ran normal hooks and created no release tag. No tags
were pushed. T027 fresh ClearML readback and T030 release acceptance remain open;
the explicit commit/push request is complete for the implementation source.

## Release acceptance resume — 2026-10-13

The user requested verification and release after source delivery. The release
checkout is isolated from the unfinished static-analysis work and contains no
local dependency source overrides. Application source and tests remain identical
to the delivered implementation; expected release writes are dated evidence,
architecture reconciliation and generated root-version/changelog metadata.

### Fresh native force and publication checks

The initial fresh CPU attempt reproduced the documented ClearML SDK naming-query
failure before inference. A separate authenticated task-list control returned a
proper empty list; it does not establish the cause of the failed invocation.
The retry uses the supported `sdk.development.report_use_subprocess=false` setting
through an isolated external SDK configuration, with credentials supplied by the
environment. See the maintained [reporting transport guidance](../../docs/multi-model-backends.md#clearml-reporting-transport-errors)
and its earlier controlled investigation. No application, SDK, dependency or
shared-service patch was made. Default subprocess reporting is not claimed fixed.

The controlled fixture contains six disjoint images across train, validation and
test, with one background image in each split. The random checkpoint establishes
execution only. Explicit `autogpu.force=true`, `queue.enabled=true` and
`autogpu.enabled=true` were supplied for CPU, GPU and two-job GPU multirun commands.
Fresh processes fetched the exact completed task IDs and canonical configuration,
then force-downloaded both required artifacts before cleanup.

| Invocation | Completed task ID | Ground-truth rows | Published audit rows |
| --- | --- | ---: | ---: |
| CPU prediction | `6b0aeccece1f4731ac77cdfd1db5e6e6` | 6 | 108 |
| GPU prediction | `88490543975c4f698875c3088f444c69` | 6 | 108 |
| Forced sweep, first job | `3d207366a9ac4836a3bafdb61adb104f` | 6 | 108 |
| Forced sweep, second job | `628e161b121e4947839ee38796b9d227` | 6 | 12 |

Every task records effective `force=true`, `queue=false` and `autogpu=false`, with
identical requested/effective concrete devices. Downloads retain all source rows,
IDs and image membership, bounded prediction confidences and the standalone
`not_evaluated`/empty-match semantics. The parent independently verified all eight
downloaded hashes and sizes. The sweep used one process and BasicLauncher, with
the first completion preceding the second start. Inherited CUDA visibility remained
unset throughout, and the dedicated queue directory was never created. Tag-scoped
cleanup returned zero projects and tasks and removed only owned invocation arenas.

Initial external harness assertions expected raw control sections and empty
selection fields that canonical serialization intentionally omits. The corrected
harness follows the actual contract; fresh CPU/GPU/sweep runs independently passed.
These corrections changed no application behavior.

Two further one-epoch train→predict pipelines passed with `compile=false`, AMP
disabled, two-image batches and worker count zero. CPU task
`e218fdf8575c4a9c9975c4af77711ce8` and GPU task
`13b6ba6cf35a40bf88773a141a4c1f96` each published six ground-truth and 108 audit rows.
Each published exactly one best Output Model; fresh forced downloads reloaded
through YOLO with the expected class. The downloaded checkpoint hash, model ID
and training task ID matched canonical prediction provenance. The parent verified
all twelve CSV hashes and both checkpoint hashes/sizes across the six accepted
invocations. The training tag was also cleaned to zero projects/tasks; queue roots
remained absent and invocation processes exited. These are execution/publication
checks using synthetic random weights, with product metrics, comparison and business
reports explicitly skipped; they make no accuracy claim. T027 is now complete.

### Quality and installed distributions

Fresh Ruff and mypy checks pass; mypy checked 283 source files. All 40 import
contracts pass, and the architecture/force/decision selection passes 150 tests,
including prohibited-dependency cases. The delivered unchanged source also passed
the full normal pytest commit hook recorded above. The release commit runs its own
required full hooks before publication.

Both preliminary distributions were built offline and installed separately
into fresh Python 3.12 environments from the frozen base/detector/export lock,
without reusing the prepared environment's site-packages. Only the approved local
external dependency copies remain editable. Wheel and source-archive installs are
noneditable; all 156 application/plugin Python modules match the checkout bytes.
Each installation records 788 passing checks: eleven installed command helps,
Hydra plugin/worker presence, every selected command/model configuration, default
and strict forced policy, the ordered five-GPU configuration example, overwrite
protection and preservation of unrelated files. Configuration checks import no
ClearML SDK. The external composition harness needed schema registration before
its first direct composition; installed commands themselves passed unchanged.
Final versioned distributions receive a fresh build/install check before tag push.

Physical multi-GPU/DDP and MPS remain unverified. The original user's waiting run
was not inspected, and its cause remains unconfirmed. The separate forced-kill
orphan-recovery and permission-denied process-inspection follow-ups remain deferred.

Fresh independent read-only release review returned `ship`, conditional on the
remaining normal version hooks, final distribution checks and explicit Git-tag push.
The reviewer inspected the five-file documentation/changelog delta, native receipts,
installed-distribution reports and fresh quality logs; no fix-first findings remain.
The preferred review model was unavailable due service capacity; a fresh supported
alternate reviewer completed the review. Changed Markdown/local anchors and the
architecture acceptance record validate successfully.

### Completed release — 2026-10-13

Acceptance commit `d240417` ran normal documentation hooks and triggered the normal
master release workflow. Its checked version commit
`ca5f703bc6ef57334f45b7875fd3783f99fd4772` passed the required Ruff, mypy,
import-linter and full pytest hooks and received annotated Git tag `v0.26.0`.
Only `pyproject.toml`, `uv.lock` and generated `CHANGELOG.md` changed in that commit.
Both version files differ from the delivered source only at the root package
version; dependency sources, versions and other lock bytes are unchanged.
The branch and explicit tag were pushed atomically, and remote branch/tag readback
confirmed the release commit. No GitHub Release, package publication or asset upload
was performed. T030 is complete.

Both final `0.26.0` archives installed into fresh frozen dependency environments,
passed dependency compatibility checks and each completed 789 acceptance checks.
Their 156 application/plugin source modules match the checked release source.
The added Hydra discovery assertion initially retained a class imported before
Hydra re-executed its module; the same identity mismatch reproduced in both the
preliminary and final installations. Initializing discovery before importing the
class corrects the external harness while preserving the strict registration
assertion. An independent read-only follow-up confirmed that correction. No project
or dependency change was needed; both final suites then passed.

| Locally verified distribution | Bytes | SHA-256 |
| --- | ---: | --- |
| `clearml_yolo-0.26.0-py3-none-any.whl` | 340199 | `410087b6c447cb066b73254302f3b766e727539d83fd3b9de8289813db63c620` |
| `clearml_yolo-0.26.0.tar.gz` | 276412 | `a2552e6bd819db2fef3b4731db2734c549b83c44d0123c378d34a8ee57e61dab` |

Release work remained isolated from the 21 snapshotted unrelated files and local
source overrides. Native task-owned processes exited, both stand tags were cleaned,
and temporary dependency links in the native worktree were removed without changing
their targets. Detailed local receipts and downloads were retained outside the
repository. The physical multi-GPU/DDP/MPS and default SDK-reporting limitations
above remain explicit; no new runtime behavior was changed during release.
