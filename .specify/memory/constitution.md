# clearml-yolo Constitution

## Core Principles

### I. Typed, Explicit Python

Python changes MUST follow the Ruff and strict mypy configuration in
[pyproject.toml](../../pyproject.toml). Its rules, exceptions, and dependency constraints are
the maintained source of truth; changes MUST NOT weaken them merely to silence a failure.

- Modules MUST use `from __future__ import annotations`, absolute imports, and configured
  import ordering. Code MUST follow the configured Python target and line-length limit.
- Functions MUST declare parameter and return types. Configuration and validated data models
  MUST use Pydantic where validation is required, following existing model conventions.
  Mutable model defaults MUST use factories.
- Project-owned interfaces MUST use explicit typed access. `Any`, dynamic attribute access,
  and casts MUST be limited to boundaries that require them, such as opaque third-party
  objects or Hydra composition. Non-obvious boundary assumptions MUST be explained.
- Lint and typing suppressions MUST name the specific rule or error code. Their reason MUST
  be clear from adjacent code or an explanation; blanket suppressions are not acceptable.
- Application logging MUST use Loguru. CLI output MUST preserve its existing contract,
  including Rich rendering where used. Comments and log messages MUST be in English.
- Exceptions MUST be handled at a boundary able to recover or report the failure, using
  specific exception types where possible. Unexpected failures MUST NOT be silently discarded.
- Names and function boundaries MUST express purpose. Comments and docstrings MUST explain
  contracts, constraints, or non-obvious decisions rather than repeat the implementation.
  Decomposition MUST follow responsibility and configured complexity checks rather than
  arbitrary function-length limits. Filesystem code MUST follow the existing `pathlib` style.

These rules keep interfaces inspectable while acknowledging the dynamic libraries used by
the pipeline.

### II. Enforced Module Boundaries

Changes MUST preserve every import-linter contract in [pyproject.toml](../../pyproject.toml),
including package layers, task layers, comparison layers, independent app entrypoints, and
forbidden external imports. The package dependency direction is:

```text
apps -> configs -> tasks -> comparison -> domain modules -> run_identity
```

App entrypoints MUST remain independent and delegate work to tasks or domain modules.
`configs` MUST build task configuration from above `tasks`; tasks MUST NOT depend on config
registration. Direct ClearML SDK access MUST remain in the ClearML adapters and permitted
tasks. Domain modules MUST remain independent of Hydra, hydra-zen, and OmegaConf as specified
by the contracts. `run_identity` MUST remain a filesystem-only bottom layer.

Torch, Ultralytics, and ClearML imports MUST stay behind the established permitted boundaries
and be deferred to use where needed to preserve responsive CLI startup. Code that only
resolves parameter names, configuration MUST NOT load model dependencies.

These boundaries keep orchestration, external services, and expensive model operations out
of independently testable domain code.

### III. Configuration and Run Ownership

Hydra applications MUST share centralized hydra-zen registration in
[configs.py](../../src/clearml_yolo/configs.py). Standalone and pipeline stage configurations
MUST derive from the same task contracts rather than duplicate independently maintained
parameter definitions.

The pipeline MUST own shared tracking, dataset, splits, checkpoint, identity and output
routing. Producers MUST pass actual outputs to consumers. Every invocation MUST own one
ClearML task; pipeline stages MUST share it. ClearML is required. Completion MUST wait for
all required stage artifacts to upload; computation or upload failures MUST fail the task
and preserve local diagnostic outputs. Credentials and dataset images MUST NOT be uploaded.

Runs MUST have isolated identities and output directories. Pipeline output overrides MUST
use run_dir; conflicting native output settings MUST be rejected explicitly. Skipped-stage
consumers MUST validate required existing inputs. Convenience links MUST preserve user data.

Model execution MUST delegate device, batch, AMP, compilation and distributed training to
Ultralytics. Runtime GPU scheduling, leases, batch tuning, augmentation-JSON processing and
configuration-tree generation MUST NOT be provided. Raw native YAML and explicitly supplied
embedded mappings MUST compose as upstream defaults < raw YAML < embedded values < CLI.
Explicit values equal to defaults MUST retain their precedence.

Candidate thresholds MUST be calibrated on validation data and frozen for test evaluation.
Baseline thresholds MUST be loaded, never recalibrated on test. Comparisons MUST use the
same current test images and inference settings; reports MUST share evaluated results.

This preserves standalone and composed behavior while preventing concurrent runs from
overwriting one another.

### IV. Proportional, Evidence-Based Verification

Every change MUST be verified against its affected behavior using documented repository tools
and current check configuration. Documentation-only changes MUST validate the changed
Markdown and referenced paths; they do not require an unrelated application test suite.

Code changes MUST run the relevant repository gates through `uv run`: `pytest`,
`ruff check .`, `mypy .`, and `lint-imports`. Verification MUST broaden when impact crosses
boundaries. Commit work MUST satisfy the applicable checks in
[.pre-commit-config.yaml](../../.pre-commit-config.yaml); hooks MUST NOT be bypassed to hide
failures. `uv run pre-commit run --all-files` is the repository's full hook check.

Tests MUST assert observable behavior and contracts. They MUST use isolated temporary paths,
controlled clocks or identities, and explicit external-dependency substitutes where needed
for deterministic execution. Bug fixes MUST capture the failing observation, reproduce it
when feasible, and verify the original failure path after the fix. When reproduction is
unavailable, reports MUST distinguish hypotheses, static evidence, and executed checks.

