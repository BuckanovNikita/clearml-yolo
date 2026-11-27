# ADR-0309 · Own the workspace and processes of a direct experiment

CY resolves where an invocation may write, tracks the processes it starts and exposes enough local evidence to diagnose its outcome. A queue client consumes these interfaces while owning its own admission, GPU reservations and scheduling.

## Workspace, run directory and scratch

CY freezes `CY_HOME` to an absolute root at startup, using the launch directory by default. Project writes, including native output overrides and relocated scratch, must physically resolve beneath it. A symlink leading outside fails containment. External read-only inputs and library-owned caches retain their locations, and CY preserves the user's home, XDG and temporary-directory selectors. A bounded, read-only Git probe of the original launch directory clears inherited Git overrides and warns once when it cannot identify a worktree. The experiment can continue. The package checkout recorded by ClearML has its own identity. The original rationale for the launch warning is undocumented.

Default result directories encode the project, task name and task ID as safe path components. An explicit pipeline `run_dir` takes precedence over `run_id`. Reusing a directory preserves its contents. Pipeline runs and default-routed training atomically update `runs/latest`. If an ordinary file or directory already has that name, CY moves it aside with its contents. Link errors warn. Hydra composition logs have a separate layout.

The outer runtime scope creates a unique `cy-runtime-*` arena. Nested scopes in the same process share it, and a spawned process entering another scope can create its own. `CY_RUNTIME_TEMP_ROOT` can relocate the scratch parent within the workspace. Arenas survive success, failure and cancellation so diagnostics remain available. A later invocation leaves them alone. Operators can remove obsolete arenas after their consumers finish. Helpers may clean their own temporary files earlier.

<details>
<summary>Sources and verification</summary>

