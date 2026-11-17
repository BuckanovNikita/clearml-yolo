# Agent workflow policy

Read this policy before planning, implementing, fixing, resuming or accepting repository
changes. Linear owns active work and GitHub PRs own delivery; follow the
[ticket workflow](agents/issue-tracker.md) for grouping, dependencies and lifecycle.
Inspect current code, configuration, hooks and existing changes before relying on
historical claims. Preserve unrelated work and ignored local configuration.

## Planning and archive policy

Spec Kit is temporarily disabled. Preserve `specs/`, `.specify/`, and archived skills,
commands and templates unchanged. Do not invoke their workflows, generate artifacts,
update their status ledgers or apply their governance gates. Reactivation requires
explicit user instruction. Read archived sources only for historical context and
requirement provenance; transfer requirements needed for active work into Linear.

The archive does not repeal product behavior. The [project contract summary](project-contracts.md)
and [current contract index](current-contracts.md) lead to maintained topic contracts.
Reconcile approved contract changes with implementation, tests, examples and portable
usage guidance. Each normative rule has an authoritative home and an executable check
or explicit verification limitation. Keep historical evidence separate from current claims.

Record the outcome, plan, compatibility boundaries, affected documentation, acceptance
checks and authorized stopping point in Linear. Reconcile them with the final task-owned
diff and actual evidence before completion. Shared skills support this workflow rather
than introducing another specification process. Planning-only requests remain read-only.

Agents may commit task-owned work, push task branches and open PRs; humans merge.
Explicit session limits and host mode take precedence. Code releases are suspended
pending PR-based release tooling; do not invoke the existing local integration or
publication commands. Deployment and package publishing require explicit authorization.
Model-weight release authorization remains separate. Project wheels and source archives
are debugging tools only, never routine verification or release deliverables.

## Engineering safeguards

These safeguards preserve the engineering obligations formerly recorded in the archived
constitution; the archive's stage order and amendment process no longer apply.

- Retain the declared Python compatibility, uv toolchain, uv_build backend and dependency
  constraints. Declare directly imported dependencies; never weaken Ruff or strict mypy
  merely to silence a failure. Executable values belong in maintained configuration.
- Use runtime annotations, absolute imports, typed parameters/returns and `typing.Self`
  where appropriate; quote forward references when runtime evaluation is unsupported.
  Do not introduce `from __future__ import annotations`. Use Pydantic for configuration
  and validated records, Pandera for dataframe validation, and factories for mutable defaults.
- Keep project interfaces explicitly typed. Confine Any, casts and dynamic access to
  necessary external boundaries with clear assumptions. Suppressions name specific codes
  and have a clear reason. Recover or report exceptions at an appropriate boundary;
  never silently discard unexpected failures.
- Use Loguru through the observability adapter and injected ports; preserve CLI output
  contracts, including Rich rendering. Comments and log messages are English. Names and
  decomposition follow responsibilities and configured complexity; use pathlib conventions.
- Keep package initialization inert and runtime initialization explicit. Defer heavyweight
  SDK imports where required for responsive help/configuration. Composition roots inject
  adapters; application use cases do not construct them or use global locators.
- Preserve centralized Hydra contracts, pipeline-owned tracking and output routing,
  isolated run identities, upload/flush completion, credential protection, native backend
  ownership and validation/test separation. The topic contracts define configuration,
  queue resource ownership, recovery order and publication behavior in detail.
- Keep credentials out of tracked files and uploads. Preserve pre-existing services,
  containers and data. Track and clean up only task-owned resources; shared-resource
  intervention requires ownership evidence and authorization. Machine-specific values
  belong in local configuration or environment guidance, not portable project policy.

## Module boundaries

For affected Python modules, inspect [.importlinter](../.importlinter),
[Ruff import restrictions](../src/ruff.toml) and the
[architecture guidance](development.md#python-integration-and-architecture).
Classify runtime modules under core, application, adapters or entrypoints. Preserve the
direction entrypoints → adapters → application ports/contracts → core; adapters do not
import application use cases or entrypoints. Cross-adapter bridges remain explicit.
Core owns no filesystem/network/process effects or SDK objects; effects belong at outer
interfaces. Direct commands remain independent of queue and optional UI imports.

Account for type-only imports, function-local imports and justified exact-edge exceptions.
Use ordinary imports for fixed targets and documented exceptions for computed loading.
Extend declarative contracts or product tests when coverage is missing; preserve approved
enforcement limits. Architecture gates inspect the actual product graph and source.

## Verification and review

Run applicable [verification stages](development.md#verification); use the
`verification-workflow` skill for selection. Automatic routing follows the staged/latest-
commit classifier in Task; explicit comprehensive commands retain their full scope.
Assess the whole branch or feature delta, not merely its last documentation commit.
Record selected checks, exclusions, source/environment identities and reuse reasons in
Linear or linked dated evidence. Reuse results only while relevant inputs remain applicable.

Tests exercise observable product behavior with isolated paths and controlled substitutes.
Bug fixes reproduce the original failing observation where feasible and verify that path
again; distinguish hypotheses, static evidence and executed checks when reproduction is
unavailable. Mocked tests cannot establish training, GPU or upload outcomes. Use the live
integration skill for native claims. A focused test run cannot establish global coverage.

Follow the commit procedure and final hook gate. Review integrated changes independently
after verification for behavior, interface, dependency, security or operational policy;
wording edits may be self-reviewed. Delegated work has bounded scope, explicit ownership,
dependencies and acceptance evidence; inspect combined results and preserve others' edits.
Report checks as passed, failed, deferred, waived or error. Required deferred verification
blocks acceptance and merge readiness; only the user may waive required checks.

## Documentation

Update affected user guidance with behavior changes. Review consistency between Linear
acceptance criteria, current contracts and the actual diff before expensive verification.
Do not invoke archived Spec Kit checks or introduce a separate documentation checker.
README is Russian; other documentation is English unless explicitly required otherwise.
Keep counts, timings and deployment observations in dated evidence.

## Workflow safeguards

- Host Plan Mode remains read-only: do not run mutating setup helpers, hooks or artifact
  generators until execution is authorized. Inspect ignore files without unrelated edits.
- Preserve unrelated staged and unstaged changes. Stage only task-owned paths or hunks;
  never stash, reset, revert or bypass hooks to hide failures. Use unique temporary
  commit-message files when writers are concurrent.
- For bug-source capture, validate file containment and symlink components before I/O.
  Preserve explicit slugs on collisions; suffix only generated slugs. Redact secrets
  from source URLs and quoted input before persistence. Apply the URL trust policy:
  ordinary web tools may fetch allowlisted hosts without peer-IP metadata; raw HTTP
  or unrecognized-host requests require public-address selection. Private/metadata
  targets remain refused.
- Reassess disproven bug hypotheses within the authorized scope. Ask only for material
  missing information or scope changes; document assumptions and deviations in Linear.
