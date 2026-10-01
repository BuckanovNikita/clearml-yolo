# Verification: Workspace-owned filesystem defaults

Date: 2026-10-01. Scope: the current working-tree filesystem implementation, with unrelated
concurrent changes preserved. No commit, dependency update or deployment was performed.

## Observations and corrections

Regression checks initially demonstrated the home-based default dataset cache, missing startup
initialization, source-adjacent execution copies and unowned bare-checkpoint download destination.
Startup auditing and independent investigation also identified native directory aliases, DDP
launcher storage and native image/label cache writes requiring explicit ownership.

Corrections preserve protocol model references, explicit relative checkpoint paths, native source
ordering and configured weight directories. Cache identity excludes the incidental execution YAML
filename. Native NDJSON/platform inputs retain supported upstream conversion before staging.

The first fresh acceptance review returned `fix-first`: staging had reused ground-truth
membership expansion, and the tracked ground-truth command discarded an expanded output path.
Added regressions reproduced both failures. Native-specific expansion now matches the installed
reader's duplicate, ordering and cwd/manifest-relative behavior; ground-truth publication and the
returned result now use the actual conversion output path.

A second fresh review identified cwd-dependent manifest cache collisions and read-only copied
permissions. Regressions reproduced both; identity now includes resolved manifest membership,
and copied images/labels receive owner-write permission without changing their sources. Parent
inspection additionally reproduced an explicit native NDJSON conversion-directory override;
conversion now preserves that selection. The specification introduction was aligned with FR-004:
warnings apply to every physical-home write destination, including workspace defaults.

The next review identified a pipeline prediction handoff coercing original references into
`Path`. Five parameterized regressions reproduced URI and string-intent loss. The pipeline now
passes the original reference through prediction; local comparison resolves bare cache names
and rejects unresolved remote references with guidance rather than coercing their schemes.

The first broad check exposed stale test assumptions about mutable working-directory defaults and
the former `RUNS_ROOT` constant. Those tests now select their workspace through `CY_HOME` while
retaining the original routing and remote-replay assertions.

## Executed checks

Runner cache/config/temp variables were explicitly routed to an ignored verification directory.
`uv run --no-sync` used the existing environment without dependency resolution or lock changes.

| Check | Result |
|---|---|
| Affected revised filesystem/native/model/training selection | 55 passed |
| Review correction selection, including native membership and tracked ground truth | 66 passed |
| Final affected selection, including cache/permission and NDJSON directory regressions | 70 passed |
| Final pipeline/model and filesystem acceptance selection | 114 passed |
| Publication command routing/replay selection | 12 passed |
| Full pytest suite after all corrections | 717 passed, 8 skipped; 4 upstream Pydantic deprecation warnings |
| Ruff | Passed |
| Strict mypy | Passed: 96 source files |
| Import-linter | Passed: 9 contracts kept, 0 broken |
| All nine CLI `--help` invocations | Passed |
| Configuration generation | Eight command YAML examples and both native groups generated |
| Generated training example with explicit cache/project overrides | Composed and resolved with both selected paths retained |
| Changed Markdown parsing/fences/whitespace and local links | Passed: 24 files, 101 links |
| `git diff --check` | Passed |

Logs and reproducible validation helpers are retained under `outputs/cy-filesystem-verification/`.
Task-owned fixture directories were removed after checks; logs and scripts remain available.
The full suite includes real dependency startup auditing and a real `YOLODataset` producing disk
image and label caches on copied fixtures. Source bytes remain unchanged. These checks do not
execute native GPU training or remote ClearML uploads; eight opt-in FiftyOne persistence checks
were skipped because a real isolated database was not selected.
Commit hooks were not run because this task does not create a commit; the relevant application
gates were run directly.

## Documentation and workflow

Reviewed the current contract index and reconciled README, filesystem policy, CLI, dataset-tracking
and configuration-resolution contracts, active specifications, quickstarts and the project-owned
end-to-end skill. Existing global environment examples select their run destinations explicitly;
their external runner/cache setup remains the caller's responsibility under the documented launch
boundary. No machine-specific instructions or installed workflow files were modified.

Spec Kit artifacts were materialized after implementation had already begun, following the updated
working agreement. Read-only prerequisite discovery used `--paths-only`; `.specify` selection state
and installed templates were not modified. Cross-artifact analysis maps all 12 functional
requirements and five success criteria to 22 original tasks. Seven traceable review/inspection
corrections and two final documentation tasks were appended without rewriting completed history.

## Acceptance boundary

Fresh independent reviewer `filesystem_handoff_acceptance` returned `ship` with no code findings
after inspecting the final pipeline correction and retained final gate evidence. Earlier fresh
reviews assessed the broader implementation and their concrete findings were corrected and tested.
Final convergence checked 12 functional requirements, five success criteria, 12 story acceptance
scenarios, six research/design decisions and five constitution principles: no actionable gaps
remain. All 31 tasks are complete; final convergence requires no further task append.

Python's initial package import precedes application bootstrap; a launcher bytecode setting is required to cover that first
interpreter write. Subsequent imports and supported application/dependency defaults are routed.
The policy preserves arbitrary explicit destinations and is not an operating-system sandbox.
Native execution of remote URI schemes, GPU training and remote ClearML uploads remain unverified.
