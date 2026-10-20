# Implementation verification — 2026-10-20

## Scope and integration

The task implements the approved selector and dependency contracts in
[spec.md](spec.md). Work began on clean baseline `129b94b`. During verification,
upstream advanced to `41a4036` (package `0.35.0`) with stable-cache and early
configuration/artifact publication changes. The task was integrated onto that
revision, preserving its behavior and all unrelated worktrees.

Three overlapping edits required manual reconciliation: pipeline imports,
validation's shared task variable, and adjacent architecture negative cases.
Both sides were retained. Existing feature history and protected external sources
were preserved. The local source-override section was saved exactly and removed
for the release-preservation tests and commit procedure; it is not a deliverable.

## Executed checks

Integrated source results:

| Check | Result |
| --- | --- |
| Focused source, pipeline, architecture, export and release-preservation tests | 332 passed |
| Ruff | Passed |
| mypy | Passed across 357 source files |
| Vulture | Passed |
| Import-linter | 43 contracts kept, none broken |
| Markdown and repository links | 542 files, no issues |
| Architecture plan structure | Passed, including pure export validation amendment |
| Replay selectors and final CSV-only guard | 60 passed |
| Final source/shared-constructor/training/pipeline/export/replay checks | 134 passed |
| Final architecture, tooling and default-dependency checks | 285 passed |
| Final static/import checks after constructor correction | Ruff, mypy (357 files), Vulture and 43 import contracts passed |
| Final documentation before evidence closure | 531 Markdown files, no issues |

Logs for these checks are retained under `.tmp/cy036/integrated`.
The integrated complete suite, final minimum-version matrix, fresh independent
review and release checks are recorded below when finished. Pending checks are
not acceptance evidence.

The [native report](native-verification.md) distinguishes pre-integration CPU/GPU
and paired metrics evidence from the repeated integrated verification.
The [dependency report](dependencies-evidence.md) and
[machine-readable version inventory](dependencies-evidence.json) record actual
floor experiments, built-wheel installation and both Python environments.
Portable skill source validation is recorded in its companion collection report.

## Reproduced failures and corrections

- Initial feature tests failed before the new contracts existed. The first
  integrated focused tests then exposed one old pipeline assertion expecting
  a raw path; it now verifies the resolved source record and derived path.
- Architecture tests rejected the new module classification and unrecognized
  effect call. Classification and one exact repository-port effect were added;
  negative cases reject SDK imports, arbitrary repository calls and file reads.
- Minimum Pydantic `2.9.2` failed queue schema generation for the native Python
  type alias. `2.10.0` passed the original subprocess failure on both Python
  minors; the declared floor was raised accordingly.
- Both initial minimum suites reached 1,547 passing tests before the export
  regression: missing weights reached task creation. The existing operation
  validation was extracted into a pure, shared input-presence method. The
  original failure and dataset-input variants now pass before any task or
  dataset effect.
- An initial default-suite attempt used relative source paths and was stopped
  to avoid importing another checkout in subprocesses. A subsequent attempt
  exposed the export regression and the release fixture's requirement that
  local source overrides be absent; it was stopped after 1,977 passing tests
  and two failures. Neither attempt is reported as a successful complete run.
  Final runs use isolated environments and absolute source paths where needed.
- A branch-switch command returned success while retaining three content
  conflicts. Compilation/lint checks detected them before native verification;
  they were reconciled and the checks rerun.
- Independent review confirmed that the SDK could fetch unrelated links despite
  the selected CSV. Two added inventory tests failed before the guard; exact
  logical-inventory validation now rejects extra files/links before materialization.
  The final source/replay group passed 60 tests and all static checks remained green.

- The integrated complete normal-suite invocation finished with 3,355 passing tests,
  30 skips, seven deselections and nine failures: the old exact dependency
  constructor assertion and eight training fixture assertions expecting a string.
  Before correction, a new old-positional-constructor regression reproduced silent
  argument misbinding. The repository port is now optional and last; local inputs
  work with the old constructor, and unsupported remote resolution fails clearly.
  The path fixture now compares the existing `str | Path` contract semantically.
  All affected modules passed in the final 134-test group. An independent executable
  probe also covered old positional and keyword construction. The final complete
  hook invocation is recorded after it finishes; this failed invocation is not
  reported as an all-green run.
- Running the source tests alone revealed implicit Hydra config registration from
  other test modules. The source test now registers its configs explicitly and
  passes in isolation on both minimum-version interpreters.

- The first contributor hook attempt exposed an invocation conflict between the
  inherited `UV_FROZEN=1` and hooks explicitly using `--locked`. The owned test
  process was interrupted, local source overrides restored, and the invocation
  corrected to `UV_NO_SYNC=1` without `UV_FROZEN`. No hooks were bypassed and no
  dependency resolution was authorized by this correction.

## Acceptance and delivery

The final complete normal-environment suite passed through the required contributor
commit hook, together with Ruff, mypy, Vulture, import contracts, whitespace and
changelog checks. Contributor commit: `a3f4c5a`. The final complete minimum suites
both exited 0: **3,370 passed, 30 skipped, seven deselected** on Python 3.12.13
and 3.13.14. Skips/deselections are not native/GPU acceptance claims.

The final minimum matrix uses pandas 3.0.0 and openpyxl 3.1.5. Pandas 2.2.3
added Excel header styling that violated the frozen workbook contract; 3.0.0
passed that original failure. Its `read_excel` path rejected openpyxl 3.1.0;
3.1.5 passed. Each interpreter passed 46 focused report/workbook checks before
the final complete run. No application or frozen-report fixture was changed to
accommodate these versions. The dependency report records the final wheel,
installed-version matrix and unchanged protected/third-party lock records.

Three independent reviews covered the integrated implementation, the CSV-only
inventory correction and constructor compatibility. All actionable findings are
resolved. The final pandas/openpyxl metadata adjustment was reconciled by the
parent against exact failure reproductions, passing focused/full suites and the
complete lock diff. Module responsibility, effects and import rules are unchanged.

The complete task-owned diff against `41a4036` (including all new files, dependency
metadata, tests and docs) matches the architecture scope. No unrelated source or
workflow tooling is included. Final documentation and architecture acceptance
checks are recorded with delivery below. Releases use Git commits and annotated
tags only; package-registry publication and deployment are outside this task.

Final pre-release documentation validation checked 544 Markdown files with no
issues. Architecture acceptance validation exited 0 after complete diff/check/review
reconciliation. The companion collection passed discovery (all four skills),
strict frontmatter checks, Markdown lint (46 files), repository links (46 files),
package-root links (three files) and its no-impact architecture acceptance.
