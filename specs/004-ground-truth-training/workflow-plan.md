# Ground-Truth Training: Remaining Spec Kit Workflow

**Created**: 2026-09-29

**Feature**: [Ground-truth-driven training](spec.md)

**Status**: Specification completed; remaining steps planned, not executed.

This document schedules the remaining feature lifecycle. `$speckit-plan` will produce
the technical `plan.md`; this workflow must be carried into that plan and its generated
tasks so implementation includes verification and convergence, not only code changes.
Commands below are skill invocations, not shell commands.

## Parallel Work and Subagent Orchestration

The user explicitly requests parallel execution and subagents for both planning and
implementation. Apply `astra-advisor:orchestration` throughout those phases. The parent
owns requirements, architecture, integration, verification, and acceptance; delegate
bounded independent work while the parent continues useful work on the critical path.

Before delegation, inspect the available native tool schema and runtime metadata. Emit
the required `ASTRA ROUTE` declaration. Select model and supported effort dynamically
for each task, with explicit controls and no inherited conversation history as required
by the orchestration skill. Do not claim requested model settings as observed runtime
settings. If the required native interface or controls are unavailable, report that
limitation and continue safe parent work; do not silently replace delegation with an
unsupported interface or external agent process.

### Planning Work

After clarification establishes the input contract, run independent investigations in
parallel. Each subagent returns findings, evidence, risks, and proposed decisions; the
parent integrates them into one consistent technical plan.

| Work package | Bounded ownership | Dependencies and acceptance evidence |
| --- | --- | --- |
| Native dataset compatibility | Read-only investigation of the locked runtime's NDJSON/local-image behavior and flat dataset requirements | Starts from the spec; returns exact compatibility evidence, conversion side effects, and split-preservation constraints. |
| Command and configuration contracts | Read-only investigation of training/pipeline configuration, precedence, resume, and output routing | Starts from the spec; returns affected public contracts and an explicit override/rejection matrix. |
| Verification and tracking requirements | Read-only investigation of existing test seams, artifact contracts, task lifecycle, and integration acceptance | Starts from the spec; returns a requirement-linked test matrix, failure scenarios, and real-run prerequisites. |
| Parent architecture and synthesis | Sole ownership of final `plan.md`, shared data model, interfaces, and integrated decisions | Parent reviews all returned evidence, resolves conflicts, checks constitution compliance, and produces a coherent plan before task generation. |

These are independently bounded packages, not a fixed agent count or model-to-role
assignment. Combine or sequence packages when actual tool support or dependencies
make that more appropriate. Do not ask several agents to duplicate the same investigation.

### Implementation Work

`$speckit-tasks` MUST encode dependencies and parallel eligibility explicitly. After the
parent establishes shared interfaces, schedule disjoint implementation packages such as:

- CSV validation, invalid-box dropping/counting, and canonical cleaned dataset records,
  with owned behavior tests.
- NDJSON export and flat export in parallel once the canonical record contract is stable,
  each with separately owned files and format-specific tests.
- Command/configuration integration once preparation interfaces are stable, with one
  owner for shared training, pipeline, and configuration files.
- Preparation artifact and tracking integration where its write set is independent of
  command integration; otherwise schedule it after the shared-file owner finishes.
- Documentation and generated-example updates after public parameter names and behavior
  are settled, alongside remaining independent implementation work.

Before each dispatch, name the task, exact owned paths, read-only/shared paths, dependencies,
requested model/effort, and required acceptance evidence. Resolve actual file ownership
from the technical plan rather than guessing module names here. Never assign concurrent
writers to the same file. Return changed paths, checks performed, and unresolved concerns.
The parent inspects and integrates every change without overwriting unrelated work.

Run independent local checks in parallel where safe. Real training jobs may run in
parallel only after checking available capacity and resource ownership; isolated output
directories and tracking identities are mandatory. Parallelism does not authorize changes
to pre-existing shared services or oversubscription of the integration environment.

### Review and Reporting

After integrating the implementation, the parent inspects the complete diff and reruns
the required checks. Then dispatch a fresh read-only subagent review with the actual
change set, specification, and verification evidence. Require the orchestration skill's
`ASTRA REVIEW` verdict; accept a substantial implementation only after `ship`. For
`fix-first`, correct findings, verify again, and obtain a new fresh review. An unavailable
review interface must be reported as an acceptance limitation, not a completed review.

Show lifecycle updates before every delegation and on completion or failure, including
agent identity, bounded ownership, and observed versus requested model/effort where
available. Include the required API-equivalent cost receipt, with unavailable usage
reported honestly and no invented delegation savings.

## Ordered Steps

