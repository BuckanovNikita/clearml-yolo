# Skill and verification consolidation — 2026-11-13

## Selection and authority

The approved interview decisions intentionally replace blanket acceptance and pairing
with reviewed affected-check evidence, retire two skills and the environment wrappers,
and remove property exploration. This is reduced automatic enforcement, not a claim of
identical assurance. The existing constitution's older blanket verification language is
superseded for this scope by the explicit user instruction; installed tooling is unchanged.

Task baseline: `5044d23`; implementation: `7b3ce9f` on `013-skill-consolidation` in an
isolated worktree. The original branch/worktree and its completed architecture changes
were preserved. Whole-branch earlier product/static/native outcomes remain recorded in
`verification-2026-11-13.md` and `architecture-reduction-2026-11-13.md`; this follow-up
changes no product source or dependency revisions. Pyproject changes only forward the
explicit pairing choice into semantic-release's restricted build environment.

Selected checks: static gates; release command scenarios; deterministic properties and
composed workflows; owned lifecycle operations and two CPU smoke invocations sharing
one adopted environment. GPU/manual charts/FiftyOne App, full coverage, mutation and
actual CY/queue pairing are unselected for this tooling/test-guidance scope. No fresh
coverage percentage, GPU, queue compatibility or remote-publishing outcome is claimed.

## Changes and reductions

Four custom skills total 920 words versus 1,956 at the baseline. Including active
operational references, guidance is 1,071 versus 2,883 words (audit-only indexes excluded
from both). Historical archive payloads and installed Spec Kit files remain unchanged.
No separate documentation checker, dependency-selection engine or evidence receipt parser
was added. The native specification, plan, task ledger and active contracts record the
intentional policy changes; relative Markdown links are absent from active custom skills.

Release requires a reviewed evidence file and explicit pairing choice. File existence
is enforced; review completeness and evidence applicability are human/agent obligations.
Conditional pairing still validates final proposed versions when selected. Local output
deletion is explicit; lifecycle teardown removes only its owned infrastructure.

## Executed checks

- Passed: original deterministic property baseline, 2 tests in 4.60 seconds.
- Passed: properties and composed product workflows after exploration retirement,
  6 tests in 23.27 seconds. Existing dependency deprecations and font warnings remain.
- Passed: focused Ruff, format and strict mypy checks reported by implementation owners.
- Passed: disposable release matrix using real Git repositories, emulated semantic-release
  and pairing commands, intercepted publication. Covers missing/invalid choices, absent
  or directory evidence, dirty/moved/held-lock refusals, new/no-version release crossed
  with required/not-required pairing, immediate/later publication, failed-push retry,
  and final-pair failure preserving prepared changes without release commit/tag.
  Actual Task conditional dispatch rejects missing/invalid choices. These checks do not
  establish real package compatibility or remote publication.
- Passed: initial independent static review found no defects in the integrated diff.
- Initial canonical pipeline: static gates passed; dependency-selected tests produced
  4,667 passed, 1 skipped and 1 failed in 843.10 seconds. The RF-DETR missing-best test
  reached the real training module despite its module substitution after earlier imports.
  Fixture diagnosis/repair and final post-verification review are recorded below.

The worktree's testmon history was seeded through a read-only SQLite backup of the
original worktree's recorded dependency history. This supports bounded current-node
selection for the changed shared test configuration; it is not fresh test execution.
The final canonical gate classifies committed inputs and records its actual execution.

## Live identity correction

The first live run passed (247.57 seconds); the second completed training/publication
but failed exact-name lookup (261.57 seconds). Native model-name collision handling
appended a display suffix to the task. The approved unique-identity approach is refined
to a pipeline-only invocation tag plus environment/project identity, while retaining
unique requested names. This avoids relying on mutable display names; it does not weaken
completion, model or artifact assertions. The failed environment was deleted and proven
absent; its failure log was sanitized. Credentials are excluded from Environment repr
so future pytest tracebacks do not print them. Successful repeat evidence follows below.

## Corrected live repeat and cleanup

Passed: two smoke invocations in one adopted environment, 2 passed with 80 dependency
warnings in 290.98 seconds. Independent API readback confirmed completed tasks
`ed442acab9174ce6ae9fa94cd8484522` and `1c9253ab2e524d52bb127d79300507fa`,
both with Output Models and distinct invocation tags. The second task acquired the
`-warm-finch` display suffix, exercising the failure path that defeated name lookup.

Passed: lifecycle export default/explicit/empty overrides, live setup refusal, invalid
delete guard and dry-run checks. Both `cy-it-8b14b5` and `cy-it-43b8c7` are proven
absent; no owned forwards or worktree `.run-tag` remain. Local outcome files and
sanitized logs are retained under `.tmp/skill-environment/`. Temporary harnesses and
forward logs were removed after preserving evidence. Disposable release repositories
and scenario harness were removed. No real release, remote push or shared-resource
intervention occurred. The isolated worktree and its normal development caches remain.

## Existing fixture failure and targeted repair

The failing RF-DETR test and production adapter were unchanged from `5044d23` through
`7b3ce9f`. Preimporting the real `rfdetr.training` reproduced AttributeError
`cls_loss_coef`: the fixture substituted sys.modules but the adapter imported the
already-bound package attribute. Patch the attribute at the actual import seam; preserve
the missing-best RuntimeError and unchanged last-checkpoint assertion. The full module
with that preimport passed: 30 tests. Ruff, formatting and strict mypy passed.
This is a test-isolation repair; product code is unchanged. Logs are retained at
`.tmp/rfdetr-preimport-red.log` and `.tmp/rfdetr-preimport-green.log`.

Reuse the initial canonical run's 4,667 successful tests and static evidence where inputs
remain unchanged. The fixture repair reruns its affected module; lifecycle/tag changes
have fresh strict static and live evidence. Final committed inputs receive the canonical
pipeline again, and independent review follows that outcome.

## Closing verification

Passed: canonical `prek run --all-files` at `4aebcb7`, with VIRTUAL_ENV,
UV_PROJECT_ENVIRONMENT, SKIP, PREK_SKIP, CY_VERIFY_SCOPE and PRE_COMMIT_ALLOW_NO_CONFIG
cleared; no hook edits. The preceding pipeline failure remains recorded above, with
its reproduced cause and successful targeted repair. The historical selected-test skip
was localized to native reflink; an explicit rerun reported filesystem FICLONE unsupported
(errno 95), 1 skipped in 0.29 seconds. No native reflink success is claimed.

Passed: fresh independent review of `4aebcb7` against `5044d23`, including actual
canonical, preimport, live-repeat and cleanup logs; no important unresolved issues.
The final evidence-only commit receives the canonical pass before completion.
