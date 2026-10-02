# Agent workflow policy

Read this policy before Spec Kit workflow stages, including planning, bug-source capture
and governance updates. The [agent instructions](../AGENTS.md) route tasks here; this
project policy supplements the installed skills without changing their files.

## Spec Kit integration

Keep installed Spec Kit skills, extension commands, templates and other `.specify/`
files unchanged unless the user explicitly requests a change to those files. Put
project workflow policy in this file or separate project hooks. Project feature
specifications under `specs/` remain project documentation.

### Automatic workflow routing

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
- For planning-only, read-only, or explicitly limited requests, perform only the
  authorized workflow stages and return the requested result. Follow the active host
  mode and retain applicable review gates; automatic routing does not authorize
  implementation, commits, deployment, or changes to installed workflow tooling.
- Do not ask the user to invoke the next skill when the completion request already
  authorizes that stage. Continue through the applicable stages and completion gates;
  ask only for material missing information or a new scope decision. If a required
  skill is unavailable, report the gap accurately.

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