Mocked tests MUST NOT be presented as evidence of training, GPU access, or artifact uploads.
[tests/test_ultralytics_params.py](../../tests/test_ultralytics_params.py) intentionally checks
the installed Ultralytics configuration; other tests may stub ClearML, Ultralytics, or Torch.
Work needing real pipeline evidence MUST follow the `running-end-to-end-tests` skill and
agent-run contract in [AGENTS.md](../../AGENTS.md).

Completion reports MUST identify checks actually performed, failures, and limitations.
Skipped or unavailable checks MUST NOT be reported as passing.

### V. Clear Communication and Safe Collaboration

User-facing README text MUST be in Russian. Other documentation, skills, and instructions
MUST be in English unless the user or project explicitly requires otherwise. Documentation
MUST use concrete language, explain decisions and constraints, and avoid redundant prose.
Observed test counts, timings, and deployment status MUST live in dated evidence rather than
evergreen instructions. Changing operational values MUST be read from their maintained source.

Contributors MUST inspect relevant code, configuration, instructions, and existing changes
before editing. Plans and task files describe intent; the current repository establishes
implementation evidence. Missing information MUST be requested when it materially changes
the result and cannot be found in available context; otherwise important assumptions MUST
be stated.

Changes MUST preserve unrelated staged and unstaged work. Contributors MUST NOT automatically
stash, reset, revert, or bypass hooks to make checks pass. Parallel work, when used, MUST have
bounded deliverables, explicit write ownership, dependencies, and acceptance evidence; the
combined result MUST be inspected.

Commits MUST occur only when requested or included in the authorized workflow, use
Conventional Commits, and stage only explicit paths or hunks belonging to the task. Concurrent
writers MUST use unique temporary commit-message files. Authorized pushes SHOULD use SSH
remotes to follow the existing repository access convention.

Processes and temporary resources created by a task MUST be tracked and cleaned up.
Pre-existing services, containers, and data MUST remain intact; intervention in a shared
resource requires ownership evidence and authorization.

## Technology and Operational Constraints

The project MUST retain its existing `uv` toolchain, `uv_build` backend, Python compatibility,
and dependency constraints unless an authorized change updates them. Exact values belong in
[pyproject.toml](../../pyproject.toml) and [uv.lock](../../uv.lock). New dependencies MUST be
declared directly when imported rather than assumed to remain available transitively.

Machine-specific infrastructure instructions MUST live in global environment skills.
Repository documentation and application code MUST remain portable. Before a real
integration run, contributors MUST follow the environment's applicable access,
capacity and resource-ownership contract. Credentials MUST stay out of tracked
files; cleanup MUST affect only resources owned by the task. Select native devices
explicitly and preserve unrelated workloads. This repository does not deploy or
tear down shared infrastructure.

Model class names MUST come from the checkpoint rather than ClearML model metadata. Exact
per-class confidence values MUST come from the `metrics_best_confidences_<split>` artifact,
not rounded dashboard thresholds.

## Development Workflow

1. Establish the requested outcome and inspect applicable instructions, current changes,
   configuration, and affected implementation. Planning-only requests MUST remain planning-only.
2. Check the proposed change against these principles and existing compatibility contracts.
   Resolve material unknowns; document important assumptions and any intended contract change.
3. Implement within the authorized scope, preserving existing work. Update affected
   documentation and behavior tests when the change requires them.
4. Run proportional verification and review the resulting diff. An unrelated check blocker
   MUST be reported specifically or handled in an isolated workspace that preserves it.
5. Report what changed, evidence obtained, and remaining limitations. Commit or push only
   within existing authorization and after the applicable stage checks pass.

## Governance

Amendment 2.0.1 relocates machine-specific operational guidance to global skills.
It preserves credential, capacity and task-owned cleanup safeguards while keeping
application and repository instructions independent of a particular installation.

This constitution records the established engineering conventions of `clearml-yolo`.
Implementation, specifications, plans, and reviews MUST comply with its principles within
their scope. [AGENTS.md](../../AGENTS.md) supplies operational guidance;
[pyproject.toml](../../pyproject.toml) and [.pre-commit-config.yaml](../../.pre-commit-config.yaml)
supply exact executable checks. Explicit user instructions remain authoritative within the
host's instruction hierarchy; conflicts MUST be surfaced rather than silently reconciled by
changing unrelated files.

Amendments MUST document the reason, affected principles, compatibility impact, and any
migration or follow-up work. The amendment MUST be reviewed within the authorized workflow,
update the version and last-amended date, and preserve the original ratification date.
Temporary Sync Impact Reports MUST be removed before committing the amended constitution.

Versions MUST follow semantic versioning: MAJOR for incompatible principle removals or
redefinitions, MINOR for new principles or materially expanded guidance, and PATCH for
non-semantic clarifications. Version 1.0.0 is the initial adoption of the previously unfilled
scaffold on the ratification date below.

Every relevant plan and change review MUST check compliance, identify deviations with their
rationale and remediation, and distinguish intended design from verified behavior. A change
that deliberately alters a governing rule MUST include an explicit amendment rather than
quietly weakening checks. Constitution updates MUST remain confined to this document;
dependent template or implementation changes require their own authorized work.

**Version**: 2.0.1 | **Ratified**: 2026-09-19 | **Last Amended**: 2026-09-20
