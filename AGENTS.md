# clearml-yolo agent instructions

`clearml-yolo` (CY) provides Hydra/hydra-zen commands (`cy`, `cy-train`, `cy-predict`, `cy-val`,
`cy-metrics`, `cy-compare`, `cy-report`, `cy-ground-truth`, `cy-export` and tools) that train,
predict, evaluate, compare, report and export detectors (YOLO, DEIMv2, RF-DETR, Faster R-CNN,
FCOS) with ClearML publication. [DOCS.md](DOCS.md) holds architecture, behavior contracts, config
keys and operations. Read the affected DOCS.md section and the user page that owns the fact before
changing behavior or configuration.

## User documentation

- The user documentation is [README.md](README.md) (entry page) and the pages that
  [docs/README.md](docs/README.md) lists. Each fact has one owning page: the page that index lists
  for its command, config group, file format or topic. Other pages link to the owner; `README.md`,
  `docs/README.md` and `GLOSSARY.md` also restate some facts (for example the command list and
  counts, Python range, install command, weight licences, defaults quoted in glossary entries).
- A behavior or configuration change updates, in the same change, its DOCS.md section, the owning
  user page and every place that restates the fact (search `README.md`, `docs/` and
  `GLOSSARY.md`). Every behavior claim on a page the change edits matches the code and agrees with
  DOCS.md; record a mismatch found on another page in the Linear issue. A fact with no owning page
  goes on the page of its command or config group.
- Adding or removing a command updates the `README.md` command table and the command counts in
  `README.md` and `docs/README.md`; adding, renaming or removing a page updates `docs/README.md`.
  `cy-download-weights` prints the URL of `docs/commands/cy-download-weights.md`: moving that page
  updates the message and its test.
- [GLOSSARY.md](GLOSSARY.md) defines the user-facing terms in English with their Russian wording
  and lists the terms the pages keep in English; developer and contract terms stay in the DOCS.md
  glossary section. User pages use the glossary's Russian wording. A change that introduces,
  renames or narrows a user-facing term updates GLOSSARY.md in the same change.

## Layout

- `src/clearml_yolo/`: `core` (pure records and algorithms), `application` (use cases, ports,
  contracts), `adapters/<responsibility>` (SDKs, files, processes), `entrypoints` (CLI, Hydra,
  composition). `tests/` unit tests; `tests/integration/` live tests; `scripts/` repo tooling
  (verification routing, mutation, release, weight packaging, Severstal corpus).
- Config: `pyproject.toml` (deps, mypy, vulture, pytest, semantic-release), `ruff.toml`,
  `src/ruff.toml`, `.importlinter`, `Taskfile.yml`, `Taskfile.ops.yml`.
- `.claude/settings.json` and `.codex/hooks.json` run `scripts/session_status.sh` at session
  start; changes it lists may belong to another session.
- `CHANGELOG.md` is written by semantic-release; never edit it by hand.

## Environment setup (per worktree)

1. Put the approved `digital-metrics` and `report-generator` copies under the ignored `external/`
   (copy or symlink; not submodules; never commit their contents). Revisions are in DOCS.md.
2. `uvx --from go-task-bin task local-deps` (builds ignored `external/wheelhouse`, creates
   ignored `uv.toml` with `find-links = ["external/wheelhouse"]`; never overwrites `uv.toml`).
3. `uv sync --locked --dev`, then `uv run --locked cy --help`.

Unset any inherited `UV_PROJECT_ENVIRONMENT`. For ad hoc commands use `uv run --frozen --no-sync ...`
so the environment is never synced; `uv run --locked` syncs `.venv` inexactly (extra packages such
as `cy-queue` stay, locked packages return to locked versions).

## Checks

There are no git hooks and no commit-message check. Run checks directly as
`uv run --locked task --exit-code <stage>`. A clone that ran the removed `scripts/install-hooks.sh`
still has dispatchers (marked `clearml-yolo worktree dispatcher`) in
`$(git rev-parse --git-path hooks)` that fail every commit: restore the `clearml-yolo-backup.*`
copies there (remove hooks marked `.absent`) or delete its `pre-commit` and `commit-msg`.

