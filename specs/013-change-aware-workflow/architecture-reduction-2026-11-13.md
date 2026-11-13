# Architecture reduction verification — 2026-11-13

Implementation commit: `14b3740` (CY 0.48.1). No release or push.

## Changes and deliberate limits

Removed all three custom architecture scripts (732 lines), replacing them with native
import-linter contracts, product-scoped Ruff configuration and product runtime tests.
Converted 70 literal dynamic import calls across 23 product modules; disposable graph
comparison found no missing converted edges. Computed DEIM imports remain explicit
exceptions. Removed the direct Grimp development declaration; import-linter still owns
its transitive dependency. No new tools or upstream dependency revisions.

Approved retirements: blanket cycles, initializer syntax restrictions, blanket core/pure
helper dependency allowlists, packager member/external allowlists, all-source-string target
resolution. Explicit layers, SDK ownership, queue and test boundaries remain. Standalone
test filenames require declarative list updates. Ruff catches import_module aliases and
qualified builtins.__import__, but not bare __import__; reflective bypasses remain review
limitations. Scientific initialization is warmed before auditing core.validation imports;
this isolates product effects, not upstream scientific-library initialization.

## Executed evidence

- Passed: 363 focused conversion tests; 239 package/config/entrypoint tests; fresh-process
  DDP reconstruction; four actual worker destination tests.
- Passed: final worker/DINOv3 selection, 49 tests after the import-order correction.
- Passed: 21 declarative import contracts; disposable violations rejected standalone
  test imports, packager importlib and SDK access from projection helpers.
- Passed: whole-project mypy (451 files), Ruff, format check, Vulture, lock validation,
  and deptry after explicitly recognizing externally provisioned TensorRT.
- Full ordinary suite: 4,676 passed, one skipped, 13 failed. All failures were confined
  to test_yolo_weights_settings.py and exposed sys.modules-only test doubles that did
  not wire parent package attributes for ordinary imports. Targeted repair and final
  verification are recorded below when complete; this initial run was not a pass.
- Passed: live CPU integration (one passed, 29 skipped, 63 deselected). The normal task
  leaves FiftyOne opt-in; those tests were subsequently run explicitly.
- Passed: all 29 live FiftyOne tests, including installed plugin registration/resources.
- Passed: paired latest-source CY/queue verification, 527 queue tests (seven deselected),
  including both source/installed metadata and queue import checks. Queue source was
  `d3627a0`, version 0.1.10; CY source was `14b3740`, version 0.48.1.

## Review and cleanup

Fresh independent review identified missing standalone-test restrictions and a packager
importlib bypass; both were corrected and re-reviewed. Its minor import-order observation
was also corrected. Review does not substitute for final verification.

CPU integration owned namespace `cy-it-586d65`; teardown proved it absent. The subsequent
FiftyOne session completed fixture teardown and left no live environment record. Its
owned local lock directory was removed. Paired-check removed its temporary environment.
No pre-existing services or data were modified. No GPU execution or release acceptance
was claimed; this was the ordinary product verification and applicable CPU/FiftyOne scope.

## Final verification

The targeted fixture repair passed all 14 tests in test_yolo_weights_settings.py,
including all 13 original failures and the unchanged real-SDK process scenario. Ruff
and mypy passed for that file. Other full-suite passing evidence is reused because only
this file's isolated fixtures changed. Final committed-content hooks and review are pending.
