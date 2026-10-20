# Agent workflow policy

Read this policy before Spec Kit workflow stages, including planning, bug-source capture
and governance updates. The [agent instructions](../AGENTS.md) route tasks here; this
project policy supplements the installed skills without changing their files.

Use `python-project-workflow` to supply Python compatibility, architecture, documentation,
verification and authorized release evidence within these routes. Spec Kit retains its
stage order, artifacts, execution roles and status ledger. Shared skills do not establish
a second plan or review process. Inspect current code, configuration, hooks and changes
before relying on historical task claims; preserve unrelated work and local overrides.

## Spec Kit integration

Each normative rule has one authoritative topic location and a linked executable
check, or an explicit verification limitation. The [contract index](current-contracts.md)
is navigation, not a duplicate specification. Contract changes reconcile specification,
implementation, tests, examples and portable usage guidance together. Architecture
gates include negative tests proving prohibited behavior is rejected.

Keep installed Spec Kit skills, extension commands, templates and other `.specify/`
files unchanged unless the user explicitly requests a change to those files. Put
project workflow policy in this file or separate project hooks. Project feature
specifications under `specs/` remain project documentation.

### Automatic workflow routing

The [stage-zero specification](../specs/000-baseline/spec.md) starts the current
numbering epoch. New feature artifacts begin at `001` and reference that baseline.
Retrieve retired evidence by its full checkpoint SHA and path; old feature numbers
can recur in the new epoch. Preserve the baseline as a specification, not an active
feature ledger, and retain the installed Spec Kit workflow.

Automatically follow the applicable Spec Kit workflow for every user request to
complete work; explicit skill invocation is unnecessary. Reuse the relevant existing
feature or bug artifacts and preserve completed history. Keep the workflow proportionate
to the request while recording intent, tasks, verification, and documentation outcomes.

- For features and other changes, use `speckit-specify`, `speckit-clarify` when material
  ambiguity remains, `speckit-plan`, `speckit-tasks`, `speckit-analyze`, and
  `speckit-implement`, followed by appropriate verification and the mandatory
  documentation stage below. Use `speckit-converge` when assessing remaining work
  against existing feature artifacts.
- For bugs, use `speckit-bug-assess`, `speckit-bug-fix`, and `speckit-bug-test`,
  including the mandatory documentation stage and verification of the original
  failure path.
- For documentation-only maintenance without application behavior changes, record
  intent, tasks, no-impact architecture and dated checks in documentation evidence;
  use the documentation stage without creating a new application feature specification.
- For resumed work, compare the current implementation and task-owned diff with the
  selected artifacts. Append missing implementation, architecture, verification and
  documentation work without rewriting completed history or retrofitting inactive plans.
- For planning-only, read-only, or explicitly limited requests, perform only the
  authorized workflow stages and return the requested result. Follow the active host
  mode and retain applicable review gates; automatic routing does not authorize
  implementation, commits, deployment, or changes to installed workflow tooling.
- Do not ask the user to invoke the next skill when the completion request already
  authorizes that stage. Continue through the applicable stages and completion gates;
  ask only for material missing information or a new scope decision. If a required
  skill is unavailable, report the gap accurately and continue independent inspection;
  unavailable required gates do not count as acceptance.