- `check`: `hygiene` (added files <= 512 KB unless LFS, conflict markers, syntax; fixes
  whitespace and fails so you can inspect), `lock` (`uv lock --check`), `ruff` (`ruff check .`),
  `format-check` (`ruff format --check .`), `architecture` (`lint-imports`), `mypy` (`mypy .`),
  `vulture`, `deptry` (`deptry .`).
- `fix`: `ruff check --fix --no-unsafe-fixes .` and `ruff format .`; never stages. Run before staging.
- `verify`: `check`, then `scripts/verification.py` routing scoped by `CY_VERIFY_SCOPE`
  (`auto`|`staged`|`working`|`commit`; `auto` = staged diff, else uncommitted, else last commit).
  Prose and tooling get `check` only; test-only changes get a bounded selection (exit 3 with
  `TARGETED VERIFICATION GAP` when a changed helper has no recorded dependents); any non-prose
  file under `src/` gets `task test`. Run `verify` on the committed tip after the last commit.
- `test` (testmon-affected unit tests), `test-full` (full unit suite, refreshes testmon),
  `coverage` (full unit suite, branch coverage against `fail_under`); `-n $CY_TEST_WORKERS`
  (default 2), `tests/integration` excluded. Check host load before heavy stages.
- `mutation` (staged; `-- --base master` for the branch; `-- --strict` fails on survivors).
  Exit 0 = advisory report, 1 = survivors under `--strict`, 2 = tool failure, never a pass. Record
  a disposition for every survivor and unreached function in the issue.
- Direct suites outside `test`: `uv run --frozen --no-sync pytest -m ddp_cpu` and
  `-m process_capabilities` (serial xdist group). Reproduce order failures with the printed
  `--randomly-seed=<seed>` or `-p no:randomly`; keep Hypothesis falsifying examples; never change a
  seed or add a retry to pass. Advisory unused-code audit: `vulture --min-confidence 60`.
- Live and release: `infra-check`, `infra-up` (`COMPONENTS=all|clearml|fiftyone`), `infra-env`,
  `infra-down`, `integration`, `acceptance` (clean committed tip: check, infra-check, coverage, integration),
  `release-validation`, `release-acceptance` (needs `CY_SEVERSTAL_ARGS`), `paired-check`.
- Task keeps no freshness cache; a skipped or interrupted run is not evidence.

Selection: localized product changes run focused tests; shared runtime/config, broad refactors or
uncertain impact run `task coverage` (claim the coverage floor only from it); product changes
include a mutation report; dependency/installation changes and interfaces cy-queue consumes need
`paired-check` against the final proposed versions before merge. After changing imports, package
initializers, composition or subprocess/plugin targets, run `architecture` and the full unit suite;
also check regenerated YAML examples and installed command helps (DDP callback, FiftyOne extension,
console publisher, terminal mirror, FiftyOne worker targets), config export per command and model,
scratch retention after success/failure/cancel, and that injected subprocess hangs end in bounded
warnings. Import contracts do not prove effect freedom; review effect ownership explicitly.
Select verification against the merge base with `master` and record both SHAs. Reuse a result only
while its inputs and environment are unchanged.

Status vocabulary: passed, failed, deferred, waived, error. A deferred required check blocks
acceptance and merge; only the user waives. Exit 3 from `infra-check`/`integration` or a busy GPU
means deferred; `infra-check` exit 1 is a configuration error.

## Live tests

- The `tests/integration/lifecycle.py` module docstring is the operating guide: each worktree
  creates and deletes its own namespace `cy-it-<6 hex>` on context `docker-desktop`; no shared
  stand is used. The platform sweeper may delete it after 48 h or a Docker Desktop/PC restart
  (the record then goes stale).
- `infra-env` output contains credentials: eval it, never print or log it. Live tests use those
  session credentials, never the user's SDK config. Put `INTEGRATION_RUN_TAG` in ClearML project
  names and tags.
- Only the creator deletes a test environment (`tests/integration/.run-tag`); never replace a live
  record to get past an ownership refusal. With `INTEGRATION_KEEP_DATA=1`, run
  `task infra-down ENV=<id>` within 48 hours. `python -m tests.integration.lifecycle stop --dry-run`
  previews deletion.
- Check GPU load before any GPU stage. Never claim multi-GPU, multi-user, two-host NFS or ClearML
  web-UI outcomes from simulations.

