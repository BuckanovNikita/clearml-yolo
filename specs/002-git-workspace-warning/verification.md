# Verification evidence — 2026-10-20

## Planning and cross-artifact analysis

Starting application HEAD: `3b3bd8fa5b727e7387a0604b94b1f755e18ae5b8`, matching
origin/master after fetch. Existing pyproject.toml local editable dependency
overrides are unrelated and preserved. Native Spec Kit helpers use an explicit
feature-directory selector; installed workflow assets remain unchanged.
Extension configuration has no registered hooks.

Specification checklist: all four items passed. The user confirmed all experiment
commands and every launch, then authorized implementation of the proposed plan.
Read-only cross-artifact analysis found no uncovered requirements, contradictory
scope, constitution violations or blocking ambiguities. FR-001–FR-006 and
SC-001–SC-002 map to T004–T006; documentation/review/release FR-007 and SC-003
map to T007–T013. Architecture planning validator passed (exit 0).

## Execution results

The first real `cy --help` regression failed before implementation: return code
was 0 and stderr was empty, so the expected warning count was 0 instead of 1
(`tests/test_git_workspace.py::test_experiment_inspection_warns_once_without_changing_stdout_or_status`,
exit 1). An initial overly narrow pytest keyword selection selected no tests
(exit 5); it was corrected before observing the behavioral failure.

The implementation now uses the runtime adapter and shared launch boundary.
Focused verification passed: `uv run --frozen --no-sync pytest
 tests/test_git_workspace.py tests/test_runtime_bootstrap.py
 tests/test_hydra_sweep_configuration.py tests/test_architecture.py -q` completed
with 321 passing tests (exit 0). This includes the 36 workspace tests, actual
console scripts for all nine experiment commands with help/config inspection,
real Git worktree/submodule fixtures and the forbidden runtime-to-ClearML edge.

Ruff, strict mypy (359 source files), Vulture and `lint-imports` all passed;
43 import contracts were kept. Initial mypy failures in test mock targets were
corrected by patching imported stdlib modules directly; no suppression was added.
`git diff --check` and the documentation checker (all tracked Markdown plus
nine explicitly supplied new Markdown files) passed: 58 files, zero issues.
The final routine result and independent acceptance are recorded below.


## Release-fixture environment correction

The first full run was interrupted after one failure (2,425 passed, 30 skipped,
7 deselected at interruption). The failing existing test was
`test_release_preserves_protected_lock_without_resolving`: its fixture copies the
semantic-release configuration through the end of pyproject.toml, thereby also
copying this checkout's pre-existing appended local `[tool.uv.sources]` section.
The resulting fixture correctly failed its no-local-sources assertion. Neither
that test nor the release helper changed in this task.

With the exact local section saved and temporarily removed, the same test passed
(exit 0, one test). The section was restored byte-for-byte. The full suite is
being rerun with the same temporary omission used by the required commit/release
procedure, using frozen/no-sync execution and restoration in a finally block.
The interrupted run is not claimed as passing verification.

Additional actual console checks passed: with an empty PATH, `cy --help` emitted
one Git-unavailable warning and exited 0. An invalid Hydra override exited 1 both
outside and inside Git, with identical stdout and the warning only outside Git.
All fixtures were task-owned temporary directories, removed after the checks.


## Process isolation for regression verification

A second run with source overrides omitted hit an unrelated existing process-tree
regression: `test_unmarked_helper_orphan_is_preserved_and_cleanup_fails_closed`
expected its ambiguous-child diagnostic but received `/proc access denied` for a
PID different from the fixture's recorded child. Its unchanged process-tree
adapter scans visible processes; other development activity was running on the
host. That run was interrupted (one failure, 1,917 passed, 30 skipped,
7 deselected); it is not a passing suite.

A task-owned user/PID namespace using `unshare --user --map-current-user --pid
--fork --mount-proc` preserves the invoking UID/GID and has zero effective
capabilities after exec. Both the ambiguous-orphan regression and the deliberately
unreadable-process regression passed there (two tests, exit 0), demonstrating
that isolation removes host interference without granting inspection privileges
or weakening assertions. No shared processes, services or kernel settings were
changed.