| Step | Invocation or activity | Required outcome and exit condition |
| --- | --- | --- |
| 1 | `$speckit-clarify` | Review the current assumptions about local images, existing splits, detection scope, flat layout, native-data compatibility, and override precedence. Record any material answers in `spec.md`; if no material ambiguity exists, report that without inventing questions. |
| 2 | `$speckit-plan` | Generate `plan.md` and applicable research, data-model, contracts, and quickstart artifacts. Resolve locked-runtime NDJSON compatibility and complete the constitution check. Include the remaining workflow below in the plan. |
| 3 | `$speckit-checklist` | Generate a feature-specific requirements checklist covering conversion fidelity, split isolation, class identity, configuration precedence, data ownership, compatibility, and tracking failures. Resolve requirement gaps before task generation. |
| 4 | `$speckit-tasks` | Generate dependency-ordered `tasks.md` from the specification and technical plan. Trace all FR-001–FR-019 and SC-001–SC-006 to implementation or verification work, including documentation and both real-run format paths. |
| 5 | `$speckit-analyze` | Analyze consistency and coverage across `spec.md`, `plan.md`, and `tasks.md`. Resolve blocking findings in the appropriate artifacts and repeat analysis after corrections. Analysis itself remains non-destructive. |
| 6 | `$speckit-implement` | Execute the tasks using existing repository contracts. Deliver CSV validation, both dataset representations, command integration, data override handling, retained preparation records, tests, and user documentation. Record actual task completion and verification evidence. |
| 7 | Repository and real-run verification | Run affected repository gates and the integration matrix below. Retain dated evidence; failures remain unfinished work. This is part of implementation acceptance, not a separate invented Spec Kit command. |
| 8 | `$speckit-converge` | After implementation has run on the complete task list, compare the current code against the specification, plan, and tasks. Append traceable tasks for any remaining work; do not rewrite existing tasks or change code during convergence. |
| 9 | `$speckit-implement`, verification, then `$speckit-converge` as needed | Complete appended tasks, rerun affected checks, and repeat convergence until no unmet requirements remain. If artifacts materially change, repeat `$speckit-analyze` before further implementation. |
| 10 | Final review and handoff | Inspect the complete change set and dated evidence, report requirement coverage and any limitations, and leave no acceptance requirement silently unverified. Commit or push only when requested. |

## Required Technical Planning Decisions

- Confirm how the locked Ultralytics runtime consumes locally referenced NDJSON images,
  preserves supplied splits, and places conversion byproducts inside the run directory.
- Define flat dataset naming, label-stem collision handling, and source-to-generated
  identity records without changing evaluation image identities.
- Specify CSV validation, relative-path resolution, background rows, duplicate handling,
  stable class mapping, and coordinate precision consistently across both formats.
- Define invalid-box dropping without aborting usable runs, a total error-box count shown
  before training, retained error reasons, and one cleaned ground-truth representation
  shared by training and evaluation. Count each rejected annotation once and keep images
  with no surviving boxes as background; distinguish an unusable training set from
  recoverable individual box errors.
- Enumerate native settings that can replace data, filter membership, or alter class
  meanings. Specify override versus rejection behavior, including resume and tracking-side
  configuration, while preserving unrelated native settings.
- Define command defaults, generated configuration examples, standalone native-data
  compatibility, skipped-training behavior, artifact contracts, and task ownership.
- Fit the implementation within current import boundaries without modifying the pinned
  `digital-metrics` dependency. Identify any genuine constitution conflict explicitly.

## Verification to Include in Tasks

1. Prove both formats preserve images, valid boxes, backgrounds, class meanings, and splits,
   with the specified 0.01-pixel coordinate tolerance and row-order independence.
2. Exercise malformed CSVs, missing images, duplicate identities, filename collisions,
   missing splits, conflicting settings, resume conflicts, and preparation failures.
   Verify invalid boxes are dropped without failing usable runs, the exact total (including
   zero) appears before training, multiply-invalid boxes count once, valid sibling boxes
   survive, and training/evaluation share cleaned annotations. Cover images with all boxes
   removed and the separate failure when no valid training instances remain.
3. Check standalone CSV training, legacy standalone native-data training, full-pipeline
   routing, `skip_train=true`, and generated command examples.
4. Run `uv run pytest`, `uv run ruff check .`, `uv run mypy .`, and `uv run lint-imports`
   for the cross-boundary implementation. Run applicable pre-commit checks before any
   requested commit; do not bypass hooks.
5. Use `running-end-to-end-tests` and the applicable environment skill to verify real
   standalone training and full-pipeline execution for both `ndjson` and `flat`. Verify
   usable checkpoints, frozen validation thresholds, paired current-test comparison where
   a baseline is supplied, artifact downloads, and a single completed ClearML task per
   successful invocation. Cover missing automatic and invalid explicit baseline behavior.
6. Verify required upload/flush and interruption failure handling, local-output retention,
   source preservation, output isolation, and exclusion of dataset images from uploads.
   Distinguish controlled failure tests from observations of real external services.
7. Record commands, outcomes, artifact references, and limitations in dated verification
   evidence. Clean up only task-owned temporary resources. Mocked checks do not establish
   native training, GPU execution, or successful ClearML uploads.

## Conditional Spec Kit Steps

- `$speckit-taskstoissues`: Run after tasks and analysis only if GitHub issue publication
  is requested; local tasks are sufficient for execution.
- `$speckit-bug-assess` → `$speckit-bug-fix` → `$speckit-bug-test`: Use for a separately
  tracked defect discovered during the work when that workflow is appropriate. Ordinary
  unfinished feature tasks remain in the implementation/convergence loop.
- `$speckit-constitution`: Use only if an intended feature decision genuinely requires
  an authorized governance amendment; do not weaken existing principles to pass a gate.
- `$speckit-assess-*`: No intake or investment gate is required to repeat the already
  specified feature. Use these only if a newly raised scope decision needs reassessment.

## Completion Criteria

All specification requirements have implementation and acceptance evidence; required
checks pass; the feature checklist has no unresolved gaps; convergence reports no
remaining work; and final review identifies no unresolved blocking findings. Any unavailable
acceptance environment or failed check must be reported as an outstanding limitation,
not counted as completed verification.