## Policy

- Mocked or fake tests (ClearML fake, simulated SDK, mocked TensorRT, CPU/Gloo DDP, simulated GPU
  telemetry) never establish native, GPU, upload, Agent replay or pairing outcomes.
- Pass ClearML project names and tags explicitly; application config must not depend on an agent
  harness or machine. Keep credentials out of tracked files and uploads.
- Preserve pre-existing services, containers, data, datasets and user SDK settings; touch a shared
  resource only with ownership evidence and user authorization.

## Architecture boundaries and hard constraints

- Layers `entrypoints -> adapters -> application -> core`, inward only; `.importlinter` is
  exhaustive and the only cross-adapter/SDK-owner edge table. Core does no I/O; application acts
  only through ports in `WorkflowDependencies`; package import has no runtime effect.
- CY never imports `cy_queue`, Textual or NVML (dependency is cy-queue -> CY). Direct commands
  reject `queue.*`, `autogpu.*`, `auto_gpu.*`, `hydra/launcher=cy_queue`; sweeps are sequential.
  A newer interface used by the queue requires raising the queue's CY minimum.
- One ClearML task per experiment command (`reuse_last_task_id=False`); workers and ranks never
  create tasks or upload. Success only after every upload is confirmed and read back (Output
  Models by SHA-256); never auto-retry uncertain deliveries.
- The `run` Configuration Object is the only replay/cache input; provenance objects never drive
  replay. Credentials never enter configuration, status or logs.
- Never retry with a smaller batch, add precision/compiler fallbacks, substitute non-finite values,
  resume training, or silently use other/random weights. Never disable checksum, size or TLS
  checks, never rewrite export sidecars, never install packages at run time.
- All project writes resolve beneath `CY_HOME`; never change HOME, XDG, TMP or library config/cache
  selectors. Thresholds calibrate only on `val`; test never calibrates.
- Commands own and must clean up every process they launch, using PID+start-time identity; never
  signal processes they cannot prove they own.
- Public CLI and Python APIs, serialized formats and scientific values are compatibility
  boundaries. Unavailable metrics stay NA, never zero.

## Language standards

- Product code never uses `from __future__ import annotations` (Pydantic and Hydra read annotations
  at runtime); keep syntax compatible with Python 3.12.13, the declared floor.
- Type everything explicitly; confine `Any`, casts and dynamic access to external boundaries with a
  stated reason. Scope mypy `ignore_missing_imports` to the affected modules; prefer stubs.
- Ruff (`ALL`, preview) and strict mypy are never weakened to pass; suppressions name rule and reason.
- Pydantic for config and validated records, Pandera for dataframes, Loguru via the observability
  adapter, pytest for tests, `pathlib` for paths; comments and log messages in English.
- Catch specific exceptions at a boundary that can act; preserve the cause; never swallow failures.
- Change dependencies with `uv add`/`uv remove`, committing `pyproject.toml` and `uv.lock` together;
  never `uv lock --upgrade` for repair; never resolve dependencies during verification.
- Remove code only after tracing its consumers; never delete validators, serialized fields or
  SDK-consumed attributes on a Vulture report alone.

## Dependencies

- Keep `digital-metrics` and `report-generator` at their approved revisions; change source,
  checkout, reference or locked revision only on explicit user intent; adapt CY and report
  upstream issues instead of patching them.
- Never commit `[tool.uv.sources]`: uv rewrites a path source into a `git+...#subdirectory=external/...`
  requirement that breaks git-link installs. Preserve ignored `uv.toml` and `external/`.
- Build CY wheels or sdists only for a concrete debugging task, never as deliverables or checks.

## Delivery and release

- Every change: a Linear issue in team `SIP`, project `clearml-yolo`, a task branch and a GitHub PR
  in `BuckanovNikita/clearml-yolo`. End the PR title with the issue identifier, `... (SIP-123)`:
  Linear links the PR and moves the issue to Done when it merges. Agents push task branches over
  the existing SSH remote and open PRs; humans squash-merge. Never push to or merge into `master`.
  Explicit no-commit or no-push limits take precedence.
