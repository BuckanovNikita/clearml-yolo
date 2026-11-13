# Agent workflow policy

Read this policy before Spec Kit workflow stages, including planning, bug-source capture
and governance updates. The [agent instructions](../AGENTS.md) route tasks here; this
project policy supplements the installed skills without changing their files.

Record Python compatibility, architecture, documentation, verification and authorized
release evidence within these routes, following the project contracts and development
procedures linked from [AGENTS.md](../AGENTS.md). Spec Kit retains its
stage order, artifacts, execution roles and status ledger. Shared skills do not establish
a second plan or review process. Inspect current code, configuration, hooks and changes
before relying on historical task claims; preserve unrelated work and ignored local configuration.

## Spec Kit integration

Each normative rule has one authoritative topic location and a linked executable
check, or an explicit verification limitation. The [contract index](current-contracts.md)
is navigation, not a duplicate specification. Contract changes reconcile specification,
implementation, tests, examples and portable usage guidance together. Architecture
gates inspect the actual product graph and source; unit tests exercise product behavior.

Keep installed Spec Kit skills, extension commands, templates and other `.specify/`
files unchanged unless the user explicitly requests a change to those files. Put
project workflow policy in this file or separate project hooks. Project feature
specifications under `specs/` remain project documentation.

### Automatic workflow routing

The [product specification](../specs/000-baseline/spec.md) and linked capability
contracts define desired behavior and acceptance. New feature work uses its own
native Spec Kit artifacts; keep implementation status out of product requirements.

Use Spec Kit for new capabilities and changes to documented behavior. Routine fixes,
documentation edits and small refactors proceed directly; update the existing native
task artifacts when applicable. Keep historical execution records in Git history. Planning-only and read-only
requests remain read-only. Verify the original failure path for bugs.

Record the task outcome, compatibility boundaries, affected documentation, concrete
acceptance checks and authorized stopping point in the native ledger. Reconcile them
with the final diff and actual check evidence before completion. Existing user or standing
authorization covers its stated commit/release scope without another stage prompt;
explicit no-commit/no-release limits and the active host mode take precedence. Evaluate
the [native release workflow](development.md#local-releases) after
[change acceptance](development.md#acceptance-tiers); the `release` skill owns the
procedure. A docs-only change may correctly produce no version tag. Deployment and package publishing remain
separate actions requiring explicit authorization.

Project wheels (`.whl`) and source archives (`.tar.gz`) are debugging tools only.
Do not add their construction, installation or delivery to routine release gates.
Use source-checkout verification for releases; a concrete packaging/install
debugging task may build local diagnostic distributions. This project-specific
rule takes precedence over shared skills' generic packaging checklists.

### Module boundaries

For affected Python modules, inspect the contracts in [.importlinter](../.importlinter),
[architecture task](../scripts/architecture.py) and the
[architecture guidance](development.md#python-integration-and-architecture).
Preserve responsibilities, interfaces, dependency direction and effect ownership.
Account for type-only and dynamic imports and justified exact-edge exceptions.
When boundary coverage is missing, extend the architecture task to inspect the affected
product boundary. Keep existing rules intact and
avoid unrelated repository refactors.

Run the applicable [verification stages](development.md#verification); the
`verification-workflow` skill selects them. The development check stage includes import/initializer/runtime-target architecture
checks; effect ownership remains a review obligation after removal of custom effect
enforcement. Automatic routing follows the staged/latest-commit classifier in Task;
explicit acceptance keeps its full scope. The full unit suite includes CPU-DDP. Reuse their results while the checked inputs remain unchanged.
Report deferred and waived checks as such, never as passed. Reconcile the final
task-owned diff with contract coverage and record actual results in dated evidence.

### Documentation

Update affected user guidance with behavior changes. Complete applicable native Spec Kit
analysis and consistency review as soon as inputs exist, before expensive checks. Use
only documentation checks native to Spec Kit or OpenSpec; no separate checker applies.

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
  Task templates do not authorize pushing or deployment.
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
