# Controlled execution and runtime isolation

The approved [feature 024 specification](../specs/024-runtime-isolation/spec.md)
amends the former queue-removal and ambient-library-configuration rules. The
[GPU execution contract](../specs/022-simple-gpu-wait/contracts/execution.md) defines
all four execution modes; [filesystem ownership](filesystem-policy.md) defines
configuration, persistent data and temporary ownership. Dated feature evidence
remains evidence of its original implementation, rather than current acceptance.

## Selected configuration export

`cy-init-config DIRECTORY [--command NAME] [--force]` accepts `cy`, `cy-train`,
`cy-predict`, `cy-val`, `cy-metrics`, `cy-report`, `cy-compare` and `cy-ground-truth`.
The default is `cy`. Each invocation writes exactly one `<command>.yaml` wrapper.
The five model commands also write `ultralytics/default.yaml` and
`ultralytics_predict/default.yaml`; the other three require no native group files.
Only selected destinations and their parents participate in overwrite preflight.
Unrelated files remain unchanged. Existing selected files fail without `--force`;
force replaces regular files only, never symlinks or directories. No ClearML task
or native model runtime is created for export.

```bash
cy-init-config cy-config
cy-init-config metrics-config --command cy-metrics
cy-metrics --config-dir metrics-config --config-name cy-metrics --help
```

Back up custom YAML before regenerating each command; see
[configuration migration](python-import-migration.md#regenerate-saved-configuration).
`dump_config_tree(directory, *, command="cy", overwrite=False)` exposes the same
selection for Python callers.

## Optional FiftyOne operations

FiftyOne remains enabled by default where publication is supported. Factory,
preflight, request preparation, publication, local receipt and run-link failures
warn and preserve otherwise successful computation and the ClearML task.
`fiftyone.enabled=false` selects a dependency-free no-op publisher. Cancellation
retains interruption semantics.

| Setting | Default seconds | Scope |
|---|---:|---|
| `fiftyone.preflight_timeout_seconds` | 60 | Setup operation, including import and worker exit |
| `fiftyone.publish_timeout_seconds` | 900 | Publication operation, including import and worker exit |
| `fiftyone.lock_timeout_seconds` | 30 | Database publication lock acquisition |

Overrides must be finite and strictly positive. Each operation uses a fresh
supervised subprocess with no GPU visibility, queue lease or ClearML task ownership.
The supervisor drains diagnostics, waits for successful exit and validates operation
and task identity plus a complete receipt before reporting success. A receipt from
a failed or timed-out worker cannot establish publication success. Termination
allows up to five seconds for graceful cleanup and five for forced reaping; unsafe
cleanup is reported explicitly. Partial persistent database state is retained for
same-task retry. Publication never installs the App plugin automatically.

```bash
cy --config-dir cy-config --config-name cy fiftyone.preflight_timeout_seconds=30 fiftyone.publish_timeout_seconds=300 fiftyone.lock_timeout_seconds=10
```

This containment does not establish the root cause of the original remote hang.
Fault injection verifies bounded failure behavior independently of that incident.

## Runtime boundary

The eight application commands and `cy-init-config` establish project configuration
through a stdlib-only bootstrap before SDK imports. `cy-dedup` loads no SDKs or
configuration, creates no application directories and keeps its cleaned atomic
temporary files beside the selected destination. Package imports remain inert. The command's owned runtime scope includes execution,
native descendants, optional publication, required uploads, task finalization and
cleanup. `native_runtime()` scopes environment and scratch for direct programmatic
use too, restores settings on exit and reuses an outer CLI arena when present.
`command.return` follows cleanup and is not a success assertion.

The boundary preserves `HOME`, package defaults and OS runtime assets. Configuration
selectors resolve inside the physical `CY_HOME` root; symlinks cannot bypass that
rule. Optional `AWS_WEB_IDENTITY_TOKEN_FILE` and `AWS_CREDENTIAL_FILE` selectors
must also remain inside that root; bootstrap validates them without creating credential
files. Explicit inputs, outputs and persistent data/cache destinations remain valid
outside that root. Relative SDK data/cache destinations are normalized against the
launch directory before the temporary SDK import-directory context, so import-time
cwd changes cannot redirect durable storage.

SDK imports bind the process to one project root because SDKs retain configuration
locations. Leaving a runtime scope restores environment and temporary settings but
does not undo that binding; selecting another `CY_HOME` requires a fresh process.
The [ClearML configuration adapter](../src/clearml_yolo/adapters/clearml/configuration.py)
owns compatibility with SDK constants lacking environment selectors: its session cache
follows `XDG_CACHE_HOME/clearml/session`, and botocore's customer model directory follows
`XDG_CONFIG_HOME/aws/models`. Their defaults under `CY_HOME` are
`.cache/clearml/session` and `.config/aws/models`; custom XDG roots must pass project
containment validation. Unsupported constant interfaces fail closed before task creation;
packaged botocore models remain available. These selections persist through SDK shutdown.
Shared GPU queue coordination is outside invocation scratch and
is not a library configuration source. External runners such as uv and pytest are
outside this command boundary.
