# Verification Evidence: Native ClearML tracking

**Date**: 2026-09-30
**Feature**: [spec.md](spec.md)
**Status**: implementation, repository gates, real acceptance and final convergence completed; limitations are stated below.
**Evidence attribution**: root executed real acceptance and combined gates; relay/publication agents executed scoped checks. This document records their reported results and independent read-only code review, not additional unseen executions.

## Repository Verification

| Check | Result |
|---|---|
| DDP regression suite | 22 passed; required-field corruption regressions reproduced failure before correction. |
| Assigned native tracking/publication/configuration tests | 17 passed; 105 affected tests passed in the broader scoped run. |
| Additional native model failure checks | 6 passed; existing native/model retrieval checks also reviewed. |
| Final full pytest | 698 passed, 8 optional FiftyOne skips, 4 existing Hydra/Pydantic deprecation warnings; 111.50 seconds. |
| Ruff | Passed. |
| Strict mypy | Passed, 93 source files. |
| Import-linter | Passed, nine contracts. |
| Diff whitespace | Passed in independent read-only review. |
| Feature Markdown | Final local-link, final-newline and code-fence validation passed for all feature and assessment documents. |

## Real Native Acceptance

Three-epoch CPU training completed in 52.6 seconds; three-epoch single-GPU training completed in 62.1 seconds. Root queried backend loss scalar histories at native epochs 0, 1 and 2 before allowing training to continue. Both runs exposed native plots/debug samples and exactly one native best Output Model. Forced-download hashes matched local best checkpoints and downloaded models loaded successfully.

| Acceptance command/run | Performance artifact count |
|---|---:|
| Ground truth | 1 |
| CPU pipeline | 8 |
| GPU candidate pipeline | 11 |
| Validation | 5 |
| Comparison | 4 |
| Report | 2 |
| Invalid configuration failure | 0 |

Inventories contained only allowed performance evidence. Temporary numbered YAML and training override JSON were not artifacts; consumed source settings and meaningful provenance remained in configuration. Exact frozen validation thresholds and identical paired current-test sources were checked. Shared cached input hashes remained unchanged.

## Failure and Cleanup Evidence

Five controlled SDK-boundary faults used a real tracking backend: rejected artifact upload, false flush confirmation, native callback connection failure, missing native model registration and SIGTERM interruption. Each failed the command/task, retained local outputs and published no artifacts/models in these cases. These are injected boundary failures, not claims that spontaneous backend faults occurred.

Root cleanup reported zero remaining task-owned tracking tasks/projects after acceptance. Pre-existing resources were preserved.

## Review and Convergence

Independent review checked current relay lifecycle, native callback compatibility, owner context, event ordering, partial-record buffering, terminal model-publication deferral, cleanup and publication/configuration regressions against the approved feature and constitution.

First convergence identified missing nonterminal field validation: incomplete but syntactically valid records could default away losses/epochs and still permit final publication. T017 added field validation before dispatch and eight failing-before-fix regressions. Re-review found no further actionable code gap. Final convergence checked all 11 functional requirements, five success outcomes, acceptance scenarios, plan decisions and five constitution principles. No actionable gaps remain; converge left tasks.md unchanged. Separate implementation bookkeeping then marked T014–T016 complete from final evidence. No application code changed after the passing final gates.

## Harness Corrections and Limitations

The acceptance harness initially expected training loss at an extra native final-validation fit event; its gate was corrected to respect upstream final-best semantics. Its inventory expectation also omitted a valid candidate-evaluation workbook when no baseline was available; that expectation was corrected. Initial failed task-owned runs were cleaned and logs retained. These harness corrections were not application fixes.

Physical multi-GPU DDP was unavailable; simulated live relay coverage does not establish physical DDP. Remote-agent cloned-task configuration recovery was verified with mocked replay coverage, not a live remote agent. No commit, push or release was performed. Machine-specific paths, endpoints and credentials are intentionally excluded from this portable record.
