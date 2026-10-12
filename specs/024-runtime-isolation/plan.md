# Controlled execution and library isolation — implementation plan

The [2026-10-12 amendment](spec.md#file-ownership-amendment--2026-10-12) governs current
file ownership; the original plan below is retained as completed history.

## Summary

Implement the approved [specification](spec.md) on the existing Python 3.12, uv,
Hydra/hydra-zen and Pydantic architecture. Keep dependency revisions unchanged.
Restore selected queue machinery from `3f236ff` (parent of removal `25e874e`),
preserving current TRACE, native DDP and task ownership integration.

## Contracts and shared interfaces

- Model wrapper fields `queue.enabled` and `autogpu.enabled` default true. Wrapper
  validation accepts them explicitly and execution removes them before workflow calls.
- Modes: both true = queued automatic; queue false = direct existing availability
  selection; auto false with queue = exact UUID union; both false = native pass-through.
  Manual queued mode rejects ambiguous CUDA selectors. Preserve an immutable mapping
  and original device order; put downstream GPU first before child creation so
  contraction retains it without modifying visibility after CUDA initialization.
- Reuse queue registry v1 with exact mode count/visible equal to the UUID union;
  capture its user-wide root before project XDG overrides. No TTL/PID-only recovery.
- FiftyOneConfig adds finite positive preflight/publish/lock timeout seconds (60/900/30).
  Preserve Publisher port. Fresh subprocess per operation exchanges Pydantic JSON;
  success requires zero exit and matching task/operation/complete receipt. No fork,
  inherited GPU/owner metadata or undrained pipes. Five-second graceful termination,
  then forced termination and five-second reap; report unsafe cleanup explicitly.
- Stdlib bootstrap lives in adapters/runtime/bootstrap.py. Public internal contract:
  `initialize_runtime_environment() -> Path` installs persistent paths idempotently;
  `runtime_environment() -> ContextManager[Path]` scopes an invocation temporary arena
  and restores process environment/tempfile state. Entry modules defer imports until
  this boundary. Preserve ordinary inert imports and explicit programmatic initialization.
- Runtime .config/.cache/.tmp live beneath resolved CY_HOME. Reject outside-project
  library config, retain explicit data/output paths. Use SDK env selectors, including
  ClearML config file/directory, five FiftyOne config files, ETA, matplotlib, torch,
  triton, Requests/netrc, botocore credentials, XDG and scoped system temp settings.
- FiftyOne child-only guarded constants loader redirects hardcoded home paths before
  __public__ import, retaining installed binary paths. No installed source edits or
  digital-metrics monkeypatch. Compatibility failure warns and disables optional work.
- cy-init-config uses public command names, default cy; dump_config_tree has the same
  keyword-only selector. Both native groups are needed by all five model schemas.

## Dependency-aware parallel ownership

Wave 1 after this interface agreement:
A owns queue/runtime/worker/launcher plus scheduler tests; B owns FiftyOne bounded
adapter/worker/compatibility, core publication timeout fields and publication tests;
C owns bootstrap/filesystem and isolation tests. Parent owns shared Hydra common,
configs/validation, composition hooks, thin entrypoints, packaging and cross-boundary
integration. Children must report requested edits outside ownership, not overwrite them.

Wave 2: exporter agent owns exporter modules/tests; documentation agent owns maintained
contracts/guides; independent test agent exercises combined behavior. Parent integrates
and verifies. Fresh independent final review starts only after parent checks, with a
ship/fix-first/rethink verdict. Respect three-child capacity; no child delegation.

## Verification

Tests first for changed behavior. Restore meaningful historical queue tests; add all
four modes, exact union/remapping/replay/contraction, cross-project coordination,
complete-sweep mixed-mode rejection, child TRACE and current CPU DDP regressions.
Fault-inject real publication process hangs/crashes and require bounded cleanup.
Seed global configs and trace subprocess reads/writes; prove no forbidden lookup and
scratch cleanup without deleting concurrent/persistent state. Check eight config
selections, Hydra round-trip, collision/force/symlink behavior and installed helps.
Run pytest, Ruff, mypy, import-linter, applicable hooks and wheel/sdist install checks.
Native acceptance: one-GPU three-command serialization, healthy and failed FiftyOne,
ClearML readback/download, native CPU/DDP and available multi-GPU contraction.
Unavailable native hardware is explicitly unverified, never inferred from mocks.

## Documentation and completion

Update README (Russian), docs/project-contracts.md, docs/current-contracts.md,
docs/filesystem-policy.md, development/import/migration guides, affected feature
003/006/011/013/022 contracts and project end-to-end skill/prerequisites. Preserve
historical evidence, mark supersession. Validate Markdown/links/examples. Record
portable dated evidence here; machine evidence stays in the global environment skill.
Use authorized release workflow after verified integration and fresh review; tags only.

## Constitution and workflow check

Typed boundaries/import checks and current toolchain remain. User approval explicitly
supersedes former ban on queue bypass and ambient-config permission. No installed
workflow or constitution file changes. No registered extension hooks. Use explicit
SPECIFY_FEATURE_DIRECTORY rather than writing protected .specify/feature.json.

## File ownership implementation — 2026-10-12

Reuse the completed feature, append tasks and preserve history. Runtime agent owns
bootstrap/filesystem and their tests; dataset agent owns dataset_cache and its tests;
dependency agent owns pyproject/lockfile. Parent owns SDK integration, callbacks,
operation scratch, docs and combined verification. These workstreams are independent
until integration. No subagent delegation. Fresh read-only review follows parent checks.

Remove isolation-only SDK constant loaders and import-directory contexts. Keep callbacks
in process memory, including fresh native DDP workers. Pass project scratch directories
explicitly to workbook and publication operations. Retain arenas and uncertain-shutdown
scratch. Maintain native dataset locks without soft fallback; never rebuild an invalid
existing entry automatically. Dependency work follows feature 025's appended amendment.

Run targeted tests, full pytest (including CPU/Gloo), Ruff, mypy, import-linter and native
SDK/distribution checks. Exercise detector/GPU/export acceptance on the new Torch pair.
Record missing NFS/multi-host evidence accurately. Update filesystem/runtime contracts,
README, migrations, affected current contracts and end-to-end guidance; validate Markdown,
links and changed examples. After integration, obtain fresh independent review and
perform the authorized existing release workflow with exact local source restoration.