The third run exposed the queue's existing namespace fence: the host's shared
queue metadata belongs to the host PID namespace, so tests in a new namespace
correctly rejected it. That run was interrupted (30 failed, 2,753 passed,
30 skipped, 7 deselected); it is not passing verification. Shared queue metadata
was not removed or modified.

The final isolation adds a private mount namespace with private propagation and
an ephemeral tmpfs over the queue root. It retains the invoking UID/GID, then
drops all capability sets before executing tests. A probe covering guardian
cleanup and deliberately unreadable processes passed (four tests). All 30 failed
queue cases then passed in this environment. Namespace exits automatically discard
the private mount and task queue state. The complete suite and commit/release hooks
use this isolation with exact local source override preservation. Test assertions,
production code and shared services were not changed to address these constraints.

## Companion documentation

The canonical corp-skills change was prepared in an isolated worktree, initially
from `9bb4f98` (collection 0.3.0), then reconciled onto newer `origin/main`
`5bfa94e5f83c5eddbfabd69929f23d1ca2bd47a1` (0.4.0). Its proposed documentation
patch release is 0.4.1. Pre-existing shared-checkout edits and the upstream cveta2
release remain intact; installed skill copies are unchanged.

Changed package paths are `skills/clearml-yolo/SKILL.md`,
`skills/clearml-yolo/references/usage.md` and
`skills/clearml-yolo/references/evaluation.md`, with task evidence and collection
release metadata. Parent inspection confirmed the actual diff matches the
implemented warning, membership criteria, stream behavior and invocation scope.
The delegate's recorded checks passed after reconciliation: discovery of all four
skills, 57-file Markdown lint, skill metadata validation, duplicate-key YAML
validation, all six packaged links, changed-document links, no-impact architecture
validation and whitespace checks.

Fresh native agent `/root/usage_evaluation` read only the skill entrypoint and
usage reference, without the expected answers, and correctly answered both new
scenarios: help/config inspection with CY_HOME elsewhere, and unverified Git
membership during a multirun. The parent reviewed the exact answers. This is
explicit skill application evidence; it establishes neither automatic skill
selection nor alternate-host/model execution. Application full-suite acceptance,
fresh final review and both repositories' delivery refs follow below.

## Final parent verification

The complete routine suite passed in the private process/queue environment:
`uv run --frozen --no-sync pytest -q -rs --durations=10` returned 0 with
3,407 passed, 30 skipped, 7 deselected and 133 warnings in 731.07 seconds.
The 30 skips comprise one unsupported native reflink check and 29 opt-in
FiftyOne database/view checks. The seven deselected physical-GPU tests remain
outside routine selection. Native two-rank/four-rank CPU DDP training and
worker/owner-failure checks passed; this does not establish GPU or remote ClearML
publication. The exact saved local source section was restored after the run.

The separate focused, architecture, import-contract and static checks above
remain passing against the same implementation. Final updated documentation
validation passed again (58 Markdown files, zero issues), as did whitespace
validation. The parent inspected all tracked changes and new source, tests and
feature artifacts, plus the companion usage/metadata diff. Existing local
dependency overrides are excluded from the task.

Fresh independent review returned **ship** with no required corrections; see
[review.md](review.md). The parent reconciled the architecture record with the
complete task-owned diff, check evidence and review, then ran the shared
architecture validator with `--phase acceptance`: passed, exit 0. Documentation
validation including the review record passed (59 Markdown files, zero issues).
Remaining ledger items are authorized Git delivery and remote-ref verification.

## Commit-hook environment

The initial feature commit attempt returned 1 before running Ruff, mypy,
import-linter or pytest: their default `uv run` invocations tried to resolve
the local-only digital-metrics dependency from the package registry while the
required local source section was absent. Other hooks, including Vulture,
passed. No commit was created, no dependency or lockfile changed, and the exact
source section was restored.

Commit/release hooks therefore use `UV_NO_SYNC=true`, the installed uv's
documented environment equivalent of `--no-sync`, which implies frozen lockfile
execution. All configured hooks still execute in the prepared environment.
A probe with source overrides temporarily removed confirmed imports resolve to
this checkout; the explicit `--locked --no-sync` invocations also work. Setting
`UV_FROZEN` alongside explicit `--locked` was rejected by argument validation,
so that redundant setting is not used. This follows the existing prepared-backend
verification policy without altering hooks or resolving dependencies.