- Resolve project writes beneath the selected workspace — [Workspace bootstrap](../src/clearml_yolo/adapters/runtime/bootstrap.py) · [Composed destination validation](../src/clearml_yolo/entrypoints/hydra/validation.py) · [Native route containment](../tests/test_native_output_containment.py) · [Workspace guide](../docs/workspace.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/28b74f72054889c4b0706fecb8983c0ed6196235)
- Route result directories by task identity or explicit destination — [Run identities and latest link](../src/clearml_yolo/adapters/storage/run_identity.py) · [Routing and displacement cases](../tests/test_run_identity.py) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/7ef1c10ab4d633d4b9535aef24167bdb5c5247da)
- Retain invocation scratch after every exit — [Retention and subprocess scenarios](../tests/test_runtime_bootstrap.py)
- Warn when Git cannot identify the launch directory as a working tree — [Launch check](../src/clearml_yolo/adapters/runtime/git_workspace.py) · [Command integration](../src/clearml_yolo/entrypoints/hydra/common.py) · [Probe and warning cases](../tests/test_git_workspace.py) · [Launch contract](../DOCS.md#commands-and-configuration)

</details>

## Cache maintenance with cy-dedup

On a quiescent cache, `cy-dedup` finds regular image files with matching names and sizes, then verifies SHA-256 and bytes. For an eligible pair it makes a verified same-filesystem reflink and atomically replaces the destination, preserving independent file semantics. Cross-device pairs, hardlinked destinations and unsupported reflinks are skipped.

The command reports scan, duplicate, reflink, skip and failure counts. A skip can leave the exit successful. A recorded failure gives exit 1. `--dry-run` permits read-only candidate discovery outside the workspace and does not test filesystem reflink support.

<details>
<summary>Sources and verification</summary>

- Reflink identical cached images with cy-dedup — [Command entry](../src/clearml_yolo/entrypoints/dedup.py) · [Comparison and replacement](../src/clearml_yolo/adapters/storage/dedup.py) · [Filesystem scenarios](../tests/test_dedup.py) · [Command and exit codes](../docs/commands/cy-dedup.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/d9d6fcdf2d1f2a8ea986cf72e6dc2aa70d483497)

</details>

## Process ownership and queue admission

A native worker or batch trial can leave descendants in another session. Linux supervision combines subreaper discovery, process birth identity and pidfds to establish which descendants belong to the invocation. It checks identity before signalling or reaping and confirms quiescence across successive scans. Cancellation permits bounded escalation from SIGTERM to SIGKILL. Uncertain ownership is an error and unknown processes are left alone. When the workflow and its cleanup both fail, CY retains both errors. Process-capability and CPU tests exercise host facilities. A native GPU cleanup claim needs evidence from that environment.

Direct CY commands accept native device settings and run Hydra sweeps sequentially. They reject queue and autogpu controls and the cy-queue launcher. Concurrent scheduling and GPU reservation belong to the separate cy-queue package, which depends on CY and calls its admission validators. Their shared one-argument validation interface is a compatibility boundary. The paired check exercises it against the proposed versions of both packages.

<details>
<summary>Sources and verification</summary>

- Supervise native descendants using Linux process identity — [Ownership and signal rules](../src/clearml_yolo/adapters/runtime/process_tree.py) · [Execution boundary](../src/clearml_yolo/adapters/runtime/execution_lifecycle.py) · [Orphan and replacement scenarios](../tests/test_subreaper_process_tree.py) · [Host capabilities](../tests/test_process_capabilities.py) · [Technical reference](../DOCS.md#process-ownership) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/e1fe64ea7a053bb39daf4d8f477f63e4a6a8a236)
- Keep GPU scheduling in cy-queue — [Admission and wrapper validation](../src/clearml_yolo/entrypoints/hydra/validation.py) · [Legacy control cases](../tests/test_execution_controls.py) · [Direct execution scenarios](../tests/test_direct_execution.py) · [Queue guide](../docs/queue.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/ad6a8ec81901801c7bb434beed67405da81551ab)

</details>

## Console delivery and readable telemetry

Hydra commands redirect stdout and stderr to append-only journals in the invocation arena. Scalars append as individual JSON lines. A separate terminal mirror renders output, while an attach-only publisher tails the journals for ClearML and acknowledges flushed byte offsets. A stalled publisher leaves the local bytes available and the final barrier reports uncertain delivery. CY does not automatically resend an uncertain stream. Native output is captured as emitted.

The mirror and console worker translate recognized identifiers even when they straddle read chunks. The series registry keeps readable labels stable during an invocation and disambiguates collisions. Tables retain numeric column types. Raw journal bytes and scientific record identities remain available for comparison with the rendered view.

<details>
<summary>Sources and verification</summary>

- Journal native output before publishing it to ClearML — [Capture and scalar journal](../src/clearml_yolo/adapters/observability/capture.py) · [Publication barrier](../src/clearml_yolo/adapters/clearml/console.py) · [Publisher protocol](../src/clearml_yolo/adapters/clearml/console_worker.py) · [Capture and stalled publisher cases](../tests/test_console_capture.py) · [Published telemetry](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/063b670e3ecb0ee9dca9acaffa83244f40eb76e2)
- Render readable identifiers consistently across output surfaces — [Presentation rules](../src/clearml_yolo/core/presentation.py) · [ClearML adapters](../src/clearml_yolo/adapters/clearml/report.py) · [Readable output cases](../tests/test_readable_output.py) · [Table alias cases](../tests/test_clearml_report.py) · [Telemetry reference](../DOCS.md#diagnostics) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/8ca7d6bc37a0a28ba2c53eeb73c0b9d51ab58a99)

</details>

## Progress and diagnostics

The progress display adapts to the terminal and checks image counts against the expected population. Setting `CY_PROGRESS_FILE` lets a local observer, including cy-queue, follow fields such as `progress`, `iteration` and `task_url` in a workspace-local JSON file. Each update merges fields and atomically replaces the file so readers see complete snapshots. Independent writers have no shared transaction.

At `LOGURU_LEVEL=TRACE`, CY records operation start, completion, failure and interruption. A process-local watchdog writes heartbeats and bounded stack snapshots when the stack changes, through a separate stderr descriptor. Context fields are allow-listed and redacted. Snapshots identify source locations without inspecting local variables. The sampling interval is diagnostic, and leaves operation deadlines and exit status to their respective owners.

<details>
<summary>Sources and verification</summary>

- Trace long-running operations with a bounded watchdog — [Operation and watchdog rules](../src/clearml_yolo/adapters/observability/tracing.py) · [Lifecycle and watchdog tests](../tests/test_tracing.py) · [Environment setting](../docs/installation.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/8ca7d6bc37a0a28ba2c53eeb73c0b9d51ab58a99)
- Expose invocation progress to local observers — [Progress reporting](../src/clearml_yolo/adapters/observability/progress.py) · [JSON update](../src/clearml_yolo/adapters/observability/capture.py) · [Partial batches and local observers](../tests/test_console_capture.py) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/d96263c2444f6d69bd5e862a7acd1c0f01f6061f)

</details>
