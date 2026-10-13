# Static analysis follow-up verification — 2026-10-13

## Scope and workflow

Continued the approved audit on base `99befea` using the existing Spec Kit feature.
Recovered only the earlier task-owned uncommitted changes into an isolated branch.
The main checkout also contains unrelated GPU cancellation work; that work is excluded
from this task's diff. The earlier [verification](verification-2026-10-12.md) remains
historical evidence; the [rule inventory](ruff-rule-inventory.csv) now describes this
follow-up. No installed workflow tooling or external dependency source was changed.

The architecture plan was structurally validated before implementation. Existing
import contracts and architecture tests cover the runtime modules; the new tooling
tests cover release imports and development-only analysis packages, with negative
cases. SciPy/significance, export quality and progress modules were inspected and
tested but needed no source edits. The extra detector-tracking caller was added to
the scope and the plan revalidated before its correction.

Parent-owned work: configuration, lock, tooling boundary tests, docs and integration.
Two bounded agents handled source cleanup and typing checks independently, both
requested as GPT-6.1 Sol at medium effort; realized runtime settings are not exposed.
Neither delegated further. Fresh acceptance review follows integrated verification.

## Policy and dependency evidence

Observed tools: Python 3.12.13, Ruff 0.16.1, mypy 2.3.0 and Vulture 2.16.
Ruff's installed catalog has 968 entries: 812 stable, 138 preview and 18 removed.
Effective selection has 722 stable and 13 explicitly selected preview rules enabled;
85 stable rules are unselected, five stable rules explicitly ignored and 125 previews
unselected. Each CSV row was compared with catalog lifecycle and effective enabled
codes, rather than inferring selection from family prefixes. Formatter preview stays
disabled; lint preview can still affect behavior of existing selected rules.

`uv lock --check --offline` passes with 276 packages. Parsed comparison with the base
lock confirms every pre-existing non-root package node is identical. Added packages:
Vulture 2.16, scipy-stubs 1.18.0.1, types-tqdm 4.70.0.20260906, optype 0.19.0 and
numpy-typing-compat 20260602.2.5. Runtime dependencies, optional extras and both protected
editable dependency nodes stay unchanged. Packaging 26.2 is now declared directly in the development group for the metadata
guard; its existing lock node is unchanged. The stubs are development-only; removing
SciPy/tqdm missing-import overrides requires no new casts, Any values or suppressions.

The [advisory Vulture inventory](vulture-advisory-2026-10-13.txt) contains 85 findings
at 60%; the 80% gate is clean. Dynamic callbacks/attributes and possible unused names
remain review candidates, not proven dead code or a blanket allowlist.

## Verification evidence

- The Unicode COCO regression failed with an ASCII `UnicodeDecodeError` before the
  production read gained `encoding="utf-8"`; it passes afterward. The test keeps UTF-8
  filesystem encoding while switching text locale to C. It was exercised on Linux/WSL,
  uses canonical ASCII codec detection, and skips on non-Linux platforms. The final
  portability guard was rechecked with Ruff/mypy and the focused regression (one pass).
  Release helper tests now use a Unicode directory containing spaces.
- Initial parent mypy exposed a second `_verify_model` caller in detector tracking.
  Its publication suite reproduced 10 positional-call failures before correction;
  the updated detector/native suites pass all 34 tests. Repository search finds both
  verifier calls and both now use named expectations.
- Source delegate focused checks: 86 tests for Unicode COCO/native models/comparison/
  release; 20 Faster R-CNN tests; 194 architecture/detector/filesystem/ground-truth/
  inference/trace tests. Five upstream deprecation warnings occurred in the latter.
- Typing delegate: 58 significance/export-quality/comparison-observability tests pass.
  Temporary bad calls to `binomtest` (`alternative="unsupported"`),
  `linear_sum_assignment` (`maximize="yes"`) and `tqdm` (`total="two"`) cause mypy
  exit 1 with three call-overload/arg-type errors. The sample was removed.
- Parent `ruff check .`, `mypy .` (284 files), Vulture, import-linter (40 contracts),
  and architecture/tooling tests (108 passed, five upstream warnings) pass.
- Actual Vulture pre-commit negative control: an owned script with an unused required
  argument is rejected at 100% confidence (Vulture exit 3, pre-commit exit 1). The
  sample is removed in `finally` and the same hook passes again.

The initial full pytest process started before the second verifier caller was fixed
and retained its imported code: 10 detector-publication failures, 2,268 passes,
30 skips and 56 warnings in 436.68 seconds. All ten failures match the reproduced
positional-call regression; the corrected tree is rechecked by the full hook suite.

The corrected full suite passes through the pytest hook: **2,278 passed, 30 skipped,
56 warnings in 436.63 seconds**, including native CPU DDP scenarios. All other hooks
pass. The aggregate command nevertheless exits 1 because the parent edited evidence
and the test portability guard during execution; pre-commit correctly detects the
changed files. A frozen-tree aggregate rerun is required before acceptance.

