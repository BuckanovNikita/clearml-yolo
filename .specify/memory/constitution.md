# clearml-yolo Constitution

## Core Principles

### I. Typed, Explicit Python

Python changes MUST follow the Ruff and strict mypy configuration in
[pyproject.toml](../../pyproject.toml). Its rules, exceptions, and dependency constraints are
the maintained source of truth; changes MUST NOT weaken them merely to silence a failure.

- Modules MUST NOT use `from __future__ import annotations`. Use runtime annotations,
  `typing.Self` for methods returning their receiver, and quoted forward references or
  stub-only generics where runtime evaluation is unsupported. Modules MUST use absolute
  imports and configured import ordering, Python target and line-length limit.
- Functions MUST declare parameter and return types. Configuration and validated structured records
  MUST use Pydantic. Dataframe validation MUST use explicit Pandera schemas, preserving
  the maintained input and recoverable-row policies.
  Mutable model defaults MUST use factories.
- Project-owned interfaces MUST use explicit typed access. `Any`, dynamic attribute access,
  and casts MUST be limited to boundaries that require them, such as opaque third-party
  objects or Hydra composition. Non-obvious boundary assumptions MUST be explained.
- Lint and typing suppressions MUST name the specific rule or error code. Their reason MUST
  be clear from adjacent code or an explanation; blanket suppressions are not acceptable.
- Application logging MUST use Loguru through the observability adapter and injected
  application ports. CLI output MUST preserve its existing contract, including Rich
  rendering where used. Comments and log messages MUST be in English.
- Exceptions MUST be handled at a boundary able to recover or report the failure, using
  specific exception types where possible. Unexpected failures MUST NOT be silently discarded.
- Names and function boundaries MUST express purpose. Comments and docstrings MUST explain
  contracts, constraints, or non-obvious decisions rather than repeat the implementation.
  Decomposition MUST follow responsibility and configured complexity checks rather than
  arbitrary function-length limits. Filesystem code MUST follow the existing `pathlib` style.

These rules keep interfaces inspectable while acknowledging the dynamic libraries used by
the pipeline.

### II. Enforced Module Boundaries

All runtime modules MUST be classified under core, application, adapters or entrypoints.
Direct commands MUST remain independent of queue and optional UI imports; Hydra multiruns
use the standard sequential BasicLauncher, without a project launcher plugin. The dependency
direction is entrypoints -> adapters -> application ports/contracts -> core. Application
use cases MUST depend on ports/contracts and core rather than concrete adapters. Adapters
MUST NOT depend on application use cases or entrypoints. Cross-adapter integration bridges
MUST be explicit. Import-linter and architecture tests MUST enforce exhaustive
classification, SDK ownership, transitive core/application isolation, independent command
entrypoints and acyclic helpers.

Core permits the standard library, Pydantic, Pandera, pandas, NumPy and SciPy, with no
filesystem/network/process effects or SDK objects. Configuration resolution, model loading,
tracking, storage, reporting and process admission belong at explicit outer interfaces.
Package initialization MUST be inert; runtime initialization is explicit at invocation.
Torch, Ultralytics and ClearML imports MUST be deferred to use where necessary to retain
responsive help/configuration commands. The composition root MUST inject concrete adapters;
application use cases MUST NOT construct them or obtain them through a global locator.

### III. Configuration and Run Ownership

Hydra applications MUST share centralized hydra-zen registration in
[Hydra configuration](../../src/clearml_yolo/entrypoints/hydra/configs.py). Standalone and pipeline stage configurations
MUST derive from the same task contracts rather than duplicate independently maintained
parameter definitions.

The pipeline MUST own shared tracking, dataset, splits, checkpoint, identity and output
routing. Producers MUST pass actual outputs to consumers. Every execution invocation MUST
own one ClearML task; pipeline stages MUST share it. ClearML is required for execution.
Local configuration initialization MUST NOT create a task or load model runtimes.
Completion MUST wait for
all required artifacts and native output models to upload and flush; computation, callback,
upload, flush, or interruption failures MUST fail the task and preserve local diagnostics.
Credentials MUST NOT be uploaded. Native Ultralytics training and validation image previews
MAY be published by the invocation owner; workers MUST NOT create tasks or publish.
The best checkpoint MUST use the same native Output Model record, without duplicate artifacts.

Runs MUST have isolated identities and output directories. Pipeline output overrides MUST
use run_dir; conflicting native output settings MUST be rejected explicitly. Skipped-stage
consumers MUST validate required existing inputs. Convenience links MUST preserve user data.

