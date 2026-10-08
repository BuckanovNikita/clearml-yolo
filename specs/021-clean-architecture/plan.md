# Clean Architecture and Pandera Implementation Plan

## Approved design
Use `core`, `application.contracts`, `application.ports`, `application.use_cases`, responsibility-specific `adapters`, and `entrypoints`. The external `hydra_plugins.cy_queue` root remains the public launcher target. Entry points compose adapters; adapters implement application ports; application workflows depend inward on ports/contracts/core. Core holds scientific records/policies and Pandera schemas. No legacy import shims.

## Technical context
Python 3.12, uv/uv_build, strict mypy, Ruff, pytest, import-linter 2.13. Add pandera[pandas]>=0.34.1,<0.35, numpy>=1.24.4, pandas>=2.1.1 without unrelated upgrades. Preserve approved external source trees.

## Phases and ownership
1. Record approved requirements, exhaustive module migration, characterization baseline and constitution amendment.
2. Extract domain records/schema validation; preserve invalid-box and raw prediction behavior.
3. Extract adapters, computation/rendering, identity storage and observable diagnostics.
4. Inject workflow ports, normalize Hydra at entrypoints, remove helper cycle/import effects; update runtime targets.
5. Enforce complete import rules and negative architecture tests.
6. Validate all affected behavior, documentation, packaging and native acceptance; independent review and Git-tag-only release.

Parent owns migration/integration, pyproject/lock, architecture contracts and final checks. Parallel agents get disjoint source/test ownership, no recursive delegation. No agent commits independently.

## Interfaces
DatasetStore, ModelRunner, EvaluationEngine, EvaluationWriter, ModelRepository, TrackingSession, Publisher, ReportRenderer, RunStorage and ExecutionResources are explicit typed application ports. ComputedEvaluation carries scientific outputs; EvaluationArtifacts carries dashboard frames and paths. SDK types remain in adapters. Existing data-bearing model fields are retained.

## Validation
Pandera schemas distinguish raw GT, prepared GT, raw predictions, evaluation predictions, results and publication inputs. coerce=False, strict=False, no automatic row drop. CSV lexical parsing and image I/O stay adapters. Errors map to structured project findings without changing recoverable policies.

## Migration and documentation
Read migration-map.json. Regenerate YAML with changed configuration-model targets into a new directory and transfer settings; retain native YAML. Update docs/current-contracts.md, docs/development.md, README.md, affected maintained contracts, and docs/import-boundaries.md and docs/python-import-migration.md. Validate Markdown/local links and examples. Preserve dated history.

## Constitution check
Approved redesign requires targeted amendment of Principles I–III and relocated links; preserve other principles, ratification/history and installed templates/scripts. No behavior changes to recovery/publication contracts are implied.

## Acceptance
Full pytest, Ruff, strict mypy, lint-imports, applicable hooks; installed wheel/sdist and ten helps; architecture injection tests; real CPU/GPU baseline/candidate/download, configuration replay, queue/optional-publication/failure tests per E2E skill. Record unverified gates honestly. Review before release, use Git tags only.