Final aggregate-hook and fresh-review results follow below. Markdown parsing and
local-link checks pass for the task documents; generated CHANGELOG.md is inspected.
 No GPU training or real ClearML publication result is claimed
for this tooling follow-up; those application acceptance scenarios were not rerun.

## Documentation scope

Updated the policy report, development procedures and feature artifacts. Reviewed
README, application configuration, publication/runtime contracts and native acceptance
guidance: no updates are needed because public interfaces and scientific calculations
are unchanged. Internal keyword-only expectations and explicit Unicode decoding are
covered by focused tests. The approved scope uses the full suite (including native
CPU DDP) and does not require new GPU/ClearML runs.

## Independent review and hook retry

Fresh read-only reviewer `acceptance_review` returned **ship**, with no actionable
implementation finding. Its first dispatch encountered model capacity; the retry
completed without changing the selected model or any tracked file. It reviewed the
entire 41-file diff and independently passed Ruff, mypy (284 files), Vulture, all
40 import contracts, 169 focused tooling/model-publication/Unicode/release tests,
94 architecture tests, whitespace and architecture planning validation. It also
verified all 270 baseline non-root lock nodes and every inventory row/selection.

The frozen aggregate retry passed earlier gates but pytest terminated with SIGILL
(exit 132) during `test_ddp_incomplete_final_state_fails_before_best_upload`, with
garbage collection in the relay thread. This is not a pytest assertion failure.
Neither native_ddp.py, tracing.py nor test_native_ddp.py differs from the base.
The [previous release evidence](../022-simple-gpu-wait/verification-force.md#source-delivery-authorization--2026-10-13)
records the same failure pattern before this task's changes. Cause remains unresolved;
no application, interpreter or dependency workaround was introduced. An unchanged
rerun of `tests/test_native_ddp.py tests/test_native_ddp_cpu.py` passes **27 tests in
59.60 seconds**, including the original test path and real CPU distributed scenarios.
A complete normal hook retry is still required; no checks are disabled or skipped
to avoid this observation.

## Final parent acceptance

The unchanged frozen-tree retry of
`UV_NO_SYNC=1 uv run --frozen --no-sync pre-commit run --all-files` exits **0**: all
12 configured pre-commit checks pass. Pytest's JUnit report records **2,308 tests,
zero failures/errors, 30 skipped (2,278 passed), 414.012 seconds**. The diagnostic
`PYTEST_ADDOPTS` only adds JUnit output and skip reporting; no selection/exclusion
changes were used. Skips comprise 29 opt-in live FiftyOne checks and one unsupported
native reflink case. They do not establish live database or reflink acceptance.

Documentation validation parses 13 changed Markdown documents and resolves 37 local
file links; the existing release-evidence anchor is verified against its heading.
The generated changelog was inspected. Configuration examples are exercised by the
actual Ruff/mypy/Vulture/import/pytest/hook commands, and the CSV matches installed
lifecycle/effective settings. Architecture acceptance is structurally validated after
recording all executed checks and the fresh review. No outstanding implementation
or verification task remains; source commit, master integration and release follow.

The one SIGILL is retained as an unresolved, previously documented intermittent
observation. The original DDP path, real CPU DDP scenarios and the complete normal
hooks pass on unchanged-source reruns; this is not a claimed root-cause fix.

## Master delivery and release

Source commit `b43edf6` (`fix(quality): tighten lint gates and decode text explicitly`)
passed every normal commit hook. Its pytest report records **2,278 passed, 30 skipped,
zero failures/errors in 417.746 seconds**. Master was fast-forwarded to this commit.

The established release helper then completed successfully on master, creating checked
commit `cec2020` (`chore(release): 0.26.1`) and annotated tag `v0.26.1`. Release-commit
pytest records **2,278 passed, 30 skipped, zero failures/errors in 430.406 seconds**;
normal quality hooks were enabled throughout. Release preparation changed only
the package version, the root lockfile version and the generated changelog. All
270 original non-root lock nodes remain unchanged; the five planned development
dependency nodes are the only additions relative to the baseline.

After checking remote refs for concurrent updates, an atomic push advanced remote
master from `99befea` to `cec2020` and published `v0.26.1`. No GitHub Release,
package publication or uploaded asset was created. The local dependency source
overrides were absent during both commits and restored exactly afterward, unstaged.

The main checkout's unrelated cancellation work was preserved separately from the
task-owned audit changes. Original tracked/index patches and untracked files were
saved before integration; all unrelated untracked files matched that snapshot and
12 unrelated file hashes were captured for the final checkout-restoration check.
The final evidence-only update does not change executable code or dependency policy;
Markdown, local-link, whitespace and architecture acceptance checks apply to it.
