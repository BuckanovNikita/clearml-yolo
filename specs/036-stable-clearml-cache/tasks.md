# Tasks: Stable ClearML parameter identity

## Foundation

- [x] T001 Record approved requirements, research, interfaces and architecture.
- [x] T002 Validate architecture plan and analyze requirement/task coverage.

## Implementation

- [x] T003 [P] [US1] Add failing publication/replay tests; implement shared General
  projection and preserve canonical native replay settings. Publication agent owns
  parameters, native_runtime, detectors, Hydra common and related tests.
- [x] T004 [P] [US2] Add failing installed-SDK hashing tests; implement conservative
  controller normalizer and explicit versioned identity. Cache agent owns cache module/tests.
- [x] T005 [US2] Propagate validated dataset cache identity through PreparedDataset
  and training provenance; test root relocation and differing dataset identity.
- [x] T006 [US3] Integrate streams and extend architecture negative coverage.

## Verification and Documentation

- [x] T007 Run focused/full behavior, architecture, Ruff, mypy and Vulture checks.
- [x] T008 Verify real CPU native publication and controller cache miss/hit/miss.
- [x] T009 Update tracking contract, index, README/technical guidance and corp-skills
  usage/evaluation; validate docs, links and examples.
- [x] T010 Obtain fresh independent review after integration/checks; resolve findings.
- [x] T011 Reconcile actual scope/evidence and validate architecture acceptance.
- [ ] T012 Follow commit procedure, native Git-only release, pushes and ref verification.

## Independent review follow-up

- [x] T013 Restore legacy General-only execution settings on remote replay without
  changing modern canonical precedence or current output routing.
- [x] T014 Reject malformed device/cache-token collisions conservatively.
- [x] T015 Preserve Unicode through the SDK JSON/HOCON replay parser.
- [x] T016 Enforce the two pure projection modules' dependency/effect boundaries
  with scoped positive/negative tests and a fresh-process import/call guard.
- [x] T017 Qualify canonical replay documentation for embedded application callers.
- [x] T018 Preserve JSON whose escape semantics differ from SDK replay, with actual
  SDK regressions for Unicode, escaped slash and control escapes.
- [x] T019 Retain ClearML project identity when it selects unresolved input models,
  and pipeline run roots when skipped stages consume existing outputs.
- [x] T020 Restrict device normalization to selectors accepted by the relevant
  native/detector/export consumer; preserve unsupported aliases and invalid forms.

## Remaining gate recorded on 2026-10-16

T008 remains blocked by the shared environment's capacity WAIT. No live resources
were created. T011 reconciliation is recorded, but its acceptance validator fails
solely on the unexecuted live check. T012 release remains unstarted. Local checks,
documentation and independent source review are complete; they do not replace the
required live publication/cache evidence.

## Live acceptance resumed on 2026-10-20

T008 passed using real native CPU publication and the installed SDK's external
`ClearmlJob` cache lookup against the live server. A plain, uninstrumented repeat
established miss/hit/scientific-miss after an independently observed diagnostic
run; direct single-GPU training/publication also passed. The first remote attempt
failed native model enrichment once; neither repeat reproduced it, and its cause
remains unconfirmed. See [verification.md](verification.md#live-acceptance-resumed-2026-10-20)
for evidence boundaries and cleanup. T011 final integrated reconciliation and
T012 delivery remain parent-owned.

## Final integration on 2026-10-20

Task 037 completed the combined source/configuration/documentation checks and fresh
independent review. T011 is accepted against that integrated delta; T012 Git delivery
is recorded in the stage-zero cutover after the preservation commit.