Record the task outcome, compatibility boundaries, affected documentation, concrete
acceptance checks and authorized stopping point in the native ledger. Reconcile them
with the final diff and actual check evidence before completion. Existing user or standing
authorization covers its stated commit/release scope without another stage prompt;
explicit no-commit/no-release limits and the active host mode take precedence. Evaluate
the [native release workflow](development.md#local-releases) after acceptance. A docs-only
change may correctly produce no version tag. Deployment and package publishing remain
separate actions requiring explicit authorization.

### Mandatory module architecture planning and acceptance

Use the shared `module-architecture-planning` skill for repository change planning,
implementation, fixes, resumed work and acceptance. Apply it within the native workflow;
do not copy its validator or modify installed Spec Kit skills, templates or `.specify/`
files. If the skill is unavailable, report the missing gate rather than claiming it passed.

Before implementation, inspect task-owned scope, current code and executable contracts.
Record affected modules' responsibilities, interfaces and invariants, placement, allowed
and forbidden dependencies, and effect ownership. Justify additions instead of creating
pass-through modules. Map each affected module to executable boundary coverage in an
adjacent `architecture.json` using the shared skill's record format; the native task ledger
remains authoritative for status.

| Workflow | Architecture placement and acceptance |
| --- | --- |
| Feature or refactor | Add an architecture section and linked record to `plan.md`, then dependent implementation, check and documentation tasks to `tasks.md`. Analyze coverage before implementation; reconcile it during verification. |
| Bug | Add architecture decisions and the adjacent record to `assessment.md` remediation; record actual changes and acceptance in `fix.md` and `test.md`. Keep the bug workflow and verify the original failure path. |
| Resumed work or converge | Compare current scope and code with existing decisions. Missing records or enforcement become explicit remaining tasks; preserve completed history and respect converge's append-only rules. Do not bulk-retrofit inactive plans. |
| Documentation-only | Record `impact: none` with inspected paths and a concrete reason, then validate changed documentation. Runtime fixes and executable contract/checker changes require module impact even if imports stay unchanged. |
| Planning-only or read-only | Return decisions, proposed record content and checks without artifact writes or mutating hooks. Optional stdin record validation is read-only; it does not establish implementation acceptance. |

For this Python project, inspect the actual contracts in
[.importlinter](../.importlinter) and [architecture tests](../tests/test_architecture.py),
with the maintained [architecture guidance](development.md#python-integration-and-architecture).
Reuse their relevant coverage for inward dependencies, exhaustive classification, SDK
ownership, cycles, application/core effects, inert initializers and dynamic Hydra/plugin/
worker targets. Account for type-only and dynamic imports and justified exact-edge
exceptions; stale documentation counts are not coverage evidence. If enforcement is
missing, plan scoped executable checks for affected modules and edges, including a
negative case demonstrating that a prohibited dependency fails. Do not weaken rules,
expand ignore lists or require an unrelated repository refactor to pass the gate.

Resolve `scripts/validate_architecture.py` from the shared skill directory, supply the
repository root explicitly and validate the record with `--phase plan` before
implementation. The skill documents its command and record schema. Include concrete
acceptance commands and expectations in the record and ledger. For runtime module work,
run `uv run lint-imports` and `uv run pytest tests/test_architecture.py` separately,
together with affected behavior and documentation checks and any scoped enforcement
added by the task. These commands complement record validation.

Before acceptance, inspect the complete task-owned diff, including additions, removals,
renames, dependency configuration and composition targets. Reconcile it with module
scope, contract coverage and completed tasks, and identify excluded unrelated work.
Record actual dated check results and negative-case evidence. Review responsibilities,
interface depth, dependency direction and inversion, effect ownership and justified
exceptions against project rules. The final review required by [AGENTS.md](../AGENTS.md)
covers Python and architecture evidence after integration and verification; reuse that
review instead of adding a competing review process. Validate the reconciled
record with `--phase acceptance`; missing, unavailable or failing required checks or
review block acceptance. No-impact work needs its documentation checks outside the
minimal record. The validator checks record structure and references; it neither runs
recorded commands nor proves source quality, truthful evidence or exhaustive diff review.

### Mandatory documentation stage

Every Spec Kit implementation or bug-fix workflow must complete a **Documentation
update** stage after implementation and before reporting completion. This is a required
project completion gate, including when an existing task list omits documentation.

- During planning, identify the documentation affected by the proposed changes using
  [the current contract index](current-contracts.md). Include this scope in `plan.md`
  and add explicit documentation update and validation tasks in a dedicated final phase
  of `tasks.md`, with concrete paths and dependencies on the implementation tasks.
- During implementation, reconcile that scope with the actual code/configuration diff.
  Add missing documentation tasks to the existing ledger without rewriting completed
  history. For bug workflows, record the scope and outcome in the bug's existing
  remediation/verification artifacts instead of requiring a feature task ledger.
- Update affected contracts, active specs, quickstarts, README, migrations and
  project-owned integration skills together. Update the contract index when authority
  changes and applicable global environment examples when execution guidance changes.
  Preserve dated evidence and distinguish verified behavior from intent.
- Validate changed Markdown and local links, and check documented commands/configuration
  examples when their behavior changes. Mark documentation tasks complete only after
  these checks; report their results and any remaining gaps in the completion report.
  Unfinished required documentation or failed validation blocks completion.
- If the changes have no documentation impact, record the reviewed scope and concrete
  reason in the task ledger or bug verification report. A justified no-change outcome
  satisfies this stage; silently skipping it does not.

### Portable usage skill maintenance

The canonical portable `clearml-yolo` usage skill lives in
[corp-skills/skills/clearml-yolo](https://github.com/BuckanovNikita/corp-skills/tree/main/skills/clearml-yolo).
This repository owns application contracts; corp-skills owns the distributable
usage package. Edit its source, not installed skill copies. Machine-specific stand,
GPU and credential setup stays in global environment skills.

For changes to CLI/API, Hydra configuration/defaults, model selection, inputs/outputs,
queue behavior, publication or failure recovery, inspect the skill during planning.
List affected skill/reference paths and dependent update/validation tasks in the
native feature or bug ledger. During the documentation stage, reconcile that scope
with the actual diff, update examples and evaluation cases, or record an inspected
no-change reason for internal-only work. Preserve completed task history.

Before acceptance, verify examples against current entrypoint schemas and source;
use isolated output roots for help/config checks and distinguish them from real
training, GPU or publication evidence. Validate package metadata, local links,
Markdown and discovery following
[corp-skills maintenance](https://github.com/BuckanovNikita/corp-skills/blob/main/MAINTENANCE.md).
Record source version/commit, changed skill paths, actual checks and limitations in
dated workflow evidence, with a companion corp-skills commit when available.
Missing access to the source or required validation leaves an open documentation
task and blocks completion. Follow each repository's authorized release workflow;
skill installation and unrelated dependency updates are separate actions.

### Workflow safeguards

- In host Plan Mode, return read-only findings or a proposed plan before executing
  workflow hooks, mutating setup helpers, artifact writes or generated-file checks.
  Existing authorization satisfies the same action/scope gate; retain only unresolved
  decisions and the explicitly invoked SDD workflow's review gates.
- Before plan setup, use read-only prerequisite discovery and confirm the exact
  `spec.md` exists. Do not call `setup-plan.sh` when missing: that helper can
  create the feature directory and write `plan.md` before specification validation.
- Inspect ignore files without automatic edits outside the authorized task. Always
  verify proportionally; add tests when required by the contract or behavior/risk.
  Task templates do not authorize commits or deployment.
- For bug workflows, normalize slugs and validate containment and existing symlink
  components before I/O. Preserve explicit slug identity on collisions; suffix only
  generated slugs. Apply the URL trust policy before fetching, and redact secrets
  from source URLs and quoted input before persistence. Ordinary web tools may fetch
  allowlisted hosts without peer-IP metadata; raw HTTP or unrecognized-host requests
  must enforce public-address selection. Private/metadata targets remain refused.
- Reassess a disproven bug hypothesis and continue within the authorized bug scope,
  documenting deviations. Ask only for material missing information or scope changes.
- Preserve dated constitution history and keep temporary impact reports in the
  response rather than tracked governance content. Use the current contract index
  to identify amendments instead of presenting historical requirements as current.
