# Cross-artifact Analysis — 2026-09-28

## Scope

Reviewed the specification, plan, tasks, constitution, current CLI contracts, implementation,
installation guidance, shared skills, and dated release evidence. This is a retrospective
Spec Kit record for implemented code and the completed v0.3.0 publication workflow.
The user explicitly authorized including concurrent dependency and skill changes.
The [native configuration feature](../003-ultralytics-config-groups/spec.md) later superseded
the sparse native configuration details with top-level shared and prediction groups and two
additional generated files; constitution 4.0.0 governs that current behavior.

## Requirement Coverage

| Requirement | Tasks | Evidence or acceptance |
|---|---|---|
| FR-001 | T005–T008 | Entrypoint metadata, nine installed helps |
| FR-002 | T005–T006, T014 | Eight command examples and Hydra round trips; the [native configuration feature](../003-ultralytics-config-groups/spec.md) later added two native group files |
| FR-003 | T005–T006, T014 | Collision, force, symlink, directory, unrelated-content checks |
| FR-004 | T006–T007, T014 | Initialization without service configuration; dependency boundaries |
| FR-005 | T005, T008, T014 | Usage comments, required inputs, native overrides |
| FR-006 | T003, T009–T012 | Zero first-party future imports; runtime/typing gates |
| FR-007 | T003–T004, T008, T013, T016 | Constitution 3.0.0 and current contract amendments |
| FR-008 | T012, T014–T017, T021 | Repository, distribution, documentation, live, and failure checks |
| FR-009 | T017–T018 | Commit, pushed source/tag, downloadable checksummed assets |
| FR-010 | T019, T021 | Unchanged gitlink revisions, editable sync, explicit Git package installation |
| FR-011 | T020–T021 | Canonical skill tree, host metadata, template/script contracts |
| SC-001 | T005, T014 | Every example composes through its installed command |
| SC-002 | T005, T014 | User-content protection assertions |
| SC-003 | T009–T012, T017 | AST inspection and complete repository gates |
| SC-004 | T014, T021 | Both distributions expose all nine commands |
| SC-005 | T018 | Remote source identity and downloaded asset hashes |

All 11 functional requirements and five success criteria have task coverage. All 21 tasks
support an identified requirement, validation step, or necessary workflow setup. US1 and US2
were independently testable; US3 publication followed the combined verification gates.

## Findings and Resolutions

- The former constitution required a future import and prohibited configuration generation.
  The explicit user instructions superseded those policies in constitution 3.0.0. Constitution
  4.0.0 and the [native configuration contracts](../003-ultralytics-config-groups/contracts/configuration.md)
  now govern native groups. Historical evidence remains untouched.
- Initial release documents excluded the concurrent submodules and skills. The user's scope
  confirmation superseded that assumption; FR-010/011, T019–T021, and installation evidence
  now cover them. Upstream source files and approved revisions remain unchanged.
- Distribution metadata does not carry uv editable source selection. Release instructions
  therefore provide explicit pinned upstream Git requirements; fresh installs verify this path.
- The first live upload error is documented separately from the successful retry. Upload
  rejection injection is distinguished from an actual service outage; multi-GPU and model
  accuracy claims are explicitly limited.
- Relative validation-guide links were corrected to repository paths. Shared skills use
  installed script keys and composed template output; analysis resolution preserves the pointer.

No unresolved requirement ambiguity, duplicate requirement, or constitution conflict was
identified. Publication tasks closed after verification of the remote tag and downloaded asset hashes.
All 21 tasks are complete. This retrospective report does not claim planning preceded implementation.

See the [dated evidence](../../docs/evidence/2026-09-28-release-030.md) and
[task record](tasks.md) for execution state.
