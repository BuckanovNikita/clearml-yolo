# Tasks: ClearML ground truth and default dependencies

## Foundation

- [x] T001 Record approved requirements and decisions in spec.md and plan.md.
- [x] T002 Validate architecture.json plan phase and analyze requirement coverage.

## US1 — ClearML annotation sources

- [x] T003 [US1] Add failing selector/resolver tests in tests/test_ground_truth_sources.py.
- [x] T004 [US1] Implement source records and repository port in src/clearml_yolo/application.
- [x] T005 [US1] Implement deferred dataset CSV resolution in src/clearml_yolo/adapters/clearml/datasets.py and inject it in src/clearml_yolo/entrypoints/composition.py.
- [x] T006 [US1] Integrate all consumers and derived paths in src/clearml_yolo/application/use_cases.
- [x] T007 [US1] Validate Hydra, queue and replay source mappings in src/clearml_yolo/entrypoints/hydra and tests/test_ground_truth_sources.py.

## US2 — Local compatibility

- [x] T008 [US2] Implement execution-only local warnings and internal-path suppression in src/clearml_yolo/application/ground_truth.py; cover them in tests/test_ground_truth_sources.py.

## US3 — Complete default installation

- [x] T009 [P] [US3] Add metadata regressions in tests/test_default_dependencies.py and update tests/test_tooling_boundaries.py.
- [x] T010 [P] [US3] Merge runtime extras and verify minimum floors in pyproject.toml and uv.lock, retaining protected sources; record dependencies evidence.
- [x] T011 [US3] Update missing-dependency diagnostics in queue.py and adapters/rfdetr/backend.py.

## Integration and verification

- [x] T012 Verify positive/negative architecture and all affected behavior; record results in verification.md.
- [x] T013 Run real ClearML CSV-only retrieval and wheel/default/minimum-environment checks; record native and dependency evidence.

## Documentation update

- [x] T014 Update README.md and docs input, installation, queue and current contract guidance after T006/T010.
- [x] T015 Update and validate corp-skills clearml-yolo source usage/evaluation guidance after T014.
- [x] T016 Validate changed Markdown, links, configuration examples and packaging instructions.

## Acceptance and release

- [x] T017 Obtain fresh independent review after parent integration/checks and reconcile architecture.json with actual diff and evidence.
- [x] T018 Complete task-owned conventional commits and native Git-tag-only release/delivery after acceptance.

## Dependencies and parallel ownership

T001–T002 gate implementation. Parent owns T003–T008/T011 and application integration.
The dependency agent owns T009–T010 and dependency evidence, including isolated
minimum-version environments. Documentation can proceed after interfaces are fixed;
T012–T018 require integrated results. No child may delegate further. Changes to
pyproject.toml are split by hunk: dependency tables belong to the dependency agent,
import-linter contracts belong to the parent.

## Requirement coverage

FR-001–004: T003–T007/T013. FR-005: T007–T008/T012.
FR-006–008: T009–T011/T013. FR-009: T014–T018.
SC-001–004 are covered by T012–T018. No unresolved specification ambiguity remains.

## Concurrent baseline integration — 2026-10-20

T001–T017 record the completed feature work and checks on the earlier integrated
source at task commits `a3f4c5a` and `de726d9`; they are not acceptance of the new
merge. Preserve that history. The fully checked/built `aaa35d9` / `v0.36.0`
candidate was not pushed because the ancestry gate detected upstream `0340e9c`.
The ledger now belongs to the new `001` epoch. T018 stays pending.

- [x] T019 Preserve upstream cleanup, dedicated `ruff.toml` / `.importlinter` settings and relocated frozen fixtures while integrating the feature's exact SDK/classification rules.
- [x] T020 Reconcile current guides, the contract index and relocated feature records; validate Markdown, links and unchanged public examples on the merged tree.
- [x] T021 Rerun affected/static/import checks and both minimum-version affected groups after T019; record results without replacing earlier evidence.
- [x] T022 Reconcile architecture and obtain fresh independent review of the merged source/docs after T020–T021.
- [x] T023 Rebuild the release from current master, pass required full commit/release hooks and final-source wheel probes, then complete T018 with verified branch/tag delivery.
- [x] T024 Reconcile companion skill source links/evidence with this new feature path and the final published application commit before the companion collection release.

Parent owns T019/T021–T024 and the architecture record; the documentation agent
owns T020. These gates are sequential after their declared dependencies; existing
runtime contracts, approved dependency revisions and historical checks are preserved.

## Final closure

All task and integration gates are complete. [Delivery](release.md) records the
verified application `v0.36.0`, final build artifacts, companion `v0.2.12`, executed
checks and remaining out-of-scope verification limits. Earlier pending statements
retain their chronological context and are superseded by this closure.
