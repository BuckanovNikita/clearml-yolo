# Tasks: automatic multirun tags

## Setup and architecture

- [x] T001 Inspect direct/queue launch and tracking contracts; record scope in plan.md.
- [x] T002 [P] Independently investigate launch edge cases alongside parent planning.
- [x] T003 Validate architecture.json before implementation and analyze artifact consistency.

## US1 — group tasks from one launch

- [x] T004 [US1] Add failing real Hydra/queue regressions in tests/test_multirun_tags.py.
- [x] T005 [US1] Add shared tag helper in src/clearml_yolo/entrypoints/hydra/sweeps.py.
- [x] T006 [US1] Integrate invocation-local direct tagging in src/clearml_yolo/entrypoints/hydra/common.py.
- [x] T007 [US1] Freeze queued tags in src/clearml_yolo/entrypoints/hydra/queue_config.py.
- [x] T008 [US1] Verify behavior, dependency contracts and static checks; record verification.md.

## Documentation update and acceptance

- [x] T009 Update README.md, docs/queue.md, docs/project-contracts.md and docs/current-contracts.md.
- [x] T010 Validate changed Markdown/local links and documented validation commands.
- [x] T011 Obtain fresh independent review and reconcile architecture.json against the final diff.
- [ ] T012 Complete authorized checked commit and Git-tag-only release workflow.

Dependencies: T001–T003 precede T004; T004 precedes T005–T007; T008 follows integration.
T009–T010 follow the implementation contract; T011 follows verification; T012 follows acceptance.
Only investigation is delegated in parallel; the parent owns shared launch/test files.