- Team `SIP` holds one project per repository and one number space across them: pass `team: SIP`
  and `project: clearml-yolo` on every Linear create and list. This project is what a skill calls
  the issue tracker. Issues start from the Linear template `default`, with an explicit `state`:
  `In Progress` for work that starts now, otherwise the triage role.
- The Linear status is the triage role. Where a skill names a role, set the status:

  | Role              | Status                                | Meaning                           |
  | ----------------- | ------------------------------------- | --------------------------------- |
  | `needs-triage`    | `Triage`, no `ready-for-human` label  | Maintainer evaluates the issue    |
  | `needs-info`      | `Backlog`                             | Waiting on the reporter           |
  | `ready-for-agent` | `Todo`                                | Fully specified for an agent      |
  | `ready-for-human` | `Triage` + label `ready-for-human`    | Requires human implementation     |
  | `wontfix`         | `Canceled`, after a comment says why  | Will not be actioned              |

  `ready-for-human` is the only role with a label; remove it when the issue leaves the role. An
  issue with no role yet goes to `Triage`. `In Progress`, `In Review`, `Done` and `Duplicate` are
  past triage. Category roles are labels: `bug` = `Bug`, `enhancement` = `Feature`.
- Dependencies are Linear relations (`blockedBy` / `blocks`). Merge a duplicate with `duplicateOf`
  on the absorbed issue: Linear moves it to `Duplicate`, and setting that status directly fails.
- Evidence (counts, timings, SHAs, IDs, commands) lives only in the issue and PR.
- Done = merged to `master` with acceptance criteria met. Dependent work starts only after its
  prerequisite is verified on its base branch; a canceled prerequisite means replanning, never a
  bypass.
- Stacked PRs target their parent branch; humans merge bottom-up; `--force-with-lease` only on
  task-owned branches.
- A squash-merge into `master` releases automatically (semantic-release). No CI check runs on PRs,
  so verification, review and pairing finish before merge.
- Commit types drive the version and are not checked by any hook: `feat`, `fix`, `perf` and any
  breaking type (`!` or `BREAKING CHANGE:`) bump; others do not. The PR title becomes the squash
  header and the release parser also reads headers inside the squash body; fix any wrong type.
  Allowed types: build, chore, ci, docs, feat, fix, perf, refactor, style, test; the release
  parser silently ignores a malformed header.
- The release job needs `GITHUB_TOKEN` `contents: write` and repository rules that let it push to
  `master`; never weaken human protections to grant that. After merge, record on the issue the
  release run URL, source and final SHAs, version (or no-version result) and tag. The job
  establishes no native, GPU, upload or pairing outcome.
- Code releases are commits and annotated `v*` tags only; `weights-*` GitHub Releases only on
  explicit request. Never overwrite, move or delete tags.

## Pitfalls

- `uv.lock` does not enforce the external revisions; a stale wheelhouse silently installs other code.
- `check` covers the whole tree; `verify` routes one change set only (staged, else uncommitted, else
  the last commit). On a clean tip a prose-only last commit reruns no product tests, so select
  branch-wide checks from the merge base yourself.
- mypy package-level `ignore_missing_imports` also hides missing submodules.
- Standalone pytest module names in `.importlinter` are listed by hand; add new ones.
- `tests/test_native_config.py` deliberately reads the installed Ultralytics configuration.

## Working agreement
- At the start of work, state the worktree path, the current branch and its relation to the default branch; say when remote refs were not fetched.
- Inspect existing and staged changes before editing. Preserve unrelated work and local overrides; stage only task-owned paths and inspect the staged diff.
- Report what each executed check establishes and what remains unverified; distinguish mocked checks, live outcomes and historical evidence. Clean up task-owned processes and temporary resources.
- Tests must exercise product code, never project tooling.
- Changes to behavior, interfaces, dependencies, security or operational policy need a fresh independent review after integration and verification. Small wording edits may be self-reviewed.
- Split large work into independent delegated tasks with explicit write ownership and acceptance evidence; delegated agents do not delegate further.
- Use Conventional Commits. Commit automatic formatting separately from logic. Local commits within the task scope need no approval.
- README.md and docs/ are Russian; AGENTS.md, DOCS.md and GLOSSARY.md are English. Keep observed counts, timings and deployment status out of all of them.
- Keep machine-specific paths, endpoints and settings in local configuration, not in these files.