Model execution MUST delegate native training and inference to the selected backend;
YOLO device, batch, AMP, compilation and distributed behavior belongs to Ultralytics.
Approved detector families and export operations follow the
[backend](../../specs/000-baseline/spec.md#detector-backends-and-deployment-export) and
[export](../../docs/tensorrt-deployment.md) contracts. Export
MUST NOT register another trained model; numerical parity and labeled-corpus accuracy
acceptance remain separate, with target-runtime evidence required for deployment claims.

Direct commands MUST execute configured devices without scheduling. `cy-queue` MAY
provide explicit whole-GPU count/device requests, persistent same-user workers, durable
shared records, host-local coordination and reordering of pending jobs. The
[queue contract](../../docs/queue.md) governs owner execution/cancellation, earliest
runnable ordering, atomic current-generation reservations and fresh memory admission.
Training MUST retain the full allocation until acknowledged contraction; absent that
notification the full reservation remains. The first device stays reserved through
owned descendant exit unless explicitly freed. Explicit per-device freeing MUST fence
older guardians without signalling processes or changing job outcomes. Job completion,
cleanup evidence and GPU availability MUST remain separate. Stale unlocked metadata MUST
NOT alone veto admission; uncertain outcomes require owner recovery, never automatic retry.
MIG scheduling, TTL/PID-only cleanup inference, upstream monkeypatches, batch tuning and
augmentation-JSON processing remain unsupported.

`cy-init-config` MUST export only the selected command (default `cy`) and model's editable
examples, protecting existing files unless replacement is explicit. Default YOLO model
commands include top-level `ultralytics` and `ultralytics_predict` groups and required inputs.
The shared group MUST cover the installed native configuration and preserve its comments;
the prediction group MUST override applicable shared values. Explicit nulls and explicit
values equal to defaults MUST retain their precedence. Stage-irrelevant settings MUST be
commented in stage YAML and excluded from native execution. Unsupported wrapper and native
settings MUST fail strict validation. Non-null native
`cfg` and nested stage-native mappings are unsupported. Standalone training MUST require
CSV ground truth; dataset preparation and replay MUST use the same current input contract.
Effective native YAML MUST be saved locally with original comments retained. Remote replay
MUST use canonical nonempty configurations with secrets sanitized; Configuration Objects
MUST NOT be duplicated as artifacts. Native General parameters own training arguments. Output and checkpoint
ownership MUST remain with the pipeline. Existing examples MUST be protected unless
replacement is explicit; unrelated files MUST be preserved.

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
[tests/test_native_config.py](../../tests/test_native_config.py) intentionally checks
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

Model class names MUST come from the checkpoint rather than ClearML model metadata.
Task recovery MUST follow the ordered checkpoint and threshold selection in the
[recovery contract](../../specs/000-baseline/spec.md#evaluation-comparison-and-historical-model-recovery).
Current best Output Models and exact validation thresholds remain preferred; approved
historical checkpoint artifacts, named threshold payloads and dashboard recovery are valid
fallbacks. Explicit threshold maps take precedence. Dashboard recovery MUST warn about
rounding and unavailable calibration provenance; malformed present sources MUST fail.
Recovery MUST preserve available precision and current comparison settings, and MUST NOT
import historical predictions or silently recalibrate on test data.

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

Amendment 9.0.0 (2026-10-15) reconciles Principles II–III and operational constraints
with approved features 024, 025, 029 and 031 and the task-recovery amendment. It replaces
the retired launcher/FIFO-only scheduler restrictions with direct execution and explicit
shared-queue controls; recognizes backend/export ownership, selected configuration export,
acknowledged allocation contraction and generation-fenced per-device freeing; and restores
ordered historical checkpoint/threshold recovery with precision warnings. This is a major
governance correction, not new runtime authorization. Existing dependency, privacy,
publication and evidence requirements remain. Prior amendments and their dates below are
preserved; their superseded requirements do not override current topic contracts.

Amendment 8.0.0 implements the user-approved full clean-architecture redesign and Pandera
validation. Principles I–III replace the historical flat module ordering with exhaustive
core/application/adapter/entrypoint contracts and define Pydantic for records versus
Pandera for dataframes. Existing CLI fields, numerical behavior, publication and resource
ownership contracts remain unchanged. Old Python import paths are removed; generated
YAML with old configuration-model targets must be regenerated. No legacy path translation
or upstream source changes are authorized by this amendment. Historical amendments below
remain a dated record, not a requirement to preserve removed Python paths.

Amendment 7.0.0 implements the explicitly approved GPU experiment queue. Principle III replaces
the blanket runtime-scheduling prohibition with a narrow permission for a user-wide, local,
whole-NVIDIA-device FIFO scheduler derived from native settings. It requires atomic reservations,
fail-closed telemetry, pre-task/pre-context waiting, isolated execution children, and separate
requested/effective provenance while prohibiting daemon, bypass, priority, TTL/PID-only reclaim,
new count configuration, MIG/cross-host scope, and upstream monkeypatching. Existing single-task,
native configuration, publication, privacy, dependency, and evidence rules remain mandatory.

Amendment 6.0.0 implements the user-approved removal of all legacy compatibility paths.
Standalone training now requires CSV ground truth; current model publications and evaluation
configuration are the sole supported contracts. Strict input validation replaces migration
branches. Historical records and prior amendments are preserved as dated history; current
requirements supersede their compatibility and migration obligations. No old data is migrated
or deleted, and dependency revisions and installed workflow tooling remain unchanged.

Amendment 5.0.0 authorizes native previews and native model publication, replaces duplicate
configuration artifacts with canonical replay configurations, and adopts readable exact
threshold tables. Historical tasks remain unchanged. Credential protection, single-task
ownership, and upload-completion guarantees remain mandatory.

Amendment 2.0.1 relocates machine-specific operational guidance to global skills.
It preserves credential, capacity and task-owned cleanup safeguards while keeping
application and repository instructions independent of a particular installation.

Amendment 3.0.0 implements the user's explicit requests to restore `cy-init-config` and
remove all future-annotations imports. It reverses the import mandate in Principle I
and the config-generation prohibition in Principle III, adds the generator to Principle II's
dependency direction, and exempts local initialization from task ownership. The major version
reflects these incompatible governance changes. Existing execution, privacy, dependency and
verification contracts remain in force. Migration removes the imports, repairs annotations
that require explicit deferral, and regenerates obsolete examples using current defaults.

Amendment 4.0.0 implements the approved native configuration groups change. Principle III
replaces sparse stage mappings and raw `cfg` precedence with shared native defaults,
prediction overrides, stage filtering, comment-preserving YAML and ClearML records.
This incompatible interface change requires regenerated examples and migration to top-level
Hydra groups; all execution ownership, privacy and verification safeguards remain in force.

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

**Version**: 9.0.0 | **Ratified**: 2026-09-19 | **Last Amended**: 2026-10-15
