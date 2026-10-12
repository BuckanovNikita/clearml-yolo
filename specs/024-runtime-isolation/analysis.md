# Pre-implementation consistency analysis — 2026-10-11

FR-001 maps T013–T014; FR-002–006 map T004–T006; FR-007–008 map T007–T009;
FR-009–011 map T010–T012; FR-012 is enforced by T015–T021. Four user stories cover
all five requests. Every implementation area has tests, ownership and dependencies.
No unresolved user decisions or critical inconsistencies found. The accepted user
plan supersedes old bypass/config defaults; historical evidence is retained. Original
hang reproduction and physical multi-GPU execution remain evidence limits until run.
No extension hooks registered. Spec quality checklist: 6/6 satisfied.

## Implementation rulings

- Generic desktop XDG search lists are ambient discovery defaults. Replace inherited
  XDG_CONFIG_DIRS/XDG_DATA_DIRS with project-local lists instead of rejecting normal
  OS values; explicit outside-project library config file/path selectors still fail.
  Evidence: standard inherited XDG_DATA_DIRS otherwise broke every installed CLI help.

## Integration amendments — 2026-10-11

- The filesystem-only `cy-dedup` retains its existing no-SDK/no-startup-directory
  contract. Its atomic temporary files already have destination-local ownership and
  cleanup. The eight application entrypoints and configuration exporter install the
  runtime SDK environment; command TRACE completion follows owned scratch cleanup.
- Direct programmatic `native_runtime()` scopes and restores bootstrap mutations.
  Persistent explicit initialization remains available before SDK imports. Tests now
  restore process environment/bootstrap state between cases rather than leaking one
  test project's configuration into another test's subprocess.
- Publication workers use supervisor-owned temporary directories through interpreter
  shutdown. Unsafe cleanup retains a durable conservative marker plus an in-memory
  retention fallback; recovery requires proof that known owners have exited.
- Optional AWS credential file selectors are constrained to the physical project root
  without synthesizing files. Relative durable SDK data paths are normalized before
  import-time cwd changes. SDK imports retain a durable one-project process binding;
  scope restoration cannot safely permit another root with cached SDK settings.
- ClearML session-cache and botocore customer-model constants have no sufficient
  environment selectors. The owned ClearML configuration compatibility adapter checks
  their interfaces and redirects them to project paths before task creation, retaining
  installed model defaults and the selected paths through SDK shutdown.

## File ownership consistency analysis — 2026-10-12

The user-approved amendment explicitly supersedes the original library-isolation and
arena-cleanup requirements; completed history is preserved. All requirements map to
T023–T029, with dependency verification in feature 025 T059–T061. No material user
ambiguity remains. Existing environment overrides are the only initial working change.
No installed workflow tooling or external dependency source is modified. The main
integration risk is fresh DDP workers: removing persisted temporary settings must retain
owner-only callbacks. Cleanup on uncertain shutdown and native lock failure require
behavioral regression evidence. NFS cannot be claimed from local subprocess tests.
