# Integrated verification — 2026-10-29

Verified working feature 008 on source baseline
`0037059dcf8a8ed16582f256b98036480cabd842`, Python 3.12.13, installed CY 0.41.0.
The working tree includes preserved, uncommitted feature 007. Results below cover
the integrated source; they do not establish release acceptance for 007 or a new
release version. Approved external dependency revisions were unchanged.

## Parent checks

| Command | Observed result |
| --- | --- |
| `uv run --frozen --no-sync python scripts/verify.py` | Passed: Ruff, strict mypy, Vulture, all 52 import contracts, ordinary pytest: 4,344 passed, 30 skipped, 81 deselected |
| Focused docs/architecture/release regression pytest selection | Passed: 118 tests |
| `uv run --frozen --no-sync cy-docs --check` | Passed: 467 fields, 156 command/model/profile configurations, eight tutorials |
| `CY_DOCS_BROWSER_CHANNEL=chrome uv run --frozen --no-sync pytest -q browser_tests` | Passed: ten browser cases |
| Strict mypy over `src/clearml_yolo tests browser_tests` | Passed: 434 source files |
| `uv run --frozen --no-sync python scripts/verify.py --docs` | Passed: Markdown and local paths/anchors, including new feature/tutorial files |
| Scoped `ruff format --check` on new documentation code/tests | Passed: 35 files already formatted |

After independent-review corrections, reran the canonical command on the stabilized
source: **4,358 passed, 30 skipped, 81 deselected**, 182 warnings, 999.95 seconds for
pytest. Ruff, strict mypy, Vulture and all 52 import contracts passed. Final logs
use `application-ef4b587f5b824b0fa8c287d2ca782e18`; the successful receipt was replaced
only after the verifier confirmed unchanged inputs. The final browser rerun passed
**11 cases** in 51.82 seconds. `cy-docs --check` again reported 467/156/8, and the
documentation verifier passed with `docs-ac991591eced495daaf3179be40c3b7c` logs.
These later observations supersede the initial integrated counts in the table.

Final catalog review found that implicit argparse switches were described with raw
`None`/`str` metadata instead of effective `False`/boolean semantics. A failing
regression reproduced the issue; the projection now reads inert parser defaults
and action shapes. Six focused catalog tests passed. With this final correction,
the full canonical run passed **4,359 tests**, with **30 skipped, 81 deselected**
and 182 warnings, in 995.14 seconds. Static checks and all 52 import contracts
passed; receipt logs use `application-fd69e9fb0b7443c19da494184d165c2b`.
The final browser run passed 11 cases in 49.72 seconds, docs coverage remained
467/156/8 and documentation validation passed (`docs-bc86ab8c6ea8424695c3c2d8d772daf8`).
Installed catalog/parser checks and real worker checks were repeated on the new
337-file digest recorded at the end of [installation evidence](installation.md).
These are the final runtime-source observations; subsequent edits are acceptance
records only.

The configured mutation scope (datasets, evaluation policy and export quality),
its selected tests and approved runtime dependency sources were unchanged; no
new scientific-policy mutation run was required for metadata and docs changes.

Canonical evidence is in Git-private `verification/application.json` and the
`application-0451239fc8b74de88bb586dd425b7eeb` logs. The full pytest invocation
took 1,002.94 seconds and emitted 182 warnings, primarily existing upstream
deprecations, runtime warnings and font glyph warnings. Skipped/deselected checks
are not reported as passing. The ordinary suite includes native CPU-DDP;
the separately selected physical GPU/remote suites retain their documented limits.

The browser cases use the installed Chrome channel with Python Playwright.
They verify search/filter/deep links, examples and edits, required-field state,
named-document and sweep previews, errors, stale-result invalidation, copy/download,
keyboard navigation, offline requests, responsive layout and server/worker shutdown.
The development-only Playwright browser download timed out; it was stopped, and
Chrome provided the browser-test execution. No Node installation is needed by users.

## Regressions and corrected observations

The captured compatibility fixture predates declaration replacement. Tests compare
unresolved and resolved compositions for all 156 combinations, command schemas,
legacy override shapes, exact utility help and parsing, with existing export/replay
tests retained in the complete suite. Runtime validators and public model targets
remain authoritative.

An earlier full run had two failures: the new docs entrypoint was missing from
the command-independence inventory, and temporary local uv sources were present
in a release-test fixture. Added the explicit command contract and removed the
task-created local source section. The original failure paths then passed, and
the complete suite above ran with that section absent. A subsequent static pass
identified the new preview validation module's OmegaConf edge; recording that
composition owner's explicit dependency fixed the import contract before the
successful complete run.

Preview audit regressions now cover package-qualified resolver selectors,
Hydra package replacement, nested defaults resolvers, traversal in group values,
ordered delete/add overrides and cleanup of descendants after a successful worker
closes its pipes. Validation tests first exposed 26 failures in the earlier pure
validator; 39 cases now cover types/ranges, inactive settings, target identity,
nulls and independent errors beside unresolved expressions. Resolver, dataset,
weights and augmentation execution remain prohibited in preview.

