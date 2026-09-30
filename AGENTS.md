# Personal engineering instructions

## Working agreement

Carry the requested outcome through implementation and appropriate verification.
Inspect relevant code, configuration, and existing changes before editing. Treat plans
and task files as intent and the current repository as implementation evidence. Preserve
unrelated work. Ask only for information that materially changes the result and is unavailable
in the repository.

Respect the active host mode: planning-only work permits inspection, not file writes or
mutating hooks. Skills and generated tasks do not broaden authorization. Reuse existing
authorization within its scope; ask again only for a material new decision or scope change.

For a bug, capture and reproduce the failing observation when feasible. Verify the
original failure path after the fix. Report checks and limitations accurately.

## Verification and collaboration

Use the repository's documented tooling and current check configuration. For code or
commit work, select the affected gates from:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run lint-imports
uv run pre-commit run --all-files
```

Documentation-only work needs Markdown and link validation, not an unrelated application
suite. The mocked suite cannot prove native training, a GPU, or ClearML uploads. Do not
claim those outcomes without dated real-run evidence.

Track processes and temporary resources created by this task and clean them up. Leave
pre-existing shared services, containers, and data intact.

## Python preferences

Follow the existing toolchain. Prefer strict types, explicit access, Loguru for application
logging, and Pydantic for validated configuration. Catch exceptions at a boundary that can
handle them, using specific types where practical. Keep code comments and log messages in
English.

## Git and documentation

Commit only when requested. Stage explicit paths or hunks belonging to the task; preserve
unrelated staged and unstaged changes. Do not stash, reset, revert, or bypass hooks to make
a check pass. Use Conventional Commits when committing.

Write README.md in Russian. Write other documentation, skills, and instruction files in
English unless the user or project states otherwise. Keep observed test counts, timings,
and deployment status in dated evidence rather than evergreen documentation.

--- project-doc ---

# clearml-yolo

`clearml-yolo` is a Python 3.12 group of Hydra/hydra-zen applications for native
Ultralytics YOLO training, prediction, validation, metrics, reports, and model comparison.
`cy` runs the pipeline; `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`, `cy-report`,
`cy-compare`, and `cy-ground-truth` run individual stages.

## Project contracts

Nine entrypoints: `cy`, `cy-train`, `cy-predict`, `cy-val`, `cy-metrics`,
`cy-report`, `cy-compare`, `cy-ground-truth`, and `cy-init-config`.
`cy-init-config DIRECTORY [--force]` writes editable examples for the eight execution
commands without creating a ClearML task. `cy-queue` remains removed.

Native model settings use top-level Hydra groups `ultralytics` and `ultralytics_predict`
for all model commands. The shared group covers detection-relevant installed upstream defaults; prediction
inherits applicable values through visible configuration references, preserving explicit nulls
and overrides. Prediction execution reads only its resolved group. Project defaults are
imgsz=960, compile=true and nms=true; prediction uses conf=0.001, batch=1, rect=true and
save=false. Native normalization is recorded separately from requested values.
Generated `ultralytics/default.yaml` and `ultralytics_predict/default.yaml` contain native
keys without wrapper indentation and preserve original comments. Use ordinary overrides
such as `ultralytics.epochs=10` and `ultralytics_predict.batch=8`.
Stage-irrelevant settings are commented in exported native YAML and excluded from execution.
Raw `cfg` loading, non-null native `cfg`, nested stage-native mappings and duplicate native
comparison inference settings are removed and must fail with migration guidance.
Effective native YAML and retained prediction manifests support replay; YAML is retained
locally with comments preserved; canonical run/dataset/report configurations and native General
parameters support ClearML replay without artifact copies.
Pass device, batch, AMP, compilation and native augmentation options directly to Ultralytics.

The project no longer provides GPU scheduling, filesystem queues or leases, batch tuning,
custom augmentation JSON, `--force-gpu`, or disabled tracking. Removed options must fail
rather than be silently ignored.

`run_dir` owns output routing for `cy`. Pipeline stages cannot use conflicting stage output
paths or conflicting native training project/name. Standalone output-producing commands use
fresh output directories and require their explicit inputs. Keep ClearML SDK access in its
adapters and tasks; output routing has no dependency on ClearML.

Candidate thresholds are calibrated on validation once and frozen for evaluation. Pipeline
comparison uses test; standalone `cy-compare` defaults to test and accepts a split override.
Both models use identical current images from that split and matching inference settings.
Reports consume their paired results and manifest split from `comparison_dir`. Historical
dashboards are not comparison input. Source task/model links provide provenance; comparison
retrieves weights and exact thresholds, without importing source configurations over the
current comparison settings.
The automatic baseline is the latest completed prod-tagged task excluding the current task;
missing automatic baseline skips comparison, while invalid explicit references fail.

ClearML is required for execution commands. One execution invocation owns exactly one task;
nested stages reuse it and workers do not create tasks or upload artifacts.
Complete a task only after all required artifacts and the native best Output Model
are uploaded, verified and flushed. Fail task and command on computation, upload, flush, or interruption
errors while retaining local output. Never capture credentials. Native owner-only training/validation image previews are permitted.
Use the shared CSV-addressed dataset cache outside run outputs; source images are immutable.

## External dependencies

`digital-metrics` and `report-generator` live in `external/` as Git submodules.
Both track upstream `main` through `.gitmodules`; `git submodule update --remote`
advances their checkouts when an upstream update is requested.
Initialize them with `git submodule update --init --recursive` before `uv sync`.
Local development installs them editable through `[tool.uv.sources]`; the parent
repository's gitlinks pin their revisions. For installations without submodules,
users can select Git URLs and branches per README.md. Git sources use
`branch = "main"` (or `master` for a user-selected repository); `uv.lock` records
the resolved commits.

`digital-metrics` is an external dependency. Keep it pinned to the approved upstream
revision. Do not change its source, checkout, dependency reference or locked revision
without the user's explicit intent to change it. General implementation,
cleanup and dependency maintenance requests do not authorize such changes. Adapt
`clearml-yolo` integration code when compatibility work is needed; report upstream
issues instead of patching or monkeypatching the dependency.

## Project and environment guidance

- Read `pyproject.toml` for entrypoints, dependencies and import contracts.
- Use [the current contract index](docs/current-contracts.md) to select maintained contracts
  by topic; no single release-era directory defines every current behavior.
- For a contract change, update affected active specs, quickstarts, README, migrations and
  project-owned integration skills together, including applicable global environment examples. Preserve dated
  evidence and checked task history; annotate superseded intent instead of claiming it was
  newly verified. Record unexplained code/spec mismatches with concrete evidence.
- Keep artifact inventories in the maintained publication contract; avoid copying
  counts into instructions. Claim implemented/verified status only with linked evidence
  and its limitations. Documentation updates do not authorize dependency changes.
- For integration verification, load the project skill `running-end-to-end-tests`.
- Machine-specific endpoints, credentials, capacity, run helpers and local execution
  records belong in global environment skills. When available, load
  `clearml-yolo-environment` for this project's local integration environment.
  Other installations should use their own environment instructions.
- Pass ClearML project names and tags explicitly. Application configuration must not
  depend on an agent harness or a particular machine.

## Spec Kit integration

Keep installed Spec Kit skills, extension commands, templates and other `.specify/`
files unchanged unless the user explicitly requests a change to those files. Put
project workflow policy in this file or separate project hooks. Project feature
specifications under `specs/` remain project documentation.

### Mandatory documentation stage

Every Spec Kit implementation or bug-fix workflow must complete a **Documentation
update** stage after implementation and before reporting completion. This is a required
project completion gate, including when an existing task list omits documentation.

- During planning, identify the documentation affected by the proposed changes using
  [the current contract index](docs/current-contracts.md). Include this scope in `plan.md`
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
