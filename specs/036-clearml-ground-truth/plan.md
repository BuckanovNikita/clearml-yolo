# Implementation plan

## Summary and technical context

Implement the approved [specification](spec.md) in the existing uv/uv_build Python
>=3.12.13,<3.14 package. Keep the protected external dependency revisions and all
existing CSV/publication behavior. The working tree was clean at baseline 129b94b.
No installed workflow tooling or constitution changes are required.

## Architecture

The [architecture record](architecture.json) governs scope, ownership and checks.
Application contracts define ClearMLDatasetRef and ResolvedGroundTruth. A typed
GroundTruthRepository port returns a local CSV and remote provenance. The new
ClearML datasets adapter owns SDK calls and CSV hashing; application ground_truth
policy handles input normalization, one local warning and provenance recording.
Composition injects the adapter. No application/core module imports the SDK or
performs filesystem effects. Existing SDK ownership gets one exact adapter edge.
Resolved records pass through nested stages, including derived training CSVs, to
avoid repeated lookup/warnings. Consumers continue reading ordinary Paths.
Hydra and queue validation validate selectors without fetching them; help stays lazy.

## Implementation sequence and ownership

1. Parent records spec/plan/tasks, validates architecture and analyzes coverage.
2. Parent implements typed source contracts, resolver, command/queue integration and
   behavioral regressions. Dependency agent independently owns dependency metadata,
   lockfile, packaging tests and minimum-version investigation after the plan gate.
3. Documentation agent updates current user/contract guidance and portable usage skill
   after public interfaces are fixed. Parent owns integration and dated verification.
4. Parent verifies combined changes, runs real CSV-only ClearML retrieval, reconciles
   architecture/diff and obtains fresh independent review. Resolve findings before
   the authorized conventional commit and Git-tag-only native release workflow.

## Dependency compatibility

Remove project optional-dependencies and merge queue-ui/detectors/export into runtime.
Keep dev separate, upstream extras, exact pins and upper bounds. Start isolated
minimum-resolution experiments at existing supported floors; test both Python
minors, raise only demonstrated incompatible floors, and retain exact evidence.
Do not call a resolver result a passing runtime check. Normal uv.lock preserves
existing versions where possible; minimum-test resolutions are separate evidence.
Missing external access or checks remain acceptance gaps, not inferred passes.

## Documentation and acceptance

Update README (Russian), input provenance, current contract index, model/queue and
development installation guidance, and corp-skills clearml-yolo usage/evaluation
references. Preserve historical evidence. Run focused and full pytest, Ruff, mypy,
Vulture, import-linter, architecture positive/negative tests, documentation checks,
wheel metadata/default installation and dependency-minimum checks. Real ClearML
fixture execution follows the native and machine-environment skills with task-owned
resources. Architecture acceptance follows integration, checks and independent review.

## Integration amendment — 2026-10-20

The upstream branch advanced from the inspected baseline to `41a4036` (version
0.35.0) during verification, adding stable cache/configuration and early publication.
Preserve those changes when integrating this feature, rerun affected/native checks
and review the resulting combined implementation. Other worktrees contain unrelated
changes and must remain untouched.

The full regression suite exposed an export ordering regression: missing required
inputs reached task initialization. Extract the existing operation-presence policy
into pure `ExportSettings.validate_input_presence`, reused by `ExportRequest` and
the application before task creation or remote resolution. Keep final request
paths typed and preserve the original validation messages. Existing core import
and no-effect contracts cover this scoped change.

Independent review reproduced an SDK selective-download edge case that retrieves
unrelated external links. Enforce the approved CSV-only logical dataset inventory
before materialization; reject additional files or links and retain root-missing
and unfinalized failures. Cover the failure before fixing it and repeat native
rejection checks. Document archive transport/cache limitations separately from
the selected CSV and its unchanged media references.

Full integration testing exposed exact old constructor/path assertions. Preserve
manual and positional `WorkflowDependencies` callers by adding the new repository
as an optional final capability with default `None`; composition still injects it.
Only ClearML selector resolution requires that capability and fails clearly if
absent. Local paths remain usable with the old constructor. Update test fixtures
to compare accepted path values semantically, and verify the old constructor as
an executable compatibility regression before final acceptance.