Task-owned Python files passed lint and scoped formatting checks. An optional
whole-tree `ruff format --check .` also identified existing formatting differences
outside this feature; no unrelated files were reformatted. Formatting the whole
repository is not part of its canonical verification command.

## Additional evidence and acceptance limits

- [Separate source installation](installation.md): latest snapshot, all 337 files
  identical, module roots in independent site-packages, real isolated previews and
  positive-control file-access observation.
- [Native pipelines](native.md): fresh YOLO CPU and Faster R-CNN GPU training,
  downloaded checkpoints/artifacts, frozen thresholds and paired current-test reports.
- [Documentation and skill](documentation.md): portable guidance and independent
  behavioral evaluations; host/model limitations remain explicit.
- [Paired source verification](paired.md): current CY 0.41.0 / queue 0.1.3 normal
  resolution and 518 queue tests; a proposed release pair still needs verification.

Final independent review, architecture reconciliation and delivery status are
recorded separately. Passing checks do not authorize including unfinished 007 or
other repositories' pre-existing changes in an 008 commit.

Reconstructed the initial tracked working state from HEAD plus the captured
pre-existing patch using a task-owned temporary index. All 14 pre-existing tracked
paths outside explicitly shared files remained byte-identical. Shared README and
contract/skill changes were compared with retained original copies; the additions
preserve earlier content. The untracked 007 command receives only the planned
inert parser refactor; its implementation and all other 007 paths remain outside
008 write ownership. No original index entries were changed by this comparison.

Final architecture acceptance validation exited zero after the fresh closing
verdict and diff reconciliation were persisted. Refreshed documentation checks
and `git diff --check` passed. A final process inventory found no documentation
server or preview worker. Removed task-owned temporary scripts, local context,
logs and snapshot directories after retaining necessary baseline copies, screenshots
and verification logs in Git-private `verification/cy008-preservation`. Native
stand evidence remains in its private evidence archive. The CY index remains
untouched; delivery exclusions are recorded in [delivery](delivery.md).

## Integration onto released 0.42.0

The explicit release request and fetched history selected remote baseline
`f8eb8a3c198806c08c0a41161aa4e8034dec0273`, retaining final feature 007 fixes.
Only feature 008 changes were merged from its preserved initial-007 baseline:
18 modified paths and 65 new paths, with no conflicts. A package inventory
comparison found exactly two differences from the earlier reviewed 008 package:
`adapters/assets/hub.py` and `adapters/assets/preparation.py`, both byte-identical
to released 007. The 008 runtime, browser assets and tutorial inputs are unchanged.

The first integrated canonical run passed Ruff, strict mypy, Vulture, all 52
import contracts and **4,373 tests**, with 30 skipped, 81 deselected and 182 warnings
in 1018.13 seconds. Its verification receipt was correctly withheld because the
new environment acquired `pi-heif` 1.4.0 during execution. The only recently changed
inventoried dependency files belong to that package. Installed Ultralytics retries
unidentified images through a lazy codec installer, consistent with the bad-image
regression path; the separate installation task's commands targeted only its own
private environment. No application source changed and no upstream dependency
source or lockfile was edited. Dependency consistency passed for 286 installed
packages; the canonical gate is rerun with this stable prepared environment.
The failed-receipt run ID is `66ef563ffa2446e2b8378ad2714e9784`.

Independent integrated browser verification passed all **11** cases in 52.69
seconds with the available Chrome channel. `cy-docs --check` passed with **467
fields, 156 configurations and 8 tutorials**. Markdown/local-link checks and
whitespace checks passed. Proposed 0.43.0 noneditable installation and the paired
0.43.0 / queue 0.1.4 checks are recorded in [installation](installation.md) and
[release pair](release-pair.md). Existing native YOLO/non-YOLO artifact evidence
remains applicable to unchanged 008 behavior; released 007 supplies its separate
native diagnostic-fix acceptance. No new physical/native run is claimed here.

## Stable integrated canonical acceptance

The repeat canonical command exited zero and produced its accepted verification
receipt. Ruff, strict mypy, Vulture and all 52 import contracts passed; the complete
ordinary suite passed **4,373 tests**, with 30 skips, 81 deselections and 182 warnings
in 998.92 seconds. Native CPU distributed-training and injected negative import
cases are included. Optional skipped/deselected targets are not counted as passing.
The input inventory was stable across this entire run; a separate mid-run audit
also found zero changed or removed inputs.

Run ID: `e95a955538f44bd7aacf2189cff39978`. The Git-private
`.git/verification/application.json` receipt records command arguments, successful
exit codes, log hashes and the verified content fingerprint:

- `a715608f9fbbda7c91358de88e7ddfa8445b8fd9a580921bbe787eb0d21d79ed`.

This supersedes the earlier withheld receipt. The source version remains 0.42.0
until the native release hook creates the proposed 0.43.0 metadata; final pairing
will compare that actual committed source with the independently tested proposal.
