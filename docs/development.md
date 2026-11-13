# Development and commit procedures

User-facing workflows are in the [README](../README.md); setup and operational
context are collected in the [technical reference](../TECH_DETAILS.md).

Read the relevant section before environment setup, code verification, dependency work or
any commit. The [agent instructions](../AGENTS.md) define authorization and task routing.
Read [pyproject.toml](../pyproject.toml) for package/dependency/release settings,
[ruff.toml](../ruff.toml) for lint policy and [.importlinter](../.importlinter) for import
contracts. Ruff and import-linter discover their dedicated files automatically.
The shared `python-code-standards` and `python-import-contracts` skills supply Python
requirements within the [native workflow](agent-workflow.md); this document owns the project's commands and
dependency/commit/release procedures.

## Python compatibility

The package supports Python `>=3.12.13,<3.14`. Development, Ruff and mypy retain
Python 3.12 as the oldest supported minor; `.python-version` selects the development
default rather than limiting installation to that minor. Verify packaging and the
routine suite on both Python 3.12 and 3.13 when changing interpreter compatibility.

Linux native execution additionally requires the existing pidfd, subreaper and
`/proc` capability checks. A Python version constraint cannot guarantee those
build/kernel capabilities. See [queue supervision](queue.md#guardians-cancellation-and-recovery).

## Runtime dependency compatibility

All CY runtime capabilities install by default, including the detector stack and
ONNX export. The separate `cy-queue` source package owns scheduling, the Textual TUI
and NVML; install it after CY into the same environment using
[queue installation](queue.md#installation). Neither distribution is assumed to be
available on PyPI. There are no project extras; remove
`--extra detectors`, `--extra export`, `--extra queue-ui` and corresponding package
extras from recipes. Keep development tools in `dependency-groups.dev`; required
upstream extras such as `rfdetr[train]` and `pandera[pandas]` remain runtime inputs.

[`pyproject.toml`](../pyproject.toml) owns direct lower bounds, exact pins and upper
bounds. The normal lockfile records the selected environment. When changing floors,
test an isolated `lowest-direct` resolution on Python 3.12.13 and 3.13, record the
resolved versions and executed checks in dated evidence, and raise a floor only
when compatibility evidence requires it. Resolution alone is not a runtime check.
Keep minimum-version resolutions separate from the normal lockfile, retain approved
external source revisions and avoid unrelated upgrades. TensorRT system requirements
remain external prerequisites. DEIMv2 source and non-YOLO pretrained assets can
resolve at execution through the [asset adapter](model-assets.md); explicit local
checkouts and files remain authoritative. Dependency installation is always external.

## Verification

[Taskfile.yml](../Taskfile.yml) owns verification commands, ordering and change routing;
[Taskfile.ops.yml](../Taskfile.ops.yml) owns infrastructure and release stages. prek is a
serial dispatcher with Conventional Commits validation. Invoke explicit stages with
`uv run --locked task --exit-code <stage>` after preparing the
[local external packages](#external-dependencies). Clear inherited
`UV_PROJECT_ENVIRONMENT` before the outer command; Task isolates child environments
and caches per worktree. Never treat Task freshness or an interrupted run as evidence.

### Automatic routing

| Changed inputs | Automatic scope |
| --- | --- |
| Documentation, instructions/skills, tooling, dependencies or infrastructure only | Hygiene, applicable native documentation checks, static checks and commit safeguards; no product tests or live infrastructure |
| Test code only | Static checks, changed eligible unit-test files, valid cached failed IDs and known testmon dependents of changed shared fixtures/helpers |
| Product source or shipped runtime configuration/assets under `src/` | Ordinary product verification |
| Mixed changes | Strongest relevant route |

Prose-only files under `src/` remain non-code. Renames/deletions consider old and new
paths. Hooks classify the staged diff; post-commit automatic checks classify the latest
commit. Earlier product changes do not retrigger tests for a prose-only follow-up.
Static-only work does not rerun cached failed tests. Infrastructure manifests under
`tests/integration/environment/` and the environment lifecycle remain infrastructure
inputs even though they live beneath `tests/`.

Test-only selection excludes live tests and heavy markers (including CPU-DDP and
process-capability scenarios). Cached IDs are checked against current collection;
deleted/stale IDs are discarded. Test execution records new failures and clears successful
retries in the normal pytest cache. Shared helpers defined inside test modules also
include their recorded dependents. Shared-test changes without dependency history report
a targeted-verification gap instead of falling back to the full suite. Selectors are
explicitly bounded. Collection runs inside the verifier; an empty final selection
launches no pytest process. Explicit `test`,
`test-full`, `coverage`, `properties`, `integration`, acceptance and release commands
execute their requested scope regardless of change classification.

### Order and evidence reuse

Complete applicable native Spec Kit documentation analysis and consistency review as
soon as inputs exist. Then run hygiene/safe fixes, syntax and required-input checks,
lock freshness, remaining static checks, and resource preflight before expensive
execution. Early failures and automatic edits stop later stages; inspect and stage
edits before retrying. Ruff correction remains an explicit `fix` operation.

Reuse successful checks while relevant inputs remain unchanged. Prose corrections do
not invalidate product evidence; review fixes rerun affected checks. Schedule the final
`prek run --all-files` with hook overrides cleared as the canonical automatic pass,
without first running an equivalent `verify`. No separate documentation checker applies.

| Stage | Purpose |
| --- | --- |
| `local-deps` | Prepare the ignored external wheelhouse and local resolver configuration |
| `fix` | Safe Ruff fixes and formatting; never stages files |
| `check` | Hygiene/early input checks, lock freshness, Ruff, architecture, mypy, Vulture, deptry |
| `architecture` | Import contracts, dynamic imports, initializers, runtime targets and tooling boundaries |
| `verify` | Automatic change-aware static and selected product verification |
| `test` / `test-full` | Explicit affected unit tests / full unit suite with refreshed testmon history |
| `coverage` / `properties` | Explicit full unit coverage / Hypothesis exploration |
| `mutation` | Scoped [changed-function mutation report](#mutation-report) |
| `infra-check` | Bounded read-only infrastructure preflight |
| `infra-up` / `infra-env` / `infra-down` | Owned environment creation, exports and guarded deletion |
| `integration` | Non-GPU live product tests, including CPU smoke, with owned setup/teardown |
| `acceptance` | Explicit complete change acceptance on a clean committed tip |
| `release-acceptance` | Explicit release automated gates and paired check |
| `paired-check` | [Final CY/queue source compatibility](#paired-cy-and-queue-release-check) |
| `release-local` / `release-publish` | [Local integration/versioning / authorized publishing](#local-releases) |

Inspect current host load before heavy stages and select the configured worker count
accordingly. Verification never builds CY distributions. `local-deps` builds only
approved external development inputs. The explicit `test` stage may start a full
baseline for an unseen testmon namespace; automatic test-only routing does not use
that expanding mode. A deselected test is not fresh execution.

### Lock freshness

The lock check never rewrites `uv.lock`. The approved external packages resolve through
the ignored `uv.toml` and `external/wheelhouse`; prepare them before verification.
Never commit `[tool.uv.sources]` or change approved dependency revisions to repair setup.

### Hooks and staging guard

Install worktree-aware hooks with `bash scripts/install-hooks.sh`; the installer keeps
previous hooks for rollback. Before prek can stash files, the pre-commit dispatcher
runs Task `staging-check`. It refuses every unstaged tracked change and
nonignored untracked file without staging, stashing or deleting anything.

Task `hygiene` checks all tracked regular text files, excluding symlinks and binary
content from text fixes. The existing 512 KB added-file limit and Git LFS exclusion
remain; on a committed-tip pass it checks files added by that commit. Existing large
tracked inputs such as the lockfile retain their prior size eligibility. Whitespace/final-newline fixes fail the invocation for inspection and staging.
prek dispatches Task serially and validates Conventional Commits; explicit live,
acceptance, property and mutation stages stay outside ordinary commits.

Run `fix` before staging, inspect its changes and follow the
[commit procedure](#commit-procedure). Rebase/cherry-pick/merge do not run pre-commit
hooks; verify the combined content explicitly.

### Acceptance tiers

Explicit **change acceptance** (`acceptance`) requires a clean committed tip, static
checks, bounded infrastructure preflight before expensive execution, property
exploration, the full unit suite with its configured coverage floor, non-GPU live
integration including CPU smoke, and a final clean/unchanged-tip check. Classification
does not skip requested checks. Product changes additionally need a branch mutation
report and fresh independent review; operational-policy changes also need independent
review after integrated verification.

**Release acceptance** adds the required single-GPU Severstal suite, FiftyOne native
database tests and final paired compatibility. Task owns their command options and
cleanup. Select required GPU options from pytest help and
[Severstal execution checks](augmentation.md#severstal-execution-checks). Check current
pcboard capacity before GPU work. Native direct/queued runs, API publication readback
and standalone rendered-chart observations follow the
[end-to-end skill](../.agents/skills/running-end-to-end-tests/SKILL.md).

Physical multi-GPU, external multi-user, two-host NFS and unavailable ClearML web-UI
scenarios are outside maintained mandatory acceptance. Product capabilities remain
supported; CPU DDP, simulated regressions, single-GPU direct/queued execution,
publication/readback, FiftyOne, standalone charts and paired integration remain covered.
Do not claim physical topology or embedded UI evidence from simulations or API payloads.

Report every selected required check as **passed**, **failed**, **deferred**, **waived**
or **error**. Temporary resource unavailability (including `infra-check` exit 3 or a
busy GPU) defers supported checks and blocks acceptance/integration/release. Continue
independent work and retry when availability changes. A user-authorized waiver is not
a pass. Configuration/permission errors (`infra-check` exit 1) need diagnosis;
assertion failures after successful setup remain test failures.

The [integration skill](../.agents/skills/running-integration-tests/SKILL.md) owns
selection and recovery decisions for the isolated environment. Live tests are selected
explicitly and use session-owned credentials, never the user's SDK configuration.
Provision required optional SDK decoders before execution; no package installation or
update belongs in a check. See [static analysis policy](static-analysis.md) for native
checker configuration and exclusions. Mocked results cannot establish native training,
GPU access or uploads; record those outcomes in dated evidence.

### Native CPU distributed regression tests

The `ddp_cpu` suite runs real native YOLO training, validation and checkpoint creation
in two-rank and four-rank CPU/Gloo process groups. It belongs to the unit suite, so
`test-full` and both acceptance tiers run it; it shares the `serial` xdist group with the
process-supervision tests, so one worker runs those tests one at a time while other tests
stay parallel. To select it directly:

```bash
uv run --frozen --no-sync pytest -m ddp_cpu
uv run --frozen --no-sync pytest tests/test_native_ddp_cpu.py
```

Use the existing repository environment on Linux or WSL with Torch distributed/Gloo
support. Only unsupported platform or unavailable Gloo prerequisites may skip;
native runtime, process and callback failures remain failures. The suite creates
isolated synthetic data and randomly initialized models from the installed local
YOLOv8n architecture YAML, with no pretrained download, network access, GPU or
ClearML service requirement. Tests use a local recording task at the tracking
boundary while exercising the production owner relay.

Successful scenarios verify actual CPU/Gloo/DDP processes, parameter updates and
cross-rank synchronization, sampler partitions, live ordered owner-only telemetry
and one inference-loadable native best checkpoint. Worker and owner-callback
failure scenarios verify failed completion and cleanup of owned processes,
descendants and relay activity. Scenario execution is bounded by a 180-second
deadline and a 30-second process-group timeout; cleanup allows five seconds for
graceful shutdown before terminating only the owned process tree.

Test-only trainer adaptations retain installed native loops and do not add a
production CPU distributed launcher. Local task recordings establish callback
behavior and model association. Accelerator launch, NCCL, AMP and actual ClearML
uploads/downloads require separate evidence. Physical multi-GPU execution is outside
the maintained mandatory gate; record observed results with their environment and limitations.

### Generated and composed regressions

Hypothesis and pytest-cov are development dependencies. The routine suite stays offline;
generated CY cases exercise lexical CSV identity, prediction-cache provenance and
frozen validation thresholds. Queue state-transition cases live in cy-queue. Composed workflow tests join saved Hydra
configuration, real storage, evaluation and report boundaries. `HYPOTHESIS_PROFILE`
selects the deterministic default profile `clearml-yolo` or the larger `explore`
profile that the `properties` stage uses. To run these tests with branch coverage:

```bash
uv run --frozen --no-sync pytest tests/test_quality_properties.py tests/test_workflow_quality.py --cov=clearml_yolo --cov-branch --cov-report=term-missing --cov-report=html:.tmp/coverage/html
uv run --frozen --no-sync pytest -m process_capabilities
```

Coverage identifies unexercised paths; it does not establish assertion quality. Preserve
Hypothesis's reported falsifying example and reproduce a failure before changing its
seed or adding retries. pytest-randomly prints its seed; reproduce an order-dependent
failure with `--randomly-seed=<seed>`, or disable shuffling with `-p no:randomly`. The
local `.hypothesis/` example database is ignored by Git. Keep mutation/fault
observations and run counts in dated feature evidence.

Single-GPU and FiftyOne live suites live in `tests/integration`, outside automatic
verification. Follow the [integration skill](../.agents/skills/running-integration-tests/SKILL.md)
for selection, prerequisites and cleanup evidence.

### Mutation report

`task mutation` is the scoped mutation acceptance of a change. It mutates only the
top-level functions and methods changed in the staged diff (or against a named base) in a
fresh workspace exported from the index, and reports killed, surviving, not-reached and
not-run mutants.

- **Test selection per change**: the union of the test node ids that `.testmondata`
  records for the changed files and that still exist in the staged tree, and, for a
  changed module without such validated testmon nodes, the test modules (`test_*.py`)
  that import it. When `.testmondata` is missing or unreadable, the import scan alone
  selects. When nothing is selected, mutmut does not run and the functions are reported
  as "Not reached by tests".
- **Excluded tests**: `tests/integration` is never selected, and every run deselects
  `-m "not ddp_cpu and not process_capabilities and not gpu_controls"`, tests that need
  real processes or hardware (`gpu_controls` is reserved for GPU-holding tests).
- **Budget**: 8 changed functions and 300 seconds by default; functions beyond the
  budget are reported as skipped, and mutants left unjudged count as not run.

`[tool.mutmut]` in [pyproject.toml](../pyproject.toml) holds the settings; generated
`mutants/` content is ignored by Git, Ruff and mypy and is outside Vulture's maintained
paths.

```bash
uv run --locked task --exit-code mutation                     # staged change
uv run --locked task --exit-code mutation -- --base master    # whole branch
uv run --locked task --exit-code mutation -- --strict         # survivors fail
```

| Exit | Meaning |
| --- | --- |
| 0 | Report produced; survivors and unreached functions are advisory. |
| 1 | Under `--strict`: surviving mutants, or changed functions no selected test reaches. |
| 2 | Tool or configuration error, or the clean test run failed; unresolved, never a pass. |

Run it explicitly for code changes before acceptance; it never runs in a commit hook and
is never cached. The `mutation-testing` skill owns survivor triage and settings
invariants. Keep dispositions in dated feature evidence.

### Static-analysis boundaries

Keep lint and stub distributions in the development group when adding runtime
dependencies. Review the tooling boundaries of `scripts/` when changing development
scripts. Ruff preview checks require explicit code selection; review the
[policy report](static-analysis.md) and refresh the rule inventory when changing the
locked Ruff version.

## Python integration and architecture

Use the [Python import migration](python-import-migration.md) when updating scripts or
saved Hydra targets. Workflows live in `application.use_cases` and require an explicit
`WorkflowDependencies` value. The composition root in `entrypoints.composition` creates
one dependency bundle per invocation; tests inject their own ports. Scientific core
code may use NumPy, pandas, SciPy, Pydantic and Pandera, but owns no SDK calls, logging
configuration, rendering or filesystem effects. Keep the pinned `digital-metrics`
algorithms in evaluation adapters and copy exact values into core evaluation records.

Purity and effect ownership remain design/review obligations. Custom static effect
enforcement has been removed, so architecture success no longer proves absence of
filesystem, environment, process or SDK effects inside otherwise allowed modules.
Import boundaries, dynamic imports, initializer restrictions and runtime-target
resolution remain automated; reviewers must inspect effect ownership explicitly.

Run `uv run --locked task --exit-code architecture` and the complete ordinary suite when
changing imports, package initializers, composition or subprocess/plugin targets. Static
architecture rules run in the development check stage; runtime import and Hydra
composition checks remain product tests. Updating a dependency boundary also requires
regenerated YAML checks and installed command helps, including DDP callback and
FiftyOne extension targets. Check CY source installs include its bounded console
publisher, terminal mirror and FiftyOne worker; the queue source install must include
its guardian, snapshot runner and GPU probe. Verify CY has no cy_queue/Textual/NVML
imports, direct Hydra sweeps stay sequential, and queue tests preserve atomic batch
validation, deferred UI imports and owner-only jobs. Run the queue repository tests,
Ruff, strict mypy and import contracts in the combined environment when changing
the shared interfaces. Include both-package identity checks.
Check selected config export for every command/model selection, ordinary SDK configuration
with unchanged external selectors and project-contained application destinations, and retained project scratch after success, failure and
cancellation. Verify explicit project temp paths without changing global SDK temp defaults.
Check fresh DDP callback ownership and restored in-memory settings without settings-file writes.
Invalid dataset entries must be preserved and reported; native locks must not fall back to soft locks. Fault-inject real subprocess
hangs during import, publication and shutdown; require bounded optional warnings and
validated receipts, rather than inferred success. See [runtime isolation](runtime-isolation.md).
Update maintained code links and migration guidance; preserve completed feature history as dated intent.
For detector/export changes, include the runtime prerequisites and acceptance matrices in
the [model guide](multi-model-backends.md) and [deployment guide](tensorrt-deployment.md).
Use `uv run --frozen --no-sync` for ad hoc commands in a deliberately prepared backend
environment so they never sync it. Task stages always run `uv run --locked`, which syncs
the worktree `.venv` to `uv.lock`. The sync is inexact: extra packages such as
`cy-queue` stay installed, while locked packages are restored to their locked versions.
The [paired release check](#paired-cy-and-queue-release-check) uses its own temporary
virtual environment.

## External dependencies

The [shared evaluation and reporting guide](shared-evaluation-reporting.md) describes
the additive APIs used by application adapters and the retained compatibility wrappers.
Dependency source revisions change only through an explicitly authorized update, with
both legacy and new interface checks and application parity evidence.

`digital-metrics` and `report-generator` live in ignored local directories under
`external/`. They are ordinary source copies, not parent-repository submodules.
Copy the approved source trees to `external/digital-metrics` and
`external/report-generator` before installing dependencies. Independent clones at
these paths also work; do not add their contents or Git metadata to this repository.

| Dependency | Upstream | Approved source revision |
| --- | --- | --- |
| digital-metrics | [repository](https://github.com/Wasilkas/digital-metrics) | `6e801be1564dce458294eb23592cc1aa0939c4d9` |
| report-generator | [repository](https://github.com/Wasilkas/report-generator) | `7339ef864b4ff1b1db499a08d647193128088e80` |

The committed project declares both packages by version only and never contains
`[tool.uv.sources]`. Development resolves them from a local wheelhouse of source
distributions built from the approved copies. Set up each worktree once, from its root,
after copying the sources:

```bash
uv build --sdist external/digital-metrics -o external/wheelhouse
uv build --sdist external/report-generator -o external/wheelhouse
[ -e uv.toml ] || printf 'find-links = ["external/wheelhouse"]\n' > uv.toml
uv sync --locked --dev
bash scripts/install-hooks.sh
```

The third command creates `uv.toml` only when it is absent; if `uv.toml` already exists,
add `find-links = ["external/wheelhouse"]` to it by hand. The Task stage `local-deps`
automates the first three commands and never overwrites an existing `uv.toml`. In a
fresh checkout, before the environment exists, run it as
`uvx --from go-task-bin task local-deps`. In an existing environment, rebuild the
wheelhouse after an authorized change of an approved external revision with
`uv run --locked task --exit-code local-deps`. `uv.toml`, `external/` and its wheelhouse
are gitignored; every worktree needs its own `external/` (a copy or symlink) and
`uv.toml`. The committed `uv.lock` records both packages as
`source = { registry = "external/wheelhouse" }` and does not store their source contents
or enforce their Git revisions. Then check the installation with
`uv run --locked cy --help`.

Why this layout:

- A committed path source in `[tool.uv.sources]` breaks installation from a git link:
  uv rewrites it to a `git+…#subdirectory=external/…` requirement that does not exist in
  the repository.
- A repository-root `uv.toml` cannot declare `sources`, but it can add `find-links`,
  which keeps all local configuration out of tracked files.
- End users install CY from a git link, ignore this lockfile and resolve both packages
  from their own package index; they have no GitHub access, so git sources are not an
  option.

Do not update upstream source revisions during ordinary setup. Existing submodule
users should preserve their populated source trees before switching to this revision;
remove only their obsolete `.git` pointer files and local `submodule.*` configuration.
Retaining `.git/modules/` preserves old dependency history for recovery.

`digital-metrics` is an external dependency. Keep it pinned to the approved upstream
revision. Do not change its source, checkout, dependency reference or locked revision
without the user's explicit intent to change it. General implementation,
cleanup and dependency maintenance requests do not authorize such changes. Adapt
`clearml-yolo` integration code when compatibility work is needed; report upstream
issues instead of patching or monkeypatching the dependency.

## Commit procedure

Commit when user or standing authorization covers the native completion workflow.
Explicit no-commit/no-release limits and the active host mode take precedence. Stage
explicit paths or hunks belonging to the task; preserve unrelated staged and unstaged
changes. Do not stash, reset, revert or bypass hooks to make a check pass. Use Conventional
Commits and inspect hook-generated changes before retrying.

Split work into coherent task-owned commits. Intermediate commits may use `SKIP=verify`
with final verification still outstanding; message validation and the staging guard stay
active. Keep mechanical formatting fixes in a separate commit. Do not use `--no-verify`
or blanket skips to hide failures. After the final task commit, run
`env -u SKIP -u PREK_SKIP -u CY_VERIFY_SCOPE -u PRE_COMMIT_ALLOW_NO_CONFIG uv run --locked prek run --all-files`
as the canonical automatic pass, without an equivalent preceding `verify`. If hooks
edit files, inspect and commit those mechanical fixes separately, then rerun affected
checks and the final pipeline until committed content passes without outstanding edits.
Relevant subsequent changes invalidate only affected evidence.

Change acceptance needs a clean committed tip. Each worktree uses its own prepared
environment ([setup](#external-dependencies)): Task pins each stage to the worktree's
`.venv`, so worktrees never share an environment. Do not resolve or update dependencies
during verification; dependency changes land as ordinary reviewed commits that update
`pyproject.toml` and `uv.lock` together. Releases run from a clean prepared checkout.

## Paired CY and queue release check

Before delivery of either package, inspect the latest CY and cy-queue source/default
branch/tag state, preserving unrelated work. Use the intended final versions, never
stale installed metadata as evidence. Task `paired-check` resolves both source checkouts
normally in a temporary environment, checks dependency consistency and source/installed
identity, runs the queue suite/help, reports identities and removes its environment.
`CY_QUEUE_DIR` selects the sibling source location when needed. Run relevant queue
static/import checks too when shared interfaces change.

Within local release, pairing runs once against the final versions inside the
semantic-release build step. A no-version outcome checks the unchanged pair once.
Immediate authorized publishing reuses that invocation's checks; later publishing
performs a fresh pass without re-versioning. Explicit `release-acceptance` includes
its own paired check. Missing/incompatible sources, stale metadata or failed/unavailable
checks block delivery. CY stays independent of the queue at runtime; the queue raises
its minimum CY version when it adopts a newer interface.

## Local releases

Code releases contain Git commits and annotated version tags only. Build project
wheels/source archives only for a concrete packaging investigation, never as routine
release checks or deliverables. The model-assets exception below remains separate.

python-semantic-release owns version selection, changelog, release commits and annotated
tags using [pyproject.toml](../pyproject.toml). No-version outcomes are successful.
Task supplies orchestration through:

- `release-local -- --expected-tip SHA [--branch NAME] [--publish]`: validate and
  fast-forward local integration, then semantic versioning. Local integration/tagging
  requires release authorization but does not require push authorization. `--publish`
  additionally requires explicit publishing authorization.
- `release-publish -- --expected-tip SHA [--tag vX]`: publish an existing accepted tip
  after fresh automated gates, without creating a new version.

The [release skill](../.agents/skills/release/SKILL.md) owns authorization, independent
review, native observations and recovery decisions. Both routes retain a nonblocking
Git-common-directory release lock, clean-tree and expected-commit checks, fast-forward
integration and checks that refs have not moved. Never wait on or break another run's
lock. Required shared gates run before advancing master; a failed or deferred gate
leaves it unchanged. Publishing pushes master and the pinned annotated tag for the
current source version, including an unpublished ancestor tag after prose-only
follow-ups, and confirms both remotely. The tagged commit must declare that same version.

Shared automated stages prevent duplicate execution. The semantic-release build step
refreshes the lock's root version, restricts prepared changes to `pyproject.toml`,
`uv.lock` and `CHANGELOG.md`, validates version-only project/lock changes, and runs the
paired check against final source versions before any release commit/tag. The version
commit alone may skip the ordinary verify hook; staging and message safeguards remain.
A failed validation creates no release commit/tag and leaves prepared changes for
explicit recovery. Inspect and recover only this attempt's changes; never hand-edit
versions/tags or reset unrelated work. No persistent verification receipt is created.

## Model-weight releases

The user-authorized model-assets exception permits `weights-*` GitHub Releases in
`BuckanovNikita/clearml-yolo` containing verified model-weight/source tar archives,
manifest, checksums and upstream notices. It does not authorize project wheels,
source distributions or registry packages. Weight tags have an independent cadence
from application versions; code releases neither package nor upload weights.
Reuse the current snapshot across code releases until its catalogue needs an update.

Inspect the current [eligible catalogue](model-assets.md#catalogue-and-automatic-execution),
native caches and upstream licence terms (the
[2026-10-29 licence inventory](https://github.com/BuckanovNikita/clearml-yolo/blob/91756fa4661c79854dacd7c827832854dc63e787/specs/009-release-weights/licenses.md) records those of the initial snapshot), then
assemble a complete snapshot with the explicit maintainer command:

```bash
uv run --frozen --no-sync python scripts/package_weights.py \
  --output ./weight-release --tag weights-YYYY-MM-DD --notices ./weight-notices
```

Replace the example date and notice directory deliberately. The script resolves the
eligible catalogue and writes independent `.tar` files, `manifest.json` and
`SHA256SUMS`; any unresolved entry fails packaging. Its default archive target is
1,900,000,000 bytes, including tar overhead and notices, below the 2 GiB hosting limit.
It performs no upload and does not change the runtime pin. Include every applicable
licence and attribution, source availability directions for AGPL assets, and DEIMv2's
non-commercial restriction. For DINOv3, preserve the exact bundled agreement,
the separately linked Meta website agreement and the timm model card; prominently
display “Built with DINOv3” in release notes and related product documentation.
Retain the genuine converted-checkpoint provenance and applicable use restrictions.
Preserve original upstream identities and real Hub
snapshot/configuration metadata; never fabricate a snapshot commit from a file hash.

Before publication, verify catalogue completeness, archive/member size and hashes,
safe members and fresh-cache offline native loading. Publish the manifest, checksum
file and all archives under the chosen new weight tag. Make the deliberate model
release visible as GitHub Latest so users can find its assets; runtime selection
still uses the packaged pin and never the moving latest endpoint. Verify the actual
hosted bytes against the manifest. Record the tag, sources, licence notices, executed checks
and limitations in dated feature evidence. Do not replace published bytes in place;
corrections use a new snapshot identity.

After verifying publication, deliberately update the packaged
`src/clearml_yolo/adapters/assets/weights-manifest.json` pin to that manifest and run
the applicable architecture, behavior, documentation, paired compatibility and
independent review gates before code delivery. The pin participates in automatic
preparation fingerprints. Packaging, mocked transport or an uploaded asset alone
does not establish successful native restoration or complete code-release acceptance.
